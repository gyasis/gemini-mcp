"""
StateManager - SQLite-based state persistence for research tasks.

Uses Python's built-in sqlite3 module for zero external dependencies.
Stores task state and results with WAL mode for better concurrent access.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
import logging

from . import TaskStatus, ResearchTask, ResearchResult, Source

logger = logging.getLogger(__name__)


class StateManager:
    """SQLite-based state persistence for research tasks."""

    DB_PATH = Path("deep_research.db")

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the state manager.

        Args:
            db_path: Optional custom database path. Defaults to deep_research.db
        """
        self.db_path = db_path or self.DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a new database connection."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
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
                    model TEXT DEFAULT 'gemini-2.0-flash-thinking-exp',
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
                    FOREIGN KEY (task_id) REFERENCES research_tasks(task_id)
                );
            ''')
            conn.commit()
        finally:
            conn.close()

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
                model=row['model'] or 'gemini-2.0-flash-thinking-exp',
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

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> None:
        """Update specific fields of a task."""
        if not updates:
            return

        # Build dynamic update query
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

    def delete_task(self, task_id: str) -> bool:
        """Delete a task and its results."""
        conn = self._get_connection()
        try:
            # Delete results first (foreign key)
            conn.execute("DELETE FROM research_results WHERE task_id = ?", (task_id,))
            cursor = conn.execute("DELETE FROM research_tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

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
                    model=row['model'] or 'gemini-2.0-flash-thinking-exp',
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
