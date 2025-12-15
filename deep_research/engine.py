"""
DeepResearchEngine - Wraps Gemini Deep Research Interactions API.

Uses the Interactions API (NOT generateContent) for deep research.
Model: deep-research-pro-preview-12-2025 (December 2025 release)
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime

from google import genai

from . import Source, ResearchResult

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

    # Maximum wait time (60 minutes is API max, we use 8 hours for user config)
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
        """Start a deep research query using Interactions API.

        The Deep Research agent REQUIRES background=True (async execution).
        Research typically takes 20 minutes, max 60 minutes.

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
        on_progress: Optional[Callable[[int, str], None]] = None,
        poll_interval: int = None,
        max_wait_seconds: int = None
    ) -> Dict[str, Any]:
        """Poll for research completion using Interactions API.

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
                # Use Interactions API to get status
                interaction = await asyncio.to_thread(
                    self.client.interactions.get,
                    interaction_id
                )
                poll_count += 1

                status = getattr(interaction, 'status', 'unknown')

                # Estimate progress based on elapsed time (research typically 20 mins)
                progress = min(95, int((elapsed / 1200) * 100))  # 20 min = 100%
                current_action = self._get_action_from_status(status, elapsed)

                logger.debug(f"Poll {poll_count}: status={status}, progress~{progress}%")

                # Call progress callback if provided
                if on_progress:
                    try:
                        on_progress(progress, current_action)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")

                if status == "completed":
                    logger.info(f"Research completed after {poll_count} polls ({elapsed:.1f}s)")
                    return self._parse_interaction(interaction)

                elif status == "failed":
                    error_msg = getattr(interaction, 'error', 'Unknown error')
                    logger.error(f"Research failed: {error_msg}")
                    raise Exception(f"Research failed: {error_msg}")

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

    def _get_action_from_status(self, status: str, elapsed: float) -> str:
        """Generate human-readable action based on status and elapsed time."""
        if status == "completed":
            return "Research complete"
        elif status == "failed":
            return "Research failed"

        # Estimate phase based on typical 20-minute research duration
        minutes = elapsed / 60
        if minutes < 2:
            return "Analyzing query and planning research..."
        elif minutes < 5:
            return "Searching and gathering sources..."
        elif minutes < 10:
            return "Reading and synthesizing information..."
        elif minutes < 15:
            return "Compiling findings..."
        elif minutes < 20:
            return "Generating comprehensive report..."
        else:
            return "Finalizing research (complex query)..."

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
