# Feature Specification: Hybrid Deep Research System

**Feature Branch**: `001-hybrid-deep-research`
**Created**: 2025-12-14
**Status**: Ready for Implementation
**Input**: PRD documents from `/prd/` directory

## Overview

Add 6 new MCP tools to the Gemini MCP Server wrapping Google's Gemini Deep Research API with a hybrid synchronous-to-asynchronous execution model, native OS notifications, and permanent Markdown file persistence.

### Key Design Principle: Zero Setup Required

The current MCP server runs with a single command (`uv run python server.py`) - no Docker, no external services. This feature **preserves that simplicity**:

- **Default**: SQLite + asyncio (zero external dependencies)
- **Optional Future**: Redis + Celery (for power users who need distributed workers)

Users just start the MCP server. Everything else is automatic.

### Key Insight: Native Multi-Hop

Gemini Deep Research API **natively handles** multi-hop reasoning and automatic research cycles. The API autonomously:
- Formulates and refines queries
- Navigates complex information landscapes
- Identifies knowledge gaps and iteratively improves results
- Synthesizes information from multiple sources

We do NOT need to implement multi-hop orchestration - Gemini does this automatically.

### New Tools Summary

| Tool | Purpose | Token Cost |
|------|---------|------------|
| `start_deep_research` | Wrap Gemini Deep Research with hybrid sync→async switching | HIGH (10K-500K+) |
| `check_research_status` | Poll status of running research | ZERO (SQLite read) |
| `get_research_results` | Retrieve completed results | ZERO (SQLite read) |
| `cancel_research` | Cancel running research | ZERO (local operation) |
| `estimate_research_cost` | Estimate before starting | LOW (<1K tokens) |
| `save_research_to_markdown` | Save results to permanent MD files | ZERO (Jinja2 template) |

**Token Cost Legend**: ZERO = no LLM tokens consumed; LOW = <1,000 tokens; HIGH = 10,000+ tokens (Gemini Deep Research API)

## User Scenarios & Testing

### User Story 1 - Synchronous Research with Auto-Async Fallback (Priority: P1)

User asks a research question. The system attempts synchronous execution first, but Gemini Deep Research typically requires background execution due to its multi-hop nature. The system auto-switches to async mode when Gemini returns an async response.

**Why this priority**: Core MVP functionality - all research queries flow through this tool. Without this, there's no research capability.

**Reality Check**: Gemini Deep Research is designed for long-running tasks (5-15 minutes typical, up to hours for complex queries). Most queries will switch to async mode - synchronous completion is the exception, not the rule.

**Independent Test**: Can be tested by calling `start_deep_research` and verifying either immediate results OR async task_id returned within 30 seconds.

**Acceptance Scenarios**:

1. **Given** user calls `start_deep_research`, **When** Gemini returns synchronous response (simple queries), **Then** results are returned immediately with full report, sources, and cost metadata.

2. **Given** user calls `start_deep_research`, **When** Gemini signals async execution is required (typical case), **Then** return task_id within 30 seconds and continue in background.

3. **Given** user calls `start_deep_research`, **When** the query is empty or invalid, **Then** return 400 error with clear error message.

4. **Given** Gemini API is unavailable, **When** user calls `start_deep_research`, **Then** return graceful error with diagnostic information (per constitution Principle III).

---

### User Story 2 - Long-Running Async Research with Notifications (Priority: P2)

User asks a complex research question. The system runs in async mode (typical case), continues in background via asyncio task, and sends a native OS desktop notification when complete. Research may take 5-15 minutes for typical queries, potentially hours for complex ones. Task state is persisted to SQLite for crash recovery.

**Why this priority**: Critical for handling complex queries without blocking. This is what differentiates "Deep Research" from simple queries.

**Independent Test**: Can be tested by asking a complex multi-topic query and verifying: (1) async switch response with task_id, (2) status polling works, (3) notification appears on completion, (4) results retrievable.

**Acceptance Scenarios**:

1. **Given** user calls `start_deep_research` with any query, **When** Gemini signals async execution (typical), **Then** system returns task_id within 30 seconds and continues in background.

2. **Given** research is running async, **When** user calls `check_research_status(task_id)`, **Then** return current progress percentage, elapsed time, and estimated completion.

