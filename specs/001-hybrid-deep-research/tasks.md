# Tasks: Hybrid Deep Research System

**Feature**: 001-hybrid-deep-research
**Date**: 2025-12-14
**Branch**: `001-hybrid-deep-research`
**Architecture**: SQLite + asyncio (zero external dependencies)

---

## Task Legend

| Symbol | Meaning |
|--------|---------|
| `[P]` | **Parallel** - Can run with multiple agents simultaneously |
| `[S]` | **Sequential** - Must wait for dependencies to complete |
| `->` | Depends on (must complete first) |
| `\|\|` | Can run in parallel with |

---

## Constitution VII Compliance: Wave Execution Schema

Per Constitution Principle VII, all tasks declare file_locks and phases include checkpoint_after blocks.

```json
{
  "execution_plan": {
    "phase_id": "001-hybrid-deep-research",
    "waves": [
      {
        "wave_id": 1,
        "strategy": "PARALLEL_SWARM",
        "rationale": "Setup tasks have no shared file locks",
        "tasks": ["T001", "T002", "T003", "T004"],
        "checkpoint_after": {
          "enabled": true,
          "git_agent": "git-version-manager",
          "memory_bank_agent": "memory-bank-keeper",
          "commit_message": "feat(deep-research): Phase 1 setup complete"
        }
      },
      {
        "wave_id": 2,
        "strategy": "PARALLEL_SWARM",
        "rationale": "Foundation modules have separate file locks",
        "tasks": ["T005", "T006", "T007", "T008"],
        "checkpoint_after": {
          "enabled": true,
          "git_agent": "git-version-manager",
          "memory_bank_agent": "memory-bank-keeper",
          "commit_message": "feat(deep-research): Foundation modules complete"
        }
      },
      {
        "wave_id": 3,
        "strategy": "SEQUENTIAL_MERGE",
        "rationale": "Engine depends on all foundation modules",
        "tasks": ["T009", "T010"],
        "checkpoint_after": {
          "enabled": true,
          "git_agent": "git-version-manager",
          "memory_bank_agent": "memory-bank-keeper",
          "commit_message": "feat(deep-research): Core engine complete"
        }
      },
      {
        "wave_id": 4,
        "strategy": "PARALLEL_SWARM",
        "rationale": "US1 sync/async paths can develop in parallel",
        "tasks": ["T011", "T012"],
        "checkpoint_after": { "enabled": false }
      },
      {
        "wave_id": 5,
        "strategy": "SEQUENTIAL_MERGE",
        "rationale": "Results tool and integration test depend on both paths",
        "tasks": ["T013", "T014"],
        "checkpoint_after": {
          "enabled": true,
          "git_agent": "git-version-manager",
          "memory_bank_agent": "memory-bank-keeper",
          "commit_message": "feat(deep-research): US1 MVP complete"
        }
      },
      {
        "wave_id": 6,
        "strategy": "PARALLEL_SWARM",
        "rationale": "Status tool and notification trigger are independent",
        "tasks": ["T015", "T016"],
        "checkpoint_after": { "enabled": false }
      },
      {
        "wave_id": 7,
        "strategy": "SEQUENTIAL_MERGE",
        "rationale": "Progress updates and integration test are sequential",
        "tasks": ["T017", "T018"],
        "checkpoint_after": {
          "enabled": true,
          "git_agent": "git-version-manager",
          "memory_bank_agent": "memory-bank-keeper",
          "commit_message": "feat(deep-research): US2 async notifications complete"
        }
      },
      {
        "wave_id": 8,
        "strategy": "PARALLEL_SWARM",
        "rationale": "US3 and US4 are completely independent features",
        "tasks": ["T019", "T020"],
        "checkpoint_after": { "enabled": false }
      },
      {
        "wave_id": 9,
        "strategy": "PARALLEL_SWARM",
        "rationale": "US3 tool and US4 test are independent",
        "tasks": ["T021", "T022"],
        "checkpoint_after": {
          "enabled": true,
          "git_agent": "git-version-manager",
          "memory_bank_agent": "memory-bank-keeper",
          "commit_message": "feat(deep-research): US3-US4 complete"
        }
      },
      {
        "wave_id": 10,
        "strategy": "PARALLEL_SWARM",
        "rationale": "Template and storage class have separate file locks",
        "tasks": ["T023", "T024"],
        "checkpoint_after": { "enabled": false }
      },
      {
        "wave_id": 11,
        "strategy": "SEQUENTIAL_MERGE",
        "rationale": "MD tool depends on template and storage",
        "tasks": ["T025"],
        "checkpoint_after": {
          "enabled": true,
          "git_agent": "git-version-manager",
          "memory_bank_agent": "memory-bank-keeper",
          "commit_message": "feat(deep-research): US5 persistence complete"
        }
      },
      {
        "wave_id": 12,
        "strategy": "PARALLEL_SWARM",
        "rationale": "Polish tasks modify different files (T026 excluded - shares file lock with T006)",
        "tasks": ["T027", "T028", "T029"],
        "checkpoint_after": { "enabled": false }
      },
      {
        "wave_id": 12.5,
        "strategy": "SEQUENTIAL_MERGE",
        "rationale": "T026 must run after T006 completes (same file lock: state_manager.py)",
        "tasks": ["T026"],
        "checkpoint_after": { "enabled": false }
      },
      {
        "wave_id": 13,
        "strategy": "SEQUENTIAL_MERGE",
        "rationale": "Final integration test validates all changes",
        "tasks": ["T030"],
        "checkpoint_after": {
          "enabled": true,
          "git_agent": "git-version-manager",
          "memory_bank_agent": "memory-bank-keeper",
          "commit_message": "feat(deep-research): v3.7.0 complete"
        }
      }
    ]
  }
}
```

