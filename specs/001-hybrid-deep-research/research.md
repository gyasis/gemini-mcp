# Research: Hybrid Deep Research System

**Date**: 2025-12-14
**Feature**: 001-hybrid-deep-research
**Research Phases**: PHASE 1A (Gemini), PHASE 1B (Context7), PHASE 1C (DeepLake RAG), PHASE 2 (Brainstorm)

---

## Executive Summary

This research consolidates findings from parallel research agents investigating the technical foundations for implementing a Hybrid Deep Research System that wraps Google's Gemini Deep Research API.

**Key Discovery**: Gemini Deep Research API provides **native multi-hop reasoning** - we do NOT need to implement this ourselves. The API autonomously formulates queries, identifies knowledge gaps, and synthesizes information.

**Architecture Decision**: SQLite + asyncio as default backend (zero external dependencies), preserving the "just run `uv run python server.py`" simplicity.

---

## PHASE 1A: Gemini Deep Research API (2025)

### Core Capabilities

- **Native Multi-Hop Reasoning**: Gemini Deep Research powers iterative planning, query formulation, result reading, knowledge gap identification, and recursive searching
- **Vastly Improved Web Search**: Can navigate deep into websites to extract specific data points
- **Async Execution**: Long-running operations (5-15 minutes typical, up to hours for complex queries)
- **Interactions API**: Unified interface for models and agents with multi-turn interactions and built-in Google Search
- **Autonomous Planning**: Agent autonomously plans, executes, and synthesizes multi-step research tasks with high factual accuracy

### Access Pattern

```python
# Using google-genai SDK
from google import genai

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# Start deep research
response = await client.aio.models.generate_content(
    model="deep-research-pro-preview-12-2025",
    contents=query,
    config={"response_modalities": ["TEXT"]}
)
```

### Polling Pattern (for async responses)

```python
# The response includes interaction_id for tracking
interaction_id = response.id

# Poll for completion
while True:
    status = await client.aio.interactions.get(interaction_id)
    if status.state == "completed":
        return status.outputs[-1].text
    elif status.state == "failed":
        raise Exception(status.error)
    await asyncio.sleep(10)
```

### Streaming Support

- Real-time updates available via streaming API
- Enable thinking summaries to receive intermediate reasoning steps
- Handle network interruptions by resuming with Interaction ID

---

## PHASE 1A: SQLite State Management

### Architecture

- **Zero dependencies**: Python stdlib sqlite3 module
- **Concurrent access**: WAL mode for read/write parallelism
- **JSON storage**: Serialize complex objects as JSON text fields
- **Recovery**: Store `interaction_id` for crash recovery

### State Persistence Pattern

```python
import sqlite3
import json
from pathlib import Path

class StateManager:
    DB_PATH = Path("deep_research.db")

    def __init__(self):
        self.conn = sqlite3.connect(self.DB_PATH, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS research_tasks (
                task_id TEXT PRIMARY KEY,
                interaction_id TEXT,
                query TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                enable_notifications BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS research_results (
                task_id TEXT PRIMARY KEY,
                report_markdown TEXT,
                sources_json TEXT,
                metadata_json TEXT,
                FOREIGN KEY (task_id) REFERENCES research_tasks(task_id)
            );
        ''')
        self.conn.commit()
```

### Recovery Pattern

```python
def get_incomplete_tasks(self) -> list:
    """Resume tasks after server restart."""
    cursor = self.conn.execute(
        "SELECT task_id, interaction_id FROM research_tasks WHERE status = 'running'"
    )
    return cursor.fetchall()
```

---

## PHASE 1A: Asyncio Background Tasks

### Architecture

- **Zero external services**: Uses Python stdlib asyncio
- **Task isolation**: Each research runs in separate asyncio.Task
- **Event loop**: Runs in MCP server's existing event loop
- **Cancellation**: Clean task cancellation via asyncio.Task.cancel()

### Background Task Manager Pattern

```python
import asyncio
from typing import Dict

class BackgroundTaskManager:
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}

    def start_task(self, task_id: str, coro) -> None:
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

    def get_running_tasks(self) -> list:
        """Get list of running task IDs."""
        return [tid for tid, task in self._tasks.items() if not task.done()]
```

### Hybrid Sync-to-Async Pattern

