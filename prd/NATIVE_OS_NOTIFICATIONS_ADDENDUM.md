# Native OS Notifications Addendum
## PRD Update: Desktop Notifications Instead of External Services

**Version:** 1.1  
**Date:** December 14, 2025  
**Status:** Ready for Implementation  
**Supersedes:** Notification System section in main PRD

---

## Executive Summary

Based on multi-hop research using Gemini tools, we're **replacing external notification services** (webhooks, email, Discord, Slack, Telegram) with **native OS desktop notifications** for a better developer experience.

### Why This Change?

**Before (External Services):**
- ❌ Requires webhook URLs setup
- ❌ Requires email SMTP configuration
- ❌ Requires Discord/Slack integration
- ❌ Developer must check external app
- ❌ Doesn't work offline

**After (Native OS):**
- ✅ Zero configuration needed
- ✅ Notification appears on developer's screen
- ✅ Works across Linux, macOS, Windows
- ✅ Works offline
- ✅ Native look and feel
- ✅ Perfect for developer tools

---

## Research Findings

### From Gemini Research (December 14, 2025)

**Best Cross-Platform Python Libraries:**

#### 1. **notifypy** ⭐ RECOMMENDED
- **Lightweight**: Minimal dependencies
- **Cross-platform**: Linux, macOS, Windows
- **Thread-safe**: Works with Celery workers
- **Icon support**: Can show custom icons
- **Simple API**: Easy integration
- **Active development**: Well-maintained

#### 2. **plyer** (Backup)
- **Established**: Widely used
- **Cross-platform abstraction**: Hides platform differences
- **More dependencies**: May require platform-specific packages
- **Older**: Less active development

#### 3. **desktop-notifier** (Advanced)
- **Modern**: Latest features
- **Clickable**: Supports callback actions
- **Multiple buttons**: Action buttons
- **Reply field**: User can respond
- **Requires event loop**: More complex

### From Gemini Brainstorm (December 14, 2025)

**Key Recommendations:**

1. **Start with notifypy** - Best balance of simplicity and features
2. **Graceful fallback** - If notifypy fails, try plyer, then command-line
3. **Icon embedding** - Bundle icon with package
4. **Thread-safe execution** - Works with Celery workers
5. **Error handling** - Fallback to console print if all fail

---

## Updated Architecture

### Notification Flow (Native OS):

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User starts Deep Research                                │
│    - Query: "Complex research question..."                  │
│    - Runs in background via Celery                          │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. Research runs for 20+ minutes                            │
│    - User continues working on other tasks                   │
│    - Progress saved in Redis                                 │
└──────────────────────┬───────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. Research completes                                        │
│    - Celery worker saves results                             │
│    - Triggers notification                                   │
└──────────────────────┬───────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. Native OS Notification (notifypy)                        │
│    - Shows on developer's screen                             │
│    - Works on Linux/macOS/Windows                            │
│    - No external service needed                              │
└──────────────────────┬───────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. Developer sees notification                               │
│    - "🔬 Gemini Deep Research Complete!"                     │
│    - "Task abc-123 finished. Click to view results."         │
│    - Native OS notification center/tray                      │
└──────────────────────────────────────────────────────────────┘
```

---

## Updated Tool Specifications

### Tool 1: `start_deep_research` (Modified)

**Parameters SIMPLIFIED:**

```python
@mcp.tool()
async def start_deep_research(
    query: str,
    enable_notifications: bool = True,  # SIMPLIFIED!
    max_wait_hours: int = 3,
    enable_multi_hop: bool = False
) -> Dict[str, Any]:
```

**Removed Parameters:**
- ❌ `notification_type` (no longer needed)
- ❌ `notification_config` (no longer needed)

**New Behavior:**
- If `enable_notifications=True`: Show native OS notification when complete
- If `enable_notifications=False`: Silent mode (no notification)

---

## Implementation Specification

### Dependencies

**Add to `requirements.txt`:**
```txt
# Native OS Notifications
notify-py>=0.3.42        # Primary notification library
plyer>=2.1.0            # Fallback notification library
```

### Notification Module

**File:** `deep_research/notification.py`

```python
"""
Native OS Desktop Notification System
Supports: Linux, macOS, Windows
"""

