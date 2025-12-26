# MCP Tool Contracts: Hybrid Deep Research System

**Feature**: 001-hybrid-deep-research
**Date**: 2025-12-14
**Storage**: SQLite (zero external dependencies)

---

## Tool Summary

| Tool | Purpose | Token Cost | Async |
|------|---------|------------|-------|
| `start_deep_research` | Initiate research with hybrid execution | HIGH | Yes |
| `check_research_status` | Poll running task status | ZERO | No |
| `get_research_results` | Retrieve completed results | ZERO | No |
| `cancel_research` | Cancel running task | ZERO | No |
| `estimate_research_cost` | Pre-estimate cost/duration | LOW | No |
| `save_research_to_markdown` | Persist results to file | ZERO | No |

---

## Tool 1: `start_deep_research`

### Schema

```json
{
  "name": "start_deep_research",
  "description": "Start a deep research task using Gemini Deep Research API. Gemini Deep Research natively handles multi-hop reasoning, automatic query refinement, and source synthesis. This tool wraps that capability with hybrid sync-to-async execution using SQLite for state persistence and asyncio for background tasks.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Research question or topic to investigate",
        "minLength": 3,
        "maxLength": 10000
      },
      "enable_notifications": {
        "type": "boolean",
        "description": "Send desktop notification on completion",
        "default": true
      },
      "max_wait_hours": {
        "type": "integer",
        "description": "Maximum hours for async research before timeout",
        "default": 8,
        "minimum": 1,
        "maximum": 24
      },
      "model": {
        "type": "string",
        "description": "Gemini model for research",
        "default": "deep-research-pro-preview-12-2025"
      }
    },
    "required": ["query"]
  }
}
```

### Response: Sync Complete

```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "mode": "sync",
  "results": {
    "report": "# Research Report\n\n## Executive Summary\n...",
    "sources": [
      {
        "title": "Source Title",
        "url": "https://example.com/article",
        "relevance_score": 0.95
      }
    ],
    "metadata": {
      "duration_minutes": 2.5,
      "tokens_used": {"input": 15000, "output": 8000},
      "cost_usd": 0.05
    }
  }
}
```

### Response: Async Switch

```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running_async",
  "mode": "async",
  "message": "Research running in background. Desktop notification will be sent on completion.",
  "check_status_command": "check_research_status(task_id='550e8400-e29b-41d4-a716-446655440000')"
}
```

### Error Response

```json
{
  "success": false,
  "error": "GEMINI_UNAVAILABLE",
  "message": "Gemini API is not available: Invalid API key",
  "suggestion": "Check GEMINI_API_KEY in .env file"
}
```

---

## Tool 2: `check_research_status`

### Schema

```json
{
  "name": "check_research_status",
  "description": "Check status of a running deep research task. Zero token cost - reads from SQLite state.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": {
        "type": "string",
        "description": "Task UUID from start_deep_research",
        "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
      }
    },
    "required": ["task_id"]
  }
}
```

### Response: Running

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running_async",
  "progress": 65,
  "current_action": "Analyzing source 45/70...",
  "elapsed_minutes": 12.5,
  "tokens_used": {
    "input": 150000,
    "output": 50000
  },
  "cost_so_far": 0.90,
  "estimated_completion_minutes": 8
}
```

### Response: Completed

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "current_action": "Research complete",
  "elapsed_minutes": 18.5,
  "message": "Use get_research_results(task_id='550e8400-e29b-41d4-a716-446655440000') to retrieve results"
}
```

### Error Response

```json
{
  "success": false,
  "error": "TASK_NOT_FOUND",
  "message": "No research task found with ID: 550e8400-e29b-41d4-a716-446655440000",
  "suggestion": "Verify task_id from start_deep_research response"
}
```

---

## Tool 3: `get_research_results`

### Schema

```json
{
  "name": "get_research_results",
  "description": "Retrieve completed research results. Zero token cost - reads from SQLite result store.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": {
        "type": "string",
        "description": "Task UUID",
        "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
      },
      "include_sources": {
        "type": "boolean",
        "description": "Include source list in response",
        "default": true
      }
    },
    "required": ["task_id"]
  }
}
```

### Response: Success

```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "What are the latest developments in quantum computing?",
  "report": "# Research Report: Quantum Computing Developments\n\n## Executive Summary\n\nQuantum computing has seen significant advances in 2025...\n\n## Key Findings\n\n### 1. Hardware Breakthroughs\n...\n\n### 2. Software Advances\n...\n\n## Conclusion\n...",
  "sources": [
    {
      "title": "IBM Quantum Roadmap 2025",
      "url": "https://research.ibm.com/quantum-roadmap",
      "snippet": "IBM announces 100,000 qubit target...",
      "relevance_score": 0.98
    },
    {
      "title": "Google Willow Chip Announcement",
      "url": "https://blog.google/quantum",
      "snippet": "Error correction milestone achieved...",
      "relevance_score": 0.95
    }
  ],
  "metadata": {
    "duration_minutes": 18.5,
    "tokens_used": {
      "input": 450000,
      "output": 120000
    },
    "cost_usd": 3.24,
    "mode": "async",
    "model": "deep-research-pro-preview-12-2025",
    "source_count": 47,
    "started_at": "2025-12-14T10:15:30Z",
    "completed_at": "2025-12-14T10:34:00Z"
  }
}
```

