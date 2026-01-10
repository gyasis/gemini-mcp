"""
FASTMCP TASK MIGRATION - Minimal Example
==========================================

Shows how to add FastMCP task support to deep research
WITHOUT removing any custom logic.

BEFORE: @mcp.tool()
AFTER:  @mcp.tool(task=True) + Progress dependency
"""

from fastmcp import FastMCP
from fastmcp.dependencies import Progress
from typing import Dict, Any

# ============================================================================
# BEFORE: Current Implementation (No FastMCP Tasks)
# ============================================================================

@mcp.tool()
async def start_deep_research_OLD(
    query: str,
    enable_notifications: bool = True,
    max_wait_hours: int = 8,
    model: str = "deep-research-pro-preview-12-2025"
) -> Dict[str, Any]:
    """Current implementation - no task support."""

    task_id = str(uuid.uuid4())

    # Create task in SQLite
    state_manager.save_task(task)

    # Try sync completion (30s timeout)
    result = await deep_research_engine.execute_with_timeout(
        query=query,
        model=model,
        timeout_seconds=30,
        on_progress=lambda p, a: state_manager.update_task(
            task_id, {"progress": p, "current_action": a}
        )
    )

    # If timeout, schedule background task
    if result["status"] == "timeout":
        background_task_manager.schedule_task(task_id, ...)
        return {"task_id": task_id, "status": "running"}

    # If completed, return results
    return {"task_id": task_id, "status": "completed", "results": result}


# ============================================================================
# AFTER: With FastMCP Task Support (Minimal Change)
# ============================================================================

@mcp.tool(task=True)  # ← ONLY LINE THAT CHANGES!
async def start_deep_research(
    query: str,
    enable_notifications: bool = True,
    max_wait_hours: int = 8,
    model: str = "deep-research-pro-preview-12-2025",
    progress: Progress = Progress()  # ← ADD THIS DEPENDENCY
) -> Dict[str, Any]:
    """With FastMCP task support - LLM gets notified automatically.

    FastMCP handles:
    - Task ID generation (still generate your own for SQLite)
    - MCP protocol task lifecycle
    - Client notifications when complete
    - tasks/get polling endpoint

    Your code handles:
    - Gemini API polling (your custom loop)
    - SQLite state persistence
    - Hanging detection
    - Progress estimation
    """

    # Generate YOUR task ID (for SQLite tracking)
    task_id = str(uuid.uuid4())

    # Create task in SQLite (UNCHANGED)
    state_manager.save_task(task)

    # Bridge: Connect your progress to FastMCP
    async def progress_bridge(pct: int, action: str):
        """Bridge between your polling and FastMCP progress."""
        # Update SQLite (your existing code)
        state_manager.update_task(task_id, {"progress": pct, "current_action": action})

        # Update FastMCP (NEW - notifies LLM)
        await progress.set_total(100)
        await progress.set_message(action)
        # Can't set exact progress in current FastMCP Progress API
        # It uses increment() instead, but message is enough for LLM

    # Try sync completion with 30s timeout (UNCHANGED)
    result = await deep_research_engine.execute_with_timeout(
        query=query,
        model=model,
        timeout_seconds=30,
        on_progress=progress_bridge  # ← Use bridge instead of lambda
    )

    # Handle timeout: REMOVE background task manager
    # FastMCP's task wrapper IS your background execution
    if result["status"] == "timeout":
        # Get interaction_id from timeout result
        interaction_id = result["interaction_id"]

        # Just poll until complete (FastMCP makes THIS the background task)
        final_result = await deep_research_engine.poll_until_complete(
            interaction_id=interaction_id,
            task_id=task_id,
            on_progress=progress_bridge,
            max_wait_seconds=max_wait_hours * 3600
        )

        # Update SQLite with results (UNCHANGED)
        state_manager.update_task(task_id, {
            "status": TaskStatus.COMPLETED,
            "results": final_result
        })

        return final_result

    # If completed, return results (UNCHANGED)
    return result


# ============================================================================
# WHAT GETS REMOVED: BackgroundTaskManager
# ============================================================================

# REMOVE: No longer need custom background task scheduling
# FastMCP's task wrapper handles async execution

# BEFORE: You had background_task_manager.schedule_task()
# AFTER:  FastMCP automatically makes the entire function async


# ============================================================================
# WHAT STAYS: Everything Else
# ============================================================================

# ✅ SQLite state_manager - Still needed for persistence
# ✅ Custom polling loop - Still needed to poll Gemini
# ✅ Hanging detection - Still your domain logic
# ✅ Progress estimation - Still your custom algorithm
# ✅ Notifications - Still your feature


# ============================================================================
# LLM USAGE PATTERN (Updated Docs)
# ============================================================================

"""
BEFORE (No Task Support):
--------------------------
LLM: start_deep_research("quantum computing")
→ Gets: {"task_id": "abc123", "status": "running"}
→ Has to: Manually check status every N seconds
→ Problem: Wastes context window babysitting

AFTER (With Task Support):
---------------------------
LLM: start_deep_research("quantum computing")
→ FastMCP returns task_id immediately
→ LLM can: Do other work, move on to different tasks
→ FastMCP notifies: When research completes
→ LLM then: Calls get_research_results(task_id) for zero-cost retrieval

Token Savings:
- Before: ~5-10k tokens per manual check
- After: One notification, one retrieval call
"""


# ============================================================================
# ARCHITECTURE DIAGRAM
# ============================================================================

"""
┌─────────────────────────────────────────────────────────┐
│ LLM Agent Session                                       │
│ ┌─────────────────┐      ┌──────────────────┐         │
│ │ Start Research  │──┬──→│ Do Other Work    │         │
│ └─────────────────┘  │   └──────────────────┘         │
│                      │   ┌──────────────────┐         │
│                      └──→│ More Tasks       │         │
│                          └──────────────────┘         │
│                                    ↓                    │
│                      ┌──────────────────────┐         │
│                      │ [Notification]       │         │
│                      │ Research Complete!   │         │
│                      └──────────────────────┘         │
│                                    ↓                    │
│                      ┌──────────────────────┐         │
│                      │ Get Results (0 cost) │         │
│                      └──────────────────────┘         │
└─────────────────────────────────────────────────────────┘

FastMCP Task Layer (protocol compliance)
├── Async execution wrapper
├── MCP tasks/get endpoint
└── Completion notification

Your Custom Code (unchanged)
├── Gemini API polling loop
├── SQLite state persistence
├── Hanging detection
├── Progress estimation
└── Desktop notifications
"""