import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class NativeNotifier:
    """
    Cross-platform native OS notification manager
    Uses notifypy as primary, plyer as fallback
    """
    
    def __init__(self, app_name: str = "Gemini Deep Research"):
        self.app_name = app_name
        self.icon_path = self._get_icon_path()
        self._notifier = None
        self._initialize()
    
    def _initialize(self):
        """Initialize notification library (try notifypy first)"""
        # Try notifypy (primary)
        try:
            from notifypy import Notify
            self._notifier = "notifypy"
            logger.info("Using notifypy for notifications")
            return
        except ImportError:
            logger.warning("notifypy not available, trying plyer...")
        
        # Try plyer (fallback)
        try:
            from plyer import notification
            self._notifier = "plyer"
            logger.info("Using plyer for notifications")
            return
        except ImportError:
            logger.warning("plyer not available, trying command-line...")
        
        # Try command-line (last resort)
        self._notifier = "cli"
        logger.info("Using command-line for notifications")
    
    def send(
        self,
        title: str,
        message: str,
        icon: Optional[str] = None,
        timeout: int = 10
    ) -> bool:
        """
        Send native OS notification
        
        Args:
            title: Notification title
            message: Notification message
            icon: Path to icon (optional)
            timeout: Display duration in seconds
        
        Returns:
            True if notification sent successfully
        """
        try:
            if self._notifier == "notifypy":
                return self._send_notifypy(title, message, icon, timeout)
            elif self._notifier == "plyer":
                return self._send_plyer(title, message, icon, timeout)
            elif self._notifier == "cli":
                return self._send_cli(title, message)
            else:
                # Fallback to console
                logger.warning(f"No notification system available")
                print(f"\n{'='*60}")
                print(f"🔔 {title}")
                print(f"{message}")
                print(f"{'='*60}\n")
                return False
        
        except Exception as e:
            logger.error(f"Notification failed: {e}")
            # Fallback to console
            print(f"\n🔔 {title}: {message}\n")
            return False
    
    def _send_notifypy(self, title: str, message: str, icon: Optional[str], timeout: int) -> bool:
        """Send notification using notifypy"""
        from notifypy import Notify
        
        notification = Notify()
        notification.application_name = self.app_name
        notification.title = title
        notification.message = message
        
        if icon or self.icon_path:
            notification.icon = icon or self.icon_path
        
        notification.send()
        logger.info(f"Notification sent: {title}")
        return True
    
    def _send_plyer(self, title: str, message: str, icon: Optional[str], timeout: int) -> bool:
        """Send notification using plyer"""
        from plyer import notification
        
        notification.notify(
            title=title,
            message=message,
            app_name=self.app_name,
            app_icon=icon or self.icon_path or '',
            timeout=timeout
        )
        logger.info(f"Notification sent: {title}")
        return True
    
    def _send_cli(self, title: str, message: str) -> bool:
        """Send notification using command-line tools"""
        import subprocess
        import sys
        
        try:
            if sys.platform == "linux" or sys.platform == "linux2":
                # Linux: notify-send
                subprocess.run([
                    'notify-send',
                    title,
                    message,
                    '--app-name', self.app_name,
                    '--icon', 'dialog-information'
                ], check=True)
                return True
            
            elif sys.platform == "darwin":
                # macOS: osascript
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(['osascript', '-e', script], check=True)
                return True
            
            elif sys.platform == "win32":
                # Windows: PowerShell
                ps_script = f"""
                Add-Type -AssemblyName System.Windows.Forms
                $notification = New-Object System.Windows.Forms.NotifyIcon
                $notification.Icon = [System.Drawing.SystemIcons]::Information
                $notification.BalloonTipTitle = '{title}'
                $notification.BalloonTipText = '{message}'
                $notification.Visible = $true
                $notification.ShowBalloonTip(10000)
                """
                subprocess.run(['powershell', '-Command', ps_script], check=True)
                return True
            
        except Exception as e:
            logger.error(f"CLI notification failed: {e}")
            return False
    
    def _get_icon_path(self) -> Optional[str]:
        """Get path to notification icon"""
        # Look for icon in package
        icon_locations = [
            Path(__file__).parent / "assets" / "icon.png",
            Path(__file__).parent.parent / "assets" / "icon.png",
        ]
        
        for icon in icon_locations:
            if icon.exists():
                return str(icon)
        
        return None


# Global notifier instance
_notifier = NativeNotifier()


def notify_completion(task_id: str, duration_minutes: float, cost_usd: float):
    """
    Send notification when Deep Research completes
    
    Args:
        task_id: Task ID
        duration_minutes: Research duration
        cost_usd: Total cost
    """
    title = "🔬 Gemini Deep Research Complete!"
    message = f"""
Task: {task_id[:8]}...
Duration: {duration_minutes:.1f} minutes
Cost: ${cost_usd:.2f}

Click to view results.
    """.strip()
    
    _notifier.send(title=title, message=message)


def notify_error(task_id: str, error_message: str):
    """
    Send notification when Deep Research fails
    
    Args:
        task_id: Task ID
        error_message: Error description
    """
    title = "❌ Gemini Deep Research Failed"
    message = f"""
Task: {task_id[:8]}...
Error: {error_message}

Check logs for details.
    """.strip()
    
    _notifier.send(title=title, message=message)


