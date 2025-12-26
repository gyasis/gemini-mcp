# Data Model: Hybrid Deep Research System

**Feature**: 001-hybrid-deep-research
**Date**: 2025-12-14
**Storage**: SQLite (zero external dependencies)

---

## Entity Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     ResearchTask                            │
│  (Central entity tracking research lifecycle)               │
├─────────────────────────────────────────────────────────────┤
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ResearchState                           │   │
│  │  (In-memory state for active tasks)                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ResearchResult                          │   │
│  │  (Final output: report, sources, metadata)           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## SQLite Schema

### Table: research_tasks

```sql
CREATE TABLE IF NOT EXISTS research_tasks (
    task_id TEXT PRIMARY KEY,
    interaction_id TEXT,              -- Gemini's server-side ID (key for recovery!)
    query TEXT NOT NULL,
    status TEXT DEFAULT 'pending',    -- pending, running, completed, failed, cancelled
    progress INTEGER DEFAULT 0,       -- 0-100 percentage
    current_action TEXT,              -- Human-readable current step
    enable_notifications BOOLEAN DEFAULT TRUE,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,
    error_message TEXT,               -- Error details if failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Index for startup recovery
CREATE INDEX IF NOT EXISTS idx_tasks_status ON research_tasks(status);
```

### Table: research_results

```sql
CREATE TABLE IF NOT EXISTS research_results (
    task_id TEXT PRIMARY KEY,
    report_markdown TEXT,             -- Full research report
    sources_json TEXT,                -- JSON array of source objects
    metadata_json TEXT,               -- JSON with tokens, cost, duration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id)
);
```

---

## Core Entities (Python Dataclasses)

### ResearchTask

Represents a deep research operation from initiation to completion.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

class TaskStatus(str, Enum):
    """Research task lifecycle states."""
    PENDING = "pending"           # Created, not yet started
    RUNNING = "running"           # In progress (sync attempt)
    RUNNING_ASYNC = "running_async"  # Background async execution
    COMPLETED = "completed"       # Successfully finished
    FAILED = "failed"             # Error during execution
    CANCELLED = "cancelled"       # User-initiated cancellation

@dataclass
class ResearchTask:
    """Tracks lifecycle of a deep research request."""

    # Identifiers
    task_id: str                          # UUID v4
    interaction_id: Optional[str] = None  # Gemini API interaction ID

    # Request
    query: str = ""                       # Original research question

    # Status
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0                     # 0-100 percentage
    current_action: str = ""              # Human-readable current step

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Token Tracking
    tokens_input: int = 0                 # Input tokens consumed
    tokens_output: int = 0                # Output tokens generated
    cost_usd: float = 0.0                 # Estimated cost in USD

    # Notification Config
    enable_notifications: bool = True     # Send desktop notification

    # Error
    error_message: Optional[str] = None
```

### ResearchResult

Final output of completed research.

```python
@dataclass
class ResearchResult:
    """Completed research output."""

    # Task Reference
    task_id: str

    # Report Content
    report: str                           # Full Markdown report

    # Sources
    sources: list                         # List of Source objects

    # Metadata
    metadata: dict                        # Duration, tokens, cost, model

    # Timestamp
    created_at: datetime = field(default_factory=datetime.utcnow)
```

---

## Supporting Types

### Source

```python
@dataclass
class Source:
    """A source referenced in the research."""

    title: str                            # Source title
    url: str                              # Source URL
    snippet: str = ""                     # Relevant excerpt
    relevance_score: float = 0.0          # 0.0-1.0 relevance
```

### TokenUsage

```python
@dataclass
class TokenUsage:
    """Token consumption tracking."""

    input: int = 0                        # Input tokens
    output: int = 0                       # Output tokens

    @property
    def total(self) -> int:
        return self.input + self.output

    def estimate_cost_usd(self) -> float:
        """Estimate USD cost based on Gemini pricing."""
        # Deep Research pricing (approximate)
        input_cost = self.input * 0.000001    # $1/1M input tokens
        output_cost = self.output * 0.000004  # $4/1M output tokens
        return input_cost + output_cost
```

### CostEstimate

```python
@dataclass
class CostEstimate:
    """Pre-research cost and duration estimate."""

    query_complexity: str                 # simple, medium, complex

    # Duration Estimates (minutes)
    min_minutes: float
    max_minutes: float
    likely_minutes: float

    # Cost Estimates (USD)
    min_usd: float
    max_usd: float
    likely_usd: float

    # Predictions
    will_likely_go_async: bool
    recommendation: str                   # Human-readable suggestion
```

---

## State Manager Implementation

```python
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Tuple

