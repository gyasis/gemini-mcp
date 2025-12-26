"""
HangingDetector - Detects stuck/hanging Deep Research tasks.

Tracks progress over time and identifies patterns that indicate a task
is no longer making progress (hung) vs still actively researching.

Expected Deep Research duration:
- Simple queries: 5-15 minutes (typical)
- Complex queries: 20-40 minutes
- Maximum timeout: 60 minutes

Tasks with no API status change for extended periods are likely hung.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ProgressSnapshot:
    """A single progress measurement at a point in time."""
    timestamp: datetime
    progress: int  # 0-100 (display progress, may be synthetic)
    action: str = ""
    api_status: str = ""  # Actual API status (in_progress, completed, failed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "progress": self.progress,
            "action": self.action,
            "api_status": self.api_status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressSnapshot":
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return cls(
            timestamp=ts or datetime.utcnow(),
            progress=data.get("progress", 0),
            action=data.get("action", ""),
            api_status=data.get("api_status", "")
        )


@dataclass
class HangingStatus:
    """Result of hanging detection analysis."""
    is_hanging: bool
    reason: str
    confidence: float  # 0.0-1.0 confidence in the detection
    elapsed_minutes: float
    last_progress: int
    stall_minutes: float = 0.0  # Minutes since last progress change (DEPRECATED: use status_stall_minutes)
    status_stall_minutes: float = 0.0  # Minutes since API status actually changed
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_hanging": self.is_hanging,
            "reason": self.reason,
            "confidence": round(self.confidence, 2),
            "elapsed_minutes": round(self.elapsed_minutes, 1),
            "last_progress": self.last_progress,
            "stall_minutes": round(self.stall_minutes, 1),
            "status_stall_minutes": round(self.status_stall_minutes, 1),
            "recommendation": self.recommendation
        }


class HangingDetector:
    """Detects stuck/hanging Deep Research tasks based on API status patterns.

    Detection Rules:
    1. Expected duration: 5-15 min simple, 20-40 min complex (observed behavior)
    2. API status stalled: Same status for extended period without completion
    3. Excessive duration: Running >60 minutes
    4. No status change after initial start

    Thresholds (configurable):
    - STALL_THRESHOLD_MINUTES: Time without API status change = likely hung
    - EXPECTED_MAX_MINUTES: Normal max duration before concern
    - EXCESSIVE_MINUTES: Definitely hung if still running
    """

    # Thresholds based on observed behavior (5-40 min typical)
    STALL_THRESHOLD_MINUTES = 15  # Same API status for this long = stalled
    EXPECTED_MAX_MINUTES = 25     # Normal tasks should complete by now
    CONCERN_MINUTES = 30          # Getting suspicious
    EXCESSIVE_MINUTES = 60        # Almost certainly hung

    def __init__(
        self,
        stall_threshold_minutes: int = None,
        expected_max_minutes: int = None,
        excessive_minutes: int = None
    ):
        """Initialize the hanging detector.

        Args:
            stall_threshold_minutes: Minutes without progress = stalled
            expected_max_minutes: Expected max duration for normal tasks
            excessive_minutes: Duration that definitely indicates hanging
        """
        self.stall_threshold = stall_threshold_minutes or self.STALL_THRESHOLD_MINUTES
        self.expected_max = expected_max_minutes or self.EXPECTED_MAX_MINUTES
        self.excessive = excessive_minutes or self.EXCESSIVE_MINUTES

        # Progress history per task
        self._history: Dict[str, List[ProgressSnapshot]] = {}

    def record_progress(
        self,
        task_id: str,
        progress: int,
        action: str = "",
        api_status: str = ""
    ) -> None:
        """Record a progress snapshot for a task.

        Args:
            task_id: The task ID
            progress: Current progress percentage (0-100) - may be synthetic
            action: Current action description
            api_status: Actual API status (in_progress, completed, failed) - used for stall detection
        """
        if task_id not in self._history:
            self._history[task_id] = []

        snapshot = ProgressSnapshot(
            timestamp=datetime.utcnow(),
            progress=progress,
            action=action,
            api_status=api_status
        )
        self._history[task_id].append(snapshot)

        # Keep only last 100 snapshots per task to avoid memory bloat
        if len(self._history[task_id]) > 100:
            self._history[task_id] = self._history[task_id][-100:]

    def get_history(self, task_id: str) -> List[ProgressSnapshot]:
        """Get progress history for a task."""
        return self._history.get(task_id, [])

    def clear_history(self, task_id: str) -> None:
        """Clear progress history for a completed/cancelled task."""
        if task_id in self._history:
            del self._history[task_id]

    def load_history_from_snapshots(
        self,
        task_id: str,
        snapshots: List[Dict[str, Any]]
    ) -> int:
        """Load progress history from persisted snapshots (e.g., SQLite).

        Use this to restore hanging detection state after server restart.

        Args:
            task_id: The task ID
            snapshots: List of snapshot dicts from StateManager.get_progress_snapshots()
                       Each dict has: timestamp, progress, action, api_status

        Returns:
            Number of snapshots loaded
        """
        if task_id not in self._history:
            self._history[task_id] = []

        for snap in snapshots:
            ts = snap.get("timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            elif not isinstance(ts, datetime):
                ts = datetime.utcnow()

            self._history[task_id].append(ProgressSnapshot(
                timestamp=ts,
                progress=snap.get("progress", 0),
                action=snap.get("action", ""),
                api_status=snap.get("api_status", "")
            ))

        # Keep only last 100
        if len(self._history[task_id]) > 100:
            self._history[task_id] = self._history[task_id][-100:]

        return len(snapshots)

    def analyze(self, task_id: str, created_at: datetime = None) -> HangingStatus:
        """Analyze a task's progress history to detect hanging.

        Args:
            task_id: The task ID to analyze
            created_at: Task creation time (for elapsed calculation)

        Returns:
            HangingStatus with detection result and recommendations
        """
        history = self._history.get(task_id, [])
        now = datetime.utcnow()

        # Calculate elapsed time
        if created_at:
            elapsed = (now - created_at).total_seconds() / 60
        elif history:
            elapsed = (now - history[0].timestamp).total_seconds() / 60
        else:
            elapsed = 0

        # Not enough data
        if len(history) < 2:
            return HangingStatus(
                is_hanging=False,
                reason="Insufficient progress data",
                confidence=0.0,
                elapsed_minutes=elapsed,
                last_progress=history[-1].progress if history else 0,
                recommendation="Continue monitoring"
            )

        last_snapshot = history[-1]
        last_progress = last_snapshot.progress

        # Calculate both stall metrics
        status_stall_minutes = self._calculate_status_stall_time(history)
        progress_stall_minutes = self._calculate_progress_stall_time(history)

        # Rule 1: Check for excessive total duration
        if elapsed > self.excessive:
            return HangingStatus(
                is_hanging=True,
                reason=f"Excessive duration: {elapsed:.0f} min (expected 5-40 min)",
                confidence=0.95,
                elapsed_minutes=elapsed,
                last_progress=last_progress,
                stall_minutes=progress_stall_minutes,
                status_stall_minutes=status_stall_minutes,
                recommendation="Cancel task - almost certainly hung/crashed"
            )

        # Rule 2: Check for stalled API status (PRIMARY detection method)
        if status_stall_minutes > self.stall_threshold:
            confidence = min(0.9, 0.5 + (status_stall_minutes / self.excessive) * 0.4)
            return HangingStatus(
                is_hanging=True,
                reason=f"API status unchanged for {status_stall_minutes:.0f} min",
                confidence=confidence,
                elapsed_minutes=elapsed,
                last_progress=last_progress,
                stall_minutes=progress_stall_minutes,
                status_stall_minutes=status_stall_minutes,
                recommendation="Consider cancelling - no API response change detected"
            )

        # Rule 3: Check for concerning duration with slow progress
        if elapsed > self.CONCERN_MINUTES and last_progress < 50:
            return HangingStatus(
                is_hanging=False,  # Not definitively hung yet
                reason=f"Slow progress: {last_progress}% after {elapsed:.0f} min",
                confidence=0.4,
                elapsed_minutes=elapsed,
                last_progress=last_progress,
                stall_minutes=progress_stall_minutes,
                status_stall_minutes=status_stall_minutes,
                recommendation="Monitor closely - slower than expected"
            )

        # Rule 4: Check for stuck at high percentage (common pattern)
        if last_progress >= 90 and status_stall_minutes > 10:
            return HangingStatus(
                is_hanging=True,
                reason=f"Stuck at {last_progress}% for {status_stall_minutes:.0f} min (finalization hung)",
                confidence=0.8,
                elapsed_minutes=elapsed,
                last_progress=last_progress,
                stall_minutes=progress_stall_minutes,
                status_stall_minutes=status_stall_minutes,
                recommendation="Cancel task - finalization appears hung"
            )

        # Normal operation
        return HangingStatus(
            is_hanging=False,
            reason="Task progressing normally",
            confidence=0.1,
            elapsed_minutes=elapsed,
            last_progress=last_progress,
            stall_minutes=progress_stall_minutes,
            status_stall_minutes=status_stall_minutes,
            recommendation="Continue - within expected parameters"
        )

    def _calculate_status_stall_time(self, history: List[ProgressSnapshot]) -> float:
        """Calculate how long API status has been unchanged.

        This is the PRIMARY metric for hanging detection since progress is synthetic.
        Returns minutes since the last api_status change.
        """
        if len(history) < 2:
            return 0.0

        current_status = history[-1].api_status
        current_time = history[-1].timestamp

        # If no api_status recorded, fall back to progress-based stall
        if not current_status:
            return self._calculate_progress_stall_time(history)

        # Walk backwards to find when api_status last changed
        last_change_time = current_time
        for snapshot in reversed(history[:-1]):
            if snapshot.api_status and snapshot.api_status != current_status:
                break
            last_change_time = snapshot.timestamp

        stall_seconds = (current_time - last_change_time).total_seconds()
        return stall_seconds / 60

    def _calculate_progress_stall_time(self, history: List[ProgressSnapshot]) -> float:
        """Calculate how long progress has been stalled (DEPRECATED - use status stall).

        Returns minutes since the last progress change.
        Note: Progress may be synthetic, so this is less reliable than status stall.
        """
        if len(history) < 2:
            return 0.0

        current_progress = history[-1].progress
        current_time = history[-1].timestamp

        # Walk backwards to find when progress last changed
        last_change_time = current_time
        for snapshot in reversed(history[:-1]):
            if snapshot.progress != current_progress:
                break
            last_change_time = snapshot.timestamp

        stall_seconds = (current_time - last_change_time).total_seconds()
        return stall_seconds / 60

    def get_progress_rate(self, task_id: str) -> Optional[float]:
        """Calculate progress rate (percentage per minute).

        Returns None if insufficient data.
        """
        history = self._history.get(task_id, [])
        if len(history) < 2:
            return None

        first = history[0]
        last = history[-1]

        progress_delta = last.progress - first.progress
        time_delta_min = (last.timestamp - first.timestamp).total_seconds() / 60

        if time_delta_min <= 0:
            return None

        return progress_delta / time_delta_min

    def estimate_remaining_time(self, task_id: str) -> Optional[float]:
        """Estimate remaining time to completion (minutes).

        Returns None if cannot estimate.
        """
        history = self._history.get(task_id, [])
        if len(history) < 2:
            return None

        rate = self.get_progress_rate(task_id)
        if rate is None or rate <= 0:
            return None

        remaining_progress = 100 - history[-1].progress
        return remaining_progress / rate


# Module-level singleton
_hanging_detector: Optional[HangingDetector] = None


def get_hanging_detector() -> HangingDetector:
    """Get or create the singleton HangingDetector instance."""
    global _hanging_detector
    if _hanging_detector is None:
        _hanging_detector = HangingDetector()
    return _hanging_detector
