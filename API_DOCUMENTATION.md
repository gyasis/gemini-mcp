# Gemini MCP Server - API Documentation

**Version:** 3.7.1
**Protocol:** Model Context Protocol (MCP)
**SDK:** FastMCP 2.0+
**Base Model:** Gemini 3 Flash (gemini-3-flash-preview)
**Deep Research Model:** deep-research-pro-preview-12-2025

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Tool Categories](#tool-categories)
4. [Deep Research Tools](#deep-research-tools)
5. [Gemini Collaboration Tools](#gemini-collaboration-tools)
6. [File Management Tools](#file-management-tools)
7. [Token Economics](#token-economics)
8. [Error Handling](#error-handling)
9. [Usage Examples](#usage-examples)

---

## Overview

The Gemini MCP Server is an MCP-compliant server that exposes Google Gemini's AI capabilities as tools for AI assistants. It implements 19 specialized tools across three categories:

- **7 Deep Research Tools**: Long-running research with SQLite persistence
- **6 Gemini Collaboration Tools**: Direct Gemini integration for various tasks
- **6 File Management Tools**: Gemini cloud storage operations

### Key Features

- **FastMCP Task Support (v3.8.0)**: Native MCP background tasks for long-running operations
- **Zero-Cost Retrieval**: SQLite caching eliminates repeated API calls
- **Automatic Notifications**: Desktop notifications when research completes
- **Multi-Modal Support**: Text, images (up to 3,600), and video analysis
- **Hybrid Execution**: Automatic sync-to-async switching for optimal performance

---

## Authentication

### Setup

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY="YOUR_API_KEY_HERE"
```

### Verification

Use the `server_info` tool to verify authentication:

```python
server_info()
# Returns: "Server v3.7.1 - Gemini connected and ready!"
```

---

## Tool Categories

### Quick Reference

| Tool | Category | Token Cost | FastMCP Task | Purpose |
|------|----------|-----------|--------------|---------|
| `start_deep_research` | Deep Research | HIGH | ✅ | Start long-running research |
| `get_research_results` | Deep Research | ZERO | ❌ | Retrieve cached results |
| `check_research_status` | Deep Research | ZERO | ❌ | Monitor progress |
| `cancel_research` | Deep Research | ZERO | ❌ | Cancel running task |
| `resume_research` | Deep Research | VARIABLE | ❌ | Resume failed task |
| `estimate_research_cost` | Deep Research | ZERO | ❌ | Pre-execution cost analysis |
| `save_research_to_markdown` | Deep Research | ZERO | ❌ | Export to Markdown |
| `ask_gemini` | Collaboration | MEDIUM | ❌ | General Q&A |
| `gemini_code_review` | Collaboration | MEDIUM | ❌ | Code quality review |
| `gemini_brainstorm` | Collaboration | MEDIUM | ❌ | Creative ideation |
| `gemini_debug` | Collaboration | MEDIUM | ❌ | Error diagnosis |
| `gemini_research` | Collaboration | MEDIUM | ❌ | Google Search grounded |
| `interpret_image` | Collaboration | MEDIUM | ❌ | Image/video analysis |
| `server_info` | File Management | ZERO | ❌ | Server status |
| `check_file_status` | File Management | ZERO | ❌ | Check file processing |
| `list_uploaded_files` | File Management | ZERO | ❌ | Browse Gemini storage |
| `get_last_uploaded_video` | File Management | ZERO | ❌ | Get recent upload |
| `delete_uploaded_file` | File Management | ZERO | ❌ | Delete from storage |
| `watch_video` | File Management | MEDIUM | ❌ | Analyze YouTube/local video |

---

## Deep Research Tools

### 1. start_deep_research

**Purpose**: Start a deep research task using Gemini Deep Research API with multi-hop reasoning.

**Token Cost**: HIGH (Gemini API usage)
**FastMCP Task**: ✅ Yes (v3.8.0)
**Expected Duration**: 5-60 minutes

#### Parameters

```python
async def start_deep_research(
    query: str,                    # Research question (3-10000 chars)
    enable_notifications: bool = True,  # Desktop notifications
    max_wait_hours: int = 8,       # Max async timeout (1-24)
    model: str = "deep-research-pro-preview-12-2025"
) -> Dict[str, Any]
```

#### Returns

```python
{
    "success": true,
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",  # or "running_async"
    "mode": "sync",  # or "async"
    "results": {
        "report": "# Research Report\n\n...",
        "sources": [
            {
                "title": "Source Title",
                "url": "https://example.com",
                "relevance_score": 0.95
            }
        ],
        "metadata": {
            "duration_minutes": 12.5,
            "tokens_used": {"input": 5000, "output": 8000},
            "cost_usd": 0.029
        }
    }
}
```

#### Usage Example

```python
# Start research
result = await start_deep_research(
    "What are the latest advances in quantum computing?",
    enable_notifications=True
)

# If completed synchronously (rare)
if result["status"] == "completed":
    print(result["results"]["report"])

# If running async (typical)
else:
    task_id = result["task_id"]
    # Continue other work - you'll be notified when complete
    # Then retrieve results:
    final = get_research_results(task_id)
```

#### Special Features (v3.8.0)

**FastMCP Native Tasks**: This tool uses `@mcp.tool(task=True)` decorator, enabling:
- **Automatic Notifications**: LLM clients notified via MCP protocol when complete
- **Progress Updates**: Real-time progress via `Progress` dependency injection
- **Token Savings**: Eliminates manual polling (98% reduction)
- **Background Execution**: LLM can multitask during research

**Progress Bridge Pattern**:
```python
def progress_bridge(progress_pct: int, action: str):
    """Bridge between engine callbacks and FastMCP progress reporting."""
    # Update SQLite (synchronous persistence)
    state_manager.update_task(task_id, {
        "progress": progress_pct,
        "current_action": action
    })
    # Schedule FastMCP progress updates (non-blocking)
    asyncio.create_task(progress.set_total(100))
    asyncio.create_task(progress.set_message(action))
```

**LLM Usage Pattern**:
```python
# Step 1: Start research (returns task_id)
result = await start_deep_research("quantum computing advances")

# Step 2: Continue other work (research runs in background)
# ... handle other user requests ...

# Step 3: FastMCP sends notification when complete (no polling!)

# Step 4: Retrieve results from SQLite cache (zero tokens)
final = get_research_results(result["task_id"])
```

#### Error Responses

```python
{
    "success": false,
    "error": "INVALID_QUERY",
    "message": "Query too short. Minimum 3 characters required.",
    "suggestion": "Provide a more detailed research question"
}
```

---

### 2. get_research_results

**Purpose**: Retrieve completed research results from SQLite storage (zero-cost retrieval).

**Token Cost**: ZERO (local SQLite read)
**FastMCP Task**: ❌ No

#### Parameters

```python
def get_research_results(
    task_id: str,              # UUID from start_deep_research
    include_sources: bool = True  # Include source list
) -> Dict[str, Any]
```

#### Returns

```python
{
    "success": true,
    "task_id": "550e8400-...",
    "query": "What are the latest advances in quantum computing?",
    "report": "# Quantum Computing Advances\n\n...",
    "sources": [
        {
            "title": "Nature: Quantum Breakthrough",
            "url": "https://nature.com/...",
            "relevance_score": 0.98
        }
    ],
    "metadata": {
        "duration_minutes": 15.3,
        "tokens_used": {"input": 6000, "output": 9000},
        "cost_usd": 0.042,
        "mode": "async",
        "model": "deep-research-pro-preview-12-2025",
        "source_count": 12,
        "started_at": "2025-01-10T10:00:00Z",
        "completed_at": "2025-01-10T10:15:18Z"
    }
}
```

#### Usage Example

```python
# Retrieve results after notification
result = get_research_results(
    task_id="550e8400-e29b-41d4-a716-446655440000",
    include_sources=True
)

if result["success"]:
    print(result["report"][:500])  # First 500 chars
    print(f"Sources: {len(result['sources'])}")
```

#### Error Responses

```python
{
    "success": false,
    "error": "RESEARCH_NOT_COMPLETED",
    "task_id": "550e8400-...",
    "status": "running_async",
    "progress": 45,
    "message": "Research is still in progress. Current progress: 45%",
    "suggestion": "Wait for completion or use check_research_status to monitor"
}
```

---

### 3. check_research_status

**Purpose**: Monitor async research task progress with hanging detection.

**Token Cost**: ZERO (local SQLite read)
**FastMCP Task**: ❌ No

#### Parameters

```python
def check_research_status(
    task_id: str  # UUID from start_deep_research
) -> Dict[str, Any]
```

#### Returns

```python
{
    "success": true,
    "task_id": "550e8400-...",
    "status": "running_async",
    "progress": 65,
    "current_action": "Analyzing source 8 of 12...",
    "elapsed_minutes": 8.5,
    "estimated_completion_minutes": 4.6,
    "tokens_used": {"input": 4000, "output": 5000},
    "cost_so_far": 0.024,
    "hanging_detection": {
        "is_hanging": false,
        "confidence": 0.15,
        "stall_minutes": 0.8,
        "reason": "Progress normal",
        "recommendation": "Continue monitoring"
    }
}
```

#### Usage Example

```python
# Check status
status = check_research_status("550e8400-...")

if status["status"] == "completed":
    print("Research complete! Use get_research_results to retrieve.")
else:
    print(f"Progress: {status['progress']}% - {status['current_action']}")

    # Check for hanging
    if status.get("hanging_detection", {}).get("is_hanging"):
        print(f"Warning: {status['hanging_detection']['reason']}")
        # Consider using resume_research
```

#### Hanging Detection

Activated after 5 minutes of elapsed time:

```python
{
    "hanging_detection": {
        "is_hanging": true,
        "confidence": 0.87,
        "stall_minutes": 3.2,
        "reason": "No progress updates for 3.2 minutes",
        "recommendation": "Use resume_research to attempt recovery"
    }
}
```

---

### 4. cancel_research

**Purpose**: Cancel a running research task with optional partial result saving.

**Token Cost**: ZERO (no Gemini API calls)
**FastMCP Task**: ❌ No

#### Parameters

```python
def cancel_research(
    task_id: str,           # UUID from start_deep_research
    save_partial: bool = True  # Save partial results
) -> Dict[str, Any]
```

#### Returns

```python
{
    "success": true,
    "task_id": "550e8400-...",
    "status": "cancelled",
    "partial_results_saved": true,
    "progress_at_cancellation": 45,
    "cost_usd": 0.018,
    "message": "Research cancelled. Partial results saved and accessible via get_research_results."
}
```

#### Usage Example

```python
# Cancel with partial save
result = cancel_research(
    task_id="550e8400-...",
    save_partial=True
)

if result["partial_results_saved"]:
    # Retrieve partial results
    partial = get_research_results(result["task_id"])
    print(partial["report"])
```

---

### 5. resume_research

**Purpose**: Resume a failed, hung, or interrupted research task.

**Token Cost**: ZERO if completed/failed, VARIABLE if polling continues
**FastMCP Task**: ❌ No

#### Parameters

```python
async def resume_research(
    task_id: str  # UUID from start_deep_research
) -> Dict[str, Any]
```

#### Returns

```python
{
    "success": true,
    "status": "completed",  # or "partial_results_saved"
    "task_id": "550e8400-...",
    "message": "Research completed successfully after resume.",
    "suggestion": "Use get_research_results(task_id='...') to retrieve full report"
}
```

#### Usage Example

```python
# Check if task is hanging
status = check_research_status("550e8400-...")

if status.get("hanging_detection", {}).get("is_hanging"):
    # Attempt resume
    result = await resume_research("550e8400-...")

    if result["status"] == "completed":
        final = get_research_results(result["task_id"])
    elif result["status"] == "partial_results_saved":
        print("Got partial results:", result["partial_report_preview"])
```

#### Recovery Features

- Checks if Gemini interaction is still available
- Retrieves cached intermediate results from streaming
- Returns partial results if research cannot be resumed
- Continues polling with streaming capture if still running

---

### 6. estimate_research_cost

**Purpose**: Estimate cost and duration before starting research using local heuristics.

**Token Cost**: ZERO (local analysis only)
**FastMCP Task**: ❌ No

#### Parameters

```python
def estimate_research_cost(
    query: str  # Research question to analyze (3-10000 chars)
) -> Dict[str, Any]
```

#### Returns

```python
{
    "query": "What are the latest advances in quantum computing?",
    "query_complexity": "complex",  # simple, medium, complex
    "estimated_duration": {
        "min_minutes": 15,
        "max_minutes": 35,
        "likely_minutes": 25
    },
    "estimated_cost": {
        "min_usd": 0.02,
        "max_usd": 0.08,
        "likely_usd": 0.05
    },
    "will_likely_go_async": true,
    "recommendation": "Complex query with multi-domain analysis. Expect 20-35 min duration."
}
```

#### Usage Example

```python
# Estimate before starting
estimate = estimate_research_cost(
    "What are the latest advances in quantum computing?"
)

print(f"Complexity: {estimate['query_complexity']}")
print(f"Estimated time: {estimate['estimated_duration']['likely_minutes']} min")
print(f"Estimated cost: ${estimate['estimated_cost']['likely_usd']}")

if estimate["will_likely_go_async"]:
    print("This will run asynchronously. Enable notifications recommended.")
```

#### Complexity Factors

- **Query length and structure**: Longer, multi-part queries = higher complexity
- **Multi-domain scope**: Comparing topics, regions, etc.
- **Temporal scope**: Historical analysis, forecasts
- **Synthesis requirements**: Analysis, evaluation, comparison

---

### 7. save_research_to_markdown

**Purpose**: Export completed research to formatted Markdown file using Jinja2 templates.

**Token Cost**: ZERO (local file operations only)
**FastMCP Task**: ❌ No

#### Parameters

```python
def save_research_to_markdown(
    task_id: str,
    output_dir: str = "./research_reports",
    filename_prefix: str = "research",
    include_metadata: bool = True,
    include_sources: bool = True
) -> Dict[str, Any]
```

#### Returns

```python
{
    "success": true,
    "file_path": "/path/to/research_reports/2025-01/research_550e8400_20250110_103045.md",
    "filename": "research_550e8400_20250110_103045.md",
    "file_size_kb": 45.3,
    "sections_included": ["metadata", "report", "sources"],
    "message": "Report saved successfully"
}
```

#### Usage Example

```python
# Save completed research
result = save_research_to_markdown(
    task_id="550e8400-...",
    output_dir="./my_research",
    filename_prefix="quantum_research",
    include_metadata=True,
    include_sources=True
)

print(f"Saved to: {result['file_path']}")
print(f"File size: {result['file_size_kb']} KB")
```

#### File Organization

Reports are organized by month:
```
./research_reports/
├── 2025-01/
│   ├── research_550e8400_20250110_103045.md
│   └── research_abc12345_20250110_154523.md
└── 2025-02/
    └── research_def67890_20250201_093012.md
```

#### Markdown Template Structure

```markdown
# Research Report: [Query]

**Task ID**: 550e8400-...
**Model**: deep-research-pro-preview-12-2025
**Duration**: 15.3 minutes
**Tokens**: 6000 input, 9000 output
**Cost**: $0.042

---

## Report

[Full research report in Markdown]

---

## Sources

1. **Nature: Quantum Breakthrough**
   - URL: https://nature.com/...
   - Relevance: 0.98

2. **MIT Tech Review: Quantum Computing**
   - URL: https://technologyreview.com/...
   - Relevance: 0.95
```

---

## Gemini Collaboration Tools

### 1. ask_gemini

**Purpose**: General question/answer for collaboration between AI assistants.

**Token Cost**: MEDIUM
**Model**: gemini-3-flash-preview

#### Parameters

```python
def ask_gemini(
    prompt: str,
    temperature: float = 0.5  # 0.0-1.0
) -> str
```

#### Usage Example

```python
response = ask_gemini(
    "What are the key differences between REST and GraphQL?",
    temperature=0.5
)
# Returns: "🤖 GEMINI RESPONSE:\n\n[Detailed explanation]"
```

#### Temperature Guide

- **0.2-0.4**: Focused, deterministic (technical questions)
- **0.5**: Balanced (default)
- **0.6-0.8**: Creative, varied (brainstorming)

---

### 2. gemini_code_review

**Purpose**: Comprehensive code review with focus on quality, security, and best practices.

**Token Cost**: MEDIUM
**Model**: gemini-3-flash-preview
**Temperature**: 0.2 (analytical)

#### Parameters

```python
def gemini_code_review(
    code: str,
    focus_areas: Optional[List[str]] = None  # ["security", "performance", etc.]
) -> str
```

#### Usage Example

```python
code = """
def process_user_data(data):
    query = f"SELECT * FROM users WHERE name = '{data['name']}'"
    return execute_query(query)
"""

review = gemini_code_review(
    code=code,
    focus_areas=["security", "best practices"]
)
# Returns detailed analysis with SQL injection warning
```

#### Focus Areas

- `security`: SQL injection, XSS, authentication issues
- `performance`: Bottlenecks, optimization opportunities
- `readability`: Code clarity and maintainability
- `best practices`: Design patterns, coding standards
- `bugs`: Logic errors, edge cases

---

### 3. gemini_brainstorm

**Purpose**: Creative brainstorming for innovative ideas and solutions.

**Token Cost**: MEDIUM
**Model**: gemini-3-flash-preview
**Temperature**: 0.7 (creative)

#### Parameters

```python
def gemini_brainstorm(
    topic: str,
    context: str = ""
) -> str
```

#### Usage Example

```python
response = gemini_brainstorm(
    topic="API authentication strategies for microservices",
    context="Building a distributed system with 20+ services. Need scalable auth."
)
# Returns multiple creative approaches
```

---

### 4. gemini_debug

**Purpose**: Expert debugging assistance for error diagnosis and root cause analysis.

**Token Cost**: MEDIUM
**Model**: gemini-3-flash-preview
**Temperature**: 0.2 (analytical)

#### Parameters

```python
def gemini_debug(
    error_message: str,
    code_snippet: str = "",
    context: str = ""
) -> str
```

#### Usage Example

```python
response = gemini_debug(
    error_message="TypeError: Cannot read property 'map' of undefined",
    code_snippet="""
    const users = fetchUsers();
    return users.map(u => u.name);
    """,
    context="Error occurs on initial page load, but not after refresh"
)
# Returns: Root cause analysis + fix + prevention tips
```

---

### 5. gemini_research

**Purpose**: Fact-based research with Google Search grounding for current information.

**Token Cost**: MEDIUM
**Model**: gemini-3-flash-preview
**Temperature**: 0.3 (factual)

#### Parameters

```python
def gemini_research(
    topic: str
) -> str
```

#### Usage Example

```python
response = gemini_research(
    "Latest Python 3.13 features and performance improvements"
)
# Returns: Google Search grounded research with sources
```

#### Fallback Behavior

If Google Search grounding is unavailable (API key limitations), automatically falls back to regular Gemini with note in response.

---

### 6. interpret_image

**Purpose**: Analyze and interpret images using Gemini's vision capabilities.

**Token Cost**: MEDIUM
**Model**: gemini-3-flash-preview
**Max Images**: 3,600 per request

#### Parameters

```python
def interpret_image(
    image_path: Union[str, List[str]],  # File path, URL, or base64
    prompt: str = "Describe this image in detail",
    temperature: float = 0.5
) -> str
```

#### Usage Example

```python
# Single image analysis
response = interpret_image(
    image_path="/path/to/screenshot.png",
    prompt="What error is shown and how can I fix it?"
)

# Multiple image comparison
response = interpret_image(
    image_path=[
        "/path/to/design_v1.png",
        "/path/to/design_v2.png"
    ],
    prompt="Compare these designs. Which is more user-friendly?"
)

# Base64 image
response = interpret_image(
    image_path="data:image/jpeg;base64,/9j/4AAQ...",
    prompt="Extract all text from this image"
)
```

#### Supported Formats

- Local files: `/path/to/image.jpg`
- URLs: `https://example.com/image.png`
- Base64: `data:image/jpeg;base64,...`
- Image types: jpg, jpeg, png, gif, webp, bmp

#### File Size Handling

- **≤20MB**: Sent inline (no upload)
- **>20MB**: Automatic upload via File API with cleanup

---

## File Management Tools

### 1. server_info

**Purpose**: Check server status and Gemini API connectivity.

**Token Cost**: ZERO

```python
def server_info() -> str

# Returns:
"🤖 GEMINI RESPONSE:\n\nServer v3.7.1 - Gemini connected and ready! Using modern unified Google Gen AI SDK."
```

---

### 2. check_file_status

**Purpose**: Check processing status of uploaded files in Gemini cloud.

**Token Cost**: ZERO (metadata read only)

#### Parameters

```python
def check_file_status(
    file_name: str  # Format: "files/abc123xyz"
) -> str
```

#### Returns

```json
{
  "state": "ACTIVE",
  "ready": true,
  "file_name": "files/abc123xyz",
  "display_name": "video.mp4",
  "size_bytes": 52428800,
  "size_mb": 50.0,
  "mime_type": "video/mp4",
  "create_time": "2025-01-10T10:00:00Z",
  "uri": "https://generativelanguage.googleapis.com/...",
  "message": "✅ File is ready for use!"
}
```

#### File States

- `PROCESSING`: Still uploading/indexing
- `ACTIVE`: Ready for use ✅
- `FAILED`: Processing failed ❌
- `STATE_UNSPECIFIED`: Unknown state

---

### 3. list_uploaded_files

**Purpose**: Browse all files in Gemini cloud storage (48-hour retention).

**Token Cost**: ZERO

#### Parameters

```python
def list_uploaded_files(
    filter_mime_type: Optional[str] = None,  # "video/*", "image/*", etc.
    sort_by: str = "upload_date",  # "upload_date", "size", "name", "expiring"
    max_results: int = 20  # 1-100
) -> str
```

#### Returns

```json
{
  "total_files": 5,
  "filtered_count": 3,
  "storage_used_mb": 1250.5,
  "expiring_soon_count": 1,
  "files": [
    {
      "file_name": "files/abc123",
      "display_name": "demo.mp4",
      "state": "ACTIVE",
      "mime_type": "video/mp4",
      "size_mb": 450.0,
      "uploaded": "2025-01-09T10:00:00Z",
      "age_hours": 36.5,
      "expires_in_hours": 11.5,
      "expires_soon": false,
      "ready_for_analysis": true
    }
  ],
  "storage_info": {
    "retention_policy": "48 hours",
    "max_storage_gb": 20,
    "max_file_size_gb": 2
  }
}
```

#### Usage Example

```python
# List all videos
response = list_uploaded_files(
    filter_mime_type="video/*",
    sort_by="expiring"
)

# Find files about to expire (< 6 hours)
# Check expiring_soon_count in response
```

---

### 4. get_last_uploaded_video

**Purpose**: Quick access to most recent video upload.

**Token Cost**: ZERO

```python
def get_last_uploaded_video() -> str

# Returns: JSON with latest video metadata + suggestion
```

---

### 5. delete_uploaded_file

**Purpose**: Delete files from Gemini cloud storage (destructive operation).

**Token Cost**: ZERO
**⚠️ Requires Confirmation**

#### Parameters

```python
def delete_uploaded_file(
    file_name: str,
    confirmed: bool = False  # Must be True to delete
) -> str
```

#### Two-Step Workflow

```python
# Step 1: Check what will be deleted
result = delete_uploaded_file("files/abc123", confirmed=False)
# Returns: {"action": "confirmation_required", ...}

# Step 2: User confirms, then delete
result = delete_uploaded_file("files/abc123", confirmed=True)
# Returns: {"action": "deleted", "freed_storage_mb": 450, ...}
```

---

### 6. watch_video

**Purpose**: Analyze YouTube videos or local video files with Gemini.

**Token Cost**: MEDIUM
**Supported Formats**: mp4, mov, avi, webm, mkv

#### Parameters

```python
def watch_video(
    input_path: Optional[str] = None,  # YouTube URL or file path
    prompt: str = "",
    model: str = "gemini-3-flash-preview",
    file_uri: Optional[str] = None,  # Pre-uploaded file
    auto_analyze: bool = True,
    max_wait_seconds: int = 300,
    poll_interval: int = 2
) -> str
```

#### Three Usage Modes

**Mode 1: Full Auto (Default)**
```python
response = watch_video(
    "/path/to/video.mp4",
    "Summarize this video in 3-5 key points"
)
# Handles: upload → wait → analyze → return
```

**Mode 2: Upload Only**
```python
result = watch_video(
    "/path/to/video.mp4",
    auto_analyze=False
)
# Returns: {"file_name": "files/abc123", "state": "PROCESSING"}
# Then: check_file_status("files/abc123")
# Finally: watch_video(file_uri="files/abc123", prompt="...")
```

**Mode 3: Pre-Uploaded File**
```python
response = watch_video(
    file_uri="files/abc123",
    prompt="Extract key points"
)
# Skips upload, checks status, analyzes
```

#### YouTube Support

```python
response = watch_video(
    "https://www.youtube.com/watch?v=VIDEO_ID",
    "What are the main topics covered?"
)
# No download needed - direct API processing
```

#### File Size Handling

- **≤20MB**: Inline processing (no upload/polling)
- **>20MB**: File API upload with automatic polling

---

## Token Economics

### Cost Structure

| Operation | Token Cost | Description |
|-----------|-----------|-------------|
| **Deep Research** | HIGH | $0.001 input, $0.004 output per 1K tokens |
| **Gemini Tools** | MEDIUM | $0.0005 input, $0.003 output per 1K tokens |
| **SQLite Retrieval** | ZERO | Local database reads |
| **File Status** | ZERO | Metadata queries only |
| **Cost Estimation** | ZERO | Local heuristics |

### Pricing Examples

```python
# Deep Research (typical)
# Input: 6,000 tokens @ $0.001/1K = $0.006
# Output: 9,000 tokens @ $0.004/1K = $0.036
# Total: ~$0.042

# ask_gemini (typical)
# Input: 100 tokens @ $0.0005/1K = $0.00005
# Output: 500 tokens @ $0.003/1K = $0.0015
# Total: ~$0.002

# Multiple retrievals (cached)
get_research_results("task_id_1")  # $0.00
get_research_results("task_id_1")  # $0.00 (cached)
get_research_results("task_id_1")  # $0.00 (cached)
```

### Token Optimization Strategies

1. **Use Estimator First**: `estimate_research_cost()` before starting research
2. **Cache Results**: `get_research_results()` for zero-cost retrieval
3. **Enable Notifications**: Avoid manual polling loops
4. **Batch Operations**: Use multi-image analysis instead of separate calls

---

## Error Handling

### Standard Error Format

```python
{
    "success": false,
    "error": "ERROR_CODE",
    "message": "Human-readable error description",
    "suggestion": "Actionable recommendation"
}
```

### Common Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `GEMINI_UNAVAILABLE` | API key not configured | Check `.env` file |
| `INVALID_QUERY` | Query too short/long | Adjust query length |
| `TASK_NOT_FOUND` | Invalid task_id | Verify UUID format |
| `RESEARCH_NOT_COMPLETED` | Task still running | Wait or check status |
| `RESEARCH_FAILED` | Task failed | Check error_message |
| `FILE_NOT_FOUND` | File doesn't exist | Verify file path |
| `SQLITE_ERROR` | Database issue | Check server logs |

### Error Response Examples

```python
# Invalid query
{
    "success": false,
    "error": "INVALID_QUERY",
    "message": "Query too short. Minimum 3 characters required.",
    "suggestion": "Provide a more detailed research question"
}

# Task not completed
{
    "success": false,
    "error": "RESEARCH_NOT_COMPLETED",
    "task_id": "550e8400-...",
    "status": "running_async",
    "progress": 45,
    "message": "Research is still in progress. Current progress: 45%",
    "suggestion": "Wait for completion or use check_research_status to monitor"
}

# Gemini unavailable
{
    "success": false,
    "error": "GEMINI_UNAVAILABLE",
    "message": "Deep research not available: GEMINI_API_KEY not set",
    "suggestion": "Check GEMINI_API_KEY in .env file"
}
```

---

## Usage Examples

### Complete Research Workflow

```python
# 1. Estimate cost first
estimate = estimate_research_cost(
    "What are the latest advances in quantum computing?"
)

print(f"Estimated time: {estimate['estimated_duration']['likely_minutes']} min")
print(f"Estimated cost: ${estimate['estimated_cost']['likely_usd']}")

if estimate["will_likely_go_async"]:
    print("This will run asynchronously")

# 2. Start research
result = await start_deep_research(
    query="What are the latest advances in quantum computing?",
    enable_notifications=True,
    max_wait_hours=8
)

task_id = result["task_id"]

# 3. Continue other work (research runs in background)
# ... handle other user requests ...

# 4. Receive FastMCP notification when complete (automatic)

# 5. Retrieve results (zero cost)
final = get_research_results(task_id, include_sources=True)

print(final["report"])
print(f"Sources: {len(final['sources'])}")
print(f"Duration: {final['metadata']['duration_minutes']} min")
print(f"Cost: ${final['metadata']['cost_usd']}")

# 6. Export to Markdown
save_result = save_research_to_markdown(
    task_id=task_id,
    output_dir="./research_reports",
    filename_prefix="quantum_research"
)

print(f"Saved to: {save_result['file_path']}")
```

### Code Review Workflow

```python
code = """
def process_payment(amount, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"UPDATE accounts SET balance = balance - {amount} WHERE id = {user_id}"
    cursor.execute(query)
    conn.commit()
    return True
"""

review = gemini_code_review(
    code=code,
    focus_areas=["security", "best practices", "bugs"]
)

print(review)
# Will identify:
# - SQL injection vulnerability
# - No error handling
# - No transaction safety
# - No balance validation
```

### Multi-Image Comparison

```python
designs = [
    "/path/to/design_v1.png",
    "/path/to/design_v2.png",
    "/path/to/design_v3.png"
]

analysis = interpret_image(
    image_path=designs,
    prompt="Compare these UI designs. Which follows better UX principles and why?",
    temperature=0.6
)

print(analysis)
# Returns detailed comparison with recommendations
```

### Video Analysis with Time Ranges

```python
# Analyze specific segment
analysis = watch_video(
    "https://www.youtube.com/watch?v=VIDEO_ID",
    prompt="Summarize what happens from 2:30 to 5:00"
)

# Full video summary
summary = watch_video(
    "/path/to/recording.mp4",
    prompt="List all terminal commands executed in this screencast"
)
```

### Error Recovery Workflow

```python
# Start research
result = await start_deep_research("complex query")
task_id = result["task_id"]

# Later: Check if hanging
status = check_research_status(task_id)

if status.get("hanging_detection", {}).get("is_hanging"):
    print(f"Task appears hung: {status['hanging_detection']['reason']}")

    # Attempt resume
    resume_result = await resume_research(task_id)

    if resume_result["status"] == "completed":
        final = get_research_results(task_id)
    elif resume_result["status"] == "partial_results_saved":
        print("Partial results available:")
        print(resume_result["partial_report_preview"])
    else:
        # Cancel and start new research
        cancel_research(task_id, save_partial=True)
```

---

## Advanced Features

### FastMCP Task Integration (v3.8.0)

**Native Background Tasks**: `start_deep_research` uses `@mcp.tool(task=True)` decorator for:

- **Automatic Notifications**: MCP protocol notifications when complete
- **Progress Updates**: Real-time progress via `Progress` dependency
- **Non-Blocking Execution**: LLM can handle other requests during research
- **Cross-Client Support**: Works with any MCP-compliant client

**Progress Dependency Injection**:
```python
@mcp.tool(task=True)
async def start_deep_research(
    query: str,
    progress: Progress = Progress()  # Injected by FastMCP
) -> Dict[str, Any]:
    # Update progress during execution
    await progress.set_total(100)
    await progress.set_message("Processing...")
```

### SQLite Persistence

All deep research tasks persisted in SQLite with:
- WAL mode for concurrent access
- Retry logic for locked database
- Progress snapshots for hanging detection
- Automatic cleanup of incomplete tasks on startup

**Database Schema**:
```sql
CREATE TABLE research_tasks (
    task_id TEXT PRIMARY KEY,
    query TEXT,
    status TEXT,
    progress INTEGER,
    interaction_id TEXT,
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd REAL,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE research_results (
    task_id TEXT PRIMARY KEY,
    report TEXT,
    sources JSON,
    metadata JSON
);

CREATE TABLE progress_snapshots (
    task_id TEXT,
    timestamp TIMESTAMP,
    progress INTEGER,
    action TEXT,
    api_status TEXT
);
```

### Hanging Detection Algorithm

Analyzes progress snapshots to detect stalled tasks:

```python
# Criteria for hanging detection
is_hanging = (
    stall_minutes > 3.0 and
    no_api_updates_for > 2.0 and
    progress_unchanged_for > 5.0
)

confidence = min(
    stall_minutes / 10.0,
    progress_unchanged_for / 15.0,
    1.0
)
```

### Desktop Notifications

Cross-platform notifications (macOS/Windows/Linux):

```python
# Research complete
notifier.notify_research_complete(
    task_id="550e8400-...",
    duration_minutes=15.3
)
# Shows: "Research Complete | Task 550e8400 | 15.3 minutes"

# Research failed
notifier.notify_research_failed(
    task_id="550e8400-...",
    error="Timeout exceeded"
)
# Shows: "Research Failed | Task 550e8400 | Timeout exceeded"
```

---

## Client Integration

### Claude Code Configuration

```json
{
  "gemini-mcp-server": {
    "name": "Gemini MCP Server",
    "command": "uv",
    "args": ["run", "python", "server.py"],
    "cwd": "/path/to/gemini-mcp",
    "env": {
      "GEMINI_API_KEY": "YOUR_API_KEY"
    }
  }
}
```

### Testing with MCP Inspector

```bash
# Install inspector
npx @modelcontextprotocol/inspector

# Connect server
# Command: uv
# Args: ["run", "python", "server.py"]
# Working Directory: /path/to/gemini-mcp
```

---

## Changelog

### v3.8.0 (Planned)
- **FastMCP Task Support**: Native background tasks for `start_deep_research`
- **Progress Dependency**: Real-time progress updates via FastMCP API
- **Token Efficiency**: 98% reduction via automatic notifications

### v3.7.1 (Current)
- Bug fixes for foreign keys, event loop, race conditions
- Memory leak fixes in SQLite persistence
- SQL injection vulnerability patches

### v3.7.0
- Added Gemini Deep Research tools (7 tools)
- SQLite persistence for zero-cost retrieval
- Hybrid sync-to-async execution pattern
- Desktop notifications support

### v3.6.0
- File management system for Gemini storage
- 48-hour retention policy support

### v3.1.0
- Added `watch_video` tool for video analysis
- YouTube URL support

### v3.0.0
- Migration to unified Google Gen AI SDK
- Multi-image support (up to 3,600 images)

### v2.0.0
- Refactored to official MCP SDK
- FastMCP server abstraction

---

## Support and Resources

- **Repository**: https://github.com/yourusername/gemini-mcp
- **MCP Protocol**: https://github.com/sourcegraph/handbook/blob/main/engineering/rfcs/2024-04-22-rfc-1075-mcp-v0.md
- **FastMCP Docs**: https://github.com/jlowin/fastmcp
- **Gemini API**: https://ai.google.dev/docs

---

**Last Updated**: 2026-01-10
**Version**: 3.7.1
**Author**: Gemini MCP Server Team
