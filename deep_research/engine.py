"""
DeepResearchEngine - Wraps Gemini Deep Research API with hybrid sync-to-async execution.

Uses the unified google-genai SDK for Gemini API access.
Implements 30s sync timeout then async handoff pattern.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime

from google import genai
from google.genai import types

from . import TaskStatus, Source, ResearchTask, ResearchResult

logger = logging.getLogger(__name__)


class DeepResearchEngine:
    """Wraps Gemini Deep Research API with hybrid execution patterns."""

    # Deep Research model (as per research.md)
    DEFAULT_MODEL = "gemini-2.0-flash-thinking-exp"

    # Timeout before switching to async (30 seconds per spec)
    SYNC_TIMEOUT_SECONDS = 30

    # Default polling interval
    DEFAULT_POLL_INTERVAL = 10

    # Maximum wait time (8 hours)
    MAX_WAIT_SECONDS = 28800

    def __init__(self, client: genai.Client):
        """Initialize the deep research engine.

        Args:
            client: Initialized google-genai Client instance
        """
        self.client = client

    async def start_research(
        self,
        query: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a deep research query.

        Args:
            query: The research question/topic
            model: Optional model override (defaults to DEFAULT_MODEL)

        Returns:
            Dict with interaction_id, status, and initial response info
        """
        model_to_use = model or self.DEFAULT_MODEL
        logger.info(f"Starting deep research with model {model_to_use}: {query[:100]}...")

        try:
            # Use async generate_content for deep research
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model_to_use,
                contents=query,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                )
            )

            # For deep research models, the response may include an interaction ID
            # for long-running operations. If not, we treat it as immediately complete.
            interaction_id = getattr(response, 'id', None) or getattr(response, 'name', None)

            # Check if response completed immediately
            if response.text:
                logger.info("Research completed synchronously")
                return {
                    "interaction_id": interaction_id,
                    "status": "completed",
                    "result": self._parse_response(response),
                    "completed_immediately": True
                }

            # Response is pending async completion
            logger.info(f"Research started async, interaction_id: {interaction_id}")
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
        on_progress: Optional[Callable[[int, str], None]] = None,
        poll_interval: int = None,
        max_wait_seconds: int = None
    ) -> Dict[str, Any]:
        """Poll for research completion.

        Args:
            interaction_id: The interaction ID from start_research
            on_progress: Optional callback(progress_percent, current_action)
            poll_interval: Seconds between polls (default: 10)
            max_wait_seconds: Maximum wait time (default: 8 hours)

        Returns:
            Dict with report, sources, and metadata

        Raises:
            TimeoutError: If max_wait_seconds exceeded
            Exception: If research fails
        """
        poll_interval = poll_interval or self.DEFAULT_POLL_INTERVAL
        max_wait_seconds = max_wait_seconds or self.MAX_WAIT_SECONDS

        start_time = asyncio.get_event_loop().time()
        poll_count = 0

        logger.info(f"Polling for completion: {interaction_id}")

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time

            if elapsed > max_wait_seconds:
                raise TimeoutError(
                    f"Research exceeded max wait time of {max_wait_seconds}s"
                )

            try:
                status = await self._get_status(interaction_id)
                poll_count += 1

                state = status.get("state", "unknown")
                progress = status.get("progress", 0)
                current_action = status.get("current_action", "Researching...")

                logger.debug(f"Poll {poll_count}: state={state}, progress={progress}%")

                # Call progress callback if provided
                if on_progress:
                    try:
                        on_progress(progress, current_action)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")

                if state == "completed":
                    logger.info(f"Research completed after {poll_count} polls ({elapsed:.1f}s)")
                    return status.get("result", {})

                elif state == "failed":
                    error_msg = status.get("error", "Unknown error")
                    logger.error(f"Research failed: {error_msg}")
                    raise Exception(f"Research failed: {error_msg}")

                # Continue polling
                await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                logger.info(f"Polling cancelled for {interaction_id}")
                raise
            except Exception as e:
                if "failed" in str(e).lower():
                    raise
                logger.warning(f"Poll error (will retry): {e}")
                await asyncio.sleep(poll_interval)

    async def _get_status(self, interaction_id: str) -> Dict[str, Any]:
        """Get current status of a research interaction.

        Note: The actual Gemini Deep Research API polling mechanism may differ.
        This implementation assumes the response object contains status info.
        For the thinking model, responses are typically synchronous.

        Args:
            interaction_id: The interaction ID to check

        Returns:
            Dict with state, progress, current_action, and optionally result/error
        """
        # For gemini-2.0-flash-thinking-exp, responses are typically synchronous.
        # The polling pattern is primarily for the deep-research-pro-preview model.
        # This method serves as a placeholder for async status checking.

        # In practice, most "thinking" model responses complete immediately,
        # so this would return completed status.

        # TODO: When using actual deep-research-pro-preview model,
        # implement proper interactions.get() polling here

        return {
            "state": "completed",
            "progress": 100,
            "current_action": "Research complete"
        }

    async def execute_with_timeout(
        self,
        query: str,
        model: Optional[str] = None,
        timeout_seconds: int = None,
        on_progress: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """Execute research with sync timeout, returning early if exceeds threshold.

        This implements the hybrid sync-to-async pattern:
        1. Start research
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

        # If completed immediately, return result
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
                    poll_interval=2  # Poll more frequently during sync phase
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

    def _parse_response(self, response) -> Dict[str, Any]:
        """Parse a Gemini response into structured result.

        Args:
            response: The Gemini API response object

        Returns:
            Dict with report, sources, and metadata
        """
        report_text = ""
        sources: List[Source] = []
        metadata: Dict[str, Any] = {}

        try:
            # Extract text content
            if hasattr(response, 'text'):
                report_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content.parts:
                    report_text = candidate.content.parts[0].text

            # Extract usage metadata if available
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                metadata['tokens_input'] = getattr(usage, 'prompt_token_count', 0)
                metadata['tokens_output'] = getattr(usage, 'candidates_token_count', 0)

            # Extract grounding sources if available (for research-grounded responses)
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    grounding = candidate.grounding_metadata
                    if hasattr(grounding, 'web_search_queries'):
                        metadata['search_queries'] = grounding.web_search_queries
                    if hasattr(grounding, 'grounding_chunks'):
                        for chunk in grounding.grounding_chunks:
                            if hasattr(chunk, 'web'):
                                sources.append(Source(
                                    title=getattr(chunk.web, 'title', 'Unknown'),
                                    url=getattr(chunk.web, 'uri', ''),
                                    snippet=getattr(chunk, 'text', '')[:200] if hasattr(chunk, 'text') else ""
                                ))

        except Exception as e:
            logger.warning(f"Error parsing response: {e}")
            if hasattr(response, 'text'):
                report_text = response.text

        return {
            "report": report_text,
            "sources": [s.to_dict() for s in sources],
            "metadata": metadata
        }

    def create_research_result(
        self,
        task_id: str,
        raw_result: Dict[str, Any]
    ) -> ResearchResult:
        """Create a ResearchResult from raw API result.

        Args:
            task_id: The task ID for this result
            raw_result: Dict from _parse_response or poll_until_complete

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
