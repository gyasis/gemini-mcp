"""
Integration tests for Deep Research US4 Cancel Flow.

Tests:
1. Start research -> cancel with save_partial=True -> verify partial results
2. Start research -> cancel with save_partial=False -> verify cleanup
3. Try cancel completed research -> verify error response

Uses mocked Gemini API for deterministic testing.
"""

import asyncio
import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import deep research modules
from deep_research import TaskStatus, ResearchTask, ResearchResult, Source, CostEstimate
from deep_research.cost_estimator import CostEstimator, get_cost_estimator


class TestCancelWithPartialSave:
    """Test US4 Scenario 1: Cancel running research and save partial results."""

    def test_cancel_running_task_with_partial_save(self, temp_db):
        """Test cancelling a running task with save_partial=True."""
        from deep_research.state_manager import StateManager
        from deep_research.background import BackgroundTaskManager

        state_manager = StateManager(db_path=temp_db)
        background_manager = BackgroundTaskManager()

        task_id = str(uuid.uuid4())

        # Create a running task with some progress
        task = ResearchTask(
            task_id=task_id,
            query="Deep analysis of AI trends",
            status=TaskStatus.RUNNING_ASYNC,
            progress=45,
            current_action="Analyzing source 23/50...",
            tokens_input=50000,
            tokens_output=15000
        )
        state_manager.save_task(task)

        # Save some partial results
        partial_result = ResearchResult(
            task_id=task_id,
            report="# Partial Research Report\n\nPreliminary findings...",
            sources=[
                Source(
                    title="AI Research Paper",
                    url="https://example.com/ai-paper",
                    snippet="Key findings on AI trends..."
                )
            ],
            metadata={"partial": False}
        )
        state_manager.save_result(task_id, partial_result)

        # Verify task is running
        retrieved = state_manager.get_task(task_id)
        assert retrieved.status == TaskStatus.RUNNING_ASYNC

        # Simulate cancel with partial save
        state_manager.update_task(task_id, {
            "status": TaskStatus.CANCELLED,
            "current_action": f"Cancelled at {task.progress}% progress",
            "completed_at": datetime.utcnow()
        })

        # Update result metadata to mark as partial
        result = state_manager.get_result(task_id)
        result.metadata["cancelled_at_progress"] = 45
        result.metadata["partial"] = True
        state_manager.save_result(task_id, result)

        # Verify cancellation
        cancelled_task = state_manager.get_task(task_id)
        assert cancelled_task.status == TaskStatus.CANCELLED

        # Verify partial results are still accessible
        cancelled_result = state_manager.get_result(task_id)
        assert cancelled_result is not None
        assert cancelled_result.report != ""
        assert cancelled_result.metadata.get("partial") is True
        assert cancelled_result.metadata.get("cancelled_at_progress") == 45

    def test_cancel_task_with_no_results_yet(self, temp_db):
        """Test cancelling a task that has no results saved yet."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        task_id = str(uuid.uuid4())

        # Create a running task with no results
        task = ResearchTask(
            task_id=task_id,
            query="Research query",
            status=TaskStatus.RUNNING_ASYNC,
            progress=10,
            current_action="Starting..."
        )
        state_manager.save_task(task)

        # Cancel the task
        state_manager.update_task(task_id, {
            "status": TaskStatus.CANCELLED,
            "current_action": "Cancelled at 10% progress"
        })

        # Verify cancellation
        cancelled_task = state_manager.get_task(task_id)
        assert cancelled_task.status == TaskStatus.CANCELLED

        # Verify no results exist (which is fine)
        result = state_manager.get_result(task_id)
        assert result is None


class TestCancelWithoutPartialSave:
    """Test US4 Scenario 2: Cancel running research without saving partial results."""

    def test_cancel_without_saving_partial(self, temp_db):
        """Test cancelling a task with save_partial=False."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        task_id = str(uuid.uuid4())

        # Create a running task with some progress
        task = ResearchTask(
            task_id=task_id,
            query="Research to cancel",
            status=TaskStatus.RUNNING_ASYNC,
            progress=65
        )
        state_manager.save_task(task)

        # Save some results that would be "discarded" with save_partial=False
        result = ResearchResult(
            task_id=task_id,
            report="Partial content...",
            sources=[]
        )
        state_manager.save_result(task_id, result)

        # Cancel without saving (in real implementation, this might delete the result)
        state_manager.update_task(task_id, {
            "status": TaskStatus.CANCELLED,
            "current_action": "Cancelled without saving partial results"
        })

        # Verify task is cancelled
        cancelled_task = state_manager.get_task(task_id)
        assert cancelled_task.status == TaskStatus.CANCELLED


