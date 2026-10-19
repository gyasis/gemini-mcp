"""gemini — direct Gemini CLI (google-genai SDK, no MCP): ask, code-review, brainstorm, debug, grounded search, image gen/interpret, video watch, file store, and Deep Research with a persistent SQLite job/report DB.

Replaces the gemini-mcp server's 21 tools. Key is read from gemini-mcp/.env and never printed.
Research DB: ~/.local/share/gemini-cli/research.db (absolute; `gemini research import` salvages old deep_research.db copies).
Every command takes --json (machine-readable). Errors exit 1 with an actionable message.
Needs google-genai >= 2.9 (the `steps` schema), hence the gemini-mcp venv shebang.
"""
import argparse, base64, json, mimetypes, os, re, sqlite3, subprocess, sys, time, urllib.request, uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path.home() / "Documents/code/gemini-mcp/.env")
from google import genai  # noqa: E402
from google.genai import errors as gerrors, types  # noqa: E402

__version__ = "1.0.0"
FAST = "gemini-3-flash-preview"  # server.py's model for ask/review/brainstorm/debug/search/image-read/video
DR_MODEL = "deep-research-preview-04-2026"  # 12-2025 deprecated after 2026-10-22
IMAGE_MODELS = {"nano-banana-pro": "nano-banana-pro-preview", "nano-banana": "gemini-2.5-flash-image",
                "pro": "gemini-3-pro-image", "flash": "gemini-3.1-flash-image",
                "flash-lite": "gemini-3.1-flash-lite-image"}
DB_PATH = Path.home() / ".local/share/gemini-cli/research.db"
REPORT_DIR = Path.home() / ".local/share/gemini-cli/reports"
TERMINAL = {"completed", "failed", "cancelled", "incomplete", "budget_exceeded", "requires_action"}


class Fail(Exception):
    pass


# ---------------------------------------------------------------- client / retry / output
_CLIENT = None


def client():
    # One module-level Client: a temporary one is GC'd and closes its httpx session mid-call.
    global _CLIENT
    if _CLIENT is None:
        if not os.environ.get("GEMINI_API_KEY"):
            raise Fail("GEMINI_API_KEY missing (expected in ~/Documents/code/gemini-mcp/.env)")
        _CLIENT = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _CLIENT


def scrub(msg):
    k = os.environ.get("GEMINI_API_KEY")
    return msg.replace(k, "***") if k else msg


def call(fn, *a, **kw):
    """Retry network errors, 5xx and 429 (3 tries, backoff); other 4xx (incl. 404) are fatal."""
    for i in range(3):
        try:
            return fn(*a, **kw)
        except Fail:
            raise
        except gerrors.APIError as e:
            code = getattr(e, "code", 0) or 0
            if (code >= 500 or code == 429) and i < 2:
                time.sleep(2 * (i + 1) ** 2); continue
            raise Fail(scrub(f"Gemini API error HTTP {code}: {getattr(e, 'message', e)}"))
        except Exception as e:
            net = isinstance(e, (OSError, TimeoutError)) or type(e).__module__.split(".")[0] in ("httpx", "httpcore")
            if net and i < 2:
                time.sleep(2 * (i + 1) ** 2); continue
            raise Fail(scrub(f"{type(e).__name__}: {e}"))


def emit(a, text=None, **data):
    if a.json:
        print(json.dumps({"ok": True, **({"text": text} if text is not None else {}), **data}, default=str))
    elif text is not None:
        print(text)
    else:
        print(json.dumps(data, indent=2, default=str))


def enum_s(v):
    return str(getattr(v, "value", v)).lower().split(".")[-1] if v is not None else "unknown"


def gen(contents, model=FAST, temperature=None, tools=None):
    """generate_content; empty/blocked output is a FAILURE (finish_reason shown), never a result."""
    cfg = types.GenerateContentConfig(temperature=temperature, tools=tools)
    r = call(client().models.generate_content, model=model, contents=contents, config=cfg)
    try:
        text = r.text
    except Exception:
        text = None
    if not text:
        c0 = (r.candidates or [None])[0]
        raise Fail(f"{model} returned no text (finish_reason={getattr(c0, 'finish_reason', None)}, "
                   f"prompt_feedback={getattr(r, 'prompt_feedback', None)})")
    return r, text


def read_text(p):
    p = Path(p).expanduser()
    if not p.is_file():
        raise Fail(f"file not found: {p}")
    return p.read_text(errors="replace")


def stdin_if_dash(s):
    return sys.stdin.read() if s == "-" else s


# ---------------------------------------------------------------- simple text tools
def cmd_ask(a):
    prompt = stdin_if_dash(a.prompt)
    for f in a.file or []:
        prompt += f"\n\n--- {f} ---\n{read_text(f)}"
    _, t = gen(prompt, a.model, a.temperature)
    emit(a, t, model=a.model)


def cmd_code_review(a):
    code = "\n\n".join(f"# FILE: {f}\n{read_text(f)}" for f in a.files)
    focus = ", ".join(a.focus) if a.focus else "general code quality"
    prompt = f"""Please review this code with a focus on {focus}:
```
{code}
```

Provide specific, actionable feedback on:
1. Potential issues or bugs
2. Security concerns (if applicable)
3. Performance optimizations
4. Best practices
5. Code clarity and maintainability

Please be thorough but concise in your analysis."""
    _, t = gen(prompt, a.model, 0.2)
    emit(a, t, model=a.model)


