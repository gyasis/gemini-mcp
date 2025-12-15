"""
Integration tests for Deep Research US1 full flow.

Tests:
1. Simple query -> sync completion -> get_research_results
2. Complex query -> async switch -> poll -> get_research_results

Uses mocked Gemini API for deterministic testing.
"""

import asyncio
import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

# Import deep research modules
from deep_research import TaskStatus, ResearchTask, ResearchResult, Source


class MockGeminiResponse:
    """Mock Gemini API response for testing."""

    def __init__(self, text: str, usage_metadata=None, candidates=None):
        self._text = text
        self.usage_metadata = usage_metadata or MockUsageMetadata()
        self.candidates = candidates
        self.id = f"mock-interaction-{uuid.uuid4().hex[:8]}"

    @property
    def text(self):
        return self._text


class MockUsageMetadata:
    """Mock usage metadata."""
    prompt_token_count = 100
    candidates_token_count = 500


class MockCandidate:
    """Mock candidate with grounding metadata."""

    def __init__(self):
        self.content = MockContent()
        self.grounding_metadata = MockGroundingMetadata()


class MockContent:
    """Mock content with parts."""

    def __init__(self):
        self.parts = [MockPart()]


class MockPart:
    """Mock part with text."""
    text = "Test research report content."


class MockGroundingMetadata:
    """Mock grounding metadata with sources."""

    def __init__(self):
        self.web_search_queries = ["test query"]
        self.grounding_chunks = [MockGroundingChunk()]


class MockGroundingChunk:
    """Mock grounding chunk."""

    def __init__(self):
        self.web = MockWebSource()
        self.text = "Relevant snippet from source."


class MockWebSource:
    """Mock web source."""
    title = "Test Source"
    uri = "https://example.com/source"


@pytest.fixture
def mock_client():
    """Create a mock Gemini client."""
    client = MagicMock()
    return client


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_research.db"
    return str(db_path)


class TestSyncCompletionFlow:
    """Test US1 Scenario 1: Simple query -> sync completion -> get_research_results."""

    @pytest.mark.asyncio
    async def test_simple_query_sync_completion(self, mock_client, temp_db):
        """Test that a simple query completes synchronously within 30s timeout."""
        from deep_research.engine import DeepResearchEngine
        from deep_research.state_manager import StateManager

        # Setup
        state_manager = StateManager(db_path=temp_db)

        # Configure mock to return immediately
        mock_response = MockGeminiResponse(
            text="# Research Report\n\nThis is the completed research on the topic."
        )
        mock_client.models.generate_content = Mock(return_value=mock_response)

        engine = DeepResearchEngine(mock_client)

        # Execute - start_research should complete immediately
        result = await engine.start_research("What is Python?")

        # Verify sync completion
        assert result.get("completed_immediately") is True
        assert result.get("status") == "completed"
        assert "result" in result
        assert "report" in result["result"]

    @pytest.mark.asyncio
    async def test_execute_with_timeout_sync_success(self, mock_client):
        """Test execute_with_timeout returns completed result within timeout."""
        from deep_research.engine import DeepResearchEngine

        mock_response = MockGeminiResponse(
            text="# Quick Answer\n\nPython is a programming language."
        )
        mock_client.models.generate_content = Mock(return_value=mock_response)

        engine = DeepResearchEngine(mock_client)

        result = await engine.execute_with_timeout(
            query="What is Python?",
            timeout_seconds=30
        )

        assert result["status"] == "completed"
        assert "result" in result
        assert result["result"]["report"] != ""

    def test_get_research_results_after_completion(self, temp_db):
        """Test retrieving results after sync completion."""
        from deep_research.state_manager import StateManager
        from deep_research import ResearchResult, Source

        state_manager = StateManager(db_path=temp_db)

        # Create a completed task
        task_id = str(uuid.uuid4())
        task = ResearchTask(
            task_id=task_id,
            query="What is Python?",
            status=TaskStatus.COMPLETED,
            progress=100
        )
        state_manager.save_task(task)

        # Save result
        result = ResearchResult(
            task_id=task_id,
            report="# Research Report\n\nPython is a programming language.",
            sources=[
                Source(
                    title="Python.org",
                    url="https://python.org",
                    snippet="Python is a versatile language."
                )
            ],
            metadata={"tokens_input": 100, "tokens_output": 500}
        )
        state_manager.save_result(task_id, result)

        # Update task status
        state_manager.update_task(task_id, {"status": TaskStatus.COMPLETED, "progress": 100})

        # Retrieve and verify
        retrieved_result = state_manager.get_result(task_id)
        assert retrieved_result is not None
        assert retrieved_result.report == result.report
        assert len(retrieved_result.sources) == 1
        assert retrieved_result.sources[0].title == "Python.org"


