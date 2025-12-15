"""
NativeNotifier - Cross-platform desktop notifications with fallback chain.

Fallback hierarchy:
1. notify-py library (primary)
2. Platform CLI commands (notify-send for Linux, osascript for macOS)
3. Console logging (final fallback)
"""

import platform
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NativeNotifier:
    """Cross-platform desktop notification sender with graceful fallback."""

    APPLICATION_NAME = "Gemini Deep Research"

    def __init__(self):
        """Initialize the notifier."""
        self._notify_py_available: Optional[bool] = None

    def _check_notify_py(self) -> bool:
        """Check if notify-py is available."""
        if self._notify_py_available is None:
            try:
                from notifypy import Notify  # noqa: F401
                self._notify_py_available = True
            except ImportError:
                self._notify_py_available = False
                logger.debug("notify-py not available, will use fallback")
        return self._notify_py_available

    def notify(self, title: str, message: str, urgency: str = "normal") -> bool:
        """Send a desktop notification with fallback chain.

        Args:
            title: Notification title
            message: Notification body text
            urgency: Notification urgency (low, normal, critical) - used by Linux

        Returns:
            True if notification was sent successfully (any method), False otherwise
        """
        # Try notify-py first
        if self._check_notify_py():
            try:
                from notifypy import Notify
                notification = Notify()
                notification.title = title
                notification.message = message
                notification.application_name = self.APPLICATION_NAME
                notification.send()
                logger.debug(f"Notification sent via notify-py: {title}")
                return True
            except Exception as e:
                logger.warning(f"notify-py failed: {e}, trying fallback")

        # Fall back to platform-specific CLI
        return self._fallback_notify(title, message, urgency)

    def _fallback_notify(self, title: str, message: str, urgency: str = "normal") -> bool:
        """Platform-specific CLI fallback for notifications.

        Args:
            title: Notification title
            message: Notification body text
            urgency: Notification urgency

        Returns:
            True if notification sent successfully, False otherwise
        """
        system = platform.system()

        try:
            if system == "Linux":
                # Use notify-send on Linux
                cmd = ['notify-send', '-a', self.APPLICATION_NAME]
                if urgency == "critical":
                    cmd.extend(['-u', 'critical'])
                elif urgency == "low":
                    cmd.extend(['-u', 'low'])
                cmd.extend([title, message])
                subprocess.run(cmd, check=True, capture_output=True)
                logger.debug(f"Notification sent via notify-send: {title}")
                return True

            elif system == "Darwin":  # macOS
                # Use osascript on macOS
                # Escape quotes in message and title
                safe_title = title.replace('"', '\\"').replace("'", "\\'")
                safe_message = message.replace('"', '\\"').replace("'", "\\'")
                script = f'display notification "{safe_message}" with title "{safe_title}"'
                subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
                logger.debug(f"Notification sent via osascript: {title}")
                return True

            elif system == "Windows":
                # Try Windows toast notification via PowerShell
                safe_title = title.replace("'", "''")
                safe_message = message.replace("'", "''")
                script = f'''
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
                $template = @"
                <toast>
                    <visual>
                        <binding template="ToastText02">
                            <text id="1">{safe_title}</text>
                            <text id="2">{safe_message}</text>
                        </binding>
                    </visual>
                </toast>
"@
                $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
                $xml.LoadXml($template)
                $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{self.APPLICATION_NAME}").Show($toast)
                '''
                subprocess.run(
                    ['powershell', '-Command', script],
                    check=True,
                    capture_output=True
                )
                logger.debug(f"Notification sent via PowerShell: {title}")
                return True

        except FileNotFoundError:
            logger.warning(f"Notification command not found for {system}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Notification command failed: {e}")
        except Exception as e:
            logger.warning(f"Notification fallback failed: {e}")

        # Final fallback: log the notification
        logger.info(f"NOTIFICATION [{urgency.upper()}]: {title} - {message}")
        return False

    def notify_research_complete(self, task_id: str, duration_minutes: float) -> bool:
        """Send notification that research is complete.

        Args:
            task_id: The research task ID (will show first 8 chars)
            duration_minutes: How long the research took

        Returns:
            True if notification sent successfully
        """
        title = "Deep Research Complete"
        message = f"Task {task_id[:8]} finished in {duration_minutes:.1f} minutes"
        return self.notify(title, message, urgency="normal")

    def notify_research_failed(self, task_id: str, error: str) -> bool:
        """Send notification that research failed.

        Args:
            task_id: The research task ID
            error: Brief error description

        Returns:
            True if notification sent successfully
        """
        title = "Deep Research Failed"
        message = f"Task {task_id[:8]}: {error[:100]}"
        return self.notify(title, message, urgency="critical")


# Singleton instance for easy access
_notifier: Optional[NativeNotifier] = None


def get_notifier() -> NativeNotifier:
    """Get the singleton notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = NativeNotifier()
    return _notifier