3. **Given** async research completes, **When** `enable_notifications=True`, **Then** native OS notification appears on user's desktop (Linux/macOS/Windows).

4. **Given** async research completes, **When** user calls `get_research_results(task_id)`, **Then** return full report, sources, and metadata.

---

### User Story 3 - Cost Estimation Before Research (Priority: P3)

User wants to know estimated cost and duration before starting potentially expensive research. System analyzes query complexity and provides estimates.

**Why this priority**: Important for cost control but not blocking core functionality.

**Independent Test**: Can be tested by calling `estimate_research_cost` with various query complexities and verifying reasonable estimates returned.

**Acceptance Scenarios**:

1. **Given** user calls `estimate_research_cost` with query, **When** analysis completes, **Then** return complexity classification (simple/medium/complex), estimated duration range, and estimated cost range in USD.

2. **Given** complex query detected, **When** user estimates cost, **Then** show likelihood of async mode and higher cost range.

---

### User Story 4 - Cancel Running Research (Priority: P4)

User needs to cancel a long-running research task and optionally save partial results.

**Why this priority**: Important for user control but edge case - most users won't cancel.

**Independent Test**: Can be tested by starting async research, calling `cancel_research`, and verifying task stops and partial results are accessible.

**Acceptance Scenarios**:

1. **Given** research is running async, **When** user calls `cancel_research(task_id, save_partial=True)`, **Then** cancel background task, save partial results to SQLite, return final cost.

2. **Given** research is already completed, **When** user calls `cancel_research`, **Then** return error indicating research already completed.

---

### User Story 5 - Save Research to Permanent Markdown (Priority: P5)

User wants to save completed research to permanent Markdown files for later reference, sharing, and version control. Uses Jinja2 templates with zero LLM token cost.

**Why this priority**: Important for research library management but research must complete first.

**Independent Test**: Can be tested by completing research, calling `save_research_to_markdown`, and verifying clean MD file created at expected path.

**Acceptance Scenarios**:

1. **Given** research completed, **When** user calls `save_research_to_markdown(task_id)`, **Then** create formatted MD file in `{output_dir}/{YYYY-MM}/{prefix}_{task_id}_{timestamp}.md`.

2. **Given** research not completed, **When** user calls `save_research_to_markdown`, **Then** return error with current status.

3. **Given** `include_metadata=False`, **When** saving, **Then** omit metadata section (smaller file).

---

### Edge Cases

- What happens when MCP server restarts mid-research?
  - SQLite persists task state including Gemini `interaction_id`
  - On startup, server resumes polling incomplete tasks from SQLite
  - Gemini holds actual research state server-side - we just need the interaction_id

- What happens when SQLite write fails (disk full, permissions)?
  - Graceful error with clear message, research continues in memory
  - Results still saved to Markdown as backup

- What happens when user's machine loses network during async research?
  - Research continues on Gemini's servers
  - When connection restored, polling resumes automatically
  - Notification sent when research completes

- What happens when Gemini interaction_id is stale/expired on startup recovery?
  - Gemini may reject polling requests for old interaction_ids (TTL unknown)
  - System attempts to poll; if Gemini returns 404/expired error, mark task FAILED
  - Error message: "Research session expired on Gemini servers. Task was interrupted and cannot be recovered."
  - User can view partial results if any were saved before crash

- What happens when notification library unavailable (notifypy, plyer both fail)?
  - Graceful fallback to console print (log message)

- What happens when output directory doesn't exist for Markdown save?
  - Create directory automatically (mkdir -p equivalent)

- What happens when disk is full during Markdown save?
  - Return clear error message with file path and required space

## Requirements

### Functional Requirements

