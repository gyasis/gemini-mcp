# Implementation Plan: Hybrid Deep Research System

**Branch**: `001-hybrid-deep-research` | **Date**: 2025-12-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-hybrid-deep-research/spec.md`

## Summary

Add 6 new MCP tools to the Gemini MCP Server wrapping Google's Gemini Deep Research API with a hybrid synchronous-to-asynchronous execution model, native OS notifications, and permanent Markdown file persistence.

**Key Architecture Decision**: SQLite + asyncio as default backend (zero external dependencies), preserving the current "just run `uv run python server.py`" simplicity. Optional Redis + Celery support can be added in future versions.

Gemini Deep Research API natively handles multi-hop reasoning - we wrap it, not re-implement it.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastMCP 2.0, google-generativeai, notify-py, Jinja2
**Storage**: SQLite (task state), Markdown files (permanent reports)
**Testing**: pytest with mocked Gemini API responses
**Target Platform**: Linux/macOS/Windows (cross-platform MCP server)
**Project Type**: Single project with supporting module
**Performance Goals**: <30s async switch, <100ms status check, <2s notification delivery
**Constraints**: Single server.py file (per Constitution Principle II), zero external services required
**Scale/Scope**: 3+ concurrent async research tasks via asyncio

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. FastMCP Decorator-First | PASS | All 6 tools use `@mcp.tool()` decorator |
| II. Single-File Server | PASS | Tools in server.py, helpers in `deep_research/` module |
| III. Graceful Degradation | PASS | Check `GEMINI_AVAILABLE` before API calls |
| IV. Comprehensive Docs | PASS | All tools have detailed docstrings |
| V. Semantic Versioning | PASS | Increment to next MINOR version |
| VI. Agent Nesting | PASS | Asyncio tasks isolate long-running operations |
| VII. Wave-Based Execution | PASS | Task phases respect dependencies with file locks |

## Project Structure

### Documentation (this feature)

```text
specs/001-hybrid-deep-research/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── spec.md              # Feature specification
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── tools.md         # MCP tool contracts
└── quickstart.md        # Phase 1 output
```

### Source Code (repository root)

```text
gemini-mcp/
├── server.py                    # MODIFY: Add 6 @mcp.tool() functions + startup recovery
├── deep_research/              # CREATE: New module
│   ├── __init__.py
│   ├── engine.py              # DeepResearchEngine wrapping Gemini Deep Research API
│   ├── state_manager.py       # SQLite state persistence
│   ├── notification.py        # Native OS notifications (notify-py with fallback)
│   ├── cost_estimator.py      # Cost/duration estimation
│   ├── storage.py             # Markdown file persistence
│   ├── background.py          # Asyncio background task management
│   └── templates/
│       └── research_report.md.j2  # Jinja2 template
├── research_reports/          # CREATE: Output directory for MD files
├── deep_research.db           # AUTO-CREATED: SQLite database (gitignored)
└── requirements.txt           # MODIFY: Add minimal dependencies

tests/
├── unit/
│   ├── test_engine.py
│   ├── test_state_manager.py
│   ├── test_notification.py
│   └── test_storage.py
├── integration/
│   └── test_deep_research_flow.py
└── contract/
    └── test_tool_contracts.py
```

**Structure Decision**: Single project layout with `deep_research/` module for helpers (justified by >100 lines per module). Server.py contains all 6 `@mcp.tool()` decorated functions per Constitution Principle II.

## Complexity Tracking

> No Constitution violations requiring justification.

## Technical Design

### Architecture Overview

```
User Query
    │
start_deep_research() ─────────────────────────────┐
    │                                               │
[Try Sync - 30s timeout]                           │
    │                                               │
Gemini Deep Research API                           │
    │                                               │
┌──────────────────────────────────────────────────┘
│ If sync completes → Return results immediately
│ If timeout/async → Save to SQLite, spawn asyncio task
└─────────────────────────────────────────────────────┘
                                                    │
                                   Asyncio Background Task
                                   ┌───────────────────┐
                                   │ Poll Gemini API   │
                                   │ Update SQLite     │
                                   │ Track Progress    │
                                   └───────────────────┘
                                           │
                                           ▼
                              Desktop Notification (notify-py)
                                           │
                                           ▼
                              Auto-save to Markdown (Jinja2)