### Error Response: Not Completed

```json
{
  "success": false,
  "error": "RESEARCH_NOT_COMPLETED",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running_async",
  "progress": 65,
  "message": "Research is still in progress. Current progress: 65%",
  "suggestion": "Wait for completion or use check_research_status to monitor"
}
```

---

## Tool 4: `cancel_research`

### Schema

```json
{
  "name": "cancel_research",
  "description": "Cancel a running research task. Optionally save partial results.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": {
        "type": "string",
        "description": "Task UUID",
        "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
      },
      "save_partial": {
        "type": "boolean",
        "description": "Save partial results before canceling",
        "default": true
      }
    },
    "required": ["task_id"]
  }
}
```

### Response: Success

```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "partial_results_saved": true,
  "progress_at_cancellation": 65,
  "cost_usd": 0.90,
  "message": "Research cancelled. Partial results saved and accessible via get_research_results."
}
```

### Error Response: Already Completed

```json
{
  "success": false,
  "error": "RESEARCH_ALREADY_COMPLETED",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Cannot cancel: research already completed",
  "suggestion": "Use get_research_results to retrieve completed research"
}
```

---

## Tool 5: `estimate_research_cost`

### Schema

```json
{
  "name": "estimate_research_cost",
  "description": "Estimate cost and duration before starting research. Analyzes query complexity.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Research question to estimate",
        "minLength": 3,
        "maxLength": 10000
      }
    },
    "required": ["query"]
  }
}
```

### Response

```json
{
  "query": "What are the geopolitical implications of AI regulation differences between US, EU, and China?",
  "query_complexity": "complex",
  "estimated_duration": {
    "min_minutes": 15,
    "max_minutes": 60,
    "likely_minutes": 35
  },
  "estimated_cost": {
    "min_usd": 1.50,
    "max_usd": 6.00,
    "likely_usd": 3.00
  },
  "will_likely_go_async": true,
  "recommendation": "Complex multi-domain query detected. Will likely require 30+ minutes and switch to async mode. Consider breaking into smaller focused queries if time is critical."
}
```

---

## Tool 6: `save_research_to_markdown`

### Schema

```json
{
  "name": "save_research_to_markdown",
  "description": "Save completed research to permanent Markdown file. Zero token cost - uses Jinja2 templates.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task_id": {
        "type": "string",
        "description": "Task UUID",
        "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
      },
      "output_dir": {
        "type": "string",
        "description": "Directory for output files",
        "default": "./research_reports"
      },
      "filename_prefix": {
        "type": "string",
        "description": "Prefix for filename",
        "default": "research"
      },
      "include_metadata": {
        "type": "boolean",
        "description": "Include metadata section in output",
        "default": true
      },
      "include_sources": {
        "type": "boolean",
        "description": "Include sources section in output",
        "default": true
      }
    },
    "required": ["task_id"]
  }
}
```

### Response: Success

```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_path": "/home/user/research_reports/2025-12/research_550e8400_20251214_103045.md",
  "filename": "research_550e8400_20251214_103045.md",
  "file_size_kb": 45.2,
  "created_at": "2025-12-14T10:30:45Z",
  "sections_included": ["metadata", "executive_summary", "findings", "sources", "conclusion"]
}
```

### Error Response: Research Not Completed

```json
{
  "success": false,
  "error": "RESEARCH_NOT_COMPLETED",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running_async",
  "progress": 65,
  "message": "Cannot save: research still in progress (65%)",
  "suggestion": "Wait for completion before saving to Markdown"
}
```

### Error Response: Disk Full

```json
{
  "success": false,
  "error": "DISK_FULL",
  "file_path": "/home/user/research_reports/2025-12/research_550e8400_20251214_103045.md",
  "required_kb": 50,
  "available_kb": 10,
  "message": "Insufficient disk space to save report",
  "suggestion": "Free up disk space or specify alternative output_dir"
}
```

---

## Error Codes Reference

| Code | Description | HTTP Equivalent |
|------|-------------|-----------------|
| `GEMINI_UNAVAILABLE` | Gemini API not accessible | 503 |
| `INVALID_QUERY` | Query too short/long or malformed | 400 |
| `TASK_NOT_FOUND` | No task with given ID | 404 |
| `RESEARCH_NOT_COMPLETED` | Task still in progress | 409 |
| `RESEARCH_ALREADY_COMPLETED` | Cannot cancel completed task | 409 |
| `RESEARCH_FAILED` | Task failed during execution | 500 |
| `SQLITE_ERROR` | SQLite database error | 500 |
| `DISK_FULL` | Insufficient disk space | 507 |
| `PERMISSION_DENIED` | Cannot write to output_dir | 403 |

---

## Graceful Degradation

Per Constitution Principle III, all tools check availability before operations:

```python
if not GEMINI_AVAILABLE or not client:
    return {
        "success": False,
        "error": "GEMINI_UNAVAILABLE",
        "message": f"Gemini API is not available: {GEMINI_ERROR}",
        "suggestion": "Check GEMINI_API_KEY in .env file"
    }
```

Server remains operational even when external services fail, with clear diagnostic information.