---

## Dependency Graph Overview

```
PHASE 1: Setup ---------------------------------------------------------
    T001 [P] || T002 [P] || T003 [P] || T004 [P]
              |
              v
PHASE 2: Foundational --------------------------------------------------
    T005 [P] || T006 [P] || T007 [P] || T008 [P]
         |         |         |         |
         +---------+---------+---------+
                   |
                   v
              T009 [S] -> T010 [S]
                              |
                              v
PHASE 3: US1 (P1) MVP --------------------------------------------------
    T011 [P] || T012 [P]
         |         |
         +----+----+
              v
         T013 [S] -> T014 [S]
                        |
                        v
PHASE 4: US2 (P2) Async ------------------------------------------------
    T015 [P] || T016 [P]
         |         |
         +----+----+
              v
         T017 [S] -> T018 [S]
                        |
                        v
PHASE 5: US3-US4 (P3-P4) -----------------------------------------------
    T019 [P] || T020 [P]    (These can run in parallel!)
         |         |
         v         v
    T021 [S]   T022 [S]
                        |
                        v
PHASE 6: US5 (P5) Persistence ------------------------------------------
    T023 [P] || T024 [P]
         |         |
         +----+----+
              v
         T025 [S]
              |
              v
PHASE 7: Recovery & Polish ---------------------------------------------
    T027 [P] || T028 [P] || T029 [P]
              |
              v
         T026 [S] (depends on T006 file lock)
              |
              v
         T030 [S]
```

---

## PHASE 1: Setup (Wave 1)

All Phase 1 tasks are **independent** and can run in parallel.

### T001 [P] Create Module Structure

**Story**: Foundation
**Priority**: P0 (Blocking)
**Parallel**: Yes - No dependencies
**Depends On**: None
**File Locks**: `deep_research/`

```
deep_research/
├── __init__.py
├── engine.py
├── state_manager.py
├── notification.py
├── cost_estimator.py
├── storage.py
├── background.py
└── templates/
    └── research_report.md.j2
```

**Acceptance**: Directory structure exists with empty `__init__.py`

---

### T002 [P] Add Dependencies to requirements.txt

**Story**: Foundation
**Priority**: P0 (Blocking)
**Parallel**: Yes || T001, T003, T004
**Depends On**: None
**File Locks**: `requirements.txt`

```txt
# Desktop Notifications (with fallback if unavailable)
notify-py>=0.3.42

# Markdown Templates
Jinja2>=3.1.0

# Note: sqlite3 and asyncio are Python stdlib - zero external deps!
```

