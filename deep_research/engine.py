"""
DeepResearchEngine - Wraps Gemini Deep Research Interactions API.

Uses the Interactions API (NOT generateContent) for deep research.
Model: deep-research-pro-preview-12-2025 (December 2025 release)

Features:
- Streaming support with thinking summaries for real-time progress
- Hanging detection for stuck tasks
- Partial result capture for recovery from interruptions

Expected duration:
- Simple queries: 5-15 minutes
- Complex queries: 20-40 minutes
- Maximum: 60 minutes (hard timeout)
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime

from google import genai

from . import Source, ResearchResult
from .hanging_detector import get_hanging_detector, HangingStatus

logger = logging.getLogger(__name__)


class DeepResearchEngine:
    """Wraps Gemini Deep Research Interactions API."""

    # Deep Research model - December 2025 release
    # Uses Interactions API, NOT generateContent
    DEFAULT_MODEL = "deep-research-pro-preview-12-2025"

    # Timeout before returning async handle (30 seconds per spec)
    SYNC_TIMEOUT_SECONDS = 30

    # Default polling interval (API recommends 10s)
    DEFAULT_POLL_INTERVAL = 10

    # Maximum wait time - observed behavior: 5-40 min typical
    # We allow up to 60 min but detect hanging much earlier
    MAX_WAIT_SECONDS = 3600  # 60 minutes hard cap

    # Hanging detection thresholds (based on observed 5-40 min typical)
    EXPECTED_DURATION_MINUTES = 15
    CONCERN_DURATION_MINUTES = 30
    EXCESSIVE_DURATION_MINUTES = 45

    def __init__(self, client: genai.Client, state_manager=None):
        """Initialize the deep research engine.

        Args:
            client: Initialized google-genai Client instance
            state_manager: Optional StateManager for persisting progress snapshots
        """
        self.client = client
        self.hanging_detector = get_hanging_detector()
        self._state_manager = state_manager

        # Storage for partial/intermediate results
        self._intermediate_results: Dict[str, List[str]] = {}

        # Per-task locks for thread-safe access (prevents concurrent polling)
        self._task_locks: Dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()  # Protects _task_locks dict itself

    async def start_research(
        self,
        query: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a deep research query using Interactions API.

        The Deep Research agent REQUIRES background=True (async execution).
        Expected duration: 5-15 min (simple), 20-40 min (complex), max 60 min.

        Args:
            query: The research question/topic
            model: Optional model override (defaults to deep-research-pro-preview-12-2025)

        Returns:
            Dict with interaction_id, status, and initial response info
        """
        model_to_use = model or self.DEFAULT_MODEL
        logger.info(f"Starting deep research with model {model_to_use}: {query[:100]}...")

        try:
            # Use Interactions API (NOT generateContent)
            # background=True is REQUIRED for deep research
            interaction = await asyncio.to_thread(
                self.client.interactions.create,
                input=query,
                agent=model_to_use,
                background=True
            )

            interaction_id = interaction.id
            logger.info(f"Research started, interaction_id: {interaction_id}")

            # Check initial status
            status = getattr(interaction, 'status', 'in_progress')

            if status == "completed":
                # Rare: completed immediately
                logger.info("Research completed immediately")
                return {
                    "interaction_id": interaction_id,
                    "status": "completed",
                    "result": self._parse_interaction(interaction),
                    "completed_immediately": True
                }

            # Research is running async (expected case)
            return {
                "interaction_id": interaction_id,
                "status": "running",
                "completed_immediately": False
            }

        except Exception as e:
            logger.error(f"Failed to start research: {e}")
            raise

    async def poll_until_complete(
        self,
        interaction_id: str,
        task_id: str = None,
        on_progress: Optional[Callable[[int, str], None]] = None,
        poll_interval: int = None,
        max_wait_seconds: int = None,
        check_hanging: bool = True
    ) -> Dict[str, Any]:
        """Poll for research completion using Interactions API.

        Thread-safe: Uses per-task lock to prevent concurrent polling.

        Args:
            interaction_id: The interaction ID from start_research
            task_id: Optional task ID for hanging detection
            on_progress: Optional callback(progress_percent, current_action)
            poll_interval: Seconds between polls (default: 10)
            max_wait_seconds: Maximum wait time (default: 60 min)
            check_hanging: Whether to check for hanging tasks

        Returns:
            Dict with report, sources, metadata, and hanging_status

        Raises:
            TimeoutError: If max_wait_seconds exceeded
            Exception: If research fails or task is definitively hung
            RuntimeError: If concurrent polling detected for same task
        """
        poll_interval = poll_interval or self.DEFAULT_POLL_INTERVAL
        max_wait_seconds = max_wait_seconds or self.MAX_WAIT_SECONDS
        task_id = task_id or interaction_id

        # Acquire per-task lock to prevent concurrent polling
        async with self._locks_lock:
            if task_id not in self._task_locks:
                self._task_locks[task_id] = asyncio.Lock()
            task_lock = self._task_locks[task_id]

        # Check if already being polled
        if task_lock.locked():
            logger.warning(f"Task {task_id} is already being polled by another coroutine")
            raise RuntimeError(f"Concurrent polling detected for task {task_id}")

        async with task_lock:
            try:
                return await self._poll_until_complete_impl(
                    interaction_id, task_id, on_progress,
                    poll_interval, max_wait_seconds, check_hanging
                )
            finally:
                # Cleanup lock after polling completes
                async with self._locks_lock:
                    if task_id in self._task_locks:
                        del self._task_locks[task_id]

    async def _poll_until_complete_impl(
        self,
        interaction_id: str,
        task_id: str,
        on_progress: Optional[Callable[[int, str], None]],
        poll_interval: int,
        max_wait_seconds: int,
        check_hanging: bool
    ) -> Dict[str, Any]:
        """Internal polling implementation (called under lock)."""

        start_time = asyncio.get_event_loop().time()
        created_at = datetime.utcnow()
        poll_count = 0

        logger.info(f"Polling for completion: {interaction_id}")

        try:
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time

                if elapsed > max_wait_seconds:
                    raise TimeoutError(
                        f"Research exceeded max wait time of {max_wait_seconds}s"
                    )

                try:
                    # Use Interactions API to get status
                    interaction = await asyncio.to_thread(
                        self.client.interactions.get,
                        interaction_id
                    )
                    poll_count += 1

                    status = getattr(interaction, 'status', 'unknown')

                    # Estimate progress based on elapsed time (research typically 5-10 mins)
                    # Scale: 5 min = ~50%, 10 min = ~90%, beyond = diminishing
                    elapsed_min = elapsed / 60
                    if elapsed_min <= 5:
                        progress = min(50, int((elapsed_min / 5) * 50))
                    elif elapsed_min <= 10:
                        progress = min(90, 50 + int(((elapsed_min - 5) / 5) * 40))
                    else:
                        # Slow progress beyond 10 min
                        progress = min(99, 90 + int((elapsed_min - 10) / 10 * 9))

                    current_action = self._get_action_from_status(status, elapsed)

                    # Record progress for hanging detection (include actual API status)
                    self.record_progress(task_id, progress, current_action, api_status=status)

                    logger.debug(f"Poll {poll_count}: status={status}, progress~{progress}%")

                    # Check for hanging if enabled
                    hanging_status = None
                    if check_hanging:
                        hanging_status = self.check_hanging(task_id, created_at)
                        if hanging_status.is_hanging and hanging_status.confidence >= 0.9:
                            logger.warning(
                                f"Task {task_id} appears hung: {hanging_status.reason}"
                            )
                            # Don't auto-cancel, but include warning in result
                            # Let caller decide what to do

                    # Call progress callback if provided
                    if on_progress:
                        try:
                            on_progress(progress, current_action)
                        except Exception as e:
                            logger.warning(f"Progress callback error: {e}")

                    if status == "completed":
                        logger.info(f"Research completed after {poll_count} polls ({elapsed:.1f}s)")
                        result = self._parse_interaction(interaction)
                        # Clean up tracking data
                        self.clear_intermediate_results(task_id)
                        return result

                    elif status == "failed":
                        error_msg = getattr(interaction, 'error', 'Unknown error')
                        logger.error(f"Research failed: {error_msg}")
                        # Clean up tracking data
                        self.clear_intermediate_results(task_id)
                        raise Exception(f"Research failed: {error_msg}")

                    # Store any partial outputs we can extract
                    try:
                        outputs = getattr(interaction, 'outputs', [])
                        if outputs:
                            for output in outputs:
                                if hasattr(output, 'text') and output.text:
                                    self.store_intermediate_result(task_id, output.text)
                    except Exception as e:
                        logger.debug(f"Could not extract intermediate outputs: {e}")

                    # Continue polling (status is "in_progress")
                    await asyncio.sleep(poll_interval)

                except asyncio.CancelledError:
                    logger.info(f"Polling cancelled for {interaction_id}")
                    raise
                except Exception as e:
                    if "failed" in str(e).lower():
                        raise
                    logger.warning(f"Poll error (will retry): {e}")
                    await asyncio.sleep(poll_interval)

        finally:
            # CRITICAL: Always cleanup on exit (success, failure, or timeout)
            self.clear_intermediate_results(task_id)

    def _get_action_from_status(self, status: str, elapsed: float) -> str:
        """Generate human-readable action based on status and elapsed time."""
        if status == "completed":
            return "Research complete"
        elif status == "failed":
            return "Research failed"

        # Estimate phase based on typical 5-10 minute research duration (official docs)
        minutes = elapsed / 60
        if minutes < 1:
            return "Analyzing query and planning research..."
        elif minutes < 3:
            return "Searching and gathering sources..."
        elif minutes < 6:
            return "Reading and synthesizing information..."
        elif minutes < 8:
            return "Compiling findings..."
        elif minutes < 10:
            return "Generating comprehensive report..."
        elif minutes < 15:
            return "Finalizing research (complex query)..."
        elif minutes < 20:
            return "Extended research in progress..."
        else:
            return "Research taking longer than expected..."

    def check_hanging(
        self,
        task_id: str,
        created_at: datetime = None
    ) -> HangingStatus:
        """Check if a task appears to be hanging/stuck.

        Args:
            task_id: The task ID to check
            created_at: Task creation time for elapsed calculation

        Returns:
            HangingStatus with detection result and recommendations
        """
        return self.hanging_detector.analyze(task_id, created_at)

    def record_progress(
        self,
        task_id: str,
        progress: int,
        action: str = "",
        api_status: str = ""
    ) -> None:
        """Record progress for hanging detection.

        Args:
            task_id: The task ID
            progress: Current progress percentage (0-100) - may be synthetic
            action: Current action description
            api_status: Actual API status (in_progress, completed, failed) - for stall detection
        """
        self.hanging_detector.record_progress(task_id, progress, action, api_status)

        # Persist to SQLite for cross-restart hanging detection
        if self._state_manager:
            try:
                self._state_manager.save_progress_snapshot(
                    task_id, progress, action, api_status
                )
            except Exception as e:
                logger.warning(f"Failed to persist progress snapshot: {e}")

    def store_intermediate_result(
        self,
        task_id: str,
        content: str
    ) -> None:
        """Store intermediate/partial result for potential recovery.

        Args:
            task_id: The task ID
            content: Partial content to store
        """
        if task_id not in self._intermediate_results:
            self._intermediate_results[task_id] = []
        self._intermediate_results[task_id].append(content)
        logger.debug(f"Stored intermediate result for {task_id}: {len(content)} chars")

    def get_intermediate_results(self, task_id: str) -> List[str]:
        """Get stored intermediate results for a task.

        Args:
            task_id: The task ID

        Returns:
            List of intermediate content strings
        """
        return self._intermediate_results.get(task_id, [])

    def clear_intermediate_results(self, task_id: str) -> None:
        """Clear intermediate results after successful completion or cancellation."""
        if task_id in self._intermediate_results:
            del self._intermediate_results[task_id]
        self.hanging_detector.clear_history(task_id)

        # Clear persisted snapshots from SQLite
        if self._state_manager:
            try:
                cleared = self._state_manager.clear_progress_snapshots(task_id)
                if cleared > 0:
                    logger.debug(f"Cleared {cleared} progress snapshots for {task_id}")
            except Exception as e:
                logger.warning(f"Failed to clear progress snapshots: {e}")

    async def execute_with_timeout(
        self,
        query: str,
        model: Optional[str] = None,
        timeout_seconds: int = None,
        on_progress: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """Execute research with sync timeout, returning async handle if exceeds threshold.

        This implements the hybrid sync-to-async pattern:
        1. Start research via Interactions API
        2. Wait up to timeout_seconds for completion
        3. If completes within timeout, return result
        4. If exceeds timeout, return interaction_id for async polling

        Args:
            query: The research query
            model: Optional model override
            timeout_seconds: Sync timeout (default: SYNC_TIMEOUT_SECONDS)
            on_progress: Optional progress callback

        Returns:
            Dict with either:
            - {"status": "completed", "result": {...}} if completed in time
            - {"status": "running_async", "interaction_id": "..."} if timed out
        """
        timeout = timeout_seconds or self.SYNC_TIMEOUT_SECONDS

        # Start the research
        start_result = await self.start_research(query, model)

        # If completed immediately (rare), return result
        if start_result.get("completed_immediately"):
            return {
                "status": "completed",
                "result": start_result.get("result", {})
            }

        interaction_id = start_result.get("interaction_id")

        # Try to wait for completion within timeout
        try:
            result = await asyncio.wait_for(
                self.poll_until_complete(
                    interaction_id,
                    on_progress=on_progress,
                    poll_interval=5  # Poll more frequently during sync phase
                ),
                timeout=timeout
            )
            return {
                "status": "completed",
                "result": result
            }
        except asyncio.TimeoutError:
            logger.info(f"Sync timeout ({timeout}s) exceeded, switching to async")
            return {
                "status": "running_async",
                "interaction_id": interaction_id
            }

    def _parse_interaction(self, interaction) -> Dict[str, Any]:
        """Parse an Interaction response into structured result.

        Args:
            interaction: The Interactions API response object

        Returns:
            Dict with report, sources, and metadata
        """
        report_text = ""
        sources: List[Source] = []
        metadata: Dict[str, Any] = {}

        try:
            # Extract text from interaction outputs
            outputs = getattr(interaction, 'outputs', [])
            if outputs:
                # Get the last output (final result)
                last_output = outputs[-1]
                if hasattr(last_output, 'text'):
                    report_text = last_output.text

            # Extract metadata
            metadata['interaction_id'] = getattr(interaction, 'id', None)
            metadata['status'] = getattr(interaction, 'status', None)

            # Extract usage if available
            if hasattr(interaction, 'usage_metadata'):
                usage = interaction.usage_metadata
                metadata['tokens_input'] = getattr(usage, 'prompt_token_count', 0)
                metadata['tokens_output'] = getattr(usage, 'candidates_token_count', 0)

            # Extract sources from grounding metadata if available
            if hasattr(interaction, 'grounding_metadata'):
                grounding = interaction.grounding_metadata
                if hasattr(grounding, 'grounding_chunks'):
                    for chunk in grounding.grounding_chunks:
                        if hasattr(chunk, 'web'):
                            sources.append(Source(
                                title=getattr(chunk.web, 'title', 'Unknown'),
                                url=getattr(chunk.web, 'uri', ''),
                                snippet=getattr(chunk, 'text', '')[:200] if hasattr(chunk, 'text') else ""
                            ))

        except Exception as e:
            logger.warning(f"Error parsing interaction: {e}")
            # Fallback: try to get any text content
            try:
                outputs = getattr(interaction, 'outputs', [])
                if outputs and hasattr(outputs[-1], 'text'):
                    report_text = outputs[-1].text
            except Exception:
                pass

        return {
            "report": report_text,
            "sources": [s.to_dict() for s in sources],
            "metadata": metadata
        }

    async def start_research_streaming(
        self,
        query: str,
        task_id: str,
        model: Optional[str] = None,
        on_chunk: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, Any]:
        """Start research with streaming enabled to capture intermediate outputs.

        Uses stream=True + background=True for real-time progress capture.
        Streamed outputs are stored progressively for recovery from failures.

        Args:
            query: The research question/topic
            task_id: Task ID for storing intermediate results
            model: Optional model override
            on_chunk: Optional callback(chunk_type, content) for each streamed chunk

        Returns:
            Dict with interaction_id and streaming status
        """
        model_to_use = model or self.DEFAULT_MODEL
        logger.info(f"Starting streaming research with model {model_to_use}: {query[:100]}...")

        try:
            # Use Interactions API with streaming enabled
            # stream=True + background=True for async with real-time updates
            interaction = await asyncio.to_thread(
                self.client.interactions.create,
                input=query,
                agent=model_to_use,
                background=True,
                stream=True  # Enable streaming for intermediate output capture
            )

            interaction_id = interaction.id
            logger.info(f"Streaming research started, interaction_id: {interaction_id}")

            # Try to consume initial stream events
            try:
                if hasattr(interaction, '__iter__'):
                    for event in interaction:
                        # Capture thinking summaries and intermediate outputs
                        if hasattr(event, 'text') and event.text:
                            self.store_intermediate_result(task_id, event.text)
                            if on_chunk:
                                on_chunk("text", event.text)
                        elif hasattr(event, 'thinking') and event.thinking:
                            # Thinking summaries for progress tracking
                            if on_chunk:
                                on_chunk("thinking", event.thinking)
                            logger.debug(f"Thinking: {event.thinking[:100]}...")
            except Exception as stream_err:
                logger.debug(f"Stream iteration ended: {stream_err}")

            return {
                "interaction_id": interaction_id,
                "status": "streaming",
                "task_id": task_id
            }

        except Exception as e:
            logger.error(f"Failed to start streaming research: {e}")
            raise

    async def poll_with_streaming(
        self,
        interaction_id: str,
        task_id: str,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_chunk: Optional[Callable[[str, str], None]] = None,
        poll_interval: int = None,
        max_wait_seconds: int = None
    ) -> Dict[str, Any]:
        """Poll with streaming output capture for progressive caching.

        Captures all streamed outputs during polling for recovery purposes.

        Args:
            interaction_id: The interaction ID from start_research
            task_id: Task ID for storing intermediate results
            on_progress: Optional callback(progress_percent, current_action)
            on_chunk: Optional callback(chunk_type, content) for streamed chunks
            poll_interval: Seconds between polls
            max_wait_seconds: Maximum wait time

        Returns:
            Dict with report, sources, metadata, and cached_chunks count
        """
        poll_interval = poll_interval or self.DEFAULT_POLL_INTERVAL
        max_wait_seconds = max_wait_seconds or self.MAX_WAIT_SECONDS

        start_time = asyncio.get_event_loop().time()
        created_at = datetime.utcnow()
        chunks_captured = 0

        logger.info(f"Polling with streaming for: {interaction_id}")

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time

            if elapsed > max_wait_seconds:
                # Return partial results on timeout
                intermediate = self.get_intermediate_results(task_id)
                if intermediate:
                    logger.warning(f"Timeout with {len(intermediate)} cached chunks")
                    return {
                        "report": "\n\n".join(intermediate),
                        "sources": [],
                        "metadata": {
                            "partial": True,
                            "timeout": True,
                            "chunks_captured": len(intermediate)
                        }
                    }
                raise TimeoutError(f"Research exceeded max wait time of {max_wait_seconds}s")

            try:
                # Get interaction with streaming
                interaction = await asyncio.to_thread(
                    self.client.interactions.get,
                    interaction_id
                )

                status = getattr(interaction, 'status', 'unknown')

                # Capture any new outputs
                outputs = getattr(interaction, 'outputs', [])
                for output in outputs:
                    if hasattr(output, 'text') and output.text:
                        # Check if we've already stored this
                        existing = self.get_intermediate_results(task_id)
                        if output.text not in existing:
                            self.store_intermediate_result(task_id, output.text)
                            chunks_captured += 1
                            if on_chunk:
                                on_chunk("output", output.text)

                # Progress estimation
                elapsed_min = elapsed / 60
                if elapsed_min <= 5:
                    progress = min(50, int((elapsed_min / 5) * 50))
                elif elapsed_min <= 10:
                    progress = min(90, 50 + int(((elapsed_min - 5) / 5) * 40))
                else:
                    progress = min(99, 90 + int((elapsed_min - 10) / 10 * 9))

                current_action = self._get_action_from_status(status, elapsed)
                self.record_progress(task_id, progress, current_action, api_status=status)

                # Check hanging
                hanging_status = self.check_hanging(task_id, created_at)
                if hanging_status.is_hanging and hanging_status.confidence >= 0.9:
                    logger.warning(f"Task appears hung: {hanging_status.reason}")

                if on_progress:
                    try:
                        on_progress(progress, current_action)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")

                if status == "completed":
                    logger.info(f"Research completed with {chunks_captured} chunks captured")
                    result = self._parse_interaction(interaction)
                    result["metadata"]["chunks_captured"] = chunks_captured
                    self.clear_intermediate_results(task_id)
                    return result

                elif status == "failed":
                    # Return any cached partial results
                    intermediate = self.get_intermediate_results(task_id)
                    error_msg = getattr(interaction, 'error', 'Unknown error')
                    if intermediate:
                        logger.warning(f"Failed but have {len(intermediate)} cached chunks")
                        return {
                            "report": "\n\n".join(intermediate),
                            "sources": [],
                            "metadata": {
                                "partial": True,
                                "failed": True,
                                "error": str(error_msg),
                                "chunks_captured": len(intermediate)
                            }
                        }
                    raise Exception(f"Research failed: {error_msg}")

                await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                logger.info(f"Polling cancelled, {chunks_captured} chunks cached")
                raise
            except Exception as e:
                if "failed" in str(e).lower():
                    raise
                logger.warning(f"Poll error (will retry): {e}")
                await asyncio.sleep(poll_interval)

    async def resume_research(
        self,
        task_id: str,
        interaction_id: str,
        on_progress: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """Resume a failed or interrupted research task.

        Uses the stored interaction_id to reconnect and continue polling.
        Any previously cached intermediate results are preserved.

        Args:
            task_id: The original task ID
            interaction_id: The Gemini interaction ID to resume
            on_progress: Optional progress callback

        Returns:
            Dict with final result or error
        """
        logger.info(f"Resuming research task {task_id} (interaction: {interaction_id})")

        # Check what we have cached
        cached = self.get_intermediate_results(task_id)
        if cached:
            logger.info(f"Found {len(cached)} cached chunks from previous attempt")

        try:
            # Try to get current status
            interaction = await asyncio.to_thread(
                self.client.interactions.get,
                interaction_id
            )

            status = getattr(interaction, 'status', 'unknown')
            logger.info(f"Resumed interaction status: {status}")

            if status == "completed":
                # Already finished - parse and return
                result = self._parse_interaction(interaction)
                self.clear_intermediate_results(task_id)
                return {"status": "completed", "result": result}

            elif status == "failed":
                error_msg = getattr(interaction, 'error', 'Unknown error')
                # Return cached partial results if available
                if cached:
                    return {
                        "status": "failed_with_partial",
                        "result": {
                            "report": "\n\n".join(cached),
                            "sources": [],
                            "metadata": {"partial": True, "error": str(error_msg)}
                        }
                    }
                return {"status": "failed", "error": str(error_msg)}

            else:
                # Still running - continue polling with streaming capture
                result = await self.poll_with_streaming(
                    interaction_id=interaction_id,
                    task_id=task_id,
                    on_progress=on_progress
                )
                return {"status": "completed", "result": result}

        except Exception as e:
            logger.error(f"Resume failed: {e}")
            # Return cached results if available
            if cached:
                return {
                    "status": "resume_failed_with_partial",
                    "result": {
                        "report": "\n\n".join(cached),
                        "sources": [],
                        "metadata": {"partial": True, "resume_error": str(e)}
                    },
                    "error": str(e)
                }
            raise

    def create_research_result(
        self,
        task_id: str,
        raw_result: Dict[str, Any]
    ) -> ResearchResult:
        """Create a ResearchResult from raw API result.

        Args:
            task_id: The task ID for this result
            raw_result: Dict from _parse_interaction or poll_until_complete

        Returns:
            ResearchResult dataclass instance
        """
        sources = []
        for s in raw_result.get("sources", []):
            if isinstance(s, dict):
                sources.append(Source.from_dict(s))
            elif isinstance(s, Source):
                sources.append(s)

        return ResearchResult(
            task_id=task_id,
            report=raw_result.get("report", ""),
            sources=sources,
            metadata=raw_result.get("metadata", {}),
            created_at=datetime.utcnow()
        )
