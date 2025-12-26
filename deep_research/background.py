"""
BackgroundTaskManager - Asyncio-based background task management.

Uses Python's built-in asyncio for zero external dependencies.
Manages lifecycle of background research tasks with proper cleanup.
"""

import asyncio
import logging
from typing import Dict, Callable, Coroutine, Any, Optional, List

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manages asyncio background tasks for deep research operations."""

    def __init__(self):
        """Initialize the background task manager."""
        self._tasks: Dict[str, asyncio.Task] = {}

    def start_task(
        self,
        task_id: str,
        coro: Coroutine[Any, Any, Any],
        on_complete: Optional[Callable[[str, Any], None]] = None,
        on_error: Optional[Callable[[str, Exception], None]] = None
    ) -> bool:
        """Start a background task.

        Args:
            task_id: Unique identifier for the task
            coro: The coroutine to run in the background
            on_complete: Optional callback when task completes successfully
            on_error: Optional callback when task fails

        Returns:
            True if task started, False if task_id already exists
        """
        if task_id in self._tasks and not self._tasks[task_id].done():
            logger.warning(f"Task {task_id} is already running")
            return False

        async def wrapped_coro():
            """Wrapper to handle callbacks and cleanup."""
            try:
                result = await coro
                if on_complete:
                    try:
                        on_complete(task_id, result)
                    except Exception as e:
                        logger.error(f"on_complete callback failed for {task_id}: {e}")
                return result
            except asyncio.CancelledError:
                logger.info(f"Task {task_id} was cancelled")
                raise
            except Exception as e:
                logger.error(f"Task {task_id} failed with error: {e}")
                if on_error:
                    try:
                        on_error(task_id, e)
                    except Exception as cb_error:
                        logger.error(f"on_error callback failed for {task_id}: {cb_error}")
                raise

        task = asyncio.create_task(wrapped_coro())
        self._tasks[task_id] = task

        # Clean up when done
        def cleanup(t):
            self._tasks.pop(task_id, None)
            logger.debug(f"Task {task_id} cleaned up")

        task.add_done_callback(cleanup)
        logger.info(f"Started background task: {task_id}")
        return True

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task.

        Args:
            task_id: The task to cancel

        Returns:
            True if task was cancelled, False if not found or already done
        """
        if task_id not in self._tasks:
            logger.debug(f"Task {task_id} not found for cancellation")
            return False

        task = self._tasks[task_id]
        if task.done():
            logger.debug(f"Task {task_id} already completed")
            return False

        task.cancel()
        logger.info(f"Cancelled task: {task_id}")
        return True

    def is_running(self, task_id: str) -> bool:
        """Check if a task is currently running.

        Args:
            task_id: The task to check

        Returns:
            True if task exists and is not done
        """
        return task_id in self._tasks and not self._tasks[task_id].done()

    def get_running_tasks(self) -> List[str]:
        """Get list of running task IDs.

        Returns:
            List of task IDs that are currently running
        """
        return [tid for tid, task in self._tasks.items() if not task.done()]

    def get_task_count(self) -> int:
        """Get count of currently tracked tasks.

        Returns:
            Number of tasks (running or completed but not yet cleaned up)
        """
        return len(self._tasks)

    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Wait for a specific task to complete.

        Args:
            task_id: The task to wait for
            timeout: Optional timeout in seconds

        Returns:
            The result of the task

        Raises:
            KeyError: If task not found
            asyncio.TimeoutError: If timeout exceeded
            Exception: Whatever exception the task raised
        """
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found")

        task = self._tasks[task_id]
        if timeout:
            return await asyncio.wait_for(task, timeout=timeout)
        return await task

    async def cancel_all(self, timeout: float = 5.0) -> int:
        """Cancel all running tasks and wait for them to finish.

        Args:
            timeout: Maximum time to wait for tasks to cancel

        Returns:
            Number of tasks that were cancelled
        """
        running_tasks = [
            (tid, task) for tid, task in self._tasks.items()
            if not task.done()
        ]

        if not running_tasks:
            return 0

        # Cancel all tasks
        for tid, task in running_tasks:
            task.cancel()
            logger.info(f"Cancelling task: {tid}")

        # Wait for cancellation with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*[task for _, task in running_tasks], return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for {len(running_tasks)} tasks to cancel")

        return len(running_tasks)


# Singleton instance for easy access
_manager: Optional[BackgroundTaskManager] = None


def get_background_manager() -> BackgroundTaskManager:
    """Get the singleton background task manager instance."""
    global _manager
    if _manager is None:
        _manager = BackgroundTaskManager()
    return _manager
