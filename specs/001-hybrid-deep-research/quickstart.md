# Quickstart: Hybrid Deep Research System

**Feature**: 001-hybrid-deep-research
**Date**: 2025-12-14

---

## Prerequisites

- Python 3.11+
- Gemini API key with Deep Research access
- `uv` package manager (recommended)

**Note**: No Redis, Celery, or Docker required! The system uses SQLite + asyncio for zero-dependency background task execution.

---

## Installation

### 1. Install Dependencies

```bash
cd gemini-mcp
uv sync  # or: pip install -r requirements.txt
```

### 2. Configure Environment

Create/update `.env` file:

```bash
# Gemini API (required)
GEMINI_API_KEY=your_gemini_api_key_here

# Output directory (optional)
RESEARCH_REPORTS_DIR=./research_reports
```

### 3. Run MCP Server

```bash
uv run python server.py
```

That's it! No Redis, no Celery workers, no Docker containers. Just start the server.

---

## Basic Usage

### Start Research

```python
# Via MCP tool call
result = await start_deep_research(
    query="What are the latest breakthroughs in fusion energy?",
    enable_notifications=True,
    max_wait_hours=8
)

# Response (sync complete - rare, for simple queries)
{
    "success": True,
    "task_id": "abc-123...",
    "status": "completed",
    "results": {...}
}

# Response (async switch - typical)
{
    "success": True,
    "task_id": "abc-123...",
    "status": "running_async",
    "message": "Research running in background..."
}
```

### Check Status (async research)

```python
status = check_research_status(task_id="abc-123...")

# Response
{
    "status": "running_async",
    "progress": 65,
    "current_action": "Analyzing source 45/70...",
    "elapsed_minutes": 12.5,
    "estimated_completion_minutes": 8
}
```

### Get Results

```python
results = get_research_results(task_id="abc-123...", include_sources=True)

# Response
{
    "report": "# Research Report\n\n...",
    "sources": [...],
    "metadata": {
        "duration_minutes": 18.5,
        "cost_usd": 3.24
    }
}
```

### Save to Markdown

```python
saved = save_research_to_markdown(
    task_id="abc-123...",
    output_dir="./research_reports",
    filename_prefix="fusion"
)

# Response
{
    "file_path": "./research_reports/2025-12/fusion_abc-123_20251214_103045.md",
    "file_size_kb": 45.2
}
```

---

## Example Workflows

### Simple Research (likely sync)

```python
# Short, focused query - may complete synchronously
result = await start_deep_research(
    query="What is the current price of Bitcoin?",
    enable_notifications=False
)

if result["status"] == "completed":
    print(result["results"]["report"])
```

### Complex Research (async with notification)

```python
# Complex multi-domain query - will go async
result = await start_deep_research(
    query="Compare the AI regulation approaches of the US, EU, and China, including recent 2025 developments",
    enable_notifications=True,
    max_wait_hours=8
)

# Returns immediately with task_id
task_id = result["task_id"]
print(f"Research started: {task_id}")

# Desktop notification will appear when complete
# Or poll manually:
while True:
    status = check_research_status(task_id=task_id)
    if status["status"] == "completed":
        break
    print(f"Progress: {status['progress']}%")
    time.sleep(60)  # Check every minute

# Get and save results
results = get_research_results(task_id=task_id)
save_research_to_markdown(task_id=task_id)
```

### Cost-Aware Research

```python
# Estimate before starting
estimate = estimate_research_cost(
    query="Comprehensive analysis of global semiconductor supply chains"
)

print(f"Complexity: {estimate['query_complexity']}")
print(f"Estimated time: {estimate['estimated_duration']['likely_minutes']} minutes")
print(f"Estimated cost: ${estimate['estimated_cost']['likely_usd']:.2f}")
print(f"Will go async: {estimate['will_likely_go_async']}")

# User decides to proceed
if input("Proceed? (y/n): ").lower() == "y":
    result = await start_deep_research(query=estimate["query"])
```

---

## Troubleshooting

### "GEMINI_UNAVAILABLE" Error

**Cause**: Gemini API key invalid or not configured.

**Fix**:
```bash
# Verify .env file
cat .env | grep GEMINI_API_KEY

# Test API key
uv run python -c "
from google import genai
from dotenv import load_dotenv
import os
load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
print('API key valid!' if client else 'Invalid')
"
```

### No Desktop Notification

**Cause**: notify-py not installed, or system notification service unavailable.

**Fix**:
```bash
# Install notification library
pip install notify-py

# Test notification
python -c "
from notifypy import Notify
n = Notify()
n.title = 'Test'
n.message = 'Notification working!'
n.send()
"

# Linux: ensure libnotify is installed
sudo apt install libnotify-bin  # Debian/Ubuntu
```

### Research Task Not Found After Restart

**Cause**: This should not happen - SQLite persists tasks across restarts.

**Fix**:
```bash
# Check database exists
ls -la deep_research.db

# Query incomplete tasks
sqlite3 deep_research.db "SELECT task_id, status FROM research_tasks WHERE status = 'running';"
```

### SQLite "Database Locked" Error

**Cause**: Multiple processes accessing the database (rare with single MCP server).

**Fix**:
The StateManager uses WAL mode for better concurrency. If issues persist:
```bash
# Close all connections and restart server
pkill -f "python server.py"
uv run python server.py
```

---

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | (required) | Gemini API key |
| `RESEARCH_REPORTS_DIR` | `./research_reports` | Default output directory |

### Tool Defaults

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_notifications` | `true` | Send desktop notification |
| `max_wait_hours` | `8` | Maximum async duration |
| `model` | `deep-research-pro-preview-12-2025` | Gemini model |
| `include_sources` | `true` | Include sources in results |
| `include_metadata` | `true` | Include metadata in MD export |

---

## State Management

### SQLite Database

All task state is persisted in `deep_research.db`:
- Task metadata and status
- Gemini interaction IDs (for crash recovery)
- Completed research results

### Crash Recovery

On server restart, incomplete tasks are automatically resumed:
1. Server queries SQLite for tasks with `status = 'running'`
2. For each incomplete task, spawns asyncio task to resume polling
3. Gemini holds actual research state - we just need the interaction_id

---

## Architecture Overview

```
User Request → MCP Tool (start_deep_research)
    ↓
SQLite (save task with task_id)
    ↓
Asyncio Background Task
    ↓
Gemini Deep Research API (interaction_id)
    ↓
Polling Loop (asyncio, updates SQLite)
    ↓
Desktop Notification → User
```

**Key Features**:
- Zero external dependencies (no Redis, Celery, Docker)
- Single process (MCP server handles everything)
- Crash recovery via SQLite + Gemini interaction_id
- Cross-platform notifications (notify-py with fallbacks)

---

## Verification Checklist

After setup, verify each component:

- [ ] `uv run python server.py` starts without errors
- [ ] `server_info()` tool returns Gemini as available
- [ ] Test notification appears on desktop
- [ ] `estimate_research_cost()` returns valid estimate
- [ ] Simple query completes (sync or async)
- [ ] Markdown file saved to correct directory

---

## Next Steps

1. **Run first research**: Try a simple query to verify setup
2. **Test async flow**: Use a complex query to test background execution
3. **Check notifications**: Verify desktop notifications work
4. **Review reports**: Check generated Markdown files

For implementation details, see [plan.md](./plan.md).