```python
@mcp.tool()
async def start_deep_research(query: str, ...):
    task_id = str(uuid.uuid4())

    # Save to SQLite immediately
    state_manager.save_task(task_id, {"query": query, "status": "pending"})

    # Start background task
    async def research_task():
        try:
            # Call Gemini Deep Research API
            response = await engine.start_research(query)
            interaction_id = response.id

            # Update SQLite with interaction_id
            state_manager.update_task(task_id, {
                "interaction_id": interaction_id,
                "status": "running"
            })

            # Poll for completion
            result = await engine.poll_until_complete(interaction_id)

            # Save results
            state_manager.save_result(task_id, result)

            # Send notification
            if enable_notifications:
                notifier.notify("Deep Research Complete", f"Task {task_id[:8]} finished")

        except Exception as e:
            state_manager.update_task(task_id, {"status": "failed", "error": str(e)})

    # Spawn background task
    background_manager.start_task(task_id, research_task())

    return {"status": "running_async", "task_id": task_id}
```

---

## PHASE 1A: FastMCP 2.0 Patterns

### Tool Implementation

- Use `@mcp.tool()` decorator for automatic schema generation
- Return dicts for JSON serialization
- Async functions supported natively

### Progress Reporting (via SQLite)

```python
# Store progress in SQLite, clients poll via check_research_status
state_manager.update_task(task_id, {
    "progress": 65,
    "current_action": "Analyzing source 45/100..."
})
```

---

## PHASE 1A: Desktop Notifications (2025)

### Library Comparison

| Library | Pros | Cons |
|---------|------|------|
| **notify-py** | Lightweight, only loguru dependency | Basic features |
| **Plyer** | Simple, cross-platform, minimal code | Limited customization |
| **desktop-notifier** | Advanced features, clickable callbacks | macOS 10.14+ needs signed exec |

### Implementation with Fallback

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

---

## PHASE 2: Brainstorm Solutions

### Topic 1: Hybrid Sync-to-Async Execution

**Selected Approach**: SQLite + asyncio (10/10 feasibility)
- Zero external dependencies
- Python stdlib only
- Runs in MCP server process
- Graceful crash recovery via SQLite

### Topic 2: State Recovery Patterns

**Selected Approach**: SQLite with Interaction ID (10/10)
- Store Gemini's `interaction_id` in SQLite
- On restart, query SQLite for incomplete tasks
- Resume polling with saved interaction_id
- Gemini holds actual research state server-side

### Topic 3: Cross-Platform Notifications

**Selected**: notify-py with CLI fallbacks (10/10)
- Primary: notify-py library
- Fallback: Platform CLI commands (notify-send, osascript)
- Final fallback: Console logging

### Topic 4: Zero-Token Report Persistence

**Selected**: Jinja2 Templates (10/10)
- Industry-standard templating
- Powerful logic (loops, conditionals)
- Zero LLM token cost

---

## Architectural Recommendations

### Simplified Architecture (Zero External Dependencies)

```
User Request → MCP Tool (start_deep_research)
    ↓
SQLite (save task state with task_id)
    ↓
Asyncio Background Task
    ↓
Gemini Deep Research API (interaction_id)
    ↓
Polling Loop (asyncio, updates SQLite)
    ↓
Desktop Notification → User
```

### State Management Strategy

- Use SQLite for all task state persistence
- Store interaction_id for Gemini API recovery
- JSON serialize complex objects in TEXT fields
- WAL mode for concurrent read/write access

### Startup Recovery

```python
async def on_server_startup():
    """Resume incomplete tasks from SQLite."""
    incomplete = state_manager.get_incomplete_tasks()
    for task_id, interaction_id in incomplete:
        # Spawn polling task to resume
        background_manager.start_task(
            task_id,
            engine.poll_until_complete(interaction_id)
        )
```

---

## Dependencies Summary

```txt
# Add to requirements.txt (minimal!)

# Desktop Notifications (with fallback if unavailable)
notify-py>=0.3.42

# Markdown Templates
Jinja2>=3.1.0

# Already in stdlib (no install needed):
# sqlite3, asyncio, json, uuid, datetime, pathlib
```

---

## Key Insights

1. **Gemini Deep Research Native Capabilities**: Multi-hop reasoning is built-in - don't re-implement
2. **SQLite for State**: Zero-dependency persistence with crash recovery
3. **Asyncio for Background**: No Celery/Redis needed for single-server MCP
4. **Interaction ID is Key**: Gemini holds state server-side, we just need the ID
5. **notify-py Primary**: Lightweight, cross-platform, minimal dependencies
6. **Jinja2 for Reports**: Zero-token cost, full control over formatting
7. **JSON over Pickle**: Security and portability for state serialization
8. **WAL Mode**: Better concurrent SQLite access

---

## Research Sources

- Gemini Deep Research API Documentation (December 2025)
- Python sqlite3 Documentation
- Python asyncio Documentation
- FastMCP 2.0 Patterns Guide
- notify-py library documentation
- Jinja2 Template Engine Documentation
