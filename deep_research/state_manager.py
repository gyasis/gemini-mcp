"""
StateManager - SQLite-based state persistence for research tasks.

Uses Python's built-in sqlite3 module for zero external dependencies.
Stores task state and results with WAL mode for better concurrent access.
Includes retry logic for handling transient SQLite errors (database locks, busy timeouts).
"""

import sqlite3
import json
import time
import functools
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, Callable, TypeVar
from datetime import datetime
import logging

from . import TaskStatus, ResearchTask, ResearchResult, Source

logger = logging.getLogger(__name__)

# Type variable for generic return type in retry decorator
T = TypeVar('T')


def sqlite_retry(
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    backoff_factor: float = 2.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying SQLite operations on transient errors.

    Implements exponential backoff for database lock and busy errors.
    This handles concurrent access gracefully without failing immediately.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds between retries (default: 0.1)
        max_delay: Maximum delay cap in seconds (default: 2.0)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)

    Returns:
        Decorated function with retry logic

    Raises:
        sqlite3.OperationalError: After all retries exhausted
        sqlite3.DatabaseError: For non-retryable errors
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            delay = base_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    error_msg = str(e).lower()
                    # Retry on database lock or busy errors
                    if 'locked' in error_msg or 'busy' in error_msg:
                        last_error = e
                        if attempt < max_retries:
                            logger.warning(
                                f"SQLite operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                f"Retrying in {delay:.2f}s..."
                            )
                            time.sleep(delay)
                            delay = min(delay * backoff_factor, max_delay)
                            continue
                    # Non-retryable OperationalError
                    raise
                except sqlite3.DatabaseError as e:
                    # Log and re-raise non-retryable database errors
                    logger.error(f"SQLite database error in {func.__name__}: {e}")
                    raise

            # All retries exhausted
            logger.error(f"SQLite operation failed after {max_retries + 1} attempts: {last_error}")
            raise last_error

        return wrapper
    return decorator