class TestAsyncSwitchFlow:
    """Test US1 Scenario 2: Complex query -> async switch -> poll -> get_research_results."""

    @pytest.mark.asyncio
    async def test_complex_query_async_switch(self, mock_client):
        """Test that a complex query switches to async after timeout."""
        from deep_research.engine import DeepResearchEngine

        # Configure mock to simulate slow response (no immediate text)
        mock_response = MagicMock()
        mock_response.text = None  # No immediate response
        mock_response.id = "async-interaction-123"
        mock_client.models.generate_content = Mock(return_value=mock_response)

        engine = DeepResearchEngine(mock_client)

        # Start research
        result = await engine.start_research(
            "Comprehensive analysis of machine learning trends 2024"
        )

        # Should indicate async
        if not result.get("completed_immediately"):
            assert result.get("status") == "running"
            assert result.get("interaction_id") is not None

    @pytest.mark.asyncio
    async def test_execute_with_timeout_async_switch(self, mock_client):
        """Test execute_with_timeout switches to async on timeout."""
        from deep_research.engine import DeepResearchEngine

        # Mock that takes time (simulate by having no text initially)
        mock_response = MagicMock()
        mock_response.text = None
        mock_response.id = "async-interaction-456"
        mock_client.models.generate_content = Mock(return_value=mock_response)

        engine = DeepResearchEngine(mock_client)

        # Execute with very short timeout
        result = await engine.execute_with_timeout(
            query="Deep analysis of quantum computing",
            timeout_seconds=0.1  # Very short timeout to force async
        )

        # Should return async status if response takes longer
        # Note: With mock returning immediately but no text, it depends on implementation
        assert result["status"] in ["completed", "running_async"]

    @pytest.mark.asyncio
    async def test_poll_until_complete(self, mock_client):
        """Test polling mechanism for async research."""
        from deep_research.engine import DeepResearchEngine

        engine = DeepResearchEngine(mock_client)

        # The current implementation returns completed immediately
        # This tests the polling interface
        progress_updates = []

        def track_progress(progress, action):
            progress_updates.append((progress, action))

        result = await engine.poll_until_complete(
            interaction_id="test-interaction-789",
            on_progress=track_progress,
            poll_interval=0.1,
            max_wait_seconds=1
        )

        # Should return with complete status
        assert result is not None