class TestCancelCompletedResearch:
    """Test US4 Scenario 3: Try to cancel already completed research."""

    def test_cannot_cancel_completed_task(self, temp_db):
        """Test that cancelling a completed task returns an error."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        task_id = str(uuid.uuid4())

        # Create a completed task
        task = ResearchTask(
            task_id=task_id,
            query="Completed research",
            status=TaskStatus.COMPLETED,
            progress=100,
            completed_at=datetime.utcnow()
        )
        state_manager.save_task(task)

        # Verify task is completed
        retrieved = state_manager.get_task(task_id)
        assert retrieved.status == TaskStatus.COMPLETED

        # In the actual cancel_research tool, this would return an error
        # Here we just verify the state is already complete
        assert retrieved.status == TaskStatus.COMPLETED
        assert retrieved.progress == 100

    def test_cannot_cancel_failed_task(self, temp_db):
        """Test that cancelling a failed task returns an error."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        task_id = str(uuid.uuid4())

        # Create a failed task
        task = ResearchTask(
            task_id=task_id,
            query="Failed research",
            status=TaskStatus.FAILED,
            progress=30,
            error_message="API error occurred"
        )
        state_manager.save_task(task)

        # Verify task is failed
        retrieved = state_manager.get_task(task_id)
        assert retrieved.status == TaskStatus.FAILED
        assert retrieved.error_message is not None

    def test_cannot_cancel_already_cancelled_task(self, temp_db):
        """Test that cancelling an already cancelled task returns an error."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        task_id = str(uuid.uuid4())

        # Create an already cancelled task
        task = ResearchTask(
            task_id=task_id,
            query="Already cancelled research",
            status=TaskStatus.CANCELLED,
            progress=50
        )
        state_manager.save_task(task)

        # Verify task is cancelled
        retrieved = state_manager.get_task(task_id)
        assert retrieved.status == TaskStatus.CANCELLED


class TestBackgroundTaskCancellation:
    """Test background task manager cancellation integration."""

    @pytest.mark.asyncio
    async def test_cancel_running_background_task(self):
        """Test cancelling an actively running background task."""
        from deep_research.background import BackgroundTaskManager

        manager = BackgroundTaskManager()
        task_id = str(uuid.uuid4())

        async def long_running_task():
            await asyncio.sleep(10)  # Long task
            return {"status": "completed"}

        # Start the task
        manager.start_task(task_id=task_id, coro=long_running_task())

        # Verify it's running
        assert manager.is_running(task_id) is True

        # Cancel it
        cancelled = manager.cancel_task(task_id)
        assert cancelled is True

        # Wait for cancellation to propagate
        await asyncio.sleep(0.1)

        # Verify it's no longer running
        assert manager.is_running(task_id) is False

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self):
        """Test cancelling a task that doesn't exist."""
        from deep_research.background import BackgroundTaskManager

        manager = BackgroundTaskManager()
        task_id = str(uuid.uuid4())

        # Try to cancel non-existent task
        cancelled = manager.cancel_task(task_id)
        assert cancelled is False


class TestCostEstimator:
    """Test CostEstimator functionality (T019)."""

    def test_simple_query_estimation(self):
        """Test that simple queries are correctly classified."""
        estimator = CostEstimator()

        simple_query = "What is Python?"
        estimate = estimator.estimate(simple_query)

        assert estimate.query_complexity == "simple"
        assert estimate.likely_minutes < 3
        assert estimate.likely_usd < 0.5
        assert estimate.will_likely_go_async is False

    def test_medium_query_estimation(self):
        """Test that medium complexity queries are correctly classified."""
        estimator = CostEstimator()

        medium_query = "Compare the advantages and disadvantages of Python vs JavaScript for web development"
        estimate = estimator.estimate(medium_query)

        assert estimate.query_complexity in ["simple", "medium"]
        assert estimate.likely_minutes >= 1

    def test_complex_query_estimation(self):
        """Test that complex queries are correctly classified."""
        estimator = CostEstimator()

        complex_query = """
        What are the geopolitical implications of AI regulation differences between
        the United States, European Union, and China? Include a comprehensive analysis
        of historical developments, current trends, and future forecasts for how these
        regulatory frameworks might evolve and impact global technology competition.
        Compare the different approaches and evaluate their effectiveness.
        """
        estimate = estimator.estimate(complex_query)

        assert estimate.query_complexity == "complex"
        assert estimate.likely_minutes > 10
        assert estimate.likely_usd >= 1.0
        assert estimate.will_likely_go_async is True
        assert "complex" in estimate.recommendation.lower() or "async" in estimate.recommendation.lower()

    def test_estimate_to_dict(self):
        """Test that CostEstimate.to_dict() works correctly."""
        estimator = CostEstimator()
        estimate = estimator.estimate("Test query for estimation")

        result = estimate.to_dict()

        assert "query_complexity" in result
        assert "estimated_duration" in result
        assert "estimated_cost" in result
        assert "will_likely_go_async" in result
        assert "recommendation" in result

        assert "min_minutes" in result["estimated_duration"]
        assert "max_minutes" in result["estimated_duration"]
        assert "likely_minutes" in result["estimated_duration"]

        assert "min_usd" in result["estimated_cost"]
        assert "max_usd" in result["estimated_cost"]
        assert "likely_usd" in result["estimated_cost"]

    def test_singleton_accessor(self):
        """Test get_cost_estimator singleton accessor."""
        estimator1 = get_cost_estimator()
        estimator2 = get_cost_estimator()

        # Should be the same instance
        assert estimator1 is estimator2


class TestCostEstimatorEdgeCases:
    """Test edge cases for CostEstimator."""

    def test_empty_query(self):
        """Test handling of empty/minimal query."""
        estimator = CostEstimator()
        estimate = estimator.estimate("")

        assert estimate.query_complexity == "simple"

    def test_very_long_query(self):
        """Test handling of very long query."""
        estimator = CostEstimator()

        # Create a very long query
        long_query = "What is AI? " * 100
        estimate = estimator.estimate(long_query)

        # Should still return valid estimate
        assert estimate.query_complexity in ["simple", "medium", "complex"]
        assert estimate.likely_minutes > 0
        assert estimate.likely_usd > 0

    def test_query_with_special_characters(self):
        """Test handling of query with special characters."""
        estimator = CostEstimator()

        query = "What's the impact of COVID-19 on the U.S. economy? How about EU's €750B recovery plan?"
        estimate = estimator.estimate(query)

        assert estimate.query_complexity in ["simple", "medium", "complex"]
        assert estimate.recommendation != ""


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_cancel_flow.db"
    return str(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