**Acceptance**: `uv sync` succeeds without errors

---

### T003 [P] Configure Environment Variables

**Story**: Foundation
**Priority**: P0 (Blocking)
**Parallel**: Yes || T001, T002, T004
**Depends On**: None
**File Locks**: `.env.example`

Add to `.env.example`:
```bash
# Gemini API (required)
GEMINI_API_KEY=your_gemini_api_key_here

# Output directory (optional)
RESEARCH_REPORTS_DIR=./research_reports
```

**Acceptance**: `.env.example` updated, documented in quickstart.md

---

### T004 [P] Create Output Directory Structure

**Story**: Foundation
**Priority**: P0 (Blocking)
**Parallel**: Yes || T001, T002, T003
**Depends On**: None
**File Locks**: `research_reports/`, `.gitignore`

```
research_reports/
└── .gitkeep
```

Add to `.gitignore`:
```
research_reports/*.md
!research_reports/.gitkeep
deep_research.db
```

**Acceptance**: Directory created, gitignore configured

---

## PHASE 2: Foundational (Wave 2)

### T005 [P] Implement Data Models

**Story**: Foundation
**Priority**: P0 (Blocking)
**Parallel**: Yes || T006, T007, T008
**Depends On**: T001
**File Locks**: `deep_research/__init__.py`

File: `deep_research/__init__.py`