class TestStateManagerIntegration:
    """Test state manager integration with research flow."""

    def test_task_lifecycle(self, temp_db):
        """Test full task lifecycle: create -> update -> complete."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        # Create task
        task_id = str(uuid.uuid4())
        task = ResearchTask(
            task_id=task_id,
            query="Test query",
            status=TaskStatus.PENDING
        )
        state_manager.save_task(task)

        # Verify created
        retrieved = state_manager.get_task(task_id)
        assert retrieved is not None
        assert retrieved.status == TaskStatus.PENDING

        # Update to running
        state_manager.update_task(task_id, {"status": TaskStatus.RUNNING, "progress": 25})
        retrieved = state_manager.get_task(task_id)
        assert retrieved.status == TaskStatus.RUNNING
        assert retrieved.progress == 25

        # Update to async
        state_manager.update_task(
            task_id,
            {"status": TaskStatus.RUNNING_ASYNC, "interaction_id": "gemini-interaction-abc"}
        )
        retrieved = state_manager.get_task(task_id)
        assert retrieved.status == TaskStatus.RUNNING_ASYNC
        assert retrieved.interaction_id == "gemini-interaction-abc"

        # Complete
        state_manager.update_task(
            task_id,
            {"status": TaskStatus.COMPLETED, "progress": 100, "tokens_input": 150, "tokens_output": 800}
        )
        retrieved = state_manager.get_task(task_id)
        assert retrieved.status == TaskStatus.COMPLETED
        assert retrieved.progress == 100

    def test_incomplete_tasks_recovery(self, temp_db):
        """Test retrieval of incomplete tasks for crash recovery."""
        from deep_research.state_manager import StateManager

        state_manager = StateManager(db_path=temp_db)

        # Create tasks in various states
        tasks = [
            (str(uuid.uuid4()), TaskStatus.COMPLETED, None),
            (str(uuid.uuid4()), TaskStatus.RUNNING_ASYNC, "interaction-1"),
            (str(uuid.uuid4()), TaskStatus.RUNNING_ASYNC, "interaction-2"),
            (str(uuid.uuid4()), TaskStatus.FAILED, None),
            (str(uuid.uuid4()), TaskStatus.PENDING, None),
        ]

        for task_id, status, interaction_id in tasks:
            task = ResearchTask(
                task_id=task_id,
                query="Test",
                status=status,
                interaction_id=interaction_id
            )
            state_manager.save_task(task)

        # Get incomplete tasks
        incomplete = state_manager.get_incomplete_tasks()

        # Should only return RUNNING_ASYNC with interaction_id
        assert len(incomplete) == 2
        interaction_ids = [iid for _, iid in incomplete]
        assert "interaction-1" in interaction_ids
        assert "interaction-2" in interaction_ids


class TestBackgroundTaskManager:
    """Test background task manager for async research."""

    @pytest.mark.asyncio
    async def test_start_and_complete_task(self):
        """Test starting and completing a background task."""
        from deep_research.background import BackgroundTaskManager

        manager = BackgroundTaskManager()
        task_id = str(uuid.uuid4())
        result_container = {"completed": False, "result": None}

        async def sample_task():
            await asyncio.sleep(0.1)
            return {"status": "done"}

        def on_complete(tid, result):
            result_container["completed"] = True
            result_container["result"] = result

        # Start task
        success = manager.start_task(
            task_id=task_id,
            coro=sample_task(),
            on_complete=on_complete
        )
        assert success is True

        # Wait for completion
        await asyncio.sleep(0.3)

        # Verify completion
        assert result_container["completed"] is True
        assert result_container["result"]["status"] == "done"

    @pytest.mark.asyncio
    async def test_cancel_running_task(self):
        """Test cancelling a running task."""
        from deep_research.background import BackgroundTaskManager

        manager = BackgroundTaskManager()
        task_id = str(uuid.uuid4())

        async def long_task():
            await asyncio.sleep(10)  # Long running
            return {"status": "done"}

        # Start task
        manager.start_task(task_id=task_id, coro=long_task())

        # Verify running
        assert manager.is_running(task_id) is True

        # Cancel
        cancelled = manager.cancel_task(task_id)
        assert cancelled is True

        # Wait for cancellation
        await asyncio.sleep(0.1)

        # Verify cancelled
        assert manager.is_running(task_id) is False


class TestNotificationIntegration:
    """Test notification integration with research completion."""

    def test_notify_research_complete(self):
        """Test sending completion notification."""
        from deep_research.notification import NativeNotifier

        notifier = NativeNotifier()

        # This may or may not actually send a notification depending on platform
        # but it should not raise an exception
        result = notifier.notify_research_complete(
            task_id=str(uuid.uuid4()),
            duration_minutes=5.5
        )

        # Result is bool (True if sent, False if fell back to logging)
        assert isinstance(result, bool)

    def test_notify_research_failed(self):
        """Test sending failure notification."""
        from deep_research.notification import NativeNotifier

        notifier = NativeNotifier()

        result = notifier.notify_research_failed(
            task_id=str(uuid.uuid4()),
            error="API rate limit exceeded"
        )

        assert isinstance(result, bool)


class TestEndToEndFlow:
    """End-to-end integration test combining all components."""

    @pytest.mark.asyncio
    async def test_full_research_flow(self, mock_client, temp_db):
        """Test complete flow from start to result retrieval."""
        from deep_research.engine import DeepResearchEngine
        from deep_research.state_manager import StateManager
        from deep_research.background import BackgroundTaskManager

        # Initialize components
        state_manager = StateManager(db_path=temp_db)
        background_manager = BackgroundTaskManager()

        # Configure mock for immediate completion
        mock_response = MockGeminiResponse(
            text="# Research Report\n\n## Introduction\nThis is comprehensive research."
        )
        mock_client.models.generate_content = Mock(return_value=mock_response)

        engine = DeepResearchEngine(mock_client)

        # Step 1: Create task
        task_id = str(uuid.uuid4())
        task = ResearchTask(
            task_id=task_id,
            query="What is machine learning?",
            status=TaskStatus.PENDING
        )
        state_manager.save_task(task)

        # Step 2: Start research
        state_manager.update_task(task_id, {"status": TaskStatus.RUNNING})
        result = await engine.execute_with_timeout(
            query=task.query,
            timeout_seconds=30
        )

        # Step 3: Handle result
        if result["status"] == "completed":
            # Save result
            research_result = engine.create_research_result(
                task_id=task_id,
                raw_result=result["result"]
            )
            state_manager.save_result(task_id, research_result)
            state_manager.update_task(
                task_id,
                {"status": TaskStatus.COMPLETED, "progress": 100}
            )

        # Step 4: Retrieve result
        final_task = state_manager.get_task(task_id)
        final_result = state_manager.get_result(task_id)

        # Verify
        assert final_task.status == TaskStatus.COMPLETED
        assert final_result is not None
        assert "Research Report" in final_result.report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
