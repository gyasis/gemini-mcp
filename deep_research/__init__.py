"""
Deep Research Module - Data models and types for hybrid deep research system.

This module provides zero-external-dependency data models using Python's
standard library (dataclasses, enum) for the deep research functionality.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class TaskStatus(str, Enum):
    """Research task lifecycle states."""
    PENDING = "pending"           # Created, not yet started
    RUNNING = "running"           # In progress (sync attempt)
    RUNNING_ASYNC = "running_async"  # Background async execution
    COMPLETED = "completed"       # Successfully finished
    FAILED = "failed"             # Error during execution
    CANCELLED = "cancelled"       # User-initiated cancellation


@dataclass
class Source:
    """A source referenced in the research."""
    title: str                            # Source title
    url: str                              # Source URL
    snippet: str = ""                     # Relevant excerpt
    relevance_score: float = 0.0          # 0.0-1.0 relevance

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "relevance_score": self.relevance_score
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Source":
        """Create from dictionary."""
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            snippet=data.get("snippet", ""),
            relevance_score=data.get("relevance_score", 0.0)
        )


@dataclass
class TokenUsage:
    """Token consumption tracking."""
    input: int = 0                        # Input tokens
    output: int = 0                       # Output tokens

    @property
    def total(self) -> int:
        return self.input + self.output

    def estimate_cost_usd(self) -> float:
        """Estimate USD cost based on Gemini Deep Research pricing."""
        # Deep Research pricing (approximate for deep-research-pro-preview)
        input_cost = self.input * 0.000001    # $1/1M input tokens
        output_cost = self.output * 0.000004  # $4/1M output tokens
        return input_cost + output_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {"input": self.input, "output": self.output, "total": self.total}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenUsage":
        """Create from dictionary."""
        return cls(input=data.get("input", 0), output=data.get("output", 0))


@dataclass
class ResearchTask:
    """Tracks lifecycle of a deep research request."""

    # Identifiers
    task_id: str                          # UUID v4
    interaction_id: Optional[str] = None  # Gemini API interaction ID

    # Request
    query: str = ""                       # Original research question
    model: str = "deep-research-pro-preview-12-2025"

    # Status
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0                     # 0-100 percentage
    current_action: str = ""              # Human-readable current step

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Token Tracking
    tokens_input: int = 0                 # Input tokens consumed
    tokens_output: int = 0                # Output tokens generated
    cost_usd: float = 0.0                 # Estimated cost in USD

    # Notification Config
    enable_notifications: bool = True     # Send desktop notification
    max_wait_hours: int = 8               # Maximum async duration

    # Error
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "interaction_id": self.interaction_id,
            "query": self.query,
            "model": self.model,
            "status": self.status.value,
            "progress": self.progress,
            "current_action": self.current_action,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "cost_usd": self.cost_usd,
            "enable_notifications": self.enable_notifications,
            "max_wait_hours": self.max_wait_hours,
            "error_message": self.error_message
        }


@dataclass
class ResearchResult:
    """Completed research output."""

    # Task Reference
    task_id: str

    # Report Content
    report: str                           # Full Markdown report

    # Sources
    sources: List[Source] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamp
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "report": self.report,
            "sources": [s.to_dict() if isinstance(s, Source) else s for s in self.sources],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchResult":
        """Create from dictionary."""
        sources = []
        for s in data.get("sources", []):
            if isinstance(s, dict):
                sources.append(Source.from_dict(s))
            else:
                sources.append(s)

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            task_id=data["task_id"],
            report=data.get("report", ""),
            sources=sources,
            metadata=data.get("metadata", {}),
            created_at=created_at or datetime.utcnow()
        )


@dataclass
class CostEstimate:
    """Pre-research cost and duration estimate."""

    query_complexity: str                 # simple, medium, complex

    # Duration Estimates (minutes)
    min_minutes: float = 0.0
    max_minutes: float = 0.0
    likely_minutes: float = 0.0

    # Cost Estimates (USD)
    min_usd: float = 0.0
    max_usd: float = 0.0
    likely_usd: float = 0.0

    # Predictions
    will_likely_go_async: bool = False
    recommendation: str = ""              # Human-readable suggestion

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_complexity": self.query_complexity,
            "estimated_duration": {
                "min_minutes": self.min_minutes,
                "max_minutes": self.max_minutes,
                "likely_minutes": self.likely_minutes
            },
            "estimated_cost": {
                "min_usd": self.min_usd,
                "max_usd": self.max_usd,
                "likely_usd": self.likely_usd
            },
            "will_likely_go_async": self.will_likely_go_async,
            "recommendation": self.recommendation
        }


# Export all public classes
__all__ = [
    "TaskStatus",
    "Source",
    "TokenUsage",
    "ResearchTask",
    "ResearchResult",
    "CostEstimate"
]