def cmd_brainstorm(a):
    prompt = f"Let's brainstorm about: {a.topic}"
    if a.context:
        prompt += f"\n\nContext: {a.context}"
    prompt += "\n\nProvide creative ideas, alternatives, and considerations. Think outside the box and offer innovative solutions."
    _, t = gen(prompt, a.model, 0.7)
    emit(a, t, model=a.model)


def cmd_debug(a):
    prompt = f"I'm encountering a programming error and need help debugging.\n\nError Message:\n---\n{stdin_if_dash(a.error)}\n---"
    code = "\n\n".join(read_text(f) for f in a.file or [])
    if code:
        prompt += f"\n\nCode Snippet:\n---\n{code}\n---"
    if a.context:
        prompt += f"\n\nAdditional Context:\n---\n{a.context}\n---"
    prompt += """

Based on the error message and the provided information, please do the following:
1. **Analyze the Root Cause**: Explain what you believe is the most likely cause of this error.
2. **Identify the Problematic Code**: Pinpoint the specific line(s) or code block(s) that are causing the issue.
3. **Suggest a Solution**: Provide a corrected version of the code or clear, step-by-step instructions on how to fix the bug.
4. **Prevention**: Suggest how to prevent similar errors in the future."""
    _, t = gen(prompt, a.model, 0.2)
    emit(a, t, model=a.model)


def cmd_search(a):
    r, t = gen(stdin_if_dash(a.query), a.model, 0.3, tools=[types.Tool(google_search=types.GoogleSearch())])
    srcs = []
    try:
        for ch in r.candidates[0].grounding_metadata.grounding_chunks or []:
            if ch.web:
                srcs.append({"title": ch.web.title, "url": ch.web.uri})
    except Exception:
        pass
    text = t + ("\n\nSources:\n" + "\n".join(f"- {s['title']}: {s['url']}" for s in srcs) if srcs else "")
    emit(a, text, model=a.model, sources=srcs)


# ---------------------------------------------------------------- images
def image_part(src, idx, uploaded):
    if src.startswith("data:image/"):
        head, b64 = src.split(",", 1)
        return types.Part.from_bytes(data=base64.b64decode(b64), mime_type=head.split(";")[0].split(":")[1])
    if src.startswith(("http://", "https://")):
        with urllib.request.urlopen(src) as resp:
            data, mime = resp.read(), resp.headers.get_content_type()
        if not mime.startswith("image/"):
            mime = mimetypes.guess_type(src)[0] or "image/jpeg"
        return types.Part.from_bytes(data=data, mime_type=mime)
    p = Path(src).expanduser()
    if not p.is_file():
        raise Fail(f"image {idx} not found: {src}")
    mime = mimetypes.guess_type(str(p))[0]
    if not mime or not mime.startswith("image/"):
        raise Fail(f"image {idx} is not an image file: {src} (type {mime})")
    if p.stat().st_size > 20 * 1024 * 1024:  # inline limit -> File API (deleted after use)
        up = call(client().files.upload, file=str(p), config=types.UploadFileConfig(display_name=p.name))
        uploaded.append(up.name)
        return types.Part.from_uri(file_uri=up.uri, mime_type=mime)
    return types.Part.from_bytes(data=p.read_bytes(), mime_type=mime)


def cmd_image_interpret(a):
    uploaded = []
    try:
        parts = [image_part(s, i, uploaded) for i, s in enumerate(a.images, 1)]
        _, t = gen(parts + [a.prompt], a.model, a.temperature)
    finally:
        for n in uploaded:
            try: client().files.delete(name=n)
            except Exception: pass
    emit(a, t, model=a.model, images=len(a.images))


def cmd_image_gen(a):
    model_id = IMAGE_MODELS.get(a.model, a.model)
    parts = [a.prompt]
    for ref in a.ref or []:
        rp = Path(ref).expanduser()
        if not rp.is_file():
            raise Fail(f"reference image not found: {rp}")
        parts.append(types.Part.from_bytes(data=rp.read_bytes(), mime_type=mimetypes.guess_type(str(rp))[0] or "image/png"))
    r = call(client().models.generate_content, model=model_id, contents=parts,
             config=types.GenerateContentConfig(response_modalities=["IMAGE"]))
    out = Path(a.output).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    for cand in r.candidates or []:
        for part in (cand.content.parts if cand.content else []):
            inl = getattr(part, "inline_data", None)
            if inl and getattr(inl, "data", None):
                out.write_bytes(inl.data)
                emit(a, f"Image generated with {model_id}\nSaved to: {out} ({out.stat().st_size:,} bytes)\n"
                        "Look at it before using it.", model=model_id, path=str(out), bytes=out.stat().st_size)
                return
    c0 = (r.candidates or [None])[0]
    said = " | ".join(p.text[:300] for p in (c0.content.parts if c0 and c0.content else []) if getattr(p, "text", None))
    raise Fail(f"{model_id} returned no image (finish_reason={getattr(c0, 'finish_reason', None)}, "
               f"prompt_feedback={getattr(r, 'prompt_feedback', None)}, model said: {said}). "
               "Prompt may be refused or the model lacks image output; try --model pro.")