def notify_timeout(task_id: str, max_hours: int):
    """
    Send notification when Deep Research times out
    
    Args:
        task_id: Task ID
        max_hours: Maximum wait time
    """
    title = "⏰ Gemini Deep Research Timeout"
    message = f"""
Task: {task_id[:8]}...
Exceeded maximum wait time of {max_hours} hours.

Partial results may be available.
    """.strip()
    
    _notifier.send(title=title, message=message)
```

---

## Updated Celery Worker

**File:** `deep_research/worker.py`

```python
from celery import Celery
from .notification import notify_completion, notify_error, notify_timeout

app = Celery('deep_research', broker='redis://localhost:6379/0')


@app.task
def continue_deep_research(task_id: str, state: dict, enable_notifications: bool = True):
    """
    Continue Deep Research in background and send native OS notification
    """
    from .engine import DeepResearchEngine
    from .state_manager import StateManager
    
    state_manager = StateManager()
    
    try:
        # Restore and continue
        engine = DeepResearchEngine.from_state(state)
        results = engine.continue_execution()
        
        # Save results
        state_manager.save_result(task_id, results)
        state_manager.update_status(task_id, "completed")
        
        # Send NATIVE OS notification
        if enable_notifications:
            notify_completion(
                task_id=task_id,
                duration_minutes=results["metadata"]["duration_minutes"],
                cost_usd=results["metadata"]["cost_usd"]
            )
        
        return {"status": "completed", "task_id": task_id}
    
    except TimeoutError:
        # Timeout notification
        state_manager.update_status(task_id, "timeout")
        
        if enable_notifications:
            notify_timeout(task_id, state.get("max_wait_hours", 3))
        
        return {"status": "timeout", "task_id": task_id}
    
    except Exception as e:
        # Error notification
        state_manager.update_status(task_id, "failed")
        state_manager.save_error(task_id, str(e))
        
        if enable_notifications:
            notify_error(task_id, str(e))
        
        return {"status": "failed", "task_id": task_id, "error": str(e)}
```

---

## Updated Usage Examples

### Example 1: Research with Native Notifications (Default)

```python
# Start research
result = await start_deep_research(
    query="Comprehensive quantum computing analysis 2024-2025...",
    enable_notifications=True  # Native OS notification when done
)

# Returns immediately:
{
    "task_id": "abc-123",
    "status": "running_async",
    "message": "Research running in background. Native notification will appear when complete."
}

# 20 minutes later...
# Native OS notification appears on screen:
# ┌─────────────────────────────────────────┐
# │ 🔬 Gemini Deep Research Complete!       │
# │                                         │
# │ Task: abc-123...                        │
# │ Duration: 18.5 minutes                  │
# │ Cost: $3.24                             │
# │                                         │
# │ Click to view results.                  │
# └─────────────────────────────────────────┘
```

### Example 2: Silent Mode (No Notifications)

```python
# For automated scripts
result = await start_deep_research(
    query="Research question...",
    enable_notifications=False  # Silent mode
)

# No notification will appear
# Check status manually with check_research_status()
```

### Example 3: Multiple Platforms

**Linux (Ubuntu/Fedora):**
```
Notification appears via notify-send:
┌─────────────────────────────────┐
│ 🔬 Gemini Deep Research Complete! │
│ Task: abc-123...                │
│ Duration: 18.5 minutes          │
│ Cost: $3.24                     │
└─────────────────────────────────┘
```

**macOS:**
```
Notification appears in Notification Center:
┌─────────────────────────────────┐
│ Gemini Deep Research           │
│ 🔬 Deep Research Complete!      │
│                                 │
│ Task: abc-123...                │
│ Duration: 18.5 minutes          │
│ Cost: $3.24                     │
└─────────────────────────────────┘
```

**Windows 10/11:**
```
Toast notification appears:
┌─────────────────────────────────┐
│ 🔬 Gemini Deep Research         │
│                                 │
│ Deep Research Complete!         │
│ Task: abc-123...                │
│ Duration: 18.5 minutes          │
│ Cost: $3.24                     │
└─────────────────────────────────┘
```

---

## Platform-Specific Notes

### Linux
**Requirements:**
- `notify-send` (usually pre-installed)
- Or `libnotify-bin` package

**Install if needed:**
```bash
# Ubuntu/Debian
sudo apt-get install libnotify-bin

# Fedora
sudo dnf install libnotify

# Arch
sudo pacman -S libnotify
```

### macOS
**Requirements:**
- Built-in Notification Center (10.8+)
- No additional installation needed

**Permissions:**
- Terminal/Python may ask for notification permission
- Grant in System Preferences → Notifications

### Windows
**Requirements:**
- Windows 10 or newer
- Toast notifications built-in

**Permissions:**
- First notification may ask for permission
- Grant in Settings → System → Notifications

---

## Fallback Strategy

If all notification systems fail:

```python
# Graceful degradation:
1. Try notifypy
   ↓ (fails)