```

### Key Components

#### 1. DeepResearchEngine (`deep_research/engine.py`)

Wraps Gemini Deep Research API:
- Uses `client.aio.models.generate_content()` with deep research model
- Handles streaming updates when available
- Tracks token usage and cost

```python
class DeepResearchEngine:
    DEFAULT_MODEL = "deep-research-pro-preview-12-2025"

    def __init__(self, client: genai.Client):
        self.client = client

    async def start_research(self, query: str, model: str = None) -> dict:
        """Start research, returns interaction info."""
        response = await self.client.aio.models.generate_content(
            model=model or self.DEFAULT_MODEL,
            contents=query,
            config={"response_modalities": ["TEXT"]}
        )
        return {"interaction_id": response.id, "status": "running"}

    async def poll_status(self, interaction_id: str) -> dict:
        """Poll for completion status.

        See data-model.md for full implementation details.
        """
        # Implementation depends on Gemini Deep Research API specifics
        pass
```

#### 2. StateManager (`deep_research/state_manager.py`)

SQLite-based state persistence. See **[data-model.md](./data-model.md)** for complete implementation including:
- Full schema with WAL mode for concurrent access
- All CRUD methods (`save_task`, `get_task`, `update_task`, `get_incomplete_tasks`)
- Result storage methods (`save_result`, `get_result`)
- Index definitions for performance

Key design points:
- Uses `PRAGMA journal_mode=WAL` for better concurrent access
- Includes `interaction_id` field for Gemini crash recovery
- Tracks token usage and cost per task

#### 3. BackgroundTaskManager (`deep_research/background.py`)

Asyncio-based background task management:

```python
import asyncio
from typing import Dict, Callable

class BackgroundTaskManager:
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}

    def start_task(self, task_id: str, coro: Callable) -> None:
        """Start a background task."""
        task = asyncio.create_task(coro)
        self._tasks[task_id] = task

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id in self._tasks:
            self._tasks[task_id].cancel()
            return True
        return False

    def get_running_tasks(self) -> list:
        """Get list of running task IDs."""
        return [tid for tid, task in self._tasks.items() if not task.done()]
```

#### 4. NativeNotifier (`deep_research/notification.py`)

Cross-platform notifications with fallback:

```python
import platform
import subprocess
import logging

logger = logging.getLogger(__name__)

class NativeNotifier:
    def notify(self, title: str, message: str) -> bool:
        """Send notification, return True if successful."""
        try:
            from notifypy import Notify
            n = Notify()
            n.title = title
            n.message = message
            n.application_name = "Gemini Deep Research"
            n.send()
            return True
        except ImportError:
            return self._fallback_notify(title, message)
        except Exception as e:
            logger.warning(f"Notification failed: {e}")
            return self._fallback_notify(title, message)

    def _fallback_notify(self, title: str, message: str) -> bool:
        """Platform-specific fallback."""
        system = platform.system()
        try:
            if system == "Linux":
                subprocess.run(['notify-send', title, message], check=True)
                return True
            elif system == "Darwin":
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(['osascript', '-e', script], check=True)
                return True
        except Exception:
            pass
        # Final fallback: just log it
        logger.info(f"NOTIFICATION: {title} - {message}")
        return False
```

#### 5. MarkdownStorage (`deep_research/storage.py`)

Jinja2-based report generation:

```python
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

class MarkdownStorage:
    def __init__(self, output_dir: str = "./research_reports"):
        self.output_dir = Path(output_dir)
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def save_report(self, task_id: str, results: dict,
                    prefix: str = "research",
                    include_metadata: bool = True,
                    include_sources: bool = True) -> Path:
        template = self.env.get_template("research_report.md.j2")
        content = template.render(
            results=results,
            include_metadata=include_metadata,
            include_sources=include_sources
        )

        # Organize by month
        month_dir = self.output_dir / datetime.now().strftime("%Y-%m")
        month_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{prefix}_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = month_dir / filename
        filepath.write_text(content)
        return filepath
```

### Tool Implementations

#### Tool 1: `start_deep_research`

```python
@mcp.tool()
async def start_deep_research(
    query: str,
    enable_notifications: bool = True,
    max_wait_hours: int = 8,
    model: str = "deep-research-pro-preview-12-2025"
) -> Dict[str, Any]:
    """
    Start a deep research task using Gemini Deep Research API.

    Gemini Deep Research natively handles multi-hop reasoning, automatic
    query refinement, and source synthesis. This tool wraps that capability
    with hybrid sync-to-async execution.

    The system uses SQLite for state persistence and asyncio for background
    execution - no external services required.

    Args:
        query: Research question or topic
        enable_notifications: Send desktop notification on completion
        max_wait_hours: Maximum hours for async research (default: 8)
        model: Gemini model for research

    Returns:
        Sync complete: {"status": "completed", "results": {...}}
        Async switch: {"status": "running_async", "task_id": "..."}
    """
```

#### Tool 2: `check_research_status`

```python
@mcp.tool()
def check_research_status(task_id: str) -> Dict[str, Any]:
    """
    Check status of a running deep research task.

    Zero token cost - reads from SQLite state.

    Args:
        task_id: Task UUID from start_deep_research

    Returns:
        {"status": "running_async", "progress": 65, "elapsed_minutes": 12.5}
    """
