#!/usr/bin/env python3
"""
Gemini MCP Server v3.9.0
Enables a primary AI assistant to collaborate with Google's Gemini AI using the modern unified Google Gen AI SDK.

Features Gemini Deep Research tools with SQLite persistence and asyncio background tasks:
- start_deep_research: Hybrid sync-to-async research execution
- get_research_results: Zero-cost result retrieval from SQLite
- check_research_status: Monitor async task progress
- cancel_research: Stop running tasks with optional partial saves
- estimate_research_cost: Pre-execution cost analysis
- save_research_to_markdown: Export results to formatted Markdown files
"""

import os
import base64
import logging
import uuid
import json
import asyncio
from typing import Optional, List, Union, Dict, Any
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from fastmcp import FastMCP
import mimetypes

# --- IPv4 preference -------------------------------------------------------
# On networks that advertise IPv6 but cannot actually reach googleapis.com over
# it (a common ISP/router misconfiguration), getaddrinfo returns AAAA records
# first and Python has no happy-eyeballs fallback -- so every Gemini call
# stalls until timeout and the server appears to hang or report CONNECT_TIMEOUT.
# Diagnose with: `curl -6 https://generativelanguage.googleapis.com/` (hangs)
# vs `curl -4 ...` (responds). Measured on one such network: an image request
# hung >300s with default resolution and completed in 19s with IPv4 forced.
# Preferring A records is harmless where IPv6 works, since it only reorders
# candidates. Set GEMINI_MCP_ALLOW_IPV6=1 to disable this preference.
def _prefer_ipv4() -> None:
    import socket as _socket
    if os.environ.get("GEMINI_MCP_ALLOW_IPV6") == "1":
        return
    if getattr(_socket, "_gemini_mcp_v4_only", False):
        return
    _orig = _socket.getaddrinfo

    def _v4_first(host, port, family=0, *args, **kwargs):
        try:
            res = _orig(host, port, _socket.AF_INET, *args, **kwargs)
            if res:
                return res
        except _socket.gaierror:
            pass
        return _orig(host, port, family, *args, **kwargs)

    _socket.getaddrinfo = _v4_first
    _socket._gemini_mcp_v4_only = True


_prefer_ipv4()

# Configure logging for deep research
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Build an absolute path to the .env file
# This ensures it's found regardless of the script's working directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Server version
__version__ = "3.9.0"

# Initialize MCP server
mcp = FastMCP("Gemini MCP Server", version=__version__)

# Initialize Gemini with new unified SDK
try:
    from google import genai
    from google.genai import types
    
    # Get API key from environment
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        GEMINI_AVAILABLE = False
        GEMINI_ERROR = "GEMINI_API_KEY not set in environment or .env file"
        client = None
    else:
        # Initialize the modern client
        client = genai.Client(api_key=API_KEY)
        GEMINI_AVAILABLE = True
        GEMINI_ERROR = None
except Exception as e:
    GEMINI_AVAILABLE = False
    GEMINI_ERROR = str(e)
    client = None

# ============================================================================
# Deep Research Module Initialization
# ============================================================================

# Initialize deep research components (SQLite + asyncio for zero external deps)
try:
    from deep_research import TaskStatus, ResearchTask
    from deep_research.state_manager import StateManager
    from deep_research.notification import get_notifier
    from deep_research.engine import DeepResearchEngine

    # Initialize state manager (SQLite persistence)
    state_manager = StateManager()

    # Initialize notifier (cross-platform desktop notifications)
    notifier = get_notifier()

    # Initialize deep research engine (only if Gemini client available)
    if GEMINI_AVAILABLE and client:
        # Pass state_manager for progress snapshot persistence
        deep_research_engine = DeepResearchEngine(client, state_manager=state_manager)
        DEEP_RESEARCH_AVAILABLE = True
        DEEP_RESEARCH_ERROR = None
    else:
        deep_research_engine = None
        DEEP_RESEARCH_AVAILABLE = False
        DEEP_RESEARCH_ERROR = "Gemini client not available"

    logger.info("Deep research module initialized successfully")

except ImportError as e:
    state_manager = None
    notifier = None
    deep_research_engine = None
    DEEP_RESEARCH_AVAILABLE = False
    DEEP_RESEARCH_ERROR = f"Deep research module not found: {e}"
    logger.warning(f"Deep research module not available: {e}")

except Exception as e:
    state_manager = None
    notifier = None
    deep_research_engine = None
    DEEP_RESEARCH_AVAILABLE = False
    DEEP_RESEARCH_ERROR = str(e)
    logger.error(f"Failed to initialize deep research: {e}")


# ============================================================================
# Background Task Registry (for cancellation support)
# ============================================================================

# Maps task_id -> asyncio.Task for background polling coroutines
_background_tasks: Dict[str, asyncio.Task] = {}


# ============================================================================
# Deep Research Startup Recovery
# ============================================================================

async def _continue_research(task_id: str, interaction_id: str):
    """Resume polling for an incomplete task after server restart.

    Args:
        task_id: The research task ID
        interaction_id: The Gemini interaction ID for polling
    """
    if not deep_research_engine or not state_manager:
        logger.error(f"Cannot resume task {task_id}: deep research not available")
        return

    try:
        task = state_manager.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found in database")
            return

        logger.info(f"Resuming research task {task_id}")

        # Load progress history from SQLite for hanging detection
        saved_snapshots = state_manager.get_progress_snapshots(task_id)
        if saved_snapshots:
            loaded = deep_research_engine.hanging_detector.load_history_from_snapshots(
                task_id, saved_snapshots
            )
            logger.info(f"Loaded {loaded} progress snapshots for hanging detection")

        # Update task status
        state_manager.update_task(task_id, {
            "status": TaskStatus.RUNNING_ASYNC,
            "current_action": "Resuming after restart..."
        })

        # Continue polling with progress persistence
        def on_progress_with_persist(progress: int, action: str):
            state_manager.update_task(task_id, {"progress": progress, "current_action": action})
            # Note: api_status will be added by engine's record_progress call

        result = await deep_research_engine.poll_until_complete(
            interaction_id,
            task_id=task_id,
            on_progress=on_progress_with_persist
        )

        # Create and save result
        research_result = deep_research_engine.create_research_result(task_id, result)
        state_manager.save_result(task_id, research_result)
        state_manager.update_task(task_id, {
            "status": TaskStatus.COMPLETED,
            "completed_at": datetime.utcnow(),
            "progress": 100
        })

        # Send notification if enabled
        if task.enable_notifications and notifier:
            duration_minutes = (datetime.utcnow() - task.created_at).total_seconds() / 60
            notification_sent = notifier.notify_research_complete(task_id, duration_minutes)
            if not notification_sent:
                logger.warning(f"Desktop notification failed for task {task_id} - check DISPLAY/DBUS environment")

        logger.info(f"Successfully resumed and completed task {task_id}")

    except Exception as e:
        logger.error(f"Failed to resume task {task_id}: {e}")
        if state_manager:
            state_manager.update_task(task_id, {
                "status": TaskStatus.FAILED,
                "error_message": f"Resume failed: {str(e)}"
            })
        if notifier:
            notifier.notify_research_failed(task_id, str(e))


async def on_server_startup():
    """Resume incomplete tasks from SQLite on server startup.

    For tasks WITH an interaction_id: re-launches background polling to check
    if Gemini completed while the server was down, and saves results if so.

    For tasks WITHOUT an interaction_id: marks as failed (unrecoverable).
    """
    if not state_manager:
        logger.debug("Deep research not available, skipping startup recovery")
        return

    try:
        incomplete_tasks = state_manager.get_incomplete_tasks()
        if not incomplete_tasks:
            logger.debug("No incomplete research tasks to resume")
            return

        resumable = [(tid, iid) for tid, iid in incomplete_tasks if iid]
        unresumable = [(tid, iid) for tid, iid in incomplete_tasks if not iid]

        if unresumable:
            logger.info(f"{len(unresumable)} task(s) marked FAILED (no interaction_id)")
        if resumable:
            logger.info(f"{len(resumable)} task(s) resumable — launching background recovery")

        # Mark tasks without interaction_id as failed (cannot be resumed)
        for task_id, interaction_id in unresumable:
            try:
                state_manager.update_task(task_id, {
                    "status": TaskStatus.FAILED,
                    "error_message": "Task interrupted before API response (no interaction_id)"
                })
                logger.warning(f"Marked task {task_id} as failed (no interaction_id)")
            except Exception as e:
                logger.error(f"Failed to mark task {task_id} as failed: {e}")

        # Resume tasks that have an interaction_id
        for task_id, interaction_id in resumable:
            task = state_manager.get_task(task_id)
            if not task:
                continue

            bg_task = asyncio.create_task(
                _background_poll_and_save(
                    task_id=task_id,
                    interaction_id=interaction_id,
                    enable_notifications=task.enable_notifications,
                    max_wait_seconds=task.max_wait_hours * 3600,
                    created_at=task.created_at
                )
            )
            _background_tasks[task_id] = bg_task
            logger.info(f"Resumed background polling for task {task_id[:8]}")

    except Exception as e:
        logger.error(f"Startup recovery failed: {e}")


# ============================================================================
# Deep Research Tools (Wave 4-5: US1 MVP)
# ============================================================================

async def _background_poll_and_save(
    task_id: str,
    interaction_id: str,
    enable_notifications: bool,
    max_wait_seconds: int,
    created_at: datetime
):
    """Fire-and-forget coroutine: polls Gemini until complete, saves to SQLite.

    This runs entirely in the background after start_deep_research returns.
    The MCP tool call is already done — this is a server-internal coroutine.
    Registered in _background_tasks for cancellation support.

    Handles partial results: if the Gemini API gets stuck (common at 99%),
    the engine will force-complete with whatever data it has. We detect this
    via the _is_partial / _completion_reason keys in the result dict.
    """
    try:
        def on_progress(progress_pct: int, action: str):
            state_manager.update_task(task_id, {
                "progress": progress_pct,
                "current_action": action
            })

        final_result = await deep_research_engine.poll_until_complete(
            interaction_id,
            task_id=task_id,
            on_progress=on_progress,
            max_wait_seconds=max_wait_seconds
        )

        # Detect partial vs full completion
        is_partial = final_result.get("_is_partial", False)
        completion_reason = final_result.get("_completion_reason", "api_completed")

        # Save results to SQLite
        research_result = deep_research_engine.create_research_result(task_id, final_result)
        metadata = final_result.get("metadata", {})

        # Enrich metadata with completion info
        if is_partial:
            research_result.metadata["_is_partial"] = True
            research_result.metadata["_completion_reason"] = completion_reason

        state_manager.save_result(task_id, research_result)

        # Use COMPLETED_PARTIAL for forced completions, COMPLETED for clean ones
        final_status = TaskStatus.COMPLETED_PARTIAL if is_partial else TaskStatus.COMPLETED

        state_manager.update_task(task_id, {
            "status": final_status,
            "progress": 100,
            "tokens_input": metadata.get("tokens_input", 0),
            "tokens_output": metadata.get("tokens_output", 0),
            "completed_at": datetime.utcnow(),
            "current_action": f"Complete ({completion_reason})" if is_partial else "Research complete"
        })

        # Desktop notification
        if enable_notifications and notifier:
            try:
                duration_minutes = (datetime.utcnow() - created_at).total_seconds() / 60
                if is_partial:
                    notification_sent = notifier.notify_research_complete(
                        task_id, duration_minutes,
                    )
                else:
                    notification_sent = notifier.notify_research_complete(task_id, duration_minutes)
                if not notification_sent:
                    logger.warning(f"Desktop notification failed for task {task_id[:8]}")
            except Exception as notify_err:
                logger.warning(f"Notification error for {task_id[:8]}: {notify_err}")

        status_label = "partially completed (forced)" if is_partial else "completed"
        logger.info(f"Background task {task_id[:8]} {status_label} and saved to SQLite ({completion_reason})")

    except asyncio.CancelledError:
        logger.info(f"Background task {task_id[:8]} was cancelled")
        try:
            # Try to save partial results on cancellation too
            _save_partial_on_failure(task_id, "cancelled_by_user")
            state_manager.update_task(task_id, {
                "status": TaskStatus.CANCELLED,
                "completed_at": datetime.utcnow(),
                "current_action": "Cancelled by user (partial results may be available)"
            })
        except Exception as db_err:
            logger.error(f"Failed to update cancelled status for {task_id[:8]}: {db_err}")

    except Exception as e:
        logger.error(f"Background polling failed for {task_id[:8]}: {e}")
        try:
            # Try to save partial results on failure
            had_partial = _save_partial_on_failure(task_id, f"error: {str(e)[:200]}")
            state_manager.update_task(task_id, {
                "status": TaskStatus.COMPLETED_PARTIAL if had_partial else TaskStatus.FAILED,
                "error_message": str(e),
                "completed_at": datetime.utcnow(),
                "current_action": "Failed with partial results saved" if had_partial else f"Failed: {str(e)[:100]}"
            })
        except Exception as db_err:
            logger.critical(f"Failed to update error status for {task_id[:8]}: {db_err}")
        try:
            if notifier:
                notifier.notify_research_failed(task_id, str(e))
        except Exception as notify_err:
            logger.warning(f"Failed to send failure notification for {task_id[:8]}: {notify_err}")

    finally:
        # Always clean up the task registry
        _background_tasks.pop(task_id, None)