2. Try plyer
   ↓ (fails)
3. Try command-line (notify-send/osascript/PowerShell)
   ↓ (fails)
4. Print to console
   ========================================
   🔔 Gemini Deep Research Complete!
   Task: abc-123
   Duration: 18.5 minutes
   Cost: $3.24
   ========================================
```

---

## Testing Checklist

### Manual Testing:

```bash
# Test notification on your OS
python -c "from deep_research.notification import notify_completion; notify_completion('test-123', 5.5, 1.25)"

# Should see native OS notification:
# "🔬 Gemini Deep Research Complete!"
```

### Platform Testing:

- [ ] Test on Linux (Ubuntu/Fedora)
- [ ] Test on macOS (10.8+)
- [ ] Test on Windows (10/11)
- [ ] Test fallback to console if no library available
- [ ] Test notification appears during background task
- [ ] Test notification with Celery worker

---

## Advantages Over External Services

| Feature | External Services | Native OS Notifications |
|---------|------------------|------------------------|
| **Setup** | Requires configuration | Zero configuration |
| **Offline** | ❌ Requires internet | ✅ Works offline |
| **Privacy** | ❌ Data sent to external servers | ✅ Stays on local machine |
| **Speed** | Depends on network | ⚡ Instant |
| **Reliability** | Depends on service uptime | ✅ Always available |
| **Cost** | May require paid plans | ✅ Free |
| **Developer UX** | Must check external app | ✅ Appears on screen |
| **Dependencies** | Multiple APIs/webhooks | Single Python library |

---

## Migration Guide

### For Existing Code:

**Old (External Services):**
```python
await start_deep_research(
    query="...",
    notification_type="discord",
    notification_config={"webhook_url": "https://..."}
)
```

**New (Native OS):**
```python
await start_deep_research(
    query="...",
    enable_notifications=True  # Much simpler!
)
```

### For Power Users:

If you still want external services (webhook, email, etc.), you can:

1. **Use native notifications as primary**
2. **Add webhook as optional secondary notification**

```python
# Optional: Add webhook support alongside native notifications
await start_deep_research(
    query="...",
    enable_notifications=True,  # Native OS notification
    webhook_url="https://..."   # Optional: Also send to webhook
)
```

---

## Success Metrics (Updated)

### Technical:
- ✅ Notification appears < 2 seconds after completion
- ✅ 99%+ delivery rate across platforms
- ✅ < 1% fallback to console
- ✅ Works with Celery background workers

### User Experience:
- ✅ Zero configuration required
- ✅ Native look and feel per OS
- ✅ Works offline
- ✅ Developer sees notification immediately

---

## Implementation Priority

### Phase 1: Core Notification (Week 1)
- [ ] Install notifypy library
- [ ] Create `notification.py` module
- [ ] Implement `NativeNotifier` class
- [ ] Test on all 3 platforms

### Phase 2: Integration (Week 1-2)
- [ ] Update `start_deep_research` parameters
- [ ] Integrate with Celery worker
- [ ] Remove external service code
- [ ] Update documentation

### Phase 3: Polish (Week 2)
- [ ] Add custom icon
- [ ] Implement fallback strategy
- [ ] Add notification tests
- [ ] Update README

---

## Appendix: Research Sources

### Gemini Research Results
**Date:** December 14, 2025  
**Tool:** `mcp_gemini-mcp_gemini_research`

**Key Findings:**
- notifypy: Best lightweight cross-platform library
- plyer: Good fallback with more features
- desktop-notifier: Advanced features but requires event loop
- Platform-specific: Last resort

**Full research findings:** See research output above

### Gemini Brainstorm Results
**Date:** December 14, 2025  
**Tool:** `mcp_gemini-mcp_gemini_brainstorm`

**Key Recommendations:**
1. Start with notifypy (best balance)
2. Implement graceful fallbacks
3. Bundle icon with package
4. Ensure thread-safety for Celery
5. Handle all error cases

**Full brainstorm session:** See brainstorm output above

---

## Questions & Answers

**Q: Why not use Discord/Slack/Email?**  
A: Native OS notifications are simpler, faster, and work offline. Perfect for developer tools.

**Q: What if notifypy isn't available?**  
A: Automatic fallback: notifypy → plyer → CLI → console

**Q: Will this work on WSL (Windows Subsystem for Linux)?**  
A: Yes, if you have X server running. Otherwise, fallback to console.

**Q: Can I still use webhooks if needed?**  
A: Yes, you can add optional webhook support alongside native notifications.

**Q: Does this require any system permissions?**  
A: First time may ask for notification permission. User grants once.

---

**Status:** ✅ Ready for Implementation  
**Replaces:** External notification services in main PRD  
**Approval:** Recommended by Gemini multi-hop research

---

**END OF ADDENDUM**