class StateManager:
    """SQLite-based state persistence for research tasks."""

    DB_PATH = Path("deep_research.db")

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self.DB_PATH
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
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

    def save_task(self, task: ResearchTask) -> None:
        """Save or update a research task."""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT OR REPLACE INTO research_tasks
            (task_id, interaction_id, query, status, progress, current_action,
             enable_notifications, tokens_input, tokens_output, cost_usd,
             error_message, created_at, updated_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.task_id, task.interaction_id, task.query, task.status.value,
            task.progress, task.current_action, task.enable_notifications,
            task.tokens_input, task.tokens_output, task.cost_usd,
            task.error_message, task.created_at.isoformat(),
            datetime.utcnow().isoformat(),
            task.completed_at.isoformat() if task.completed_at else None
        ))
        conn.commit()
        conn.close()

    def get_task(self, task_id: str) -> Optional[ResearchTask]:
        """Retrieve a task by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM research_tasks WHERE task_id = ?", (task_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return ResearchTask(
            task_id=row['task_id'],
            interaction_id=row['interaction_id'],
            query=row['query'],
            status=TaskStatus(row['status']),
            progress=row['progress'],
            current_action=row['current_action'] or "",
            enable_notifications=bool(row['enable_notifications']),
            tokens_input=row['tokens_input'],
            tokens_output=row['tokens_output'],
            cost_usd=row['cost_usd'],
            error_message=row['error_message'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None
        )

    def get_incomplete_tasks(self) -> List[Tuple[str, str]]:
        """Get tasks that need to be resumed on startup."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT task_id, interaction_id FROM research_tasks WHERE status = 'running'"
        )
        tasks = cursor.fetchall()
        conn.close()
        return tasks

    def save_result(self, task_id: str, result: ResearchResult) -> None:
        """Save research results."""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT OR REPLACE INTO research_results
            (task_id, report_markdown, sources_json, metadata_json)
            VALUES (?, ?, ?, ?)
        ''', (
            task_id,
            result.report,
            json.dumps([vars(s) if hasattr(s, '__dict__') else s for s in result.sources]),
            json.dumps(result.metadata)
        ))
        conn.commit()
        conn.close()

    def get_result(self, task_id: str) -> Optional[ResearchResult]:
        """Retrieve research results by task ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM research_results WHERE task_id = ?", (task_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return ResearchResult(
            task_id=row['task_id'],
            report=row['report_markdown'],
            sources=json.loads(row['sources_json']) if row['sources_json'] else [],
            metadata=json.loads(row['metadata_json']) if row['metadata_json'] else {}
        )
```

---

## File Storage Schema

### Markdown Report Structure

```
research_reports/
├── 2025-12/
│   ├── research_abc-123_20251214_103045.md
│   ├── research_def-456_20251214_110230.md
│   └── research_ghi-789_20251214_113415.md
└── 2025-11/
    └── research_xyz-890_20251130_152030.md
```

### Filename Pattern

```
{prefix}_{task_id}_{YYYYMMDD}_{HHMMSS}.md
```

Components:
- `prefix`: User-configurable (default: "research")
- `task_id`: First 8 characters of UUID
- `YYYYMMDD`: Date in ISO format
- `HHMMSS`: Time in 24-hour format

---

## Entity Relationships

```
ResearchTask (1) ──────────────────── (0..1) ResearchResult
     │                                       │
     │ status: COMPLETED                     │ sources
     │                                       │
     │                                       ▼
     │                                (N) Source
     │
     │ save_research_to_markdown()
     │
     ▼
Markdown File (0..1)
```

### Lifecycle Flow

```
1. start_deep_research()
   └─> Creates ResearchTask (status: PENDING)
   └─> Spawns asyncio background task

2. Background execution
   └─> Updates ResearchTask (status: RUNNING)
   └─> Stores interaction_id for recovery
   └─> Periodically updates progress

3. Completion
   └─> Creates ResearchResult
   └─> Updates ResearchTask (status: COMPLETED)
   └─> Sends desktop notification

4. save_research_to_markdown()
   └─> Reads ResearchResult from SQLite
   └─> Renders Jinja2 template
   └─> Writes Markdown file
```

---

## Validation Rules

### ResearchTask

- `task_id`: Must be valid UUID v4
- `query`: Min 3 characters, max 10,000 characters
- `progress`: 0-100 inclusive
- `status`: Must be valid TaskStatus enum value

### ResearchResult

- `report`: Non-empty string
- `sources`: Can be empty list, but field required
- `metadata`: Must include `duration_minutes` and `cost_usd`

---

## Serialization

All complex objects serialized as JSON for:
- Security (no pickle execution risks)
- Portability (human-readable, cross-tool compatible)
- Debugging (easy inspection in SQLite browser)

```python
# Serialization example
import json
from dataclasses import asdict

task = ResearchTask(task_id="abc-123", query="...")
json_str = json.dumps(asdict(task), default=str)  # default=str handles datetime

# Deserialization
data = json.loads(json_str)
task = ResearchTask(**data)
```