def _save_partial_on_failure(task_id: str, reason: str) -> bool:
    """Attempt to save any intermediate results from a failed/cancelled task.

    Returns True if partial results were saved, False otherwise.
    """
    try:
        intermediate = deep_research_engine.get_intermediate_results(task_id)
        if not intermediate:
            logger.debug(f"No intermediate results to save for {task_id[:8]}")
            return False

        best_result = max(intermediate, key=len)
        if not best_result or len(best_result) < 50:  # Skip trivially small fragments
            return False

        from deep_research import ResearchResult
        partial_result = ResearchResult(
            task_id=task_id,
            report=best_result,
            sources=[],
            metadata={
                "_is_partial": True,
                "_completion_reason": reason,
                "_intermediate_count": len(intermediate),
                "_best_result_chars": len(best_result),
            }
        )
        state_manager.save_result(task_id, partial_result)
        logger.info(f"Saved partial result for {task_id[:8]}: {len(best_result)} chars ({reason})")
        return True
    except Exception as e:
        logger.error(f"Failed to save partial results for {task_id[:8]}: {e}")
        return False


@mcp.tool()
async def start_deep_research(
    query: str,
    enable_notifications: bool = True,
    max_wait_hours: int = 8,
    model: str = "deep-research-pro-preview-12-2025",
) -> Dict[str, Any]:
    """Start a deep research task using Gemini Deep Research API.

    **Returns task_id in seconds** — research runs in background, never times out.

    **Usage Pattern**:
    ```
    # Step 1: Start research (returns task_id in <5 seconds)
    result = start_deep_research("What is quantum entanglement?")
    task_id = result["task_id"]

    # Step 2: Do other work while research runs (5-40 minutes)

    # Step 3: Check if done
    status = check_research_status(task_id)

    # Step 4: Retrieve results (zero-cost from SQLite)
    final = get_research_results(task_id)
    ```

    **How It Works**:
    1. Saves task to SQLite immediately
    2. Calls Gemini Interactions API to start research (~2-5 seconds)
    3. Saves interaction_id to SQLite for recovery
    4. Launches background polling coroutine (fire-and-forget)
    5. Returns task_id to caller — tool call completes in seconds

    **Expected Research Duration**:
    - Simple queries: 5-15 minutes
    - Complex queries: 20-40 minutes
    - Maximum timeout: 60 minutes

    **Why This Never Times Out**:
    - The tool call returns in <5 seconds with the task_id
    - Background polling runs as a server-internal coroutine
    - Results are saved to SQLite when Gemini completes
    - Desktop notification sent on completion

    Args:
        query: Research question or topic to investigate (3-10000 chars).
        enable_notifications: Send desktop notification on completion (default: True)
        max_wait_hours: Maximum hours for background polling (1-24, default: 8)
        model: Gemini model for research (default: deep-research-pro-preview-12-2025)

    Returns:
        Dict with task_id and status. Use check_research_status or
        get_research_results to monitor/retrieve.

    Example:
        >>> result = start_deep_research("Latest advances in quantum computing")
        >>> task_id = result["task_id"]  # Available immediately
        >>> # ... later ...
        >>> final = get_research_results(task_id)
    """
    # Check availability
    if not DEEP_RESEARCH_AVAILABLE or not deep_research_engine:
        return {
            "success": False,
            "error": "GEMINI_UNAVAILABLE",
            "message": f"Deep research not available: {DEEP_RESEARCH_ERROR}",
            "suggestion": "Check GEMINI_API_KEY in .env file"
        }

    # Validate query length
    if len(query) < 3:
        return {
            "success": False,
            "error": "INVALID_QUERY",
            "message": "Query too short. Minimum 3 characters required.",
            "suggestion": "Provide a more detailed research question"
        }

    if len(query) > 10000:
        return {
            "success": False,
            "error": "INVALID_QUERY",
            "message": "Query too long. Maximum 10000 characters allowed.",
            "suggestion": "Shorten your query or break into multiple questions"
        }

    # Generate unique task ID and save to SQLite FIRST (before any API call)
    task_id = str(uuid.uuid4())
    created_at = datetime.utcnow()

    task = ResearchTask(
        task_id=task_id,
        query=query,
        model=model,
        status=TaskStatus.PENDING,
        enable_notifications=enable_notifications,
        max_wait_hours=max_wait_hours,
        created_at=created_at
    )
    state_manager.save_task(task)
    logger.info(f"Created research task {task_id[:8]}: {query[:50]}...")

    # Start research via Gemini Interactions API
    # This is the only blocking call — typically 2-5 seconds
    try:
        start_result = await deep_research_engine.start_research(query, model)
    except Exception as e:
        logger.error(f"Failed to start Gemini research for {task_id[:8]}: {e}")
        state_manager.update_task(task_id, {
            "status": TaskStatus.FAILED,
            "error_message": f"Failed to start research: {str(e)}"
        })
        return {
            "success": False,
            "task_id": task_id,
            "error": "API_START_FAILED",
            "message": f"Failed to start Gemini research: {str(e)}",
            "suggestion": "Check API key and network, then retry"
        }

    interaction_id = start_result.get("interaction_id")

    # Save interaction_id to SQLite IMMEDIATELY (critical for recovery)
    state_manager.update_task(task_id, {
        "status": TaskStatus.RUNNING_ASYNC,
        "interaction_id": interaction_id,
        "current_action": "Research started, polling in background..."
    })

    logger.info(f"Task {task_id[:8]} started with interaction_id {interaction_id}")

    # Launch background polling — registered in _background_tasks for cancellation
    bg_task = asyncio.create_task(
        _background_poll_and_save(
            task_id=task_id,
            interaction_id=interaction_id,
            enable_notifications=enable_notifications,
            max_wait_seconds=max_wait_hours * 3600,
            created_at=created_at
        )
    )
    _background_tasks[task_id] = bg_task

    return {
        "success": True,
        "task_id": task_id,
        "status": "running",
        "interaction_id": interaction_id,
        "message": (
            f"Research started and running in background. "
            f"Expected duration: 5-40 minutes. "
            f"Use check_research_status('{task_id}') to monitor progress, "
            f"or get_research_results('{task_id}') when complete."
        ),
        "next_steps": [
            f"check_research_status(task_id='{task_id}')",
            f"get_research_results(task_id='{task_id}')"
        ]
    }


@mcp.tool()
def get_research_results(
    task_id: str,
    include_sources: bool = True,
    force_retrieve: bool = False
) -> Dict[str, Any]:
    """Retrieve completed research results from SQLite storage.

    💰 **Zero-Cost Retrieval**: Reads from SQLite cache - NO Gemini API calls!

    **Usage Pattern (v3.9.0+):**
    1. Call `start_deep_research(query)` - returns task_id in seconds
    2. Research runs in background (5-40 minutes)
    3. Use `check_research_status(task_id)` to monitor progress
    4. Call THIS function to retrieve results when complete - zero tokens!

    **Stuck at 99%?** Use `force_retrieve=True` to get partial results from
    hung tasks. The system auto-saves intermediate results, so even if the
    Gemini API never returns "completed", you can still get the data.

    **Usage Example:**
    ```python
    # Normal retrieval
    final_result = get_research_results(task_id)

    # Force retrieve from stuck/failed task
    partial = get_research_results(task_id, force_retrieve=True)
    if partial["success"]:
        print(partial["report"])  # May be partial but still useful
    ```

    **Zero Token Cost** - Reads from local SQLite database, no Gemini API calls.

    Args:
        task_id: Task UUID from start_deep_research response
        include_sources: Include source list in response (default: True)
        force_retrieve: If True, retrieve results even from non-completed tasks.
            Useful when research is stuck at 99% or failed with partial data.

    Returns:
        Dict with report, sources (optional), and metadata if completed;
        error information if not found or still in progress

    Example:
        >>> result = get_research_results("550e8400-e29b-41d4-a716-446655440000")
        >>> if result["success"]:
        ...     print(result["report"][:500])  # First 500 chars of report
        ...     print(f"Sources: {len(result['sources'])}")
    """
    # Check availability
    if not state_manager:
        return {
            "success": False,
            "error": "SQLITE_ERROR",
            "message": "State manager not available",
            "suggestion": "Check server initialization"
        }

    # Validate task_id format (basic UUID check)
    try:
        uuid.UUID(task_id)
    except ValueError:
        return {
            "success": False,
            "error": "INVALID_QUERY",
            "message": f"Invalid task_id format: {task_id}",
            "suggestion": "Provide a valid UUID from start_deep_research"
        }

    # Get task from SQLite
    task = state_manager.get_task(task_id)
    if not task:
        return {
            "success": False,
            "error": "TASK_NOT_FOUND",
            "message": f"No research task found with ID: {task_id}",
            "suggestion": "Verify task_id from start_deep_research response"
        }

    # Retrievable statuses: completed, completed_partial, or force_retrieve
    retrievable_statuses = {TaskStatus.COMPLETED, TaskStatus.COMPLETED_PARTIAL}
    is_retrievable = task.status in retrievable_statuses or force_retrieve

    # Check if completed (or force_retrieve)
    if not is_retrievable:
        stuck_hint = ""
        if task.progress >= 95:
            stuck_hint = " TIP: Use force_retrieve=True to get partial results from this stuck task."
        return {
            "success": False,
            "error": "RESEARCH_NOT_COMPLETED",
            "task_id": task_id,
            "status": task.status.value,
            "progress": task.progress,
            "message": f"Research is still in progress. Current progress: {task.progress}%.{stuck_hint}",
            "suggestion": "Wait for completion, use check_research_status to monitor, or set force_retrieve=True"
        }

    # Get results from SQLite
    result = state_manager.get_result(task_id)
    if not result:
        if force_retrieve:
            return {
                "success": False,
                "error": "NO_PARTIAL_DATA",
                "task_id": task_id,
                "status": task.status.value,
                "progress": task.progress,
                "message": "No results saved yet (partial or complete). Research may still be in early stages.",
                "suggestion": "Wait longer and try again, or cancel with cancel_research"
            }
        return {
            "success": False,
            "error": "RESEARCH_FAILED",
            "task_id": task_id,
            "message": "Task completed but results not found in database",
            "suggestion": "Research may have failed. Check task status for error details."
        }

    # Calculate duration
    duration_minutes = 0
    end_time = task.completed_at or datetime.utcnow()
    if task.created_at:
        duration_minutes = (end_time - task.created_at).total_seconds() / 60

    # Determine if this is a partial result
    is_partial = (
        task.status == TaskStatus.COMPLETED_PARTIAL
        or force_retrieve
        or result.metadata.get("_is_partial", False)
    )

    # Build response per contract
    response = {
        "success": True,
        "task_id": task_id,
        "query": task.query,
        "report": result.report,
        "is_partial": is_partial,
        "metadata": {
            "duration_minutes": round(duration_minutes, 2),
            "tokens_used": {
                "input": task.tokens_input,
                "output": task.tokens_output
            },
            "cost_usd": round(task.cost_usd or (
                task.tokens_input * 0.000001 + task.tokens_output * 0.000004
            ), 4),
            "mode": "async" if task.status == TaskStatus.RUNNING_ASYNC else "sync",
            "model": task.model,
            "source_count": len(result.sources),
            "started_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "completion_reason": result.metadata.get("_completion_reason", "api_completed"),
        }
    }

    if is_partial:
        response["partial_warning"] = (
            "This result was auto-captured from a hung/failed research task. "
            "The report may be incomplete but contains the best available data."
        )

    # Include sources if requested
    if include_sources:
        response["sources"] = [s.to_dict() for s in result.sources]

    return response