- **FR-001**: System MUST implement 6 new MCP tools following FastMCP `@mcp.tool()` decorator pattern (Constitution Principle I)
- **FR-002**: System MUST remain in single `server.py` file with supporting modules in `deep_research/` directory (Constitution Principle II)
- **FR-003**: System MUST gracefully degrade when Gemini API unavailable (Constitution Principle III)
- **FR-004**: All tools MUST have comprehensive docstrings with use cases (Constitution Principle IV)
- **FR-005**: System MUST increment `__version__` to next MINOR version (Constitution Principle V)
- **FR-006**: System MUST auto-switch to async mode when Gemini API returns async response (typical case for Deep Research)
- **FR-007**: System MUST send native OS notifications (Linux/macOS/Windows) on async completion
- **FR-008**: System MUST persist research state in SQLite for crash recovery (stores interaction_id, status, timestamps)
- **FR-009**: System MUST use asyncio for background task execution (zero external dependencies)
- **FR-009a**: System MAY optionally support Redis + Celery backend via configuration (future enhancement)
- **FR-010**: System MUST save Markdown files using Jinja2 templates (zero LLM tokens)
- **FR-011**: `start_deep_research` MUST wrap Google's native Gemini Deep Research API (which handles multi-hop reasoning automatically)
- **FR-012**: System MUST track and report token usage and cost for all operations

### Non-Functional Requirements

- **NFR-001**: Initial API call and async task_id return MUST be under 30 seconds
- **NFR-002**: Async transition response to user MUST be under 30 seconds
- **NFR-003**: Status check response MUST be under 100ms
- **NFR-004**: Notification delivery MUST be under 2 seconds after completion
- **NFR-005**: Markdown template rendering MUST be under 100ms
- **NFR-006**: System MUST handle 3+ concurrent async research tasks via asyncio (I/O-bound, not CPU-bound)
- **NFR-007**: System MUST resume incomplete research tasks on server startup (from SQLite state)

### Key Entities

- **ResearchTask**: Represents a research operation with task_id, query, status, progress, timestamps, notification config
- **ResearchResult**: Contains report markdown, sources list, metadata (tokens, cost, duration)
- **ResearchState**: Serializable checkpoint for engine state (progress, partial results, current step)

## Architecture

### Module Structure

```
gemini-mcp/
├── server.py                    # MODIFY: Add 6 @mcp.tool() functions + startup recovery
├── deep_research/              # CREATE: New module
│   ├── __init__.py
│   ├── engine.py              # DeepResearchEngine wrapping Gemini Deep Research API
│   ├── state_manager.py       # SQLite state persistence (zero external deps)
│   ├── notification.py        # Native OS notifications (notifypy with fallback)
│   ├── cost_estimator.py      # Cost/duration estimation
│   ├── storage.py             # Markdown file persistence
│   ├── background.py          # Asyncio background task management
│   └── templates/
│       └── research_report.md.j2  # Jinja2 template
├── research_reports/          # CREATE: Output directory for MD files
├── deep_research.db           # AUTO-CREATED: SQLite database (gitignored)
└── requirements.txt            # MODIFY: Add minimal dependencies
```

### New Dependencies

```txt
# Required (minimal)
notify-py>=0.3.42      # Desktop notifications (with fallback if unavailable)
Jinja2>=3.1.0          # Markdown template rendering

# Already available (stdlib)
# sqlite3              # State persistence (Python stdlib)
# asyncio              # Background tasks (Python stdlib)

# Optional (future enhancement)
# redis>=5.0.0         # Distributed state (if REDIS_URL configured)
# celery>=5.3.0        # Distributed workers (if CELERY_BROKER_URL configured)
```

### State Management

SQLite tables (in `deep_research.db`):

```sql
-- Task metadata and status
CREATE TABLE research_tasks (
    task_id TEXT PRIMARY KEY,
    interaction_id TEXT,          -- Gemini's server-side ID (key for recovery!)
    query TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    progress INTEGER DEFAULT 0,
    enable_notifications BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Completed results (for retrieval without re-querying Gemini)
CREATE TABLE research_results (
    task_id TEXT PRIMARY KEY,
    report_markdown TEXT,
    sources_json TEXT,            -- JSON array of source objects
    metadata_json TEXT,           -- JSON with tokens, cost, duration
    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id)
);
```

**Key insight**: The `interaction_id` from Gemini is the critical recovery field. Even if our server crashes, Gemini holds the research state - we just need to resume polling with the saved interaction_id.

## Tool Specifications

### Tool 1: `start_deep_research`

```python
@mcp.tool()
async def start_deep_research(
    query: str,
    enable_notifications: bool = True,
    max_wait_hours: int = 8,
    model: str = "deep-research-pro-preview-12-2025"
) -> Dict[str, Any]:
```

