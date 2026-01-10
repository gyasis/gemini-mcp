# Updated Tool Docstring for LLM Agents

When you migrate `start_deep_research` to use FastMCP tasks, update the docstring to show the new pattern:

## New Docstring

```python
@mcp.tool(task=True)
async def start_deep_research(
    query: str,
    enable_notifications: bool = True,
    max_wait_hours: int = 8,
    model: str = "deep-research-pro-preview-12-2025",
    progress: Progress = Progress()
) -> Dict[str, Any]:
    """Start a deep research task using Gemini Deep Research API.

    🚀 **FastMCP Task Support**: This tool uses native MCP background tasks.
    You can start research and continue with other work - you'll be notified
    when complete.

    **Token-Efficient Usage Pattern**:
    ```
    # Step 1: Start research (returns task_id)
    result = await start_deep_research("What is quantum entanglement?")

    # Step 2: Do other work (research runs in background)
    # ... work on other tasks ...

    # Step 3: You'll receive a notification when complete
    # FastMCP automatically notifies via MCP protocol

    # Step 4: Retrieve results (zero-cost - from SQLite cache)
    final_result = await get_research_results(result["task_id"])
    ```

    **Why This Saves Tokens**:
    - No need to manually check status repeatedly
    - No context window wasted on polling
    - Single notification when complete
    - Results cached in SQLite for instant retrieval

    **Expected Duration**:
    - Simple queries: 5-15 minutes
    - Complex queries: 20-40 minutes
    - Maximum timeout: 60 minutes

    **Hybrid Execution**:
    1. Attempts synchronous completion (30-second timeout)
    2. If completes quickly: Returns full results immediately
    3. If timeout: Continues in background (you'll be notified)

    Args:
        query: Research question or topic (3-10000 chars)
               More specific queries yield better results
        enable_notifications: Desktop notification on completion (default: True)
        max_wait_hours: Maximum hours before timeout (1-24, default: 8)
        model: Gemini model (default: deep-research-pro-preview-12-2025)

    Returns:
        Dict with:
        - task_id: Unique identifier for tracking
        - status: "completed" (sync) or "running" (async)
        - results: Full report if completed synchronously
        - progress: Current progress percentage
        - current_action: What the research is doing now

    Example:
        >>> # Start research
        >>> result = await start_deep_research(
        ...     "Latest advances in quantum computing"
        ... )
        >>>
        >>> # If completed immediately (unlikely for deep research):
        >>> if result["status"] == "completed":
        ...     print(result["results"]["report"])
        >>>
        >>> # If running async (typical):
        >>> else:
        ...     task_id = result["task_id"]
        ...     # Wait for notification (no manual polling needed!)
        ...     # Then retrieve when notified:
        ...     final = await get_research_results(task_id)
    """
```

## What Changed

1. **Added "FastMCP Task Support" callout** - LLMs need to know this is different
2. **Token-efficient usage pattern** - Shows the new flow clearly
3. **Removed manual polling instructions** - No longer needed
4. **Emphasized notification pattern** - Key differentiator
5. **Zero-cost retrieval** - Important for LLM decision-making

## Why This Helps LLMs

**Before (without task support):**
```python
# LLM has to write code like this:
result = await start_deep_research("query")
task_id = result["task_id"]

# Then manually poll:
while True:
    status = await check_research_status(task_id)
    if status["status"] == "completed":
        break
    await asyncio.sleep(10)  # Wastes context

final = await get_research_results(task_id)
```

**After (with task support):**
```python
# LLM can write simple code:
result = await start_deep_research("query")
# ... do other work ...
# FastMCP notifies when done
final = await get_research_results(result["task_id"])
```

Much simpler for LLMs to use correctly!