@mcp.tool()
def check_research_status(task_id: str) -> Dict[str, Any]:
    """Check status of a running deep research task.

    **Usage (v3.9.0):**
    ```python
    # Start research (returns immediately with task_id)
    result = start_deep_research("query")
    task_id = result["task_id"]

    # Check progress periodically (or wait for desktop notification)
    status = check_research_status(task_id)
    if status["status"] == "completed":
        final = get_research_results(task_id)
    ```

    **Zero Token Cost** - Reads from local SQLite database, no Gemini API calls.

    Research runs in the background on the server. A desktop notification is
    sent when complete (if enabled). Use this to check progress or confirm
    completion before calling get_research_results.

    Args:
        task_id: Task UUID from start_deep_research response

    Returns:
        Dict with task status, progress, elapsed time, and other details

    Example:
        >>> status = check_research_status("550e8400-e29b-41d4-a716-446655440000")
        >>> if status["status"] == "completed":
        ...     print("Research complete! Use get_research_results to retrieve.")
        >>> else:
        ...     print(f"Progress: {status['progress']}% - {status['current_action']}")
    """
    # Check availability
    if not state_manager:
        return {
            "success": False,
            "error": "SQLITE_ERROR",
            "message": "State manager not available",
            "suggestion": "Check server initialization"
        }

    # Validate task_id format (basic UUID check)
    try:
        uuid.UUID(task_id)
    except ValueError:
        return {
            "success": False,
            "error": "INVALID_QUERY",
            "message": f"Invalid task_id format: {task_id}",
            "suggestion": "Provide a valid UUID from start_deep_research"
        }

    # Get task from SQLite
    task = state_manager.get_task(task_id)
    if not task:
        return {
            "success": False,
            "error": "TASK_NOT_FOUND",
            "message": f"No research task found with ID: {task_id}",
            "suggestion": "Verify task_id from start_deep_research response"
        }

    # Calculate elapsed time
    elapsed_seconds = 0
    if task.created_at:
        elapsed_seconds = (datetime.utcnow() - task.created_at).total_seconds()
    elapsed_minutes = round(elapsed_seconds / 60, 2)

    # Calculate estimated completion (if we have progress)
    estimated_completion_minutes = None
    if task.progress > 0 and task.progress < 100:
        # Linear estimation based on current progress
        estimated_total = elapsed_minutes / (task.progress / 100)
        estimated_completion_minutes = round(estimated_total - elapsed_minutes, 2)

    # Calculate cost so far
    cost_so_far = round(
        task.tokens_input * 0.000001 + task.tokens_output * 0.000004, 4
    )

    # Build response based on status
    if task.status in (TaskStatus.COMPLETED, TaskStatus.COMPLETED_PARTIAL):
        is_partial = task.status == TaskStatus.COMPLETED_PARTIAL
        return {
            "success": True,
            "task_id": task_id,
            "status": task.status.value,
            "progress": 100,
            "current_action": "Research complete (partial)" if is_partial else "Research complete",
            "elapsed_minutes": elapsed_minutes,
            "is_partial": is_partial,
            "message": f"Use get_research_results(task_id='{task_id}') to retrieve results"
        }

    elif task.status == TaskStatus.FAILED:
        # Check if partial results were saved
        has_partial = state_manager.get_result(task_id) is not None
        response = {
            "success": False,
            "task_id": task_id,
            "status": "failed",
            "progress": task.progress,
            "error_message": task.error_message or "Unknown error",
            "elapsed_minutes": elapsed_minutes
        }
        if has_partial:
            response["has_partial_results"] = True
            response["suggestion"] = f"Partial results available! Use get_research_results(task_id='{task_id}', force_retrieve=True)"
        return response

    elif task.status == TaskStatus.CANCELLED:
        has_partial = state_manager.get_result(task_id) is not None
        response = {
            "success": True,
            "task_id": task_id,
            "status": "cancelled",
            "progress": task.progress,
            "elapsed_minutes": elapsed_minutes,
            "message": "Research was cancelled"
        }
        if has_partial:
            response["has_partial_results"] = True
            response["suggestion"] = f"Partial results saved! Use get_research_results(task_id='{task_id}', force_retrieve=True)"
        return response

    else:
        # Running or running_async
        response = {
            "success": True,
            "task_id": task_id,
            "status": task.status.value,
            "progress": task.progress,
            "current_action": task.current_action or "Processing...",
            "elapsed_minutes": elapsed_minutes,
            "tokens_used": {
                "input": task.tokens_input,
                "output": task.tokens_output
            },
            "cost_so_far": cost_so_far
        }

        if estimated_completion_minutes is not None:
            response["estimated_completion_minutes"] = estimated_completion_minutes

        # Add hanging detection info for long-running tasks
        if deep_research_engine and elapsed_minutes > 5:
            try:
                hanging_status = deep_research_engine.check_hanging(
                    task_id,
                    task.created_at
                )
                response["hanging_detection"] = {
                    "is_hanging": hanging_status.is_hanging,
                    "confidence": round(hanging_status.confidence, 2),
                    "stall_minutes": round(hanging_status.stall_minutes, 1),
                    "reason": hanging_status.reason,
                    "recommendation": hanging_status.recommendation
                }
                # Add warning if task appears hung
                if hanging_status.is_hanging:
                    response["warning"] = f"Task may be hung: {hanging_status.reason}"
                    response["suggestion"] = hanging_status.recommendation
                # Suggest force_retrieve for tasks stuck at high progress
                if task.progress >= 95 and elapsed_minutes > 20:
                    response["force_retrieve_available"] = True
                    response["force_retrieve_hint"] = (
                        f"Task stuck at {task.progress}% for {elapsed_minutes:.0f} min. "
                        f"Try: get_research_results(task_id='{task_id}', force_retrieve=True)"
                    )
            except Exception as e:
                logger.debug(f"Could not check hanging status: {e}")

        return response