**Parameters**:
- `query`: The research question
- `enable_notifications`: Send native OS notification on completion (default: True)
- `max_wait_hours`: Maximum hours for async research before timeout (default: 8)
- `model`: Gemini model for deep research (default: deep-research-pro-preview-12-2025 for optimal research capabilities)

**Note**: Gemini Deep Research API natively performs multi-hop reasoning - no parameter needed. Research typically takes 5-15 minutes, complex queries may take hours.

**Returns** (sync complete):
```json
{
  "success": true,
  "task_id": "uuid",
  "status": "completed",
  "mode": "sync",
  "results": {"report": "...", "sources": [...], "metadata": {...}},
  "cost_usd": 1.25
}
```

**Returns** (async switch):
```json
{
  "success": true,
  "task_id": "uuid",
  "status": "running_async",
  "mode": "async",
  "message": "Research running in background. Notification when complete.",
  "check_status_command": "check_research_status(task_id='uuid')"
}
```

### Tool 2: `check_research_status`

```python
@mcp.tool()
def check_research_status(task_id: str) -> Dict[str, Any]:
```

**Returns**:
```json
{
  "task_id": "uuid",
  "status": "running_async",
  "progress": 65,
  "current_action": "Analyzing source 45/100...",
  "elapsed_minutes": 12.5,
  "tokens_used": {"input": 150000, "output": 50000},
  "cost_so_far": 0.90,
  "estimated_completion_minutes": 8
}
```

### Tool 3: `get_research_results`

```python
@mcp.tool()
def get_research_results(task_id: str, include_sources: bool = True) -> Dict[str, Any]:
```

**Returns**:
```json
{
  "success": true,
  "task_id": "uuid",
  "query": "Original query",
  "report": "# Research Report\n\n...",
  "sources": [...],
  "metadata": {
    "duration_minutes": 18.5,
    "tokens_used": {"input": 450000, "output": 120000},
    "cost_usd": 3.24,
    "mode": "async"
  }
}
```

### Tool 4: `cancel_research`

```python
@mcp.tool()
def cancel_research(task_id: str, save_partial: bool = True) -> Dict[str, Any]:
```

### Tool 5: `estimate_research_cost`

```python
@mcp.tool()
def estimate_research_cost(query: str) -> Dict[str, Any]:
```

**Note**: Estimates are based on query complexity. Gemini Deep Research handles depth automatically.

**Returns**:
```json
{
  "query_complexity": "medium",
  "estimated_duration": {"min_minutes": 15, "max_minutes": 45, "likely_minutes": 30},
  "estimated_cost": {"min_usd": 0.50, "max_usd": 3.00, "likely_usd": 1.50},
  "will_likely_go_async": true,
  "recommendation": "Complex query detected. May switch to async mode."
}
```

### Tool 6: `save_research_to_markdown`

```python
@mcp.tool()
def save_research_to_markdown(
    task_id: str,
    output_dir: str = "./research_reports",
    filename_prefix: str = "research",
    include_metadata: bool = True,
    include_sources: bool = True
) -> Dict[str, Any]:
```

**Returns**:
```json
{
  "success": true,
  "task_id": "abc-123",
  "file_path": "/path/to/research_reports/2025-12/research_abc-123_20251214_103045.md",
  "file_size_kb": 45.2,
  "filename": "research_abc-123_20251214_103045.md",
  "created_at": "2025-12-14T10:30:45Z"
}
```

## Success Criteria

### Measurable Outcomes

- **SC-001**: Gemini API response handling accuracy = 100% (correctly parse sync vs async response)
- **SC-002**: Notification delivery rate ≥ 99% across platforms
- **SC-003**: State recovery rate = 100% after server restart (via SQLite + interaction_id)
- **SC-004**: Cost estimation accuracy ± 10% of actual
- **SC-005**: Async completion rate ≥ 95% within max_wait_hours
- **SC-006**: Markdown save success rate ≥ 99.9%
- **SC-007**: Zero token cost for `check_research_status`, `get_research_results`, `cancel_research`, `save_research_to_markdown`

### Performance Metrics

- **PM-001**: Initial API call response < 30 seconds (returns task_id for async or immediate results for sync)
- **PM-002**: Status check latency < 100ms
- **PM-003**: Notification latency < 2 seconds post-completion
- **PM-004**: Template rendering < 100ms