# ---------------------------------------------------------------- video + files
def is_yt(u):
    return u.startswith(("http://", "https://")) and ("youtube.com" in u or "youtu.be" in u)


def cmd_video_watch(a):
    c, cleanup = client(), None
    if a.file_uri:
        fi = call(c.files.get, name=a.file_uri)
        if enum_s(fi.state) != "active":
            raise Fail(f"{a.file_uri} not ready (state {fi.state}); see `gemini files status {a.file_uri}`")
        part, label = types.Part.from_uri(file_uri=fi.uri, mime_type=fi.mime_type), f"pre-uploaded {a.file_uri}"
    elif not a.input:
        raise Fail("give a YouTube URL / local video path, or --file-uri files/xxx")
    elif is_yt(a.input):
        part, label = types.Part.from_uri(file_uri=a.input, mime_type="video/mp4"), "YouTube"
    else:
        p = Path(a.input).expanduser()
        if not p.is_file():
            raise Fail(f"{a.input} is neither a YouTube URL nor an existing file")
        mime = mimetypes.guess_type(str(p))[0]
        if not mime or not mime.startswith("video/"):
            raise Fail(f"{p} is not a video file (type {mime})")
        mb = p.stat().st_size / 1048576
        if mb <= 20:
            part, label = types.Part.from_bytes(data=p.read_bytes(), mime_type=mime), f"{p.name} {mb:.1f}MB inline"
        else:
            up = call(c.files.upload, file=str(p), config=types.UploadFileConfig(display_name=p.name))
            if a.upload_only:
                emit(a, None, mode="upload_only", file_name=up.name, file_uri=up.uri, state=enum_s(up.state), size_mb=round(mb, 2))
                return
            t0 = time.time()
            while enum_s(up.state) == "processing" and time.time() - t0 < a.max_wait:
                time.sleep(2); up = call(c.files.get, name=up.name)
            if enum_s(up.state) != "active":
                raise Fail(f"upload {up.name} state {up.state} after {int(time.time() - t0)}s; check `gemini files status {up.name}`")
            part, label, cleanup = types.Part.from_uri(file_uri=up.uri, mime_type=mime), f"{p.name} {mb:.1f}MB uploaded", up.name
    if not a.prompt:
        raise Fail("prompt required")
    try:
        _, t = gen([part, a.prompt], a.model, 0.5)
    finally:
        if cleanup:
            try: c.files.delete(name=cleanup)
            except Exception: pass
    emit(a, t, model=a.model, source=label)


def file_row(f):
    ct = getattr(f, "create_time", None)
    age = (datetime.now(timezone.utc) - ct).total_seconds() / 3600 if isinstance(ct, datetime) else 0
    sz = getattr(f, "size_bytes", 0) or 0
    return {"file_name": f.name, "display_name": getattr(f, "display_name", f.name), "state": enum_s(f.state),
            "mime_type": getattr(f, "mime_type", "unknown"), "size_mb": round(sz / 1048576, 2), "uploaded": str(ct),
            "age_hours": round(age, 1), "expires_in_hours": round(48 - age, 1), "expires_soon": 48 - age < 6,
            "ready": enum_s(f.state) == "active", "uri": getattr(f, "uri", None)}


def cmd_files_list(a):
    allf = call(lambda: list(client().files.list(config={"page_size": a.max})))
    m = a.mime

    def ok(f):
        mt = getattr(f, "mime_type", "") or ""
        return not m or (mt.startswith(m[:-2]) if m.endswith("/*") else mt == m)
    rows = [file_row(f) for f in allf if ok(f)]
    key = {"upload_date": lambda x: x["age_hours"], "name": lambda x: x["display_name"],
           "expiring": lambda x: x["expires_in_hours"], "size": lambda x: -x["size_mb"]}[a.sort]
    rows.sort(key=key)
    res = {"total_files": len(allf), "filtered_count": len(rows), "storage_used_mb": round(sum(r["size_mb"] for r in rows), 2),
           "expiring_soon_count": sum(r["expires_soon"] for r in rows), "files": rows,
           "limits": "48h retention, 20GB/project, 2GB/file"}
    if a.json:
        emit(a, None, **res)
    else:
        print(f"{res['total_files']} file(s), {res['storage_used_mb']} MB, {res['expiring_soon_count']} expiring <6h")
        for r in rows:
            print(f"{r['file_name']}  {r['state']:10} {r['mime_type']:16} {r['size_mb']:>8}MB  age {r['age_hours']}h  {r['display_name']}")


def cmd_files_status(a):
    emit(a, None, **file_row(call(client().files.get, name=a.name)))


def cmd_files_last_video(a):
    vids = [f for f in call(lambda: list(client().files.list(config={"page_size": 100})))
            if (getattr(f, "mime_type", "") or "").startswith("video/")]
    if not vids:
        emit(a, None, found=False, message="no videos in storage")
        return
    vids.sort(key=lambda f: str(getattr(f, "create_time", "")), reverse=True)
    emit(a, None, found=True, **file_row(vids[0]))


def cmd_files_delete(a):
    info = file_row(call(client().files.get, name=a.name))
    if not a.yes:
        emit(a, None, action="confirmation_required", message=f"re-run with --yes to delete {a.name} permanently", **info)
        return
    call(client().files.delete, name=a.name)
    emit(a, None, action="deleted", **info)