@mcp.tool()
def list_research_tasks(
    status_filter: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """List research tasks from SQLite - recover task_ids after tool timeouts.

    **Key Use Case**: When start_deep_research times out, the task_id is STILL
    in SQLite. Call this to recover it, then use check_research_status or
    get_research_results with the recovered task_id.

    **Zero Token Cost** - Reads from local SQLite, no Gemini API calls.

    Args:
        status_filter: Filter by status: "running", "pending", "completed",
                      "failed", "cancelled", or None for all tasks
        limit: Max tasks to return (default: 20, max: 100)

    Returns:
        Dict with tasks list (task_id, query, status, progress, timestamps)
    """
    # Check availability
    if not state_manager:
        return {
            "success": False,
            "error": "SQLITE_ERROR",
            "message": "State manager not available",
            "suggestion": "Check server initialization"
        }

    # Validate limit
    limit = max(1, min(limit, 100))

    # Validate status_filter
    valid_statuses = {"running", "pending", "completed", "completed_partial", "failed", "cancelled", None}
    if status_filter and status_filter.lower() not in {s for s in valid_statuses if s}:
        return {
            "success": False,
            "error": "INVALID_FILTER",
            "message": f"Invalid status_filter: {status_filter}",
            "suggestion": f"Use one of: running, pending, completed, completed_partial, failed, cancelled"
        }

    try:
        # Get all tasks from SQLite
        all_tasks = state_manager.get_all_tasks(limit=limit * 2)  # Get extra for filtering

        # Filter by status if provided
        if status_filter:
            status_lower = status_filter.lower()
            filtered_tasks = [
                t for t in all_tasks
                if t.status.name.lower() == status_lower
            ][:limit]
        else:
            filtered_tasks = all_tasks[:limit]

        # Format response
        task_list = []
        for task in filtered_tasks:
            elapsed_seconds = 0
            if task.created_at:
                elapsed_seconds = (datetime.utcnow() - task.created_at).total_seconds()

            task_info = {
                "task_id": task.task_id,
                "query": task.query[:100] + "..." if len(task.query) > 100 else task.query,
                "status": task.status.name.lower(),
                "progress": task.progress,
                "current_action": task.current_action,
                "elapsed_minutes": round(elapsed_seconds / 60, 2),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "model": task.model
            }

            # Add completed_at if available
            if task.completed_at:
                task_info["completed_at"] = task.completed_at.isoformat()

            # Add error_message if failed
            if task.error_message:
                task_info["error_message"] = task.error_message[:200]

            task_list.append(task_info)

        # Count by status for summary
        status_counts = {}
        for task in all_tasks:
            status_name = task.status.name.lower()
            status_counts[status_name] = status_counts.get(status_name, 0) + 1

        return {
            "success": True,
            "tasks": task_list,
            "count": len(task_list),
            "total_in_db": len(all_tasks),
            "status_counts": status_counts,
            "filter_applied": status_filter,
            "message": (
                f"Found {len(task_list)} task(s)"
                + (f" with status '{status_filter}'" if status_filter else "")
                + ". Use task_id with check_research_status or get_research_results."
            )
        }

    except Exception as e:
        logger.error(f"Error listing research tasks: {e}")
        return {
            "success": False,
            "error": "DATABASE_ERROR",
            "message": f"Failed to list tasks: {str(e)}",
            "suggestion": "Check SQLite database connectivity"
        }


@mcp.tool()
def cancel_research(
    task_id: str,
    save_partial: bool = True
) -> Dict[str, Any]:
    """Cancel a running research task. Optionally save partial results.

    Use this tool when you need to stop a long-running research task before completion.
    This is useful when:
    - The research is taking too long
    - You realize the query was incorrect
    - You want to start a different research task
    - The user requests cancellation

    **Partial Results**: By default, any partial results gathered before cancellation
    are saved and can be retrieved with get_research_results. Set save_partial=False
    to discard all progress.

    **Zero Gemini Cost**: Cancellation itself doesn't consume tokens, though
    partial costs from research already performed are retained.

    Args:
        task_id: Task UUID from start_deep_research response.
        save_partial: Whether to save partial results before canceling (default: True).

    Returns:
        Dict with cancellation status, progress at cancellation, and cost info.
    """
    if not DEEP_RESEARCH_AVAILABLE:
        return {
            "success": False,
            "error": "DEEP_RESEARCH_NOT_AVAILABLE",
            "message": f"Deep research module not available: {DEEP_RESEARCH_ERROR}"
        }

    # Validate UUID format
    try:
        uuid.UUID(task_id)
    except ValueError:
        return {
            "success": False,
            "error": "INVALID_TASK_ID",
            "message": "Invalid task_id format. Expected UUID v4."
        }

    # Get task from database
    task = state_manager.get_task(task_id)
    if not task:
        return {
            "success": False,
            "error": "TASK_NOT_FOUND",
            "message": f"No research task found with ID: {task_id}",
            "suggestion": "Verify task_id from start_deep_research response"
        }

    # Check if task is already completed or failed
    if task.status == TaskStatus.COMPLETED:
        return {
            "success": False,
            "error": "RESEARCH_ALREADY_COMPLETED",
            "task_id": task_id,
            "status": "completed",
            "message": "Cannot cancel: research already completed",
            "suggestion": "Use get_research_results to retrieve completed research"
        }

    if task.status == TaskStatus.FAILED:
        return {
            "success": False,
            "error": "RESEARCH_ALREADY_FAILED",
            "task_id": task_id,
            "status": "failed",
            "message": "Cannot cancel: research already failed",
            "error_message": task.error_message
        }

    if task.status == TaskStatus.CANCELLED:
        return {
            "success": False,
            "error": "RESEARCH_ALREADY_CANCELLED",
            "task_id": task_id,
            "status": "cancelled",
            "message": "Research was already cancelled"
        }

    # Try to cancel the background task
    progress_at_cancellation = task.progress
    partial_saved = False

    # Calculate cost so far
    cost_usd = 0.0
    if task.tokens_input > 0 or task.tokens_output > 0:
        from deep_research import TokenUsage
        usage = TokenUsage(input=task.tokens_input, output=task.tokens_output)
        cost_usd = usage.estimate_cost_usd()

    # Optionally save partial results
    if save_partial and task.progress > 0:
        # Check if there's any existing result to preserve
        existing_result = state_manager.get_result(task_id)
        if existing_result and existing_result.report:
            partial_saved = True
            # Result already exists, just mark as partial in metadata
            if existing_result.metadata is None:
                existing_result.metadata = {}
            existing_result.metadata["cancelled_at_progress"] = progress_at_cancellation
            existing_result.metadata["partial"] = True
            state_manager.save_result(task_id, existing_result)

    # Cancel the background polling coroutine if it's running
    bg_task = _background_tasks.get(task_id)
    if bg_task and not bg_task.done():
        bg_task.cancel()
        logger.info(f"Cancelled background polling coroutine for {task_id[:8]}")
    else:
        # Background task not found — update SQLite directly
        state_manager.update_task(task_id, {
            "status": TaskStatus.CANCELLED,
            "current_action": f"Cancelled at {progress_at_cancellation}% progress",
            "cost_usd": cost_usd,
            "completed_at": datetime.utcnow()
        })

    logger.info(f"Research task {task_id} cancelled at {progress_at_cancellation}%")

    response = {
        "success": True,
        "task_id": task_id,
        "status": "cancelled",
        "partial_results_saved": partial_saved,
        "progress_at_cancellation": progress_at_cancellation,
        "cost_usd": round(cost_usd, 4)
    }

    if partial_saved:
        response["message"] = "Research cancelled. Partial results saved and accessible via get_research_results."
    else:
        response["message"] = "Research cancelled. No partial results available."

    return response


@mcp.tool()
async def resume_research(task_id: str) -> Dict[str, Any]:
    """Resume a failed, hung, or interrupted research task.

    Use this tool when:
    - A research task was identified as hung by check_research_status
    - A research task failed but may have partial results
    - You want to retry a task after a transient error
    - The server was restarted while research was in progress

    **Zero Token Cost** if the research already completed or failed.
    **May Use Tokens** if research is still running and needs to continue.

    **Recovery Features**:
    - Checks if the Gemini interaction is still available
    - Retrieves any cached intermediate results from streaming
    - Can return partial results if research cannot be resumed
    - Continues polling with streaming capture if still running

    Args:
        task_id: Task UUID from start_deep_research response

    Returns:
        Dict with resume status:
        - "completed": Research finished, results available
        - "resumed": Continuing to poll, check status later
        - "failed_with_partial": Failed but has partial results
        - "unrecoverable": Cannot resume, no partial results

    Example:
        >>> status = check_research_status("550e8400...")
        >>> if status.get("hanging_detection", {}).get("is_hanging"):
        ...     result = await resume_research("550e8400...")
        ...     if result["status"] == "failed_with_partial":
        ...         print("Got partial results:", result["partial_report"][:200])
    """
    if not DEEP_RESEARCH_AVAILABLE:
        return {
            "success": False,
            "error": "DEEP_RESEARCH_NOT_AVAILABLE",
            "message": f"Deep research module not available: {DEEP_RESEARCH_ERROR}"
        }

    # Validate UUID format
    try:
        uuid.UUID(task_id)
    except ValueError:
        return {
            "success": False,
            "error": "INVALID_TASK_ID",
            "message": "Invalid task_id format. Expected UUID v4."
        }

    # Get task from database
    task = state_manager.get_task(task_id)
    if not task:
        return {
            "success": False,
            "error": "TASK_NOT_FOUND",
            "message": f"No research task found with ID: {task_id}",
            "suggestion": "Verify task_id from start_deep_research response"
        }

    # Check if already completed
    if task.status == TaskStatus.COMPLETED:
        return {
            "success": True,
            "status": "already_completed",
            "task_id": task_id,
            "message": "Research already completed. Use get_research_results to retrieve.",
            "suggestion": f"get_research_results(task_id='{task_id}')"
        }

    # Need interaction_id to resume
    if not task.interaction_id:
        return {
            "success": False,
            "error": "NO_INTERACTION_ID",
            "task_id": task_id,
            "message": "Task has no Gemini interaction ID. Cannot resume.",
            "suggestion": "Start a new research task with start_deep_research"
        }

    logger.info(f"Attempting to resume research task {task_id}")

    try:
        # Use engine's resume capability
        resume_result = await deep_research_engine.resume_research(
            task_id=task_id,
            interaction_id=task.interaction_id
        )

        resume_status = resume_result.get("status", "unknown")

        if resume_status == "completed":
            # Research finished - save results
            raw_result = resume_result.get("result", {})
            research_result = deep_research_engine.create_research_result(task_id, raw_result)
            state_manager.save_result(task_id, research_result)

            # Update task to completed
            state_manager.update_task(task_id, {
                "status": TaskStatus.COMPLETED,
                "progress": 100,
                "current_action": "Research complete (resumed)",
                "completed_at": datetime.utcnow()
            })

            return {
                "success": True,
                "status": "completed",
                "task_id": task_id,
                "message": "Research completed successfully after resume.",
                "suggestion": f"Use get_research_results(task_id='{task_id}') to retrieve full report"
            }

        elif resume_status in ["failed_with_partial", "resume_failed_with_partial"]:
            # Failed but we have partial results
            raw_result = resume_result.get("result", {})

            # Check if partial report has content
            partial_report = raw_result.get("report", "")
            if partial_report:
                # Save partial results
                research_result = deep_research_engine.create_research_result(task_id, raw_result)
                state_manager.save_result(task_id, research_result)

                # Update task with partial completion
                state_manager.update_task(task_id, {
                    "status": TaskStatus.COMPLETED,  # Mark as completed so results are retrievable
                    "progress": 100,
                    "current_action": "Partial results saved",
                    "error_message": raw_result.get("metadata", {}).get("error", "Research incomplete"),
                    "completed_at": datetime.utcnow()
                })

                return {
                    "success": True,
                    "status": "partial_results_saved",
                    "task_id": task_id,
                    "partial_report_preview": partial_report[:500] + "..." if len(partial_report) > 500 else partial_report,
                    "message": "Research failed but partial results were recovered and saved.",
                    "suggestion": f"Use get_research_results(task_id='{task_id}') to retrieve partial report"
                }
            else:
                return {
                    "success": False,
                    "status": "failed_no_results",
                    "task_id": task_id,
                    "error": resume_result.get("error", "Unknown failure"),
                    "message": "Research failed and no partial results available."
                }

        elif resume_status == "failed":
            return {
                "success": False,
                "status": "failed",
                "task_id": task_id,
                "error": resume_result.get("error", "Unknown failure"),
                "message": "Research failed. Consider starting a new research task."
            }

        else:
            return {
                "success": False,
                "status": resume_status,
                "task_id": task_id,
                "message": f"Unexpected resume status: {resume_status}"
            }

    except Exception as e:
        logger.error(f"Resume failed for {task_id}: {e}")

        # Check if we have any cached intermediate results
        cached = deep_research_engine.get_intermediate_results(task_id)
        if cached:
            partial_report = "\n\n".join(cached)
            return {
                "success": False,
                "status": "resume_failed_with_cache",
                "task_id": task_id,
                "error": str(e),
                "cached_chunks": len(cached),
                "partial_report_preview": partial_report[:500] + "..." if len(partial_report) > 500 else partial_report,
                "message": f"Resume failed but {len(cached)} cached chunks available.",
                "suggestion": "You may save these cached results manually or start new research."
            }

        return {
            "success": False,
            "error": "RESUME_FAILED",
            "task_id": task_id,
            "message": f"Failed to resume research: {str(e)}",
            "suggestion": "Consider starting a new research task"
        }


@mcp.tool()
def estimate_research_cost(query: str) -> Dict[str, Any]:
    """Estimate cost and duration before starting research. Analyzes query complexity.

    Use this tool BEFORE starting research to:
    - Understand if the query will complete quickly (sync) or take time (async)
    - Get an estimate of the token and dollar costs involved
    - Receive recommendations on query optimization
    - Make informed decisions about whether to proceed

    **Zero Token Cost**: This tool uses local heuristics only - no Gemini API calls.

    **Complexity Factors Analyzed**:
    - Query length and structure
    - Multi-domain scope (comparing topics, regions, etc.)
    - Temporal scope (historical analysis, forecasts)
    - Synthesis requirements (analysis, evaluation, comparison)

    Args:
        query: The research question to analyze (3-10000 characters).

    Returns:
        Dict with complexity assessment, duration/cost estimates, and recommendations.
    """
    if not DEEP_RESEARCH_AVAILABLE:
        return {
            "success": False,
            "error": "DEEP_RESEARCH_NOT_AVAILABLE",
            "message": f"Deep research module not available: {DEEP_RESEARCH_ERROR}"
        }

    # Validate query length
    if not query or len(query) < 3:
        return {
            "success": False,
            "error": "QUERY_TOO_SHORT",
            "message": "Query must be at least 3 characters"
        }

    if len(query) > 10000:
        return {
            "success": False,
            "error": "QUERY_TOO_LONG",
            "message": "Query must be 10000 characters or less"
        }

    # Use the CostEstimator
    from deep_research.cost_estimator import get_cost_estimator

    estimator = get_cost_estimator()
    estimate = estimator.estimate(query)

    return {
        "query": query[:200] + "..." if len(query) > 200 else query,
        "query_complexity": estimate.query_complexity,
        "estimated_duration": {
            "min_minutes": estimate.min_minutes,
            "max_minutes": estimate.max_minutes,
            "likely_minutes": estimate.likely_minutes
        },
        "estimated_cost": {
            "min_usd": estimate.min_usd,
            "max_usd": estimate.max_usd,
            "likely_usd": estimate.likely_usd
        },
        "will_likely_go_async": estimate.will_likely_go_async,
        "recommendation": estimate.recommendation
    }


@mcp.tool()
def save_research_to_markdown(
    task_id: str,
    output_dir: str = "./research_reports",
    filename_prefix: str = "research",
    include_metadata: bool = True,
    include_sources: bool = True
) -> Dict[str, Any]:
    """Save completed research to permanent Markdown file using Jinja2 templates.

    Use this tool after research completes to save results to a well-formatted
    Markdown file. Reports are organized by month for easy retrieval.

    **Zero Token Cost**: This tool uses local Jinja2 templates only - no Gemini API calls.

    **File Organization**:
    Reports are saved in month-organized directories:
    `{output_dir}/2025-12/research_550e8400_20251214_103045.md`

    **Sections Included**:
    - Title and metadata (query, cost, duration, tokens)
    - Full research report (Markdown)
    - Sources with URLs and relevance scores

    Args:
        task_id: Task UUID from start_deep_research response.
        output_dir: Directory for output files (default: ./research_reports).
        filename_prefix: Prefix for filename (default: "research").
        include_metadata: Include metadata section in output (default: True).
        include_sources: Include sources section in output (default: True).

    Returns:
        Dict with file_path, filename, file_size_kb, and sections_included.
    """
    if not DEEP_RESEARCH_AVAILABLE:
        return {
            "success": False,
            "error": "DEEP_RESEARCH_NOT_AVAILABLE",
            "message": f"Deep research module not available: {DEEP_RESEARCH_ERROR}"
        }

    # Validate UUID format
    try:
        uuid.UUID(task_id)
    except ValueError:
        return {
            "success": False,
            "error": "INVALID_TASK_ID",
            "message": "Invalid task_id format. Expected UUID v4."
        }

    # Get task from database
    task = state_manager.get_task(task_id)
    if not task:
        return {
            "success": False,
            "error": "TASK_NOT_FOUND",
            "message": f"No research task found with ID: {task_id}",
            "suggestion": "Verify task_id from start_deep_research response"
        }

    # Check if task is completed
    if task.status != TaskStatus.COMPLETED:
        return {
            "success": False,
            "error": "RESEARCH_NOT_COMPLETED",
            "task_id": task_id,
            "status": task.status.value,
            "progress": task.progress,
            "message": f"Cannot save: research {'still in progress' if task.status in [TaskStatus.RUNNING, TaskStatus.RUNNING_ASYNC] else 'not completed'} ({task.progress}%)",
            "suggestion": "Wait for completion before saving to Markdown"
        }

    # Get research result
    result = state_manager.get_result(task_id)
    if not result:
        return {
            "success": False,
            "error": "RESULT_NOT_FOUND",
            "task_id": task_id,
            "message": "Research completed but results not found in database",
            "suggestion": "Results may have been deleted. Cannot save."
        }

    # Use MarkdownStorage to save the report
    from deep_research.storage import get_markdown_storage

    storage = get_markdown_storage(output_dir)

    # Prepare task data for the template
    task_data = {
        "status": task.status.value,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "tokens_input": task.tokens_input,
        "tokens_output": task.tokens_output,
        "cost_usd": task.cost_usd,
        "model": task.model
    }

    try:
        save_result = storage.save_report(
            task_id=task_id,
            query=task.query,
            report=result.report,
            sources=result.sources,
            metadata=result.metadata,
            task_data=task_data,
            prefix=filename_prefix,
            include_metadata=include_metadata,
            include_sources=include_sources
        )
        return save_result
    except Exception as e:
        logger.error(f"Failed to save research to markdown: {e}")
        return {
            "success": False,
            "error": "SAVE_FAILED",
            "task_id": task_id,
            "message": f"Failed to save report: {str(e)}"
        }


# ============================================================================
# Original Gemini Tools
# ============================================================================

def call_gemini(prompt: str, temperature: float = 0.5, model: str = "gemini-3-flash-preview") -> str:
    """Call Gemini using the new unified SDK and return response"""
    if not GEMINI_AVAILABLE or not client:
        return f"Gemini not available: {GEMINI_ERROR}"
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=8192,
            )
        )
        return response.text
    except Exception as e:
        return f"Error calling Gemini: {str(e)}"

