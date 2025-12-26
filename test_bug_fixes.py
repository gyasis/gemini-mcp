"""
Test script to verify critical bug fixes.

Tests:
1. Bug #1: Foreign key enforcement (PRAGMA foreign_keys=ON)
2. Bug #5: SQL injection protection (column whitelist)
"""

import sqlite3
import tempfile
from pathlib import Path

from deep_research.state_manager import StateManager
from deep_research import ResearchTask, TaskStatus


def test_foreign_key_enforcement():
    """Test Bug #1: Verify foreign keys are enforced."""
    print("Testing Bug #1: Foreign key enforcement...")

    # Create temp database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        manager = StateManager(db_path)

        # Test 1: Verify PRAGMA foreign_keys is enabled
        conn = manager._get_connection()
        result = conn.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1, "❌ Foreign keys must be enabled"
        print("✅ PRAGMA foreign_keys=ON is enabled")

        # Test 2: Verify foreign key violation is caught
        try:
            conn.execute(
                "INSERT INTO research_results (task_id, report_markdown) VALUES (?, ?)",
                ("nonexistent-task-id", "test report")
            )
            conn.commit()
            assert False, "❌ Foreign key violation should have been caught"
        except sqlite3.IntegrityError as e:
            if "foreign key" in str(e).lower():
                print("✅ Foreign key violation correctly caught")
            else:
                raise
        finally:
            conn.close()

        # Test 3: Verify ON DELETE CASCADE works
        # Create a task
        task = ResearchTask(
            task_id="test-123",
            query="test query",
            status=TaskStatus.PENDING
        )
        manager.save_task(task)

        # Add a result for this task
        from deep_research import ResearchResult
        result = ResearchResult(
            task_id="test-123",
            report="Test report",
            sources=[],
            metadata={}
        )
        manager.save_result("test-123", result)

        # Verify result exists
        retrieved_result = manager.get_result("test-123")
        assert retrieved_result is not None, "❌ Result should exist"

        # Delete the task
        manager.delete_task("test-123")

        # Verify result was cascaded (deleted)
        retrieved_result = manager.get_result("test-123")
        assert retrieved_result is None, "❌ Result should be cascaded (deleted)"
        print("✅ ON DELETE CASCADE works correctly")

    print("✅ All foreign key enforcement tests passed!\n")


def test_sql_injection_protection():
    """Test Bug #5: Verify SQL injection is blocked."""
    print("Testing Bug #5: SQL injection protection...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        manager = StateManager(db_path)

        # Create a test task
        task = ResearchTask(
            task_id="test-456",
            query="test",
            status=TaskStatus.PENDING
        )
        manager.save_task(task)

        # Test: Attempt SQL injection via column name
        try:
            manager.update_task("test-456", {
                'status; DROP TABLE research_tasks--': 'hacked'
            })
            assert False, "❌ SQL injection should have been blocked"
        except ValueError as e:
            if "Invalid column names" in str(e):
                print("✅ SQL injection attempt blocked by whitelist")
            else:
                raise

        # Verify table still exists and task is unchanged
        retrieved_task = manager.get_task("test-456")
        assert retrieved_task is not None, "❌ Task should still exist"
        assert retrieved_task.status == TaskStatus.PENDING, "❌ Status should be unchanged"

        # Verify legitimate update still works
        manager.update_task("test-456", {
            'status': TaskStatus.RUNNING,
            'progress': 50
        })

        retrieved_task = manager.get_task("test-456")
        assert retrieved_task.status == TaskStatus.RUNNING, "❌ Legitimate update should work"
        assert retrieved_task.progress == 50, "❌ Progress should be updated"
        print("✅ Legitimate updates work correctly")

    print("✅ All SQL injection protection tests passed!\n")


def test_column_whitelist():
    """Test Bug #5: Verify only whitelisted columns are allowed."""
    print("Testing Bug #5: Column whitelist validation...")

    # Test allowed columns
    allowed = StateManager.ALLOWED_UPDATE_COLUMNS
    expected = {
        'interaction_id', 'status', 'progress', 'current_action',
        'enable_notifications', 'max_wait_hours', 'tokens_input',
        'tokens_output', 'cost_usd', 'error_message', 'completed_at'
    }

    assert allowed == expected, f"❌ Whitelist mismatch: {allowed} != {expected}"
    print(f"✅ Column whitelist contains {len(allowed)} allowed columns")
    print("✅ All column whitelist tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Bug Fix Verification Tests")
    print("=" * 60)
    print()

    try:
        test_foreign_key_enforcement()
        test_sql_injection_protection()
        test_column_whitelist()

        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