def cmd_info(a):
    d = {"version": __version__, "google_genai": getattr(genai, "__version__", "?"),
         "api_key_present": bool(os.environ.get("GEMINI_API_KEY")), "default_model": FAST, "deep_research_model": DR_MODEL,
         "image_models": IMAGE_MODELS, "research_db": str(DB_PATH), "research_db_exists": DB_PATH.exists()}
    try:
        next(iter(client().models.list(config={"page_size": 1})))
        d["api_reachable"] = True
    except Exception as e:
        d["api_reachable"] = False
        d["api_error"] = scrub(str(e))[:200]
    emit(a, None, **d)


# ---------------------------------------------------------------- research DB
SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs(
  interaction_id TEXT PRIMARY KEY, task_id TEXT, model TEXT, query TEXT, status TEXT,
  created_at TEXT, updated_at TEXT, completed_at TEXT, usage_json TEXT, cost_usd REAL, error TEXT);
CREATE INDEX IF NOT EXISTS idx_jobs_task ON jobs(task_id);
CREATE TABLE IF NOT EXISTS reports(
  interaction_id TEXT PRIMARY KEY, report_md TEXT, sources_json TEXT, saved_at TEXT,
  FOREIGN KEY(interaction_id) REFERENCES jobs(interaction_id));
"""
JOB_COLS = ["interaction_id", "task_id", "model", "query", "status", "created_at", "updated_at", "completed_at",
            "usage_json", "cost_usd", "error"]


def now():
    return datetime.now(timezone.utc).isoformat()


def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript(SCHEMA)
    return c


def find_job(c, ident):
    for q, p in (("interaction_id=?", ident), ("task_id=?", ident), ("interaction_id LIKE ?", ident + "%"),
                 ("task_id LIKE ?", ident + "%")):
        rows = c.execute(f"SELECT * FROM jobs WHERE {q}", (p,)).fetchall()
        if len(rows) == 1:
            return rows[0]
        if len(rows) > 1:
            raise Fail(f"ambiguous id {ident!r}: {len(rows)} jobs match; use more characters")
    return None


def upsert_job(c, rec):
    """Merge rec into the existing row (matched by interaction_id, else task_id). Existing non-empty values win,
    except status/updated_at/completed_at/usage/error, which take the incoming (fresher) value. A row without an
    interaction_id gets the synthetic key 'task:<task_id>' and is re-keyed if a real id arrives later."""
    row = None
    if rec.get("interaction_id"):
        row = c.execute("SELECT * FROM jobs WHERE interaction_id=?", (rec["interaction_id"],)).fetchone()
    if not row and rec.get("task_id"):
        row = c.execute("SELECT * FROM jobs WHERE task_id=?", (rec["task_id"],)).fetchone()
    if not row:
        rec = {**rec, "interaction_id": rec.get("interaction_id") or f"task:{rec.get('task_id') or uuid.uuid4()}"}
        c.execute(f"INSERT INTO jobs({','.join(JOB_COLS)}) VALUES({','.join('?' * len(JOB_COLS))})",
                  [rec.get(k) for k in JOB_COLS])
        return rec["interaction_id"]
    old, new, fresh = dict(row), {}, ("status", "updated_at", "completed_at", "usage_json", "error")
    for k in JOB_COLS[1:]:
        v = rec.get(k)
        if v not in (None, "") and (old.get(k) in (None, "") or k in fresh):
            new[k] = v
    iid = old["interaction_id"]
    if rec.get("interaction_id") and rec["interaction_id"] != iid and iid.startswith("task:"):
        c.execute("UPDATE reports SET interaction_id=? WHERE interaction_id=?", (rec["interaction_id"], iid))
        c.execute("UPDATE jobs SET interaction_id=? WHERE interaction_id=?", (rec["interaction_id"], iid))
        iid = rec["interaction_id"]
    if new:
        c.execute(f"UPDATE jobs SET {','.join(k + '=?' for k in new)} WHERE interaction_id=?", [*new.values(), iid])
    return iid


def save_report(c, iid, text, sources):
    old = c.execute("SELECT report_md FROM reports WHERE interaction_id=?", (iid,)).fetchone()
    if old and old["report_md"] and len(old["report_md"]) >= len(text):
        return False  # never replace with a shorter/equal text
    c.execute("INSERT OR REPLACE INTO reports VALUES(?,?,?,?)", (iid, text, json.dumps(sources), now()))
    return True


# ---------------------------------------------------------------- research (API side)
def extract(ix):
    """(report_text, sources) from an Interaction in the `steps` schema."""
    items = [i for s in (getattr(ix, "steps", None) or []) if getattr(s, "type", None) == "model_output"
             for i in (getattr(s, "content", None) or []) if getattr(i, "text", None)]
    # Join every model_output part: `output_text` holds only the LAST one, and a long report
    # arrives split across several (2026-10-19: 10.9K part 1 + 24.2K part 2, output_text = part 2 only)
    text = "".join(i.text for i in items) or getattr(ix, "output_text", None) or ""
    seen, srcs = set(), []
    for i in items:
        for an in getattr(i, "annotations", None) or []:
            u = getattr(an, "url", "") or ""
            if getattr(an, "type", None) == "url_citation" and u and u not in seen:
                seen.add(u); srcs.append({"title": getattr(an, "title", "") or "Source", "url": u})
    return text, srcs


def snap(ix):
    created, el = getattr(ix, "created", None), None
    if created:
        cdt = created if isinstance(created, datetime) else datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        el = round((datetime.now(timezone.utc) - cdt).total_seconds() / 60, 1)
    steps = getattr(ix, "steps", None) or []
    return {"status": enum_s(getattr(ix, "status", None)), "elapsed_min": el, "n_steps": len(steps),
            "step_types": [getattr(s, "type", None) for s in steps][-12:], "report_chars": len(extract(ix)[0])}


def usage_json(ix):
    u = getattr(ix, "usage", None)
    if u is None:
        return None
    try:
        return json.dumps(u.model_dump(mode="json", exclude_none=True))
    except Exception:
        return json.dumps({"repr": str(u)[:500]})


def refresh(c, ident):
    """Fetch the interaction from Google, write REAL status/usage to the DB, save any report text at once.
    Returns (interaction_id, snapshot, report_saved)."""
    row = find_job(c, ident)
    if row and row["interaction_id"].startswith("task:"):
        raise Fail(f"job {ident} has no interaction_id (never reached Google); nothing to fetch")
    ix = call(client().interactions.get, row["interaction_id"] if row else ident)
    s = snap(ix)
    created, inp = getattr(ix, "created", None), getattr(ix, "input", None)
    iid = upsert_job(c, {
        "interaction_id": ix.id, "task_id": row["task_id"] if row else str(uuid.uuid4()), "status": s["status"],
        "updated_at": now(), "usage_json": usage_json(ix),
        "model": str(getattr(ix, "agent", None) or getattr(ix, "model", None) or "") or None,
        "created_at": created.isoformat() if isinstance(created, datetime) else (str(created) if created else None),
        "completed_at": now() if s["status"] in TERMINAL else None, "query": inp if isinstance(inp, str) else None})
    text, srcs = extract(ix)
    saved = bool(text) and save_report(c, iid, text, srcs)
    c.commit()
    return iid, s, saved


def write_report_file(c, iid, out=None):
    r = c.execute("SELECT report_md FROM reports WHERE interaction_id=?", (iid,)).fetchone()
    if not r or not r["report_md"]:
        return None
    p = Path(out).expanduser() if out else REPORT_DIR / f"{iid[-12:]}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(r["report_md"])
    return str(p)


def cmd_r_start(a):
    q = stdin_if_dash(a.query)
    if not 3 <= len(q) <= 10000:
        raise Fail("query must be 3-10000 characters")
    ix = call(client().interactions.create, input=q, agent=a.model, background=True, store=True)
    c, tid = db(), str(uuid.uuid4())
    upsert_job(c, {"interaction_id": ix.id, "task_id": tid, "model": a.model, "query": q, "status": enum_s(ix.status),
                   "created_at": now(), "updated_at": now()})
    c.commit()
    emit(a, ix.id, interaction_id=ix.id, task_id=tid, model=a.model, status=enum_s(ix.status))


def cmd_r_status(a):
    iid, s, saved = refresh(db(), a.id)
    emit(a, json.dumps({"id": iid, **s, "report_saved_to_db": saved}), id=iid, report_saved_to_db=saved, **s)


def cmd_r_get(a):
    c = db()
    iid, s, _ = refresh(c, a.id)
    path = write_report_file(c, iid, a.out)
    if not path:
        raise Fail(f"no report text yet — {json.dumps(s)}")
    emit(a, json.dumps({"id": iid, "report": path, **s}), id=iid, report=path, **s)


def cmd_r_wait(a):
    c = db()
    row = find_job(c, a.id)
    ident = row["interaction_id"] if row else a.id
    while True:
        iid, s, _ = refresh(c, ident)
        print(json.dumps(s), file=sys.stderr, flush=True)
        if s["status"] in TERMINAL:
            break
        if s["elapsed_min"] is not None and s["elapsed_min"] >= a.max_min:
            call(client().interactions.cancel, iid)
            _, _, saved = refresh(c, iid)  # keep whatever exists
            c.execute("UPDATE jobs SET error=? WHERE interaction_id=?", (f"cancelled by CLI at {a.max_min} min cap", iid))
            c.commit()
            raise Fail(f"cancelled on Google after {s['elapsed_min']} min (cap {a.max_min}); partial report saved: {saved}")
        time.sleep(a.interval)
    path = write_report_file(c, iid, a.out)
    if s["status"] != "completed":
        raise Fail(f"ended with status {s['status']}" + (f"; partial report at {path}" if path else ""))
    emit(a, json.dumps({"id": iid, "report": path, **s}), id=iid, report=path, **s)


def cmd_r_cancel(a):
    c = db()
    row = find_job(c, a.id)
    iid = row["interaction_id"] if row else a.id
    r = call(client().interactions.cancel, iid)
    st, saved = enum_s(getattr(r, "status", None)), False
    try:
        _, s, saved = refresh(c, iid)  # real status + partial text
        st = s["status"]
    except Fail:
        pass
    emit(a, json.dumps({"id": iid, "status": st, "partial_report_saved": saved}), id=iid, status=st, partial_report_saved=saved)


def cmd_r_resume(a):
    """Re-attach to an interrupted job: pull real status + whatever report exists. Does not re-run research."""
    c = db()
    iid, s, _ = refresh(c, a.id)
    path = write_report_file(c, iid)
    hint = ("still running: use `gemini research wait`" if s["status"] not in TERMINAL else
            "finished" if path else "terminal with no report text; start a new run if needed")
    emit(a, json.dumps({"id": iid, "report": path, "hint": hint, **s}), id=iid, report=path, hint=hint, **s)


def cmd_r_list(a):
    q, p = "SELECT j.*, length(r.report_md) AS report_chars FROM jobs j LEFT JOIN reports r USING(interaction_id)", []
    if a.status:
        q += " WHERE j.status=?"; p.append(a.status)
    rows = [dict(r) for r in db().execute(q + " ORDER BY COALESCE(j.created_at,j.updated_at) DESC LIMIT ?", [*p, a.limit])]
    if a.json:
        emit(a, None, count=len(rows), jobs=rows)
    else:
        for r in rows:
            print(f"{(r['created_at'] or '')[:16]}  {r['status'] or '?':14} rep={r['report_chars'] or 0:>7}  "
                  f"{r['interaction_id'][:22]:22} {(r['query'] or '')[:60]!r}")


def cmd_r_estimate(a):
    """Heuristic estimate, ported from gemini-mcp deep_research/cost_estimator.py (not a billing quote)."""
    q = stdin_if_dash(a.query)
    ql, w = q.lower(), q.split()
    cnt = lambda ks: sum(k in ql for k in ks)  # noqa: E731
    wc, qm = len(w), q.count("?")
    score = (3 if wc > 50 else 2 if wc > 25 else 1 if wc > 10 else 0)
    score += min(cnt(["comprehensive", "detailed", "in-depth", "thorough", "extensive", "analysis", "compare", "contrast",
                      "evaluate", "synthesize", "implications", "geopolitical", "historical", "trends", "forecast"]), 4)
    score += min(cnt(["and", "vs", "versus", "between", "across", "multiple", "different", "various", "compare", "relation"]), 3)
    score += min(cnt(["history", "evolution", "timeline", "past", "future", "trends", "forecast", "prediction",
                      "development", "changes"]), 2)
    score += 2 if qm > 2 else 1 if qm > 1 else 0
    score += min(sum(1 for i, x in enumerate(w[1:], 1) if x and x[0].isupper() and not w[i - 1].endswith((".", "?", "!"))) // 2, 2)
    cx = "complex" if score >= 8 else "medium" if score >= 4 else "simple"
    dur = {"simple": (0.5, 3, 1), "medium": (3, 20, 8), "complex": (15, 60, 35)}[cx]
    usd = {"simple": (0.10, 0.50, 0.25), "medium": (0.50, 2.00, 1.00), "complex": (1.50, 6.00, 3.00)}[cx]
    emit(a, None, complexity=cx, minutes=dict(zip(("min", "max", "likely"), dur)), usd=dict(zip(("min", "max", "likely"), usd)),
         note="heuristic from gemini-mcp cost_estimator, not a quote")


def cmd_r_export(a):
    c = db()
    row = find_job(c, a.id)
    if not row:
        raise Fail(f"job {a.id} not in DB (run `gemini research get {a.id}` first)")
    rep = c.execute("SELECT * FROM reports WHERE interaction_id=?", (row["interaction_id"],)).fetchone()
    if not rep or not rep["report_md"]:
        raise Fail("no report stored for this job")
    q = row["query"] or ""
    title = (q.strip().splitlines() or ["research"])[0][:80]
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50] or "research"
    out = Path(a.out).expanduser() if a.out else Path.home() / "Documents/generated" / f"{slug}-{row['interaction_id'][-8:]}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    md = [f"# {title}", "", f"**Research ID:** `{row['task_id']}`  ", f"**Interaction:** `{row['interaction_id']}`  ",
          f"**Query:** {q}  ", f"**Status:** {row['status']}  ", f"**Created:** {row['created_at']}  ",
          f"**Completed:** {row['completed_at']}  ", f"**Model:** {row['model']}", "", "---", "", "## Research Report", "",
          rep["report_md"]]
    srcs = json.loads(rep["sources_json"] or "[]")
    if srcs:
        md += ["", "---", "", "## Sources", ""] + [f"{i}. [{s.get('title') or s.get('url')}]({s.get('url')})" for i, s in enumerate(srcs, 1)]
    out.write_text("\n".join(md) + "\n")
    emit(a, str(out), path=str(out), bytes=out.stat().st_size)


# ---------------------------------------------------------------- research import (salvage)
def find_db_copies():
    # prune dependency/cache trees: a bare `find $HOME` takes minutes
    prune = ["-name", "node_modules", "-o", "-name", ".git", "-o", "-name", ".cache", "-o", "-name", "site-packages",
             "-o", "-name", "miniconda3", "-o", "-name", ".local", "-o", "-name", ".npm", "-o", "-name", "recovery*"]
    r = subprocess.run(["find", str(Path.home()), "-xdev", "(", *prune, ")", "-prune", "-o", "-name", "deep_research.db",
                        "-type", "f", "-print"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    return sorted(set(r.stdout.split()))


def report_from_md(text):
    m = re.search(r"## Research Report\s*\n(.*?)(?:\n---\s*\n+## Sources|\Z)", text, re.S)
    return (m.group(1) if m else text).strip()


def cmd_r_import(a):
    c = db()
    st = {"dbs_scanned": 0, "dbs_skipped": [], "tasks_seen": 0, "reports_seen": 0, "md_files": 0, "md_reports_added": 0}
    before_j = c.execute("SELECT count(*) FROM jobs").fetchone()[0]
    before_r = c.execute("SELECT count(*) FROM reports WHERE report_md!=''").fetchone()[0]
    for p in map(Path, a.db or find_db_copies()):
        try:
            if p.resolve() == DB_PATH.resolve():
                continue
            src = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            src.row_factory = sqlite3.Row
            tasks = src.execute("SELECT * FROM research_tasks").fetchall()
            res = {r["task_id"]: r for r in src.execute("SELECT * FROM research_results")}
            src.close()
        except Exception as e:
            st["dbs_skipped"].append({"db": str(p), "why": str(e)[:80]}); continue
        st["dbs_scanned"] += 1
        for t in tasks:
            st["tasks_seen"] += 1
            usage = json.dumps({"tokens_input": t["tokens_input"], "tokens_output": t["tokens_output"]}) \
                if (t["tokens_input"] or t["tokens_output"]) else None
            iid = upsert_job(c, {"interaction_id": t["interaction_id"], "task_id": t["task_id"], "model": t["model"],
                                 "query": t["query"], "status": t["status"], "created_at": t["created_at"],
                                 "updated_at": t["updated_at"], "completed_at": t["completed_at"], "usage_json": usage,
                                 "cost_usd": t["cost_usd"] or None, "error": t["error_message"]})
            r = res.get(t["task_id"])
            if r and r["report_markdown"]:
                st["reports_seen"] += 1
                save_report(c, iid, r["report_markdown"], json.loads(r["sources_json"] or "[]"))
        c.commit()
    jl = Path.home() / ".local/share/gemini-research/jobs.jsonl"  # the first gemini-research tool's log
    if jl.exists():
        for line in jl.read_text().splitlines():
            try:
                j = json.loads(line)
                upsert_job(c, {"interaction_id": j["id"], "task_id": str(uuid.uuid4()), "model": j.get("model"),
                               "query": j.get("query"), "created_at": j.get("started")})
            except Exception:
                pass
        c.commit()
    for d in (Path.home() / "Documents/code/gemini-mcp/research_reports", Path.home() / ".local/share/gemini-research/reports"):
        for f in (d.rglob("*.md") if d.is_dir() else []):
            st["md_files"] += 1
            txt = f.read_text(errors="replace")
            m = re.search(r"Research ID:\*\*\s*`([0-9a-f-]{36})`", txt)
            row = c.execute("SELECT interaction_id FROM jobs WHERE task_id=?", (m.group(1),)).fetchone() if m else \
                c.execute("SELECT interaction_id FROM jobs WHERE interaction_id LIKE ?", (f"%{f.stem}",)).fetchone()
            if row and save_report(c, row["interaction_id"], report_from_md(txt), []):
                st["md_reports_added"] += 1
    c.commit()
    st["unique_jobs"] = c.execute("SELECT count(*) FROM jobs").fetchone()[0]
    st["jobs_added"] = st["unique_jobs"] - before_j
    st["reports_in_db"] = c.execute("SELECT count(*) FROM reports WHERE report_md!=''").fetchone()[0]
    st["reports_added"] = st["reports_in_db"] - before_r
    st["db"] = str(DB_PATH)
    emit(a, None, **st)


# ---------------------------------------------------------------- parser
def build():
    com = argparse.ArgumentParser(add_help=False)
    com.add_argument("--json", action="store_true", help="machine-readable JSON output")
    p = argparse.ArgumentParser(prog="gemini", description="Direct Gemini CLI (google-genai SDK, no MCP).")
    p.add_argument("--version", action="version", version=f"gemini {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    def leaf(parent, name, fn, help):
        x = parent.add_parser(name, parents=[com], help=help, description=help)
        x.set_defaults(fn=fn)
        return x

    def model(x, d=FAST):
        x.add_argument("--model", "-m", default=d, help=f"model id (default {d})")

    x = leaf(sub, "ask", cmd_ask, "ask_gemini: general question ('-' reads the prompt from stdin)")
    x.add_argument("prompt"); model(x); x.add_argument("--temperature", "-t", type=float, default=0.5)
    x.add_argument("--file", "-f", action="append", help="append a text file to the prompt (repeatable)")
    x = leaf(sub, "code-review", cmd_code_review, "gemini_code_review: review source files (temp 0.2)")
    x.add_argument("files", nargs="+"); x.add_argument("--focus", action="append", help="focus area (repeatable), e.g. security"); model(x)
    x = leaf(sub, "brainstorm", cmd_brainstorm, "gemini_brainstorm: creative ideas (temp 0.7)")
    x.add_argument("topic"); x.add_argument("--context", default=""); model(x)
    x = leaf(sub, "debug", cmd_debug, "gemini_debug: diagnose an error (temp 0.2)")
    x.add_argument("--error", "-e", required=True, help="error/stack trace, or '-' for stdin")
    x.add_argument("--file", "-f", action="append", help="relevant source file (repeatable)")
    x.add_argument("--context", default=""); model(x)
    x = leaf(sub, "search", cmd_search, "gemini_research: Google-Search-grounded answer (temp 0.3) with sources")
    x.add_argument("query"); model(x)

    im = sub.add_parser("image", help="image generation / interpretation").add_subparsers(dest="sub", required=True, metavar="ACTION")
    x = leaf(im, "gen", cmd_image_gen, "generate_image: write an image (models: " + ", ".join(IMAGE_MODELS) + " or raw id)")
    x.add_argument("prompt"); x.add_argument("--output", "-o", required=True)
    x.add_argument("--model", "-m", default="nano-banana-pro"); x.add_argument("--ref", action="append", help="reference image (repeatable)")
    x = leaf(im, "interpret", cmd_image_interpret, "interpret_image: IMG... [QUESTION]; image = path, URL or data:image base64")
    x.add_argument("images", nargs="+", help="image(s), optionally followed by the question")
    x.add_argument("--prompt", "-p", default="Describe this image in detail")
    x.add_argument("--temperature", "-t", type=float, default=0.5); model(x)
    vd = sub.add_parser("video", help="video analysis").add_subparsers(dest="sub", required=True, metavar="ACTION")
    x = leaf(vd, "watch", cmd_video_watch, "watch_video: YouTube URL or local file (>20MB via File API) + question")
    x.add_argument("input", nargs="?"); x.add_argument("prompt", nargs="?", default="")
    x.add_argument("--file-uri", help="analyze an already-uploaded files/xxx"); x.add_argument("--upload-only", action="store_true")
    x.add_argument("--max-wait", type=int, default=300, help="seconds to wait for File API processing"); model(x)

    fl = sub.add_parser("files", help="Gemini File API store (48h retention)").add_subparsers(dest="sub", required=True, metavar="ACTION")
    x = leaf(fl, "list", cmd_files_list, "list_uploaded_files")
    x.add_argument("--mime", help="e.g. video/* or image/png")
    x.add_argument("--sort", default="upload_date", choices=["upload_date", "size", "name", "expiring"])
    x.add_argument("--max", type=int, default=20)
    x = leaf(fl, "status", cmd_files_status, "check_file_status"); x.add_argument("name", help="files/abc123")
    x = leaf(fl, "delete", cmd_files_delete, "delete_uploaded_file (dry-run unless --yes)")
    x.add_argument("name"); x.add_argument("--yes", action="store_true", help="actually delete")
    leaf(fl, "last-video", cmd_files_last_video, "get_last_uploaded_video")
    leaf(sub, "info", cmd_info, "server_info: version, key present (never shown), connectivity, models, DB path")

    rs = sub.add_parser("research", help=f"Deep Research (jobs/reports kept in {DB_PATH})").add_subparsers(dest="sub", required=True, metavar="ACTION")
    idh = "interaction id, task id, or unique prefix"
    x = leaf(rs, "start", cmd_r_start, "start_deep_research: start in background, print interaction id (STARTS A PAID RUN)")
    x.add_argument("query"); x.add_argument("--model", "-m", default=DR_MODEL)
    x = leaf(rs, "status", cmd_r_status, "check_research_status: REAL Google status; updates DB"); x.add_argument("id", help=idh)
    x = leaf(rs, "wait", cmd_r_wait, "poll to a terminal state; at the cap it CANCELS on Google and saves partial text")
    x.add_argument("id", help=idh); x.add_argument("--max-min", type=float, default=65); x.add_argument("--interval", type=int, default=30)
    x.add_argument("--out", help="report file path")
    x = leaf(rs, "get", cmd_r_get, "get_research_results: save report to DB and a file, print the path")
    x.add_argument("id", help=idh); x.add_argument("--out", help="report path (default ~/.local/share/gemini-cli/reports/<tail>.md)")
    x = leaf(rs, "cancel", cmd_r_cancel, "cancel_research: cancel on Google, save partial text"); x.add_argument("id", help=idh)
    x = leaf(rs, "list", cmd_r_list, "list_research_tasks: read the DB")
    x.add_argument("--status"); x.add_argument("--limit", type=int, default=50)
    x = leaf(rs, "resume", cmd_r_resume, "resume_research: re-attach, refresh status, save any report (no re-run)"); x.add_argument("id", help=idh)
    x = leaf(rs, "estimate", cmd_r_estimate, "estimate_research_cost: heuristic duration/cost"); x.add_argument("query")
    x = leaf(rs, "export", cmd_r_export, "save_research_to_markdown: report + metadata + sources as .md")
    x.add_argument("id", help=idh); x.add_argument("--out", help="default ~/Documents/generated/<slug>.md")
    x = leaf(rs, "import", cmd_r_import, "salvage old gemini-mcp deep_research.db copies + MD reports (idempotent)")
    x.add_argument("--db", action="append", help="specific DB (repeatable); default: find all under $HOME")
    return p


def main():
    a = build().parse_args()
    # `gemini image interpret IMG "question"`: a trailing non-path positional is the question
    if a.fn is cmd_image_interpret and len(a.images) > 1 and a.prompt == "Describe this image in detail":
        last = a.images[-1]
        if not last.startswith(("http://", "https://", "data:")) and not Path(last).expanduser().exists():
            a.prompt = a.images.pop()
    try:
        a.fn(a)
    except Fail as e:
        print(json.dumps({"ok": False, "error": str(e)}) if a.json else f"gemini: error: {e}", file=None if a.json else sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