IMAGE_MODELS = {
    "nano-banana-pro": "nano-banana-pro-preview",
    "nano-banana": "gemini-2.5-flash-image",
    "pro": "gemini-3-pro-image",
    "flash": "gemini-3.1-flash-image",
    "flash-lite": "gemini-3.1-flash-lite-image",
}


@mcp.tool()
def generate_image(
    prompt: str,
    output_path: str,
    model: str = "nano-banana-pro",
    reference_images: Optional[List[str]] = None,
) -> str:
    """Generate an image from a text prompt using Gemini's image models (Nano Banana) and save it to disk.

    Use this when you need to CREATE a picture rather than analyze one — interpret_image is the
    read side, this is the write side. Good for:
    - Logos, app icons and favicons
    - Illustrations, diagrams and concept art
    - Mockup imagery, hero images, placeholder art
    - Editing or restyling an existing image (pass it via reference_images)

    The image is written to output_path and the path is returned; nothing is embedded in the
    response, so large images never enter the conversation. Always LOOK at the result afterwards
    (read the file, or build an HTML preview) rather than assuming it matched the prompt.

    Prompting notes that materially change the output:
    - Describe the SUBJECT, STYLE and BACKGROUND explicitly.
    - Say "NO TEXT, NO LETTERS" unless you want lettering — these models add text readily and
      usually render it badly.
    - For an icon, state the smallest size it must survive ("legible at 48x48 pixels"); models
      otherwise produce fine detail that disappears when scaled down.

    Args:
        prompt: What to generate. Specific beats short.
        output_path: Where to write the PNG. Absolute, or relative to the server's cwd.
                     Parent directories are created if missing.
        model: One of nano-banana-pro (default, highest quality), nano-banana, pro,
               flash, flash-lite — or a raw Gemini model id.
        reference_images: Optional local image paths to condition on, for editing or
                          style-matching an existing image.
    """
    if not GEMINI_AVAILABLE or not client:
        return f"❌ Gemini not available: {GEMINI_ERROR}"

    model_id = IMAGE_MODELS.get(model, model)
    parts: List[Any] = [prompt]
    try:
        for ref in (reference_images or []):
            rp = Path(ref).expanduser()
            if not rp.is_file():
                return f"❌ Reference image not found: {rp}"
            mime = mimetypes.guess_type(str(rp))[0] or "image/png"
            parts.append(types.Part.from_bytes(data=rp.read_bytes(), mime_type=mime))
    except Exception as e:
        return f"❌ Could not read reference image: {e}"

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=parts,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
    except Exception as e:
        return f"❌ Image generation failed ({model_id}): {e}"

    out = Path(output_path).expanduser()
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return f"❌ Cannot create output directory {out.parent}: {e}"

    for cand in (response.candidates or []):
        for part in (cand.content.parts if cand.content else []):
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                try:
                    out.write_bytes(inline.data)
                except Exception as e:
                    return f"❌ Could not write {out}: {e}"
                size = out.stat().st_size
                return (f"🎨 Image generated with {model_id}\n\n"
                        f"Saved to : {out}\n"
                        f"Size     : {size:,} bytes\n\n"
                        f"Now LOOK at it before using it — read the file, or build an HTML "
                        f"preview at the size it will actually be displayed.")

    # No image came back. Say WHY, and surface any text the model returned instead
    # of reporting a bare failure (a swallowed reason is worse than an error).
    reason = ""
    try:
        c0 = (response.candidates or [None])[0]
        if c0 is not None:
            reason = f" finish_reason={getattr(c0, 'finish_reason', None)}"
            for part in (c0.content.parts if c0.content else []):
                if getattr(part, "text", None):
                    reason += f" | model said: {part.text[:300]}"
    except Exception:
        pass
    fb = getattr(response, "prompt_feedback", None)
    if fb:
        reason += f" | prompt_feedback={fb}"
    return (f"❌ {model_id} returned no image.{reason}\n"
            f"Common cause: the prompt was refused, or the model id does not support "
            f"image output. Try model='pro' or rephrase the prompt.")


@mcp.tool()
def ask_gemini(prompt: str, temperature: float = 0.5) -> str:
    """Ask Gemini a general question and get a direct response for collaboration between AI assistants.

    Use this tool when you need Gemini's perspective, analysis, or expertise on any topic that doesn't
    fit the specialized tools below. This is ideal for:
    - General knowledge questions and explanations
    - Getting a second opinion on technical decisions or approaches
    - Exploring alternative viewpoints or methodologies
    - Discussing best practices, patterns, or architectural choices
    - Asking about technologies, frameworks, or concepts
    - Seeking creative solutions to problems
    - Collaborative problem-solving where two AI perspectives are valuable

    This is the most flexible tool - use it when other specialized tools (code_review, debug,
    brainstorm, research) don't fit your specific need. Think of this as asking a colleague for
    their input or expertise.

    Args:
        prompt: The question or prompt for Gemini. Be specific and provide context for best results.
        temperature: Controls randomness in responses (0.0-1.0, default: 0.5).
                    Lower values (0.2-0.4) = more focused/deterministic responses.
                    Higher values (0.6-0.8) = more creative/varied responses.
    """
    result = call_gemini(prompt, temperature)
    return f"🤖 GEMINI RESPONSE:\n\n{result}"

@mcp.tool()
def gemini_code_review(code: str, focus_areas: Optional[List[str]] = None) -> str:
    """Request a comprehensive code review from Gemini with detailed feedback on quality, security, and best practices.

    Use this tool specifically when you need expert code analysis and review. This is NOT for debugging
    errors (use gemini_debug for that). Instead, use this when you want to:
    - Get a thorough code quality assessment before committing or deploying
    - Identify potential security vulnerabilities (SQL injection, XSS, auth issues, etc.)
    - Find performance bottlenecks or optimization opportunities
    - Ensure code follows best practices and design patterns
    - Improve code readability, maintainability, and documentation
    - Catch logic bugs, edge cases, or potential runtime issues
    - Get suggestions for refactoring or architectural improvements
    - Review code for compliance with coding standards

    Gemini will provide specific, actionable feedback on issues found, explain WHY they're problems,
    and suggest concrete improvements. The review uses lower temperature (0.2) for consistent,
    analytical feedback.

    Args:
        code: The code snippet or full file to review. Include enough context for meaningful analysis.
        focus_areas: Optional list to narrow the review scope. Examples:
                    ["security"] - Focus only on security vulnerabilities
                    ["performance", "readability"] - Focus on speed and clarity
                    ["best practices", "bugs"] - Focus on correctness and patterns
                    If omitted, provides a comprehensive review of all aspects.
    """
    focus = ", ".join(focus_areas) if focus_areas else "general code quality"
    
    prompt = f"""Please review this code with a focus on {focus}:

```
{code}
```

Provide specific, actionable feedback on:
1. Potential issues or bugs
2. Security concerns (if applicable)
3. Performance optimizations
4. Best practices
5. Code clarity and maintainability

Please be thorough but concise in your analysis."""
    
    result = call_gemini(prompt, 0.2)  # Lower temperature for analytical tasks
    return f"🤖 GEMINI RESPONSE:\n\n{result}"

@mcp.tool()
def gemini_brainstorm(topic: str, context: str = "") -> str:
    """Engage Gemini in creative brainstorming to generate innovative ideas, solutions, and alternatives.

    Use this tool when you need creative, out-of-the-box thinking and want to explore multiple
    approaches or solutions. This is perfect for:
    - Generating multiple solution approaches to a problem
    - Exploring architectural options and trade-offs for a new feature
    - Coming up with creative naming ideas for projects, functions, or variables
    - Brainstorming test cases, edge cases, or scenarios to consider
    - Thinking through user experience flows and alternatives
    - Generating ideas for improving existing systems or workflows
    - Exploring "what if" scenarios and their implications
    - Finding creative ways to work around constraints or limitations
    - Discovering novel approaches to challenging technical problems

    This tool uses higher temperature (0.7) to encourage diverse, creative responses. Gemini will
    provide multiple alternatives, consider various angles, and think innovatively rather than
    converging on a single "correct" answer.

    Args:
        topic: The specific topic or problem to brainstorm about. Be clear about what you need ideas for.
        context: Additional background information, constraints, or requirements to guide the brainstorming.
                Include things like: current situation, limitations, goals, preferences, or related context
                that will help generate more relevant and practical ideas.
    """
    prompt = f"Let's brainstorm about: {topic}"
    if context:
        prompt += f"\n\nContext: {context}"
    prompt += "\n\nProvide creative ideas, alternatives, and considerations. Think outside the box and offer innovative solutions."
    
    result = call_gemini(prompt, 0.7)  # Higher temperature for creativity
    return f"🤖 GEMINI RESPONSE:\n\n{result}"

@mcp.tool()
def gemini_debug(error_message: str, code_snippet: str = "", context: str = "") -> str:
    """Get expert debugging assistance from Gemini to diagnose errors, find root causes, and get fix recommendations.

    Use this tool specifically when you encounter runtime errors, exceptions, or unexpected behavior
    that needs diagnosis. This is NOT for code review (use gemini_code_review for that). Use this when:
    - You have an error message or exception that needs analysis
    - Your code is failing and you need to identify the root cause
    - You're getting unexpected behavior and need help diagnosing why
    - Stack traces are confusing and you need help interpreting them
    - You need step-by-step guidance on fixing a specific bug
    - You want to understand WHY an error is occurring, not just how to fix it
    - You're stuck debugging and need a fresh perspective on the problem

    Gemini will systematically analyze the error, identify the root cause, pinpoint the problematic
    code, provide a fix, and suggest preventive measures. Uses lower temperature (0.2) for precise,
    analytical debugging.

    Args:
        error_message: The complete error message, exception, or stack trace. Include ALL details:
                      exception type, message, line numbers, and full stack trace if available.
        code_snippet: The relevant code that's causing the error. Include surrounding context (5-10 lines
                     before/after) so Gemini can understand how the code is being used.
        context: Additional details about the error situation:
                - When does the error occur? (startup, specific user action, certain inputs)
                - What were you trying to do when it failed?
                - What have you already tried?
                - Any relevant environment details (OS, versions, configuration)
                - Does it happen consistently or intermittently?
    """
    prompt = f"""I'm encountering a programming error and need help debugging.

Error Message:
---
{error_message}
---"""

    if code_snippet:
        prompt += f"""

Code Snippet:
---
{code_snippet}
---"""

    if context:
        prompt += f"""

Additional Context:
---
{context}
---"""

    prompt += """

Based on the error message and the provided information, please do the following:
1. **Analyze the Root Cause**: Explain what you believe is the most likely cause of this error.
2. **Identify the Problematic Code**: Pinpoint the specific line(s) or code block(s) that are causing the issue.
3. **Suggest a Solution**: Provide a corrected version of the code or clear, step-by-step instructions on how to fix the bug.
4. **Prevention**: Suggest how to prevent similar errors in the future."""
    
    result = call_gemini(prompt, 0.2)  # Lower temperature for systematic analysis
    return f"🤖 GEMINI RESPONSE:\n\n{result}"