```

#### Tool 3: `get_research_results`

```python
@mcp.tool()
def get_research_results(task_id: str, include_sources: bool = True) -> Dict[str, Any]:
    """
    Retrieve completed research results.

    Zero token cost - reads from SQLite result store.

    Args:
        task_id: Task UUID
        include_sources: Include source list in response

    Returns:
        {"report": "...", "sources": [...], "metadata": {...}}
    """
```

#### Tool 4: `cancel_research`

```python
@mcp.tool()
def cancel_research(task_id: str, save_partial: bool = True) -> Dict[str, Any]:
    """
    Cancel a running research task.

    Args:
        task_id: Task UUID
        save_partial: Save partial results before canceling

    Returns:
        {"status": "cancelled", "partial_results_saved": True}
    """
```

#### Tool 5: `estimate_research_cost`

```python
@mcp.tool()
def estimate_research_cost(query: str) -> Dict[str, Any]:
    """
    Estimate cost and duration before starting research.

    Args:
        query: Research question

    Returns:
        {"complexity": "medium", "estimated_minutes": 30, "estimated_usd": 1.50}
    """
```

#### Tool 6: `save_research_to_markdown`

```python
@mcp.tool()
def save_research_to_markdown(
    task_id: str,
    output_dir: str = "./research_reports",
    filename_prefix: str = "research",
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Save completed research to permanent Markdown file.

    Zero token cost - uses Jinja2 templates.

    Args:
        task_id: Task UUID
        output_dir: Directory for output files
        filename_prefix: Prefix for filename
        include_metadata: Include metadata section

    Returns:
        {"file_path": "...", "file_size_kb": 45.2}
    """
```

### Dependencies to Add

```txt
# requirements.txt additions

# Desktop Notifications (with fallback if unavailable)
notify-py>=0.3.42

# Markdown Templates
Jinja2>=3.1.0

# Note: sqlite3 and asyncio are Python stdlib - no external deps needed
```

### Environment Configuration

```bash
# .env additions (minimal - no Redis/Celery needed)
RESEARCH_REPORTS_DIR=./research_reports
# DEEP_RESEARCH_BACKEND=sqlite  # Default, can be "redis" in future
```

## Implementation Phases

### Phase 1: Infrastructure (Wave 1)
- T001: Create `deep_research/` module structure
- T002: Add dependencies to requirements.txt
- T003: Configure environment variables
- T004: Create output directory structure

### Phase 2: Core Components (Wave 2-3)
- T005: Implement data models (__init__.py exports)
- T006: Implement StateManager with SQLite
- T007: Implement NativeNotifier
- T008: Implement BackgroundTaskManager

### Phase 3: Engine (Wave 4)
- T009: Implement DeepResearchEngine
- T010: Implement startup recovery (resume incomplete tasks)

### Phase 4: MCP Tools (Wave 5-6)
- T011: Implement `start_deep_research` tool
- T012: Implement `check_research_status` tool
- T013: Implement `get_research_results` tool
- T014: Implement `cancel_research` tool
- T015: Implement `estimate_research_cost` tool

### Phase 5: Persistence (Wave 7)
- T016: Create Jinja2 report template
- T017: Implement MarkdownStorage
- T018: Implement `save_research_to_markdown` tool

### Phase 6: Polish (Wave 8)
- T019: Add comprehensive docstrings
- T020: Update version to next MINOR
- T021: Update CLAUDE.md documentation
- T022: Final integration test suite

## Success Criteria

| Metric | Target | Validation |
|--------|--------|------------|
| Async switch response | <30 seconds | Time from request to task_id return |
| Status check latency | <100ms | SQLite read operation |
| Notification delivery | <2 seconds | Post-completion to desktop |
| State recovery | 100% | Server restart test with incomplete tasks |
| Cross-platform notifications | 95%+ | Linux, macOS, Windows test |
| Zero-token MD generation | 100% | No LLM calls in save_research_to_markdown |
| Zero external deps | 100% | No Docker, Redis, or Celery required |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Gemini API unavailable | Graceful degradation with clear error messages |
| SQLite write failure | Graceful error, research continues in memory |
| Notification library unavailable | Fallback chain: notify-py → system command → console log |
| Disk full on MD save | Pre-check available space, clear error message |
| Server crash mid-research | SQLite persists interaction_id, resume on restart |

## Next Steps

1. Generate `research.md` with API research findings
2. Generate `data-model.md` with entity definitions
3. Generate `contracts/tools.md` with MCP tool schemas
4. Generate `quickstart.md` with setup instructions
5. Run `/speckit.tasks` to generate detailed task list