class StateManager:
    """SQLite-based state persistence for research tasks."""

    DB_PATH = Path("deep_research.db")

    # SECURITY: Whitelist of allowed columns for update_task()
    ALLOWED_UPDATE_COLUMNS = {
        'interaction_id', 'status', 'progress', 'current_action',
        'enable_notifications', 'max_wait_hours', 'tokens_input',
        'tokens_output', 'cost_usd', 'error_message', 'completed_at'
    }

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the state manager.

        Args:
            db_path: Optional custom database path. Defaults to deep_research.db
        """
        self.db_path = db_path or self.DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a new database connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # CRITICAL: Enable foreign key enforcement (disabled by default in SQLite)
        conn.execute("PRAGMA foreign_keys=ON")

        # Verify WAL mode succeeded (optional but recommended)
        result = conn.execute("PRAGMA journal_mode").fetchone()
        if result and result[0] != 'wal':
            logger.warning(f"WAL mode not active, using: {result[0]}")

        return conn

    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_connection()
        try:
            conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS research_tasks (
                    task_id TEXT PRIMARY KEY,
                    interaction_id TEXT,
                    query TEXT NOT NULL,
                    model TEXT DEFAULT 'deep-research-pro-preview-12-2025',
                    status TEXT DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    current_action TEXT,
                    enable_notifications BOOLEAN DEFAULT TRUE,
                    max_wait_hours INTEGER DEFAULT 8,
                    tokens_input INTEGER DEFAULT 0,
                    tokens_output INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status ON research_tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_created ON research_tasks(created_at);

                CREATE TABLE IF NOT EXISTS research_results (
                    task_id TEXT PRIMARY KEY,
                    report_markdown TEXT,
                    sources_json TEXT,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS progress_snapshots (
                    task_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    progress INTEGER NOT NULL,
                    action TEXT DEFAULT '',
                    api_status TEXT DEFAULT '',
                    PRIMARY KEY (task_id, timestamp),
                    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_snapshots_task ON progress_snapshots(task_id);
            ''')
            conn.commit()
        finally:
            conn.close()

    @sqlite_retry()
    def save_task(self, task: ResearchTask) -> None:
        """Save or update a research task."""
        conn = self._get_connection()
        try:
            conn.execute('''
                INSERT OR REPLACE INTO research_tasks
                (task_id, interaction_id, query, model, status, progress, current_action,
                 enable_notifications, max_wait_hours, tokens_input, tokens_output, cost_usd,
                 error_message, created_at, updated_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.task_id,
                task.interaction_id,
                task.query,
                task.model,
                task.status.value,
                task.progress,
                task.current_action,
                task.enable_notifications,
                task.max_wait_hours,
                task.tokens_input,
                task.tokens_output,
                task.cost_usd,
                task.error_message,
                task.created_at.isoformat() if task.created_at else datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                task.completed_at.isoformat() if task.completed_at else None
            ))
            conn.commit()
        finally:
            conn.close()

    @sqlite_retry()
    def get_task(self, task_id: str) -> Optional[ResearchTask]:
        """Retrieve a task by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM research_tasks WHERE task_id = ?", (task_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return ResearchTask(
                task_id=row['task_id'],
                interaction_id=row['interaction_id'],
                query=row['query'],
                model=row['model'] or 'deep-research-pro-preview-12-2025',
                status=TaskStatus(row['status']),
                progress=row['progress'] or 0,
                current_action=row['current_action'] or "",
                enable_notifications=bool(row['enable_notifications']),
                max_wait_hours=row['max_wait_hours'] or 8,
                tokens_input=row['tokens_input'] or 0,
                tokens_output=row['tokens_output'] or 0,
                cost_usd=row['cost_usd'] or 0.0,
                error_message=row['error_message'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.utcnow(),
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.utcnow(),
                completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None
            )
        finally:
            conn.close()

    @sqlite_retry()
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> None:
        """Update specific fields of a task.

        Args:
            task_id: Task ID to update
            updates: Dict of column_name -> value pairs

        Raises:
            ValueError: If any column name is not whitelisted
        """
        if not updates:
            return

        # SECURITY: Validate all column names against whitelist
        invalid_columns = set(updates.keys()) - self.ALLOWED_UPDATE_COLUMNS
        if invalid_columns:
            raise ValueError(
                f"Invalid column names in update: {invalid_columns}. "
                f"Allowed columns: {self.ALLOWED_UPDATE_COLUMNS}"
            )

        # Build dynamic update query (now safe - all keys validated)
        set_clauses = []
        values = []
        for key, value in updates.items():
            if key == 'status' and isinstance(value, TaskStatus):
                value = value.value
            elif key in ('created_at', 'updated_at', 'completed_at') and isinstance(value, datetime):
                value = value.isoformat()
            set_clauses.append(f"{key} = ?")
            values.append(value)

        # Always update updated_at
        set_clauses.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())

        values.append(task_id)

        conn = self._get_connection()
        try:
            query = f"UPDATE research_tasks SET {', '.join(set_clauses)} WHERE task_id = ?"
            conn.execute(query, values)
            conn.commit()
        finally:
            conn.close()

    @sqlite_retry()
    def get_incomplete_tasks(self) -> List[Tuple[str, Optional[str]]]:
        """Get tasks that need to be resumed on startup.

        Returns:
            List of (task_id, interaction_id) tuples for incomplete tasks
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT task_id, interaction_id FROM research_tasks WHERE status IN ('running', 'running_async')"
            )
            return cursor.fetchall()
        finally:
            conn.close()

    @sqlite_retry()
    def save_result(self, task_id: str, result: ResearchResult) -> None:
        """Save research results."""
        conn = self._get_connection()
        try:
            # Convert sources to JSON
            sources_json = json.dumps(
                [s.to_dict() if isinstance(s, Source) else s for s in result.sources]
            )
            metadata_json = json.dumps(result.metadata)

            conn.execute('''
                INSERT OR REPLACE INTO research_results
                (task_id, report_markdown, sources_json, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                task_id,
                result.report,
                sources_json,
                metadata_json,
                result.created_at.isoformat() if result.created_at else datetime.utcnow().isoformat()
            ))
            conn.commit()
        finally:
            conn.close()

    @sqlite_retry()
    def get_result(self, task_id: str) -> Optional[ResearchResult]:
        """Retrieve research results by task ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM research_results WHERE task_id = ?", (task_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            # Parse sources from JSON
            sources = []
            if row['sources_json']:
                sources_data = json.loads(row['sources_json'])
                sources = [Source.from_dict(s) if isinstance(s, dict) else s for s in sources_data]

            # Parse metadata from JSON
            metadata = {}
            if row['metadata_json']:
                metadata = json.loads(row['metadata_json'])

            return ResearchResult(
                task_id=row['task_id'],
                report=row['report_markdown'] or "",
                sources=sources,
                metadata=metadata,
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.utcnow()
            )
        finally:
            conn.close()

    @sqlite_retry()
    def delete_task(self, task_id: str) -> bool:
        """Delete a task and its results."""
        conn = self._get_connection()
        try:
            # Delete progress snapshots first
            conn.execute("DELETE FROM progress_snapshots WHERE task_id = ?", (task_id,))

            # Delete results (foreign key constraint will be enforced now)
            conn.execute("DELETE FROM research_results WHERE task_id = ?", (task_id,))

            # Delete task
            cursor = conn.execute("DELETE FROM research_tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @sqlite_retry()
    def get_all_tasks(self, limit: int = 100) -> List[ResearchTask]:
        """Get all tasks, most recent first."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM research_tasks ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            tasks = []
            for row in cursor.fetchall():
                tasks.append(ResearchTask(
                    task_id=row['task_id'],
                    interaction_id=row['interaction_id'],
                    query=row['query'],
                    model=row['model'] or 'deep-research-pro-preview-12-2025',
                    status=TaskStatus(row['status']),
                    progress=row['progress'] or 0,
                    current_action=row['current_action'] or "",
                    enable_notifications=bool(row['enable_notifications']),
                    max_wait_hours=row['max_wait_hours'] or 8,
                    tokens_input=row['tokens_input'] or 0,
                    tokens_output=row['tokens_output'] or 0,
                    cost_usd=row['cost_usd'] or 0.0,
                    error_message=row['error_message'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.utcnow(),
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None
                ))
            return tasks
        finally:
            conn.close()

    # =========================================================================
    # Progress Snapshot Persistence (for hanging detection across restarts)
    # =========================================================================

    @sqlite_retry()
    def save_progress_snapshot(
        self,
        task_id: str,
        progress: int,
        action: str = "",
        api_status: str = "",
        timestamp: Optional[datetime] = None
    ) -> None:
        """Save a progress snapshot for hanging detection persistence.

        Args:
            task_id: The task ID
            progress: Current progress percentage (0-100)
            action: Current action description
            api_status: Actual API status (in_progress, completed, failed)
            timestamp: Snapshot timestamp (defaults to now)
        """
        ts = timestamp or datetime.utcnow()
        conn = self._get_connection()
        try:
            conn.execute('''
                INSERT OR REPLACE INTO progress_snapshots
                (task_id, timestamp, progress, action, api_status)
                VALUES (?, ?, ?, ?, ?)
            ''', (task_id, ts.isoformat(), progress, action, api_status))
            conn.commit()
        finally:
            conn.close()

    @sqlite_retry()
    def get_progress_snapshots(self, task_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get progress snapshots for a task (most recent first).

        Args:
            task_id: The task ID
            limit: Maximum number of snapshots to return

        Returns:
            List of snapshot dicts with timestamp, progress, action, api_status
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                SELECT timestamp, progress, action, api_status
                FROM progress_snapshots
                WHERE task_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (task_id, limit))
            snapshots = []
            for row in cursor.fetchall():
                snapshots.append({
                    "timestamp": row['timestamp'],
                    "progress": row['progress'],
                    "action": row['action'] or "",
                    "api_status": row['api_status'] or ""
                })
            # Reverse to get oldest-first order (for hanging detector)
            return list(reversed(snapshots))
        finally:
            conn.close()

    @sqlite_retry()
    def clear_progress_snapshots(self, task_id: str) -> int:
        """Clear progress snapshots for a completed/cancelled task.

        Args:
            task_id: The task ID

        Returns:
            Number of snapshots deleted
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM progress_snapshots WHERE task_id = ?",
                (task_id,)
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