Implement from data-model.md:
- `TaskStatus` enum (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
- `Source` dataclass
- `TokenUsage` dataclass with `estimate_cost_usd()` method
- `ResearchTask` dataclass
- `ResearchResult` dataclass
- `CostEstimate` dataclass

**Acceptance**: All dataclasses serializable to JSON, type hints complete

---

### T006 [P] Implement StateManager (SQLite)

**Story**: Foundation
**Priority**: P0 (Blocking)
**Parallel**: Yes || T005, T007, T008
**Depends On**: T001, T002
**File Locks**: `deep_research/state_manager.py`

File: `deep_research/state_manager.py`

```python
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Tuple

class StateManager:
    DB_PATH = Path("deep_research.db")

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self.DB_PATH
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS research_tasks (
                task_id TEXT PRIMARY KEY,
                interaction_id TEXT,
                query TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                current_action TEXT,
                enable_notifications BOOLEAN DEFAULT TRUE,
                tokens_input INTEGER DEFAULT 0,
                tokens_output INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_status ON research_tasks(status);

            CREATE TABLE IF NOT EXISTS research_results (
                task_id TEXT PRIMARY KEY,
                report_markdown TEXT,
                sources_json TEXT,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES research_tasks(task_id)
            );
        ''')
        conn.commit()
        conn.close()

    def save_task(self, task: ResearchTask) -> None
    def get_task(self, task_id: str) -> Optional[ResearchTask]
    def update_task(self, task_id: str, updates: dict) -> None
    def get_incomplete_tasks(self) -> List[Tuple[str, str]]
    def save_result(self, task_id: str, result: ResearchResult) -> None
    def get_result(self, task_id: str) -> Optional[ResearchResult]
```

**Acceptance**: Unit tests pass with SQLite in-memory database

---

### T007 [P] Implement NativeNotifier

**Story**: US2 (P2)
**Priority**: P2
**Parallel**: Yes || T005, T006, T008
**Depends On**: T001, T002
**File Locks**: `deep_research/notification.py`

File: `deep_research/notification.py`

```python
import platform
import subprocess
import logging

logger = logging.getLogger(__name__)

class NativeNotifier:
    def notify(self, title: str, message: str) -> bool:
        """Send notification with fallback chain."""
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
        """Platform-specific CLI fallback."""
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
        # Final fallback: log it
        logger.info(f"NOTIFICATION: {title} - {message}")
        return False
```

Fallback chain: notify-py -> CLI (notify-send/osascript) -> console

**Acceptance**: Cross-platform notification test passes

---

### T008 [P] Implement BackgroundTaskManager

**Story**: Foundation
**Priority**: P0 (Blocking)
**Parallel**: Yes || T005, T006, T007
**Depends On**: T001
**File Locks**: `deep_research/background.py`

File: `deep_research/background.py`

```python
import asyncio
from typing import Dict, Callable, Coroutine, Any

class BackgroundTaskManager:
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}

    def start_task(self, task_id: str, coro: Coroutine[Any, Any, Any]) -> None:
        """Start a background task."""
        task = asyncio.create_task(coro)
        self._tasks[task_id] = task
        # Clean up when done
        task.add_done_callback(lambda t: self._tasks.pop(task_id, None))

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id in self._tasks:
            self._tasks[task_id].cancel()
            return True
        return False

    def is_running(self, task_id: str) -> bool:
        """Check if a task is currently running."""
        return task_id in self._tasks and not self._tasks[task_id].done()

    def get_running_tasks(self) -> list:
        """Get list of running task IDs."""
        return [tid for tid, task in self._tasks.items() if not task.done()]
```

**Acceptance**: Unit tests pass for task lifecycle management

---

### T009 [S] Implement DeepResearchEngine

**Story**: US1 (P1)
**Priority**: P1 (MVP)
**Parallel**: No - Sequential
**Depends On**: T005, T006, T007, T008
**File Locks**: `deep_research/engine.py`

File: `deep_research/engine.py`

> **IMPLEMENTATION NOTE**: Before implementing `_get_status()`, research the actual Gemini Deep Research API polling mechanism. Check `specs/001-hybrid-deep-research/research.md` for API documentation findings. The polling endpoint, response format, and status codes may differ from the placeholder below.

```python
from google import genai
from typing import Optional, Dict, Any, Callable
import asyncio

class DeepResearchEngine:
    DEFAULT_MODEL = "deep-research-pro-preview-12-2025"

    def __init__(self, client: genai.Client):
        self.client = client

    async def start_research(self, query: str, model: str = None) -> Dict[str, Any]:
        """Start research, returns interaction info."""
        response = await self.client.aio.models.generate_content(
            model=model or self.DEFAULT_MODEL,
            contents=query,
            config={"response_modalities": ["TEXT"]}
        )
        return {
            "interaction_id": response.id,
            "status": "running"
        }

    async def poll_until_complete(
        self,
        interaction_id: str,
        on_progress: Optional[Callable[[int, str], None]] = None,
        poll_interval: int = 10,
        max_wait_seconds: int = 28800  # 8 hours
    ) -> Dict[str, Any]:
        """Poll for completion, calling on_progress with updates."""
        start_time = asyncio.get_event_loop().time()

        while True:
            status = await self._get_status(interaction_id)

            if status.get("state") == "completed":
                return status.get("result")
            elif status.get("state") == "failed":
                raise Exception(status.get("error", "Research failed"))

            if on_progress:
                on_progress(status.get("progress", 0), status.get("action", ""))

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_seconds:
                raise TimeoutError("Research exceeded maximum wait time")

            await asyncio.sleep(poll_interval)

    async def _get_status(self, interaction_id: str) -> Dict[str, Any]:
        """Get current status from Gemini API.

        TODO: Implement based on actual Gemini Deep Research API.
        Research required: polling endpoint, auth, response schema.
        See research.md for API documentation.
        """
        raise NotImplementedError("Requires Gemini Deep Research API research")
```

**Acceptance**: Integration test with mocked Gemini API passes

---

### T010 [S] Implement Startup Recovery

**Story**: Foundation
**Priority**: P0 (Blocking)
**Parallel**: No - Sequential
**Depends On**: T009
**File Locks**: `deep_research/engine.py`, `server.py`

Implement server startup recovery:

```python
# server.py - add to server startup
async def on_server_startup():
    """Resume incomplete tasks from SQLite."""
    incomplete = state_manager.get_incomplete_tasks()
    for task_id, interaction_id in incomplete:
        if interaction_id:
            # Spawn asyncio task to resume polling
            background_manager.start_task(
                task_id,
                _continue_research(task_id, interaction_id)
            )

async def _continue_research(task_id: str, interaction_id: str):
    """Resume polling for an incomplete task."""
    try:
        task = state_manager.get_task(task_id)
        result = await engine.poll_until_complete(
            interaction_id,
            on_progress=lambda p, a: state_manager.update_task(
                task_id, {"progress": p, "current_action": a}
            )
        )
        # Save result and update status
        state_manager.save_result(task_id, result)
        state_manager.update_task(task_id, {"status": "completed"})

        # Send notification
        if task.enable_notifications:
            notifier.notify("Research Complete", f"Task {task_id[:8]} finished")
    except Exception as e:
        state_manager.update_task(task_id, {"status": "failed", "error_message": str(e)})
```

**Acceptance**: Server restart test with incomplete tasks verifies recovery

---

## PHASE 3: User Story 1 (P1) - MVP

**US1**: As a researcher, I can submit a query and receive results either synchronously or be handed off to async seamlessly.

### T011 [P] Implement start_deep_research Tool (Sync Path)

**Story**: US1 (P1)
**Priority**: P1 (MVP)
**Parallel**: Yes || T012
**Depends On**: T009, T010
**File Locks**: `server.py` (shared with T012)

File: `server.py`

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
    with hybrid sync-to-async execution using SQLite for state persistence
    and asyncio for background tasks.
    """
```

Implement sync attempt with 30-second timeout:
- Create task in SQLite (PENDING)
- Start Gemini research
- If completes within timeout: return results
- If timeout: switch to async (T012 handles this)

**Acceptance**: Contract test passes for sync complete response

---

### T012 [P] Implement start_deep_research Tool (Async Path)

**Story**: US1 (P1), US2 (P2)
**Priority**: P1 (MVP)
**Parallel**: Yes || T011
**Depends On**: T009, T010
**File Locks**: `server.py` (shared with T011 - same function, different code path)

File: `server.py`

Continue `start_deep_research` implementation:
- On sync timeout: update status to RUNNING
- Save interaction_id to SQLite for crash recovery
- Spawn asyncio background task
- Return task_id and async status

**Acceptance**: Contract test passes for async switch response

---

### T013 [S] Implement get_research_results Tool

**Story**: US1 (P1), US2 (P2)
**Priority**: P1 (MVP)
**Parallel**: No - Sequential
**Depends On**: T011, T012
**File Locks**: `server.py`

File: `server.py`

```python
@mcp.tool()
def get_research_results(
    task_id: str,
    include_sources: bool = True
) -> Dict[str, Any]:
    """
    Retrieve completed research results.

    Zero token cost - reads from SQLite result store.
    """
```

- Read from SQLite result table (zero tokens)
- Return error if not completed
- Include sources and metadata per contract

**Acceptance**: Contract test passes for both success and not-completed responses

---

### T014 [S] Integration Test: US1 Full Flow

**Story**: US1 (P1)
**Priority**: P1 (MVP)
**Parallel**: No - Sequential (Validation)
**Depends On**: T013
**File Locks**: `tests/integration/test_deep_research_flow.py`

File: `tests/integration/test_deep_research_flow.py`

Test scenarios:
1. Simple query -> sync completion -> get_research_results
2. Complex query -> async switch -> poll -> get_research_results

**Acceptance**: Both scenarios pass with mocked Gemini API

---

## PHASE 4: User Story 2 (P2) - Async Notifications

**US2**: As a power user, I can start long-running research and receive a desktop notification when complete.

### T015 [P] Implement check_research_status Tool

**Story**: US2 (P2)
**Priority**: P2
**Parallel**: Yes || T016
**Depends On**: T014
**File Locks**: `server.py`

File: `server.py`

```python
@mcp.tool()
def check_research_status(task_id: str) -> Dict[str, Any]:
    """
    Check status of a running deep research task.

    Zero token cost - reads from SQLite state.
    """
```

- Read from SQLite (zero tokens)
- Return progress, elapsed time, estimated completion
- Include cost_so_far for running tasks

**Acceptance**: Contract test passes for running and completed responses

---

### T016 [P] Implement Background Notification Trigger

**Story**: US2 (P2)
**Priority**: P2
**Parallel**: Yes || T015
**Depends On**: T010, T007
**File Locks**: `deep_research/engine.py`

Update background research completion to:
- Call `NativeNotifier.notify()` on completion
- Include task_id snippet and duration in message

**Acceptance**: Desktop notification appears when test task completes

---

### T017 [S] Implement Progress Updates

**Story**: US2 (P2)
**Priority**: P2
**Parallel**: No - Sequential
**Depends On**: T015, T016
**File Locks**: `deep_research/engine.py`, `deep_research/state_manager.py`

Update background task to:
- Extract progress from Gemini streaming updates
- Update SQLite state periodically
- Calculate estimated completion time

**Acceptance**: check_research_status shows accurate progress during execution

---

### T018 [S] Integration Test: US2 Async Flow

**Story**: US2 (P2)
**Priority**: P2
**Parallel**: No - Sequential (Validation)
**Depends On**: T017
**File Locks**: `tests/integration/test_async_flow.py`

File: `tests/integration/test_async_flow.py`

Test scenarios:
1. Start research -> check_status loop -> completion notification
2. Progress updates visible during execution

**Acceptance**: Full async flow test passes

---

## PHASE 5: User Stories 3-4 (P3-P4)

**US3** and **US4** can be implemented **in parallel** - they are independent features!

### T019 [P] Implement CostEstimator

**Story**: US3 (P3)
**Priority**: P3
**Parallel**: Yes || T020
**Depends On**: T005
**File Locks**: `deep_research/cost_estimator.py`

File: `deep_research/cost_estimator.py`

```python
from dataclasses import dataclass
from typing import Tuple

class CostEstimator:
    def estimate(self, query: str) -> CostEstimate:
        complexity = self._analyze_complexity(query)
        duration = self._estimate_duration(complexity)
        cost = self._estimate_cost(complexity)

        return CostEstimate(
            query_complexity=complexity,
            min_minutes=duration[0],
            max_minutes=duration[1],
            likely_minutes=duration[2],
            min_usd=cost[0],
            max_usd=cost[1],
            likely_usd=cost[2],
            will_likely_go_async=duration[2] > 1,  # >1 min likely goes async
            recommendation=self._generate_recommendation(complexity)
        )

    def _analyze_complexity(self, query: str) -> str
    def _estimate_duration(self, complexity: str) -> Tuple[float, float, float]
    def _estimate_cost(self, complexity: str) -> Tuple[float, float, float]
    def _generate_recommendation(self, complexity: str) -> str
```

Complexity factors: query length, domain count, temporal scope, synthesis depth

**Acceptance**: Unit tests pass for simple/medium/complex queries

---

### T020 [P] Implement cancel_research Tool (Core)

**Story**: US4 (P4)
**Priority**: P4
**Parallel**: Yes || T019
**Depends On**: T008, T006
**File Locks**: `server.py`

File: `server.py`

```python
@mcp.tool()
def cancel_research(
    task_id: str,
    save_partial: bool = True
) -> Dict[str, Any]:
    """
    Cancel a running research task.

    Optionally save partial results before canceling.
    """
```

- Cancel asyncio task via BackgroundTaskManager
- Update SQLite status to CANCELLED
- Optionally save partial results

**Acceptance**: Contract test passes for success and already-completed responses

---

### T021 [S] Implement estimate_research_cost Tool

**Story**: US3 (P3)
**Priority**: P3
**Parallel**: No - Sequential
**Depends On**: T019
**File Locks**: `server.py`

File: `server.py`

```python
@mcp.tool()
def estimate_research_cost(query: str) -> Dict[str, Any]:
    """
    Estimate cost and duration before starting research.

    Analyzes query complexity to provide time and cost estimates.
    """
```

- Use CostEstimator
- Return complexity, duration range, cost range, async prediction

**Acceptance**: Contract test passes

---

### T022 [S] Integration Test: Cancel Flow

**Story**: US4 (P4)
**Priority**: P4
**Parallel**: No - Sequential (Validation)
**Depends On**: T020
**File Locks**: `tests/integration/test_cancel_flow.py`

File: `tests/integration/test_cancel_flow.py`

Test scenarios:
1. Start research -> cancel with save_partial=True -> verify partial results
2. Start research -> cancel with save_partial=False -> verify cleanup
3. Try cancel completed research -> verify error response

**Acceptance**: All cancel scenarios pass

---

## PHASE 6: User Story 5 (P5) - Persistence

**US5**: As a researcher, I can save completed research to a permanent Markdown file.

### T023 [P] Create Jinja2 Report Template

**Story**: US5 (P5)
**Priority**: P5
**Parallel**: Yes || T024
**Depends On**: T001
**File Locks**: `deep_research/templates/research_report.md.j2`

File: `deep_research/templates/research_report.md.j2`

```jinja2
# {{ title }}

**Research ID:** `{{ task_id }}`
**Completed:** {{ completed_at }}
**Duration:** {{ duration_minutes }} minutes
**Cost:** ${{ cost_usd }}
**Model:** {{ model }}

## Executive Summary
{{ summary }}

## Key Findings
{{ report }}

{% if include_sources %}
## Sources
{% for source in sources %}
### [{{ loop.index }}] {{ source.title }}
- **URL:** {{ source.url }}
- **Relevance:** {{ "%.0f"|format(source.relevance_score * 100) }}%
- **Excerpt:** {{ source.snippet }}
{% endfor %}
{% endif %}

---
*Generated by Gemini Deep Research MCP Server*
```

**Acceptance**: Template renders without errors

---

### T024 [P] Implement MarkdownStorage

**Story**: US5 (P5)
**Priority**: P5
**Parallel**: Yes || T023
**Depends On**: T001, T002
**File Locks**: `deep_research/storage.py`

File: `deep_research/storage.py`

```python
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any

class MarkdownStorage:
    def __init__(self, output_dir: str = "./research_reports"):
        self.output_dir = Path(output_dir)
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def save_report(
        self,
        task_id: str,
        results: Dict[str, Any],
        prefix: str = "research",
        include_metadata: bool = True,
        include_sources: bool = True
    ) -> Path:
        template = self.env.get_template("research_report.md.j2")
        content = template.render(
            results=results,
            include_metadata=include_metadata,
            include_sources=include_sources
        )

        # Organize by month
        month_dir = self.output_dir / datetime.now().strftime("%Y-%m")
        month_dir.mkdir(parents=True, exist_ok=True)

        filename = self._generate_filename(task_id, prefix)
        filepath = month_dir / filename
        filepath.write_text(content)
        return filepath

    def _generate_filename(self, task_id: str, prefix: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{task_id[:8]}_{timestamp}.md"
```

- Organize by month subdirectories
- Generate unique filenames with timestamp

**Acceptance**: Unit tests pass for file creation and naming

---

### T025 [S] Implement save_research_to_markdown Tool

**Story**: US5 (P5)
**Priority**: P5
**Parallel**: No - Sequential
**Depends On**: T023, T024
**File Locks**: `server.py`

File: `server.py`

```python
@mcp.tool()
def save_research_to_markdown(
    task_id: str,
    output_dir: str = "./research_reports",
    filename_prefix: str = "research",
    include_metadata: bool = True,
    include_sources: bool = True
) -> Dict[str, Any]:
    """
    Save completed research to permanent Markdown file.

    Zero token cost - uses Jinja2 templates.
    """
```

- Read result from SQLite
- Render Jinja2 template
- Write to file system
- Return file path and size

**Acceptance**: Contract test passes, file created with correct content

---

## PHASE 7: Recovery & Polish (Wave 12-13)

### T026 [S] Implement SQLite Error Recovery

**Story**: Edge Case (spec.md)
**Priority**: P3
**Parallel**: No - Sequential (shares file lock with T006)
**Depends On**: T006 (MUST complete first - same file lock)
**File Locks**: `deep_research/state_manager.py`

> **FILE LOCK NOTE**: T026 modifies `state_manager.py` which T006 creates. Despite Wave 12 grouping, T026 MUST wait for T006 completion. If running parallel swarm, ensure T006 agent completes before T026 agent starts.

Implement retry logic for SQLite operations:

```python
class StateManager:
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5  # seconds

    def _execute_with_retry(self, operation, *args):
        for attempt in range(self.MAX_RETRIES):
            try:
                return operation(*args)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (2 ** attempt))
                    continue
                raise
```

- Retry on "database locked" errors with exponential backoff
- Log warnings on retries
- Fail gracefully with clear error message

**Acceptance**: Unit test simulates locked database, verifies retry

---

### T027 [P] Add Comprehensive Docstrings

**Story**: Constitution Principle IV
**Priority**: P0 (Required)
**Parallel**: Yes || T026, T028, T029
**Depends On**: T025
**File Locks**: `server.py`

Update all 6 tools in `server.py` with:
- Full docstrings per Constitution Principle IV
- Usage examples
- Parameter descriptions
- Return value documentation

**Acceptance**: `server_info()` shows complete tool descriptions

---

### T028 [P] Update Version to Next MINOR

**Story**: Constitution Principle V
**Priority**: P0 (Required)
**Parallel**: Yes || T026, T027, T029
**Depends On**: T025
**File Locks**: `server.py`, `pyproject.toml`, `CHANGELOG.md`

Update version in:
- `server.py` (SERVER_VERSION)
- `pyproject.toml` (if exists)
- CHANGELOG.md entry

Version: 3.6.0 -> 3.7.0

**Acceptance**: Version updated consistently across all files

---

### T029 [P] Update CLAUDE.md Documentation

**Story**: Constitution Principle IV
**Priority**: P0 (Required)
**Parallel**: Yes || T026, T027, T028
**Depends On**: T025
**File Locks**: `CLAUDE.md`

Add to CLAUDE.md:
- New tools section for deep research
- Zero external dependencies (SQLite + asyncio)
- Environment variable documentation

**Acceptance**: CLAUDE.md accurately reflects new functionality

---

### T030 [S] Final Integration Test Suite

**Story**: All Stories
**Priority**: P0 (Required)
**Parallel**: No - Sequential (Final Validation)
**Depends On**: T026, T027, T028, T029
**File Locks**: `tests/integration/test_full_system.py`

File: `tests/integration/test_full_system.py`

Run complete test suite:
1. All contract tests pass
2. All unit tests pass
3. All integration tests pass
4. Server starts without errors
5. `server_info()` returns all 6 new tools
6. **Concurrency test**: Spawn 3+ simultaneous `start_deep_research` calls, verify all complete without race conditions (NFR-006)

**Acceptance**: 100% test pass rate, no regressions, concurrent execution verified

---

## Parallel Execution Summary

### Maximum Parallelism by Phase

| Phase | Parallel Tasks | Sequential Tasks | Total |
|-------|---------------|------------------|-------|
| 1: Setup | T001-T004 (4) | - | 4 |
| 2: Foundation | T005-T008 (4) | T009, T010 (2) | 6 |
| 3: US1 | T011, T012 (2) | T013, T014 (2) | 4 |
| 4: US2 | T015, T016 (2) | T017, T018 (2) | 4 |
| 5: US3-4 | T019, T020 (2) | T021, T022 (2) | 4 |
| 6: US5 | T023, T024 (2) | T025 (1) | 3 |
| 7: Recovery & Polish | T027-T029 (3) | T026, T030 (2) | 5 |
| **Total** | **19** | **11** | **30** |

### Story Completion Order

```
Setup (P0) -------------------------------------------------------->
            |
            v
US1 (P1) --------------------------------------------------------->
                      |
                      v
US2 (P2) --------------------------------------------------------->
                               |
                               | (US3 and US4 can run in PARALLEL!)
                               +------------->
                               |       US3 (P3)
                               |
                               +------------->
                               |       US4 (P4)
                               |
                               v
US5 (P5) --------------------------------------------------------->
                                              |
                                              v
Recovery & Polish (P0) ------------------------------------------>
```

---

## Summary Statistics

- **Total Tasks**: 30
- **Parallel-Capable**: 19 (63%)
- **Sequential-Only**: 11 (37%)
- **User Stories**: 5
- **Implementation Phases**: 7
- **External Dependencies**: ZERO (SQLite + asyncio only)

**Optimal Agent Utilization**: With proper orchestration, this feature can be implemented using up to 4 parallel agents at any given time, reducing total implementation time by approximately 50% compared to sequential execution.
