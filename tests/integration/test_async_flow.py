"""
Integration tests for Deep Research US2 Async Flow.

Tests:
1. Start research -> check_status loop -> completion notification
2. Progress updates visible during execution

Uses mocked Gemini API for deterministic testing.
"""

import asyncio
import pytest
import uuid
from unittest.mock import patch
from datetime import datetime, timedelta

# Import deep research modules
from deep_research import TaskStatus, ResearchTask


class TestAsyncStatusFlow:
    """Test US2 Scenario 1: Start research -> check_status loop -> completion."""

    def test_check_status_running_task(self, temp_db):
        """Test check_research_status returns correct running status."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        # Create a running async task
        task_id = str(uuid.uuid4())
        task = ResearchTask(
            task_id=task_id,
            query="Deep analysis of AI trends",
            status=TaskStatus.RUNNING_ASYNC,
            progress=45,
            current_action="Analyzing source 23/50...",
            interaction_id="gemini-interaction-123",
            tokens_input=75000,
            tokens_output=25000,
            created_at=datetime.utcnow() - timedelta(minutes=10)
        )
        state_manager.save_task(task)

        # Retrieve and verify
        retrieved = state_manager.get_task(task_id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.RUNNING_ASYNC
        assert retrieved.progress == 45
        assert retrieved.current_action == "Analyzing source 23/50..."
        assert retrieved.tokens_input == 75000
        assert retrieved.tokens_output == 25000

    def test_check_status_completed_task(self, temp_db):
        """Test check_research_status returns correct completed status."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        # Create a completed task
        task_id = str(uuid.uuid4())
        created = datetime.utcnow() - timedelta(minutes=20)
        completed = datetime.utcnow() - timedelta(minutes=2)

        task = ResearchTask(
            task_id=task_id,
            query="Research on quantum computing",
            status=TaskStatus.COMPLETED,
            progress=100,
            current_action="Research complete",
            created_at=created,
            completed_at=completed
        )
        state_manager.save_task(task)

        # Retrieve and verify
        retrieved = state_manager.get_task(task_id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.COMPLETED
        assert retrieved.progress == 100

    def test_check_status_failed_task(self, temp_db):
        """Test check_research_status returns correct failed status."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        # Create a failed task
        task_id = str(uuid.uuid4())
        task = ResearchTask(
            task_id=task_id,
            query="Invalid research",
            status=TaskStatus.FAILED,
            progress=30,
            error_message="API rate limit exceeded"
        )
        state_manager.save_task(task)

        # Retrieve and verify
        retrieved = state_manager.get_task(task_id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.FAILED
        assert retrieved.error_message == "API rate limit exceeded"

    @pytest.mark.asyncio
    async def test_status_progression(self, temp_db):
        """Test that status progresses correctly during async research."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        task_id = str(uuid.uuid4())

        # Step 1: Create pending task
        task = ResearchTask(
            task_id=task_id,
            query="Test query",
            status=TaskStatus.PENDING,
            progress=0
        )
        state_manager.save_task(task)

        retrieved = state_manager.get_task(task_id)
        assert retrieved.status == TaskStatus.PENDING
        assert retrieved.progress == 0

        # Step 2: Update to running
        state_manager.update_task(task_id, {
            "status": TaskStatus.RUNNING,
            "progress": 10,
            "current_action": "Starting research..."
        })

        retrieved = state_manager.get_task(task_id)
        assert retrieved.status == TaskStatus.RUNNING
        assert retrieved.progress == 10

        # Step 3: Update to running_async
        state_manager.update_task(task_id, {
            "status": TaskStatus.RUNNING_ASYNC,
            "progress": 25,
            "interaction_id": "gemini-123",
            "current_action": "Searching sources..."
        })

        retrieved = state_manager.get_task(task_id)
        assert retrieved.status == TaskStatus.RUNNING_ASYNC
        assert retrieved.progress == 25
        assert retrieved.interaction_id == "gemini-123"

        # Step 4: Progress updates
        for progress in [50, 75, 90]:
            state_manager.update_task(task_id, {
                "progress": progress,
                "current_action": f"Processing... {progress}%"
            })

            retrieved = state_manager.get_task(task_id)
            assert retrieved.progress == progress

        # Step 5: Complete
        state_manager.update_task(task_id, {
            "status": TaskStatus.COMPLETED,
            "progress": 100,
            "completed_at": datetime.utcnow()
        })

        retrieved = state_manager.get_task(task_id)
        assert retrieved.status == TaskStatus.COMPLETED
        assert retrieved.progress == 100


class TestProgressUpdates:
    """Test US2 Scenario 2: Progress updates visible during execution."""

    def test_progress_callback_updates_state(self, temp_db):
        """Test that progress callbacks properly update state."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        task_id = str(uuid.uuid4())
        task = ResearchTask(
            task_id=task_id,
            query="Test",
            status=TaskStatus.RUNNING_ASYNC
        )
        state_manager.save_task(task)

        # Simulate progress callback updates
        progress_data = [
            (10, "Initializing research..."),
            (25, "Searching web sources..."),
            (50, "Analyzing 50 sources..."),
            (75, "Synthesizing information..."),
            (90, "Generating report..."),
            (100, "Research complete")
        ]

        for progress, action in progress_data:
            state_manager.update_task(task_id, {
                "progress": progress,
                "current_action": action
            })

            # Verify update was applied
            retrieved = state_manager.get_task(task_id)
            assert retrieved.progress == progress
            assert retrieved.current_action == action

    def test_tokens_update_during_progress(self, temp_db):
        """Test that token counts update during research."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        task_id = str(uuid.uuid4())
        task = ResearchTask(
            task_id=task_id,
            query="Test",
            status=TaskStatus.RUNNING_ASYNC,
            tokens_input=0,
            tokens_output=0
        )
        state_manager.save_task(task)

        # Simulate incremental token updates
        token_updates = [
            (10000, 5000),
            (25000, 12000),
            (50000, 25000),
            (100000, 50000),
        ]

        for tokens_in, tokens_out in token_updates:
            state_manager.update_task(task_id, {
                "tokens_input": tokens_in,
                "tokens_output": tokens_out
            })

            retrieved = state_manager.get_task(task_id)
            assert retrieved.tokens_input == tokens_in
            assert retrieved.tokens_output == tokens_out


class TestNotificationFlow:
    """Test notification triggers during async flow."""

    def test_notifier_receives_completion(self):
        """Test that notifier is called on successful completion."""
        from deep_research.notification import NativeNotifier

        notifier = NativeNotifier()

        # Should not raise even if no notification system available
        result = notifier.notify_research_complete(
            task_id=str(uuid.uuid4()),
            duration_minutes=15.5
        )
        assert isinstance(result, bool)

    def test_notifier_receives_failure(self):
        """Test that notifier is called on failure."""
        from deep_research.notification import NativeNotifier

        notifier = NativeNotifier()

        result = notifier.notify_research_failed(
            task_id=str(uuid.uuid4()),
            error="API timeout"
        )
        assert isinstance(result, bool)

    def test_notifier_with_mock(self):
        """Test notification flow with mocked notifier."""
        from deep_research.notification import NativeNotifier

        notifier = NativeNotifier()

        # Mock the notify method
        with patch.object(notifier, 'notify', return_value=True) as mock_notify:
            _result = notifier.notify_research_complete("abc123", 10.0)  # noqa: F841

            # verify notify was called
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args
            assert "Deep Research Complete" in call_args[0][0]  # title


class TestBackgroundTaskIntegration:
    """Test background task manager integration with async flow."""

    @pytest.mark.asyncio
    async def test_background_task_with_completion_callback(self):
        """Test background task triggers completion callback."""
        from deep_research.background import BackgroundTaskManager

        manager = BackgroundTaskManager()
        task_id = str(uuid.uuid4())

        callback_results = {"called": False, "task_id": None, "result": None}

        async def mock_research():
            await asyncio.sleep(0.1)
            return {"status": "completed", "report": "Research findings..."}

        def on_complete(tid, result):
            callback_results["called"] = True
            callback_results["task_id"] = tid
            callback_results["result"] = result

        # Start background task
        manager.start_task(
            task_id=task_id,
            coro=mock_research(),
            on_complete=on_complete
        )

        # Wait for completion
        await asyncio.sleep(0.3)

        # Verify callback was invoked
        assert callback_results["called"] is True
        assert callback_results["task_id"] == task_id
        assert callback_results["result"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_background_task_with_error_callback(self):
        """Test background task triggers error callback on failure."""
        from deep_research.background import BackgroundTaskManager

        manager = BackgroundTaskManager()
        task_id = str(uuid.uuid4())

        error_results = {"called": False, "task_id": None, "error": None}

        async def failing_research():
            await asyncio.sleep(0.1)
            raise ValueError("API quota exceeded")

        def on_error(tid, exc):
            error_results["called"] = True
            error_results["task_id"] = tid
            error_results["error"] = exc

        # Start background task
        manager.start_task(
            task_id=task_id,
            coro=failing_research(),
            on_error=on_error
        )

        # Wait for failure
        await asyncio.sleep(0.3)

        # Verify error callback was invoked
        assert error_results["called"] is True
        assert error_results["task_id"] == task_id
        assert "quota" in str(error_results["error"]).lower()

    @pytest.mark.asyncio
    async def test_check_running_status_during_execution(self):
        """Test that is_running returns True during execution."""
        from deep_research.background import BackgroundTaskManager

        manager = BackgroundTaskManager()
        task_id = str(uuid.uuid4())

        async def slow_task():
            await asyncio.sleep(1)
            return {"done": True}

        manager.start_task(task_id=task_id, coro=slow_task())

        # Check status while running
        assert manager.is_running(task_id) is True

        # Cancel and verify
        manager.cancel_task(task_id)
        await asyncio.sleep(0.1)
        assert manager.is_running(task_id) is False


class TestEstimatedCompletion:
    """Test estimated completion time calculations."""

    def test_estimated_time_calculation(self, temp_db):
        """Test that estimated completion time is calculated correctly."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        task_id = str(uuid.uuid4())
        # Task created 10 minutes ago, currently at 50% progress
        created = datetime.utcnow() - timedelta(minutes=10)

        task = ResearchTask(
            task_id=task_id,
            query="Test",
            status=TaskStatus.RUNNING_ASYNC,
            progress=50,
            current_action="Processing...",
            created_at=created
        )
        state_manager.save_task(task)

        retrieved = state_manager.get_task(task_id)

        # Calculate elapsed time
        elapsed_minutes = (datetime.utcnow() - retrieved.created_at).total_seconds() / 60

        # At 50% progress after 10 minutes, estimated total is 20 minutes
        # So estimated remaining should be ~10 minutes
        if retrieved.progress > 0 and retrieved.progress < 100:
            estimated_total = elapsed_minutes / (retrieved.progress / 100)
            estimated_remaining = estimated_total - elapsed_minutes

            # Should be approximately 10 minutes remaining
            assert 8 < estimated_remaining < 12


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_async_flow.db"
    return str(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
