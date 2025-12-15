"""
MarkdownStorage - Saves research reports to permanent Markdown files.

Uses Jinja2 templates for consistent formatting and organizes
reports by month for easy retrieval.
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)


class MarkdownStorage:
    """Handles saving research reports to Markdown files."""

    DEFAULT_OUTPUT_DIR = "./research_reports"
    TEMPLATE_NAME = "research_report.md.j2"

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the Markdown storage.

        Args:
            output_dir: Directory for saving reports (default: ./research_reports)
        """
        self.output_dir = Path(output_dir or self.DEFAULT_OUTPUT_DIR)
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False  # Markdown doesn't need HTML escaping
        )
        logger.info(f"MarkdownStorage initialized with output_dir: {self.output_dir}")

    def save_report(
        self,
        task_id: str,
        query: str,
        report: str,
        sources: list = None,
        metadata: Dict[str, Any] = None,
        task_data: Dict[str, Any] = None,
        prefix: str = "research",
        include_metadata: bool = True,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """Save a research report to a Markdown file.

        Args:
            task_id: The research task ID
            query: The original research query
            report: The research report content (Markdown)
            sources: List of Source objects or dicts with title, url, snippet
            metadata: Additional metadata dict
            task_data: Full task data dict (created_at, completed_at, tokens, etc.)
            prefix: Filename prefix (default: "research")
            include_metadata: Include metadata section in output
            include_sources: Include sources section in output

        Returns:
            Dict with success status, file_path, filename, file_size_kb

        Raises:
            TemplateNotFound: If the report template is missing
            PermissionError: If cannot write to output directory
            OSError: If disk is full or other IO error
        """
        sources = sources or []
        metadata = metadata or {}
        task_data = task_data or {}

        # Prepare template context
        now = datetime.now()
        context = {
            "task_id": task_id,
            "query": query,
            "report": report,
            "sources": self._normalize_sources(sources),
            "title": self._generate_title(query),
            "status": task_data.get("status", "completed"),
            "created_at": task_data.get("created_at", now.isoformat()),
            "completed_at": task_data.get("completed_at", now.isoformat()),
            "duration_minutes": self._calculate_duration(task_data),
            "cost_usd": task_data.get("cost_usd", 0.0),
            "tokens_input": task_data.get("tokens_input", 0),
            "tokens_output": task_data.get("tokens_output", 0),
            "model": task_data.get("model", "gemini-2.0-flash-thinking-exp"),
            "include_metadata": include_metadata,
            "include_sources": include_sources,
            "saved_at": now.isoformat()
        }

        # Add any additional metadata
        context.update(metadata)

        # Render template
        try:
            template = self.env.get_template(self.TEMPLATE_NAME)
            content = template.render(**context)
        except TemplateNotFound:
            logger.error(f"Template not found: {self.TEMPLATE_NAME}")
            raise

        # Create month-organized directory
        month_dir = self.output_dir / now.strftime("%Y-%m")
        month_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        filename = self._generate_filename(task_id, prefix, now)
        filepath = month_dir / filename

        # Check available disk space (basic check)
        content_bytes = content.encode('utf-8')
        required_kb = len(content_bytes) / 1024

        try:
            # Check if we can stat the directory
            stat = os.statvfs(month_dir)
            available_kb = (stat.f_bavail * stat.f_frsize) / 1024
            if available_kb < required_kb + 10:  # 10KB buffer
                return {
                    "success": False,
                    "error": "DISK_FULL",
                    "file_path": str(filepath),
                    "required_kb": round(required_kb, 2),
                    "available_kb": round(available_kb, 2),
                    "message": "Insufficient disk space to save report",
                    "suggestion": "Free up disk space or specify alternative output_dir"
                }
        except (OSError, AttributeError):
            # os.statvfs may not be available on all platforms
            pass

        # Write the file
        try:
            filepath.write_text(content, encoding='utf-8')
        except PermissionError:
            logger.error(f"Permission denied writing to {filepath}")
            return {
                "success": False,
                "error": "PERMISSION_DENIED",
                "file_path": str(filepath),
                "message": f"Cannot write to directory: {month_dir}",
                "suggestion": "Check permissions or specify alternative output_dir"
            }
        except OSError as e:
            logger.error(f"OS error writing to {filepath}: {e}")
            raise

        file_size_kb = filepath.stat().st_size / 1024
        logger.info(f"Saved report to {filepath} ({file_size_kb:.1f} KB)")

        # Determine which sections were included
        sections_included = ["findings"]
        if include_metadata:
            sections_included.insert(0, "metadata")
        if include_sources and sources:
            sections_included.append("sources")

        return {
            "success": True,
            "task_id": task_id,
            "file_path": str(filepath.absolute()),
            "filename": filename,
            "file_size_kb": round(file_size_kb, 2),
            "created_at": now.isoformat(),
            "sections_included": sections_included
        }

    def _normalize_sources(self, sources: list) -> list:
        """Normalize sources to dict format.

        Args:
            sources: List of Source objects or dicts

        Returns:
            List of dicts with title, url, snippet, relevance_score
        """
        normalized = []
        for source in sources:
            if hasattr(source, 'to_dict'):
                normalized.append(source.to_dict())
            elif isinstance(source, dict):
                normalized.append({
                    "title": source.get("title", "Unknown"),
                    "url": source.get("url", ""),
                    "snippet": source.get("snippet", ""),
                    "relevance_score": source.get("relevance_score", 0.0)
                })
            else:
                # Try to extract attributes
                normalized.append({
                    "title": getattr(source, 'title', 'Unknown'),
                    "url": getattr(source, 'url', ''),
                    "snippet": getattr(source, 'snippet', ''),
                    "relevance_score": getattr(source, 'relevance_score', 0.0)
                })
        return normalized

    def _generate_title(self, query: str) -> str:
        """Generate a document title from the query.

        Args:
            query: The research query

        Returns:
            A title suitable for Markdown header
        """
        # Truncate long queries
        if len(query) > 80:
            return query[:77] + "..."
        return query

    def _generate_filename(self, task_id: str, prefix: str, timestamp: datetime) -> str:
        """Generate a unique filename for the report.

        Args:
            task_id: The task UUID
            prefix: Filename prefix
            timestamp: Timestamp for the filename

        Returns:
            Filename like "research_550e8400_20251214_103045.md"
        """
        ts = timestamp.strftime("%Y%m%d_%H%M%S")
        short_id = task_id[:8]
        return f"{prefix}_{short_id}_{ts}.md"

    def _calculate_duration(self, task_data: Dict[str, Any]) -> float:
        """Calculate duration in minutes from task data.

        Args:
            task_data: Dict with created_at and completed_at

        Returns:
            Duration in minutes (float)
        """
        created_at = task_data.get("created_at")
        completed_at = task_data.get("completed_at")

        if not created_at or not completed_at:
            return 0.0

        try:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            if isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))

            delta = completed_at - created_at
            return round(delta.total_seconds() / 60, 2)
        except (ValueError, TypeError):
            return 0.0


# Module-level singleton for convenient access
_markdown_storage = None


def get_markdown_storage(output_dir: Optional[str] = None) -> MarkdownStorage:
    """Get or create the singleton MarkdownStorage instance.

    Args:
        output_dir: Optional output directory override

    Returns:
        MarkdownStorage instance
    """
    global _markdown_storage
    if _markdown_storage is None or output_dir is not None:
        _markdown_storage = MarkdownStorage(output_dir)
    return _markdown_storage