@mcp.tool()
def gemini_research(topic: str) -> str:
    """Conduct fact-based research using Gemini with Google Search grounding for current, verified information.

    Use this tool when you need factual, up-to-date information that's grounded in real-world sources.
    This is NOT for general questions (use ask_gemini) or creative brainstorming. Use this when you need:
    - Current information about recent events, technologies, or developments
    - Factual research on specific topics, products, or technologies
    - Verification of claims or statements with web sources
    - Information about latest versions, releases, or updates
    - Market research, trends, or industry analysis
    - Documentation or specifications that are published online
    - Comparative analysis of tools, frameworks, or approaches based on real data
    - Finding examples, case studies, or real-world implementations
    - Getting information that changes frequently (pricing, features, availability)

    This tool uses Google Search grounding to ensure responses are backed by current web information
    rather than just training data. Responses will reference real sources when possible. Uses lower
    temperature (0.3) for factual accuracy.

    IMPORTANT: This requires Gemini's grounding features to be enabled on your API key. If grounding
    is not available, it will fall back to regular Gemini (still useful, but without live search).

    Args:
        topic: The specific topic or question to research. Be clear and specific about what information
              you need. Include relevant context like: technology names, version numbers, timeframes,
              or specific aspects you're interested in.
    """
    if not GEMINI_AVAILABLE or not client:
        return f"Gemini not available: {GEMINI_ERROR}"
    
    try:
        # Use the new SDK grounding functionality
        # Note: Grounding may require specific model and API access
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        response = client.models.generate_content(
            model="gemini-3-flash-preview",  # Model that supports grounding
            contents=topic,
            config=types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=0.3,  # Lower temperature for factual research
            )
        )
        
        return f"🤖 GEMINI RESEARCH RESPONSE:\n\n{response.text}"
    except Exception:
        # Fallback to regular content generation if grounding fails
        result = call_gemini(f"Research and provide current information about: {topic}", 0.3)
        return f"🤖 GEMINI RESEARCH RESPONSE (fallback):\n\n{result}\n\n[Note: Used fallback mode - grounding may not be available]"

def is_image_url(url: str) -> bool:
    """Check if a string is a valid image URL"""
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    # Check if URL ends with common image extensions
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
    return any(url.lower().endswith(ext) for ext in image_extensions) or 'image' in url.lower()

def is_base64_image(data: str) -> bool:
    """Check if a string is a base64-encoded image (starts with data:image/)"""
    return data.startswith("data:image/")

@mcp.tool()
def interpret_image(
    image_path: Union[str, List[str]],
    prompt: str = "Describe this image in detail",
    temperature: float = 0.5
) -> str:
    """Analyze and interpret images using Gemini's advanced vision capabilities to understand visual content.

    Use this tool when you need to extract information from images, understand visual content, or analyze
    screenshots, diagrams, charts, or photos. Supports single or multiple images (up to 3,600 per request).
    Perfect for:
    - Describing what's visible in photos, screenshots, or diagrams
    - Reading and extracting text from images (OCR functionality)
    - Analyzing UI/UX designs and providing feedback
    - Understanding charts, graphs, or data visualizations
    - Identifying objects, people, or elements in images
    - Comparing multiple images to find differences or similarities
    - Analyzing code screenshots or error messages shown visually
    - Understanding architectural diagrams, flowcharts, or technical drawings
    - Examining design mockups or wireframes
    - Analyzing medical images, scientific diagrams, or specialized visuals (within Gemini's capabilities)

    This tool automatically handles different image sources and sizes:
    - Local files are read directly (files >20MB use file upload API)
    - URLs are fetched and processed automatically
    - Base64-encoded images are decoded inline
    - Multiple images can be analyzed together for comparison or combined analysis

    Args:
        image_path: Can be ONE of:
                   - Single image: str (file path, URL, or base64-encoded)
                   - Multiple images: List[str] (mix of any supported formats)

                   Supported formats:
                   - Local file path: "/path/to/image.jpg", "./screenshot.png"
                   - Direct URL: "https://example.com/image.png"
                   - Base64-encoded: "data:image/jpeg;base64,/9j/4AAQ..."

                   Supported image types: jpg, jpeg, png, gif, webp, bmp

        prompt: What you want to know about the image(s). Be specific for best results:
                Single image examples:
                - "What text is visible in this screenshot?"
                - "Describe the architecture shown in this diagram"
                - "What errors or issues can you identify in this code screenshot?"

                Multiple image examples:
                - "Compare these two designs and list the differences"
                - "Which of these UI mockups follows better design principles?"
                - "Analyze the progression shown across these images"

        temperature: Controls response creativity (0.0-1.0, default: 0.5)
                    Lower (0.2-0.4) for factual descriptions, OCR, or technical analysis
                    Higher (0.6-0.8) for creative interpretations or subjective analysis

    Returns:
        Gemini's detailed analysis of the image(s), including descriptions, text extraction,
        observations, and answers to your specific questions.

    Examples:
        # Analyze a single screenshot
        interpret_image("/path/to/error.png", "What error is shown and how can I fix it?")

        # Compare multiple designs
        interpret_image(
            ["/path/to/design_v1.png", "/path/to/design_v2.png"],
            "Compare these two designs. Which is more user-friendly and why?"
        )

        # Extract text from an image
        interpret_image("https://example.com/document.jpg", "Extract all text from this image")

        # Mix of local and remote images
        interpret_image(
            ["/path/to/local.jpg", "https://example.com/remote.png"],
            "What are the common themes across these images?"
        )
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    try:
        # Normalize input to list (support both single and multiple images)
        image_paths = [image_path] if isinstance(image_path, str) else image_path

        # Validate image count (Gemini supports up to 3,600 images)
        if len(image_paths) > 3600:
            return f"🤖 GEMINI RESPONSE:\n\nError: Too many images ({len(image_paths)}). Maximum is 3,600 images per request."

        # Build contents array with all images
        contents = []
        image_info = []
        uploaded_files = []  # Track uploaded files for cleanup

        for idx, img_path in enumerate(image_paths, 1):
            # Handle base64-encoded images
            if is_base64_image(img_path):
                header, base64_data = img_path.split(',', 1)
                mime_type = header.split(';')[0].split(':')[1]
                image_data = base64.b64decode(base64_data)
                file_size_mb = len(image_data) / (1024 * 1024)

                contents.append(types.Part.from_bytes(
                    data=image_data,
                    mime_type=mime_type
                ))
                image_info.append(f"Image {idx}: Base64 ({file_size_mb:.1f}MB)")

            # Handle image URLs
            elif is_image_url(img_path):
                import urllib.request
                with urllib.request.urlopen(img_path) as url_response:
                    image_data = url_response.read()

                mime_type = url_response.headers.get_content_type()
                if not mime_type or not mime_type.startswith('image/'):
                    mime_type, _ = mimetypes.guess_type(img_path)
                    if not mime_type:
                        mime_type = 'image/jpeg'

                file_size_mb = len(image_data) / (1024 * 1024)
                contents.append(types.Part.from_bytes(
                    data=image_data,
                    mime_type=mime_type
                ))
                image_info.append(f"Image {idx}: URL ({file_size_mb:.1f}MB)")

            # Handle local file paths
            else:
                if not os.path.exists(img_path):
                    return f"🤖 GEMINI RESPONSE:\n\nError: Image {idx} not found: '{img_path}'"

                file_path = Path(img_path)
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if not mime_type or not mime_type.startswith('image/'):
                    return f"🤖 GEMINI RESPONSE:\n\nError: Image {idx} is not a valid image file: '{img_path}' (detected type: {mime_type})"

                file_size = file_path.stat().st_size
                file_size_mb = file_size / (1024 * 1024)

                # For files > 20MB, use File API
                if file_size_mb > 20:
                    uploaded_file = client.files.upload(
                        file=str(file_path),
                        config=types.UploadFileConfig(display_name=file_path.name)
                    )
                    uploaded_files.append(uploaded_file)

                    contents.append(types.Part.from_uri(
                        file_uri=uploaded_file.uri,
                        mime_type=mime_type
                    ))
                    image_info.append(f"Image {idx}: {file_path.name} ({file_size_mb:.1f}MB, uploaded)")
                else:
                    with open(file_path, 'rb') as f:
                        image_data = f.read()

                    contents.append(types.Part.from_bytes(
                        data=image_data,
                        mime_type=mime_type
                    ))
                    image_info.append(f"Image {idx}: {file_path.name} ({file_size_mb:.1f}MB)")

        # Add the prompt to contents
        contents.append(prompt)

        # Send all images to Gemini in one request
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=8192,
            )
        )

        # Clean up uploaded files
        for uploaded_file in uploaded_files:
            client.files.delete(name=uploaded_file.name)

        # Format response
        image_count = len(image_paths)
        if image_count == 1:
            header = f"🤖 GEMINI IMAGE ANALYSIS ({image_info[0].replace('Image 1: ', '')}):"
        else:
            header = f"🤖 GEMINI MULTI-IMAGE ANALYSIS ({image_count} images):\n" + "\n".join(f"  • {info}" for info in image_info) + "\n"

        return f"{header}\n\n{response.text}"

    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError analyzing image(s): {str(e)}"

@mcp.tool()
def server_info() -> str:
    """Check Gemini MCP server status, connectivity, and configuration information.

    Use this tool to verify that the Gemini MCP server is properly configured and operational.
    This is helpful for:
    - Diagnosing connection issues with the Gemini API
    - Checking if the API key is properly configured
    - Verifying the server version
    - Troubleshooting when other Gemini tools are not working
    - Getting basic health check information

    Returns information about server version, Gemini API connectivity, and any error messages
    if the service is not available.
    """
    if GEMINI_AVAILABLE:
        return f"🤖 GEMINI RESPONSE:\n\nServer v{__version__} - Gemini connected and ready! Using modern unified Google Gen AI SDK."
    else:
        return f"🤖 GEMINI RESPONSE:\n\nServer v{__version__} - Gemini error: {GEMINI_ERROR}"

@mcp.tool()
def check_file_status(file_name: str) -> str:
    """Check the processing status of an uploaded file in Gemini.

    Use this tool to verify if an uploaded file (video, image, document) is ready for use
    in Gemini API calls. This is essential for large files that require processing time.

    Perfect for:
    - Checking if a large video file has finished processing
    - Verifying file upload success before analysis
    - Debugging file upload issues
    - Monitoring processing progress for multiple files
    - Reusing previously uploaded files

    File States:
    - PROCESSING: File is being uploaded/indexed (not ready yet)
    - ACTIVE: File is ready for use in generate_content calls ✅
    - FAILED: File processing failed ❌
    - STATE_UNSPECIFIED: Unknown state

    Args:
        file_name: File identifier from upload (format: "files/abc123xyz").
                  This is returned when you upload a file or can be found in
                  previous upload responses.

    Returns:
        JSON-formatted string with:
        - state: Current processing state
        - ready: Boolean indicating if file is ready for use
        - file_name: File identifier
        - display_name: Human-readable name (if available)
        - size_bytes: File size in bytes
        - size_mb: File size in megabytes
        - mime_type: File MIME type
        - create_time: Upload timestamp
        - uri: File URI for API calls

    Example:
        # After uploading a large video
        status = check_file_status("files/abc123xyz")
        # Returns: {"state": "ACTIVE", "ready": true, "size_mb": 450, ...}
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    try:
        # Get file metadata
        file_info = client.files.get(name=file_name)

        # Determine if file is ready
        is_ready = file_info.state == "ACTIVE"

        # Build comprehensive status response
        status = {
            "state": file_info.state,
            "ready": is_ready,
            "file_name": file_info.name,
            "display_name": getattr(file_info, 'display_name', 'N/A'),
            "size_bytes": getattr(file_info, 'size_bytes', 0),
            "size_mb": round(getattr(file_info, 'size_bytes', 0) / (1024 * 1024), 2),
            "mime_type": getattr(file_info, 'mime_type', 'unknown'),
            "create_time": str(getattr(file_info, 'create_time', 'N/A')),
            "uri": file_info.uri,
        }

        # Add friendly message based on state
        if file_info.state == "ACTIVE":
            message = "✅ File is ready for use!"
        elif file_info.state == "PROCESSING":
            message = "⏳ File is still processing. Check again in a few seconds."
        elif file_info.state == "FAILED":
            message = "❌ File processing failed. Please try uploading again."
        else:
            message = f"⚠️ File state: {file_info.state}"

        status["message"] = message

        import json
        return f"🤖 GEMINI FILE STATUS:\n\n{json.dumps(status, indent=2)}"

    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError checking file status: {str(e)}\n\nMake sure the file_name is correct (format: 'files/abc123xyz')"

@mcp.tool()
def list_uploaded_files(
    filter_mime_type: Optional[str] = None,
    sort_by: str = "upload_date",
    max_results: int = 20
) -> str:
    """List all files currently stored in Gemini cloud storage for browsing and selection.

    This tool enables the primary AI assistant (Claude Code) to help users discover,
    browse, and select from their uploaded files. Essential for conversational workflows
    where users want to see what's available before choosing which file to analyze.

    **IMPORTANT: 48-Hour File Retention**
    - All uploaded files are automatically deleted after 48 hours
    - This tool shows expiration times to help prioritize analysis
    - Files marked "expires_soon" have less than 6 hours remaining

    **Use this tool when users ask:**
    - "What videos do I have uploaded?"
    - "Show me my uploaded files"
    - "Which files are about to expire?"
    - "Do I have any old uploads I should clean up?"
    - "What was I working on yesterday?"

    **Perfect for:**
    - Helping users choose which file to analyze from multiple uploads
    - Identifying files that are about to expire (< 6 hours remaining)
    - Storage management and cleanup decisions
    - Finding files by type (videos, images, documents)
    - Showing upload history and timeline

    **Storage Limits:**
    - 20 GB total per project
    - 2 GB maximum per individual file
    - Files auto-delete after 48 hours

    Args:
        filter_mime_type: Filter by MIME type pattern. Examples:
                         - "video/*" - Only show videos
                         - "video/mp4" - Only MP4 videos
                         - "image/*" - Only show images
                         - "application/pdf" - Only PDFs
                         - None - Show all files (default)

        sort_by: Sort order for results. Options:
                - "upload_date" - Newest first (default, most useful)
                - "size" - Largest files first
                - "name" - Alphabetical by display name
                - "expiring" - Files expiring soonest first

        max_results: Maximum number of files to return (default: 20, max: 100).
                    For large storage, use pagination by calling multiple times.

    Returns:
        JSON-formatted string containing:
        - total_files: Total count of files in storage
        - filtered_count: Count after applying mime_type filter
        - storage_used_mb: Total storage used in megabytes
        - files: List of file objects with metadata
        - expiring_soon_count: Files with < 6 hours remaining

        Each file object includes:
        - file_name: Gemini file identifier (use with other tools)
        - display_name: Human-readable filename
        - state: "ACTIVE", "PROCESSING", or "FAILED"
        - mime_type: File type (video/mp4, image/jpeg, etc.)
        - size_mb: File size in megabytes
        - uploaded: ISO timestamp of upload
        - age_hours: Hours since upload
        - expires_in_hours: Hours until auto-deletion (48hr limit)
        - ready_for_analysis: Boolean - can be analyzed now?

    Example Workflows:
        # User: "What videos do I have?"
        list_uploaded_files(filter_mime_type="video/*")
        # Claude shows: "You have 3 videos: athena_recording.mp4 (12hr old),
        #                demo_video.mp4 (40hr old, expires in 8hr)..."

        # User: "Show me files that are about to expire"
        list_uploaded_files(sort_by="expiring")
        # Claude shows: "2 files expiring soon: demo.mp4 in 3 hours..."

        # User: "What's in my storage?"
        list_uploaded_files()
        # Claude shows: "You have 5 files using 1.2GB..."
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    from datetime import datetime, timezone

    try:
        # List all files
        all_files = list(client.files.list(config={'page_size': max_results}))

        # Filter by mime type if specified
        if filter_mime_type:
            if filter_mime_type.endswith("/*"):
                # Wildcard filter (e.g., "video/*")
                prefix = filter_mime_type[:-2]
                filtered_files = [f for f in all_files if getattr(f, 'mime_type', '').startswith(prefix)]
            else:
                # Exact match
                filtered_files = [f for f in all_files if getattr(f, 'mime_type', '') == filter_mime_type]
        else:
            filtered_files = all_files

        # Build file list with metadata
        file_list = []
        total_size = 0
        expiring_soon_count = 0

        for f in filtered_files:
            # Calculate age and expiration
            create_time = getattr(f, 'create_time', None)
            if create_time:
                # Parse ISO timestamp
                if isinstance(create_time, str):
                    uploaded_dt = datetime.fromisoformat(create_time.replace('Z', '+00:00'))
                else:
                    uploaded_dt = create_time

                now = datetime.now(timezone.utc)
                age_delta = now - uploaded_dt
                age_hours = age_delta.total_seconds() / 3600
                expires_in_hours = 48 - age_hours
            else:
                age_hours = 0
                expires_in_hours = 48

            size_bytes = getattr(f, 'size_bytes', 0)
            size_mb = round(size_bytes / (1024 * 1024), 2)
            total_size += size_bytes

            is_expiring_soon = expires_in_hours < 6
            if is_expiring_soon:
                expiring_soon_count += 1

            file_info = {
                "file_name": f.name,
                "display_name": getattr(f, 'display_name', f.name),
                "state": f.state,
                "mime_type": getattr(f, 'mime_type', 'unknown'),
                "size_mb": size_mb,
                "uploaded": str(create_time) if create_time else "N/A",
                "age_hours": round(age_hours, 1),
                "expires_in_hours": round(expires_in_hours, 1),
                "expires_soon": is_expiring_soon,
                "ready_for_analysis": f.state == "ACTIVE"
            }
            file_list.append(file_info)

        # Sort files
        if sort_by == "upload_date":
            file_list.sort(key=lambda x: x['age_hours'])  # Newest first
        elif sort_by == "size":
            file_list.sort(key=lambda x: x['size_mb'], reverse=True)
        elif sort_by == "name":
            file_list.sort(key=lambda x: x['display_name'])
        elif sort_by == "expiring":
            file_list.sort(key=lambda x: x['expires_in_hours'])

        # Build response
        result = {
            "total_files": len(all_files),
            "filtered_count": len(filtered_files),
            "storage_used_mb": round(total_size / (1024 * 1024), 2),
            "expiring_soon_count": expiring_soon_count,
            "files": file_list,
            "storage_info": {
                "retention_policy": "48 hours",
                "max_storage_gb": 20,
                "max_file_size_gb": 2
            }
        }

        if filter_mime_type:
            result["filter_applied"] = filter_mime_type

        return f"🤖 GEMINI STORAGE LISTING:\n\n{json.dumps(result, indent=2)}"

    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError listing files: {str(e)}"

@mcp.tool()
def get_last_uploaded_video() -> str:
    """Get the most recently uploaded video file from Gemini storage.

    This is a convenience tool for quick access to the user's latest video upload
    without having to browse through all files. Specifically filters for video
    files and returns only the most recent one.

    **Use this tool when users ask:**
    - "What was the last video I uploaded?"
    - "Is my recent video upload ready?"
    - "Can I analyze that video I just uploaded?"
    - "Show me my latest upload"
    - "What video was I working on?"

    **Perfect for:**
    - Quick access to most recent video without listing all files
    - Checking if a recent upload is ready for analysis
    - Continuing work from a previous session
    - Verifying upload success
    - Getting file URI for immediate analysis

    **Returns information about:**
    - File identifier (for use with watch_video or check_file_status)
    - Processing state (ACTIVE, PROCESSING, FAILED)
    - Upload time and age
    - Expiration time (48-hour limit)
    - Size and format
    - Whether it's ready for analysis

    Returns:
        JSON-formatted string containing:
        - found: Boolean - whether a video was found
        - file_name: Gemini file identifier (e.g., "files/abc123")
        - display_name: Human-readable filename
        - state: Current processing state
        - ready: Boolean - ready for analysis?
        - mime_type: Video format
        - size_mb: File size in megabytes
        - uploaded: ISO timestamp
        - age_hours: Hours since upload
        - expires_in_hours: Hours until auto-deletion
        - uri: File URI for API calls
        - suggestion: Message for Claude to relay to user

    Example Workflows:
        # User: "Is my latest video ready?"
        get_last_uploaded_video()
        # Returns: {"found": true, "state": "ACTIVE", "ready": true, ...}
        # Claude: "Yes! Your athena_recording.mp4 is ready. Would you like
        #          me to analyze it?"

        # User: "What was I working on yesterday?"
        get_last_uploaded_video()
        # Returns: {"found": true, "age_hours": 36, ...}
        # Claude: "Your last video was demo.mp4, uploaded 36 hours ago.
        #          It expires in 12 hours."

        # No videos found
        get_last_uploaded_video()
        # Returns: {"found": false, "message": "No videos in storage"}
        # Claude: "You don't have any videos uploaded currently."
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    from datetime import datetime, timezone

    try:
        # List all files
        all_files = list(client.files.list(config={'page_size': 100}))

        # Filter for videos only
        video_files = [f for f in all_files if getattr(f, 'mime_type', '').startswith('video/')]

        if not video_files:
            return f"🤖 GEMINI RESPONSE:\n\n{json.dumps({'found': False, 'message': 'No videos found in storage. Upload a video first with watch_video().'}, indent=2)}"

        # Get most recent video (by create_time)
        video_files.sort(key=lambda f: getattr(f, 'create_time', ''), reverse=True)
        latest_video = video_files[0]

        # Calculate metadata
        create_time = getattr(latest_video, 'create_time', None)
        if create_time:
            if isinstance(create_time, str):
                uploaded_dt = datetime.fromisoformat(create_time.replace('Z', '+00:00'))
            else:
                uploaded_dt = create_time

            now = datetime.now(timezone.utc)
            age_delta = now - uploaded_dt
            age_hours = age_delta.total_seconds() / 3600
            expires_in_hours = 48 - age_hours
        else:
            age_hours = 0
            expires_in_hours = 48

        size_bytes = getattr(latest_video, 'size_bytes', 0)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        is_ready = latest_video.state == "ACTIVE"

        # Build suggestion message
        if is_ready:
            suggestion = f"✅ This video is ready for analysis. Call: watch_video(file_uri='{latest_video.name}', prompt='...')"
        elif latest_video.state == "PROCESSING":
            suggestion = f"⏳ Video is still processing. Check status with: check_file_status('{latest_video.name}')"
        else:
            suggestion = f"❌ Video processing failed (state: {latest_video.state}). Try uploading again."

        result = {
            "found": True,
            "file_name": latest_video.name,
            "display_name": getattr(latest_video, 'display_name', latest_video.name),
            "state": latest_video.state,
            "ready": is_ready,
            "mime_type": getattr(latest_video, 'mime_type', 'unknown'),
            "size_mb": size_mb,
            "uploaded": str(create_time) if create_time else "N/A",
            "age_hours": round(age_hours, 1),
            "expires_in_hours": round(expires_in_hours, 1),
            "expires_soon": expires_in_hours < 6,
            "uri": latest_video.uri,
            "suggestion": suggestion
        }

        return f"🤖 GEMINI LAST VIDEO:\n\n{json.dumps(result, indent=2)}"

    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError getting last video: {str(e)}"

@mcp.tool()
def delete_uploaded_file(file_name: str, confirmed: bool = False) -> str:
    """Delete a specific file from Gemini cloud storage.

    ⚠️ **DESTRUCTIVE OPERATION** - Requires explicit confirmation via the `confirmed` parameter.

    This tool enables manual cleanup of uploaded files to free storage space or remove
    files that are no longer needed. Files are automatically deleted after 48 hours,
    but this tool allows earlier manual deletion.

    **IMPORTANT: Safety Measures**
    - Requires `confirmed=True` to actually delete
    - First call without confirmation returns file info for review
    - Cannot be undone - deleted files are permanently removed
    - User should be asked to confirm before setting confirmed=True

    **Use this tool when users ask:**
    - "Delete that old video"
    - "Remove the demo file"
    - "Clean up my uploads"
    - "I don't need that file anymore"
    - "Free up storage space"

    **Perfect for:**
    - Cleaning up test uploads
    - Removing files no longer needed
    - Freeing storage space before hitting 20GB limit
    - Deleting failed or corrupted uploads
    - Managing storage proactively

    **Typical Workflow:**
    1. User requests deletion: "Delete the demo video"
    2. Claude calls: delete_uploaded_file("files/abc123", confirmed=False)
    3. Tool returns file info for confirmation
    4. Claude asks user: "This will delete demo.mp4 (450MB). Confirm?"
    5. User confirms: "Yes, delete it"
    6. Claude calls: delete_uploaded_file("files/abc123", confirmed=True)
    7. File is permanently deleted

    Args:
        file_name: File identifier to delete (format: "files/abc123xyz").
                  Get this from list_uploaded_files() or get_last_uploaded_video().

        confirmed: Safety flag - must be True to actually delete the file.
                  - False (default): Returns file info for review, does NOT delete
                  - True: Permanently deletes the file (cannot be undone)

    Returns:
        JSON-formatted string containing:
        - If confirmed=False:
          - action: "confirmation_required"
          - file details for review
          - warning message about permanent deletion

        - If confirmed=True:
          - action: "deleted"
          - deleted_file: Name of deleted file
          - success: true/false
          - freed_storage_mb: Storage space freed

    Example Workflows:
        # Step 1: User wants to delete
        # User: "Delete that old demo video"
        # Claude first lists to identify: list_uploaded_files()
        # Claude identifies: "files/xyz" is the demo video

        # Step 2: Claude checks what will be deleted
        delete_uploaded_file("files/xyz", confirmed=False)
        # Returns: {"action": "confirmation_required", "file_name": "demo.mp4",
        #           "size_mb": 450, "warning": "This will permanently delete..."}

        # Step 3: Claude asks user
        # Claude: "This will permanently delete demo.mp4 (450MB). Confirm?"
        # User: "Yes"

        # Step 4: Claude deletes
        delete_uploaded_file("files/xyz", confirmed=True)
        # Returns: {"action": "deleted", "success": true, "freed_storage_mb": 450}
        # Claude: "Deleted demo.mp4 and freed 450MB of storage."

    Safety Notes:
        - Always call with confirmed=False first to verify what will be deleted
        - Ask user to explicitly confirm before calling with confirmed=True
        - Consider showing file details (name, size, age) before deletion
        - Cannot recover deleted files - make sure user is certain
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"


    try:
        # First, get file info
        file_info = client.files.get(name=file_name)
        size_bytes = getattr(file_info, 'size_bytes', 0)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        display_name = getattr(file_info, 'display_name', file_name)

        # If not confirmed, return info for review
        if not confirmed:
            result = {
                "action": "confirmation_required",
                "file_name": file_name,
                "display_name": display_name,
                "size_mb": size_mb,
                "mime_type": getattr(file_info, 'mime_type', 'unknown'),
                "warning": "⚠️ This will PERMANENTLY delete this file. It cannot be recovered.",
                "message": f"To confirm deletion, call: delete_uploaded_file('{file_name}', confirmed=True)"
            }
            return f"🤖 GEMINI DELETE CONFIRMATION:\n\n{json.dumps(result, indent=2)}"

        # Confirmed - actually delete the file
        client.files.delete(name=file_name)

        result = {
            "action": "deleted",
            "success": True,
            "deleted_file": file_name,
            "display_name": display_name,
            "freed_storage_mb": size_mb,
            "message": f"✅ Successfully deleted {display_name} and freed {size_mb}MB of storage."
        }

        return f"🤖 GEMINI FILE DELETED:\n\n{json.dumps(result, indent=2)}"

    except Exception as e:
        error_result = {
            "action": "error",
            "success": False,
            "file_name": file_name,
            "error": str(e),
            "message": "Failed to delete file. It may have already been deleted or expired (48hr limit)."
        }
        return f"🤖 GEMINI RESPONSE:\n\n{json.dumps(error_result, indent=2)}"

def is_youtube_url(url: str) -> bool:
    """Check if a string is a valid YouTube URL"""
    return (url.startswith("http://") or url.startswith("https://")) and ("youtube.com" in url or "youtu.be" in url)

@mcp.tool()
def watch_video(
    input_path: Optional[str] = None,
    prompt: str = "",
    model: str = "gemini-3-flash-preview",
    file_uri: Optional[str] = None,
    auto_analyze: bool = True,
    max_wait_seconds: int = 300,
    poll_interval: int = 2
) -> str:
    """Analyze video content from YouTube or local files using Gemini's multimodal capabilities.

    **THREE USAGE MODES:**

    **Mode 1: Full Auto (Default)** - Upload, poll, and analyze automatically
    ```python
    watch_video("/path/to/video.mp4", "Summarize this video")
    # Handles everything: upload → wait → analyze → return results
    ```

    **Mode 2: Upload Only** - Upload and return file info for manual status checking
    ```python
    result = watch_video("/path/to/video.mp4", auto_analyze=False)
    # Returns: {"file_name": "files/abc123", "state": "PROCESSING", ...}
    # Then use check_file_status("files/abc123") to monitor progress
    # Finally: watch_video(file_uri="files/abc123", prompt="Analyze this")
    ```

    **Mode 3: Use Pre-Uploaded File** - Analyze an already-uploaded file
    ```python
    watch_video(file_uri="files/abc123", prompt="Extract key points")
    # Skips upload, checks status once, then analyzes
    ```

    Perfect for:
    - Summarizing video content and key points
    - Extracting specific information from tutorial or educational videos
    - Analyzing presentations, demos, or conference talks
    - Understanding what happens in a video without watching it
    - Transcribing or extracting dialogue from videos
    - Analyzing specific time ranges or segments of longer videos
    - Getting insights from recorded meetings, lectures, or screencasts
    - Identifying actions, objects, or events shown in video footage
    - Comparing content across different parts of a video

    The tool automatically handles different video sources:
    - YouTube URLs are processed directly (no download needed)
    - Local files <20MB are sent inline (no upload/polling needed)
    - Local files >20MB use Gemini's File API with automatic polling
    - Supports common video formats (mp4, mov, avi, etc.)

    Args:
        input_path: Video source - either a YouTube URL or path to a local video file.
                   Required unless file_uri is provided.
                   YouTube examples:
                   - "https://www.youtube.com/watch?v=VIDEO_ID"
                   - "https://youtu.be/VIDEO_ID"
                   Local file examples:
                   - "/path/to/recording.mp4"
                   - "./screencast.mov"

        prompt: What you want to know about the video. Required for analysis.
               General analysis:
               - "Summarize this video in 3-5 key points"
               - "What is this video about?"
               Time-specific analysis:
               - "Summarize from 1:00 to 1:30"
               - "What happens at the 5-minute mark?"
               Specific extraction:
               - "What code examples are shown in this tutorial?"
               - "List all the commands demonstrated in this video"

        model: Gemini model to use (default: gemini-3-flash-preview).

        file_uri: Use an already-uploaded file instead of uploading a new one.
                 Format: "files/abc123xyz"
                 If provided, input_path is ignored.

        auto_analyze: If True (default), automatically poll for file readiness and analyze.
                     If False, upload file and return file info without analyzing.
                     Useful for large files when you want manual control over timing.

        max_wait_seconds: Maximum time to wait for file processing (default: 300 = 5 minutes).
                         Only applies when auto_analyze=True for large files.

        poll_interval: How often to check file status in seconds (default: 2).
                      Only applies when auto_analyze=True for large files.

    Returns:
        - If auto_analyze=True: Full video analysis from Gemini
        - If auto_analyze=False: JSON with file info {"file_name": "...", "state": "...", ...}
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    import time

    try:
        # MODE 3: Use pre-uploaded file
        if file_uri:
            # Check file status once
            file_info = client.files.get(name=file_uri)

            if file_info.state != "ACTIVE":
                return f"🤖 GEMINI RESPONSE:\n\nFile {file_uri} is not ready (state: {file_info.state}). Use check_file_status('{file_uri}') to monitor progress."

            if not prompt:
                return "🤖 GEMINI RESPONSE:\n\nError: 'prompt' parameter is required when analyzing a video."

            # File is ready, analyze it
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_uri(
                        file_uri=file_info.uri,
                        mime_type=file_info.mime_type
                    ),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=8192,
                )
            )
            return f"🤖 GEMINI VIDEO ANALYSIS (Pre-uploaded: {file_uri}):\n\n{response.text}"

        # Validate input_path is provided
        if not input_path:
            return "🤖 GEMINI RESPONSE:\n\nError: Either 'input_path' or 'file_uri' must be provided."

        # Handle YouTube URLs
        if is_youtube_url(input_path):
            if not prompt:
                return "🤖 GEMINI RESPONSE:\n\nError: 'prompt' parameter is required when analyzing a video."

            # For YouTube videos, use Part.from_uri to pass the URL as video content
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_uri(
                        file_uri=input_path,
                        mime_type="video/mp4"
                    ),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=8192,
                )
            )
            return f"🤖 GEMINI VIDEO ANALYSIS (YouTube):\n\n{response.text}"

        # Handle local video files
        elif os.path.exists(input_path):
            file_path = Path(input_path)

            # Check if it's a video file
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type or not mime_type.startswith('video/'):
                return f"🤖 GEMINI RESPONSE:\n\nError: File '{input_path}' is not a valid video file (detected type: {mime_type})"

            # Get file size to determine upload method
            file_size = file_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            # For files > 20MB, use the File API with polling
            if file_size_mb > 20:
                # Upload the file first
                uploaded_file = client.files.upload(
                    file=str(file_path),
                    config=types.UploadFileConfig(display_name=file_path.name)
                )

                # MODE 2: Upload only (return file info without analyzing)
                if not auto_analyze:
                    upload_info = {
                        "mode": "upload_only",
                        "file_name": uploaded_file.name,
                        "file_uri": uploaded_file.uri,
                        "state": uploaded_file.state,
                        "size_mb": file_size_mb,
                        "message": f"File uploaded. Use check_file_status('{uploaded_file.name}') to monitor processing, then call watch_video(file_uri='{uploaded_file.name}', prompt='...') when ready."
                    }
                    return f"🤖 GEMINI FILE UPLOAD:\n\n{json.dumps(upload_info, indent=2)}"

                # MODE 1: Auto-analyze (poll until ready)
                if not prompt:
                    return "🤖 GEMINI RESPONSE:\n\nError: 'prompt' parameter is required when auto_analyze=True."

                # Poll for file readiness
                elapsed_time = 0
                file_obj = uploaded_file

                while file_obj.state == "PROCESSING" and elapsed_time < max_wait_seconds:
                    time.sleep(poll_interval)
                    elapsed_time += poll_interval
                    file_obj = client.files.get(name=uploaded_file.name)

                # Check final state
                if file_obj.state == "FAILED":
                    return "🤖 GEMINI RESPONSE:\n\nError: File processing failed. Please try uploading again."

                if file_obj.state != "ACTIVE":
                    return f"🤖 GEMINI RESPONSE:\n\nTimeout: File is still processing after {elapsed_time} seconds (state: {file_obj.state}). Use check_file_status('{uploaded_file.name}') to continue monitoring."

                # File is ready, analyze it
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_uri(
                            file_uri=file_obj.uri,
                            mime_type=mime_type
                        ),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.5,
                        max_output_tokens=8192,
                    )
                )

                # Clean up the uploaded file
                client.files.delete(name=file_obj.name)

                return f"🤖 GEMINI VIDEO ANALYSIS (Local file: {file_path.name}, {file_size_mb:.1f}MB, processed in {elapsed_time}s):\n\n{response.text}"

            else:
                # For smaller files, include inline (no upload/polling needed)
                if not prompt:
                    return "🤖 GEMINI RESPONSE:\n\nError: 'prompt' parameter is required when analyzing a video."

                with open(file_path, 'rb') as f:
                    video_data = f.read()

                response = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(
                            data=video_data,
                            mime_type=mime_type
                        ),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.5,
                        max_output_tokens=8192,
                    )
                )

                return f"🤖 GEMINI VIDEO ANALYSIS (Local file: {file_path.name}, {file_size_mb:.1f}MB, inline):\n\n{response.text}"

        else:
            return f"🤖 GEMINI RESPONSE:\n\nError: Input '{input_path}' is neither a valid YouTube URL nor an existing file path"

    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError analyzing video: {str(e)}"

async def main():
    """Main entry point with startup recovery."""
    # Run startup recovery (resume incomplete tasks)
    await on_server_startup()

    # Start the MCP server
    await mcp.run_stdio_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())