import os
import sys
import json
import psutil
import subprocess
import webview
import ctypes
from devmind.config import (
    load_config, save_config, get_blocklist, add_block, remove_block,
    get_machine_id, verify_license_key, set_license, get_resource_path
)
from devmind.dashboard import get_rank_title

UI_DIR = get_resource_path("ui")
DASHBOARD_HTML = os.path.join(UI_DIR, "dashboard.html")
LOG_PATH = os.path.expanduser("~/.devmind/focus_log.json")

# Focus Mode Global States
_dashboard_window = None
_focus_active = False
_focus_start_time = 0.0
_focus_topic = ""
_focus_blocks_start = 0

# DPI Awareness for crisp fonts
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class DashboardAPI:
    def get_stats(self):
        config = load_config()
        level = config.get("level", 1)
        xp = config.get("xp", 0)
        xp_req = int(100 * (level ** 1.5))
        
        # Resolve daemon status
        daemon_pid = None
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                name = p.info.get('name') or ''
                cmdline = p.info.get('cmdline') or []
                cmdline_lower = [arg.lower() for arg in cmdline]
                
                is_daemon = False
                if name.lower() == 'devmind.exe' and 'daemon' in cmdline_lower:
                    is_daemon = True
                elif 'python' in name.lower() and 'daemon' in cmdline_lower and any('devmind' in arg or 'run_devmind.py' in arg for arg in cmdline_lower):
                    is_daemon = True
                    
                if is_daemon:
                    daemon_pid = p.pid
                    break
            except Exception:
                pass

        stats = {
            "level": level,
            "xp": xp,
            "xp_req": xp_req,
            "rank": get_rank_title(level),
            "blocks_today": config.get("blocks_today", 0),
            "machine_id": get_machine_id(),
            "is_pro": verify_license_key(config.get("license_key", "")),
            "daemon_running": daemon_pid is not None,
            "daemon_pid": daemon_pid,
            "sound_enabled": config.get("sound_enabled", True),
            "lock_settings": config.get("lock_settings", False)
        }
        return json.dumps(stats)

    def toggle_lock_settings(self):
        config = load_config()
        state = not config.get("lock_settings", False)
        config["lock_settings"] = state
        save_config(config)
        return state

    def get_blocklist(self):
        return json.dumps(get_blocklist())

    def add_block(self, keyword):
        return add_block(keyword)

    def remove_block(self, keyword):
        return remove_block(keyword)

    def get_logs(self):
        logs = []
        if os.path.exists(LOG_PATH):
            try:
                with open(LOG_PATH, 'r') as f:
                    logs = json.load(f)
            except Exception:
                pass
        # Only return today's logs, reversed
        import datetime
        today_str = str(datetime.date.today())
        today_logs = [log for log in logs if log.get("date") == today_str]
        return json.dumps(today_logs[::-1])

    def toggle_daemon(self):
        config = load_config()
        daemon_pid = None
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                name = p.info.get('name') or ''
                cmdline = p.info.get('cmdline') or []
                cmdline_lower = [arg.lower() for arg in cmdline]
                
                is_daemon = False
                if name.lower() == 'devmind.exe' and 'daemon' in cmdline_lower:
                    is_daemon = True
                elif 'python' in name.lower() and 'daemon' in cmdline_lower and any('devmind' in arg or 'run_devmind.py' in arg for arg in cmdline_lower):
                    is_daemon = True
                    
                if is_daemon:
                    daemon_pid = p.pid
                    p.kill()
            except Exception:
                pass

        if daemon_pid:
            return False # Daemon stopped

        # Start daemon process detached
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, "daemon"]
        else:
            # Locate active helper
            run_devmind_path = os.path.join(os.path.dirname(__file__), "../run_devmind.py")
            cmd = [sys.executable, run_devmind_path, "daemon"]

        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        
        # Clean PyInstaller environment to prevent child process from locking parent's temp directory
        env = os.environ.copy()
        if "_MEIPASS" in env:
            del env["_MEIPASS"]

        subprocess.Popen(
            cmd,
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            env=env
        )
        return True # Daemon started

    def enter_focus_mode(self, topic):
        global _focus_active, _focus_start_time, _focus_topic, _focus_blocks_start, _dashboard_window
        import time
        _focus_active = True
        _focus_start_time = time.time()
        _focus_topic = topic or "Coding"
        
        config = load_config()
        _focus_blocks_start = config.get("blocks_today", 0)
        
        # Position in bottom-right corner!
        try:
            w_screen = ctypes.windll.user32.GetSystemMetrics(0)
            h_screen = ctypes.windll.user32.GetSystemMetrics(1)
            x = w_screen - 280 - 40
            y = h_screen - 220 - 60
            _dashboard_window.move(x, y)
            _dashboard_window.resize(280, 220)
        except Exception:
            pass
        return True

    def get_focus_state(self):
        global _focus_active, _focus_start_time, _focus_topic, _focus_blocks_start
        import time
        if not _focus_active:
            return json.dumps({"active": False})
        
        config = load_config()
        blocks_now = config.get("blocks_today", 0)
        session_blocks = max(0, blocks_now - _focus_blocks_start)
        elapsed = time.time() - _focus_start_time
        
        return json.dumps({
            "active": True,
            "topic": _focus_topic,
            "elapsed": elapsed,
            "session_blocks": session_blocks
        })

    def exit_focus_mode(self, save=True):
        global _focus_active, _focus_start_time, _focus_topic, _focus_blocks_start, _dashboard_window
        import time
        if not _focus_active:
            return False
            
        elapsed = time.time() - _focus_start_time
        duration_minutes = elapsed / 60.0
        
        config = load_config()
        blocks_now = config.get("blocks_today", 0)
        session_blocks = max(0, blocks_now - _focus_blocks_start)
        
        if save and duration_minutes >= 0.05: # minimum 3 seconds focus to save
            # Add to focus log!
            import datetime
            entry = {
                "date": str(datetime.date.today()),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "topic": _focus_topic,
                "duration_minutes": round(duration_minutes, 2),
                "blocked_count": session_blocks
            }
            
            # Load and write focus logs
            logs = []
            if os.path.exists(LOG_PATH):
                try:
                    with open(LOG_PATH, 'r') as f:
                        logs = json.load(f)
                except Exception:
                    pass
            logs.append(entry)
            try:
                os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
                with open(LOG_PATH, 'w') as f:
                    json.dump(logs, f, indent=4)
            except Exception:
                pass
                
            # Add Focus XP!
            # Give 10 XP per minute focused, minimum 5 XP!
            xp_gain = max(5, int(duration_minutes * 10))
            
            # Handle Leveling system inside config
            xp = config.get("xp", 0) + xp_gain
            level = config.get("level", 1)
            while True:
                req = int(100 * (level ** 1.5))
                if xp >= req:
                    xp -= req
                    level += 1
                else:
                    break
            config["xp"] = xp
            config["level"] = level
            
            # Record total focus minutes
            config["total_focus_minutes"] = config.get("total_focus_minutes", 0) + round(duration_minutes, 2)
            save_config(config)
            
        # Reset states
        _focus_active = False
        
        # Center the window back!
        try:
            w_screen = ctypes.windll.user32.GetSystemMetrics(0)
            h_screen = ctypes.windll.user32.GetSystemMetrics(1)
            x = (w_screen - 980) // 2
            y = (h_screen - 680) // 2
            _dashboard_window.move(x, y)
            _dashboard_window.resize(980, 680)
        except Exception:
            pass
        return True

    def activate_license(self, key):
        return set_license(key)

    def deactivate_license(self):
        config = load_config()
        if "license_key" in config:
            del config["license_key"]
        save_config(config)
        return True

    def toggle_sound(self):
        config = load_config()
        state = not config.get("sound_enabled", True)
        config["sound_enabled"] = state
        save_config(config)
        return state

    def get_focus_history(self):
        import json
        logs = []
        if os.path.exists(LOG_PATH):
            try:
                with open(LOG_PATH, 'r') as f:
                    logs = json.load(f)
            except Exception:
                pass
        return json.dumps(logs)

    def move_window(self, dx, dy):
        global _dashboard_window
        if _dashboard_window:
            try:
                # Direct relative movement using pywebview window handles
                x = _dashboard_window.x + dx
                y = _dashboard_window.y + dy
                _dashboard_window.move(x, y)
            except Exception:
                pass

    def toggle_minimize(self):
        global _dashboard_window
        if _dashboard_window:
            try:
                # If already minimized, restore; otherwise minimize
                if getattr(_dashboard_window, 'visible', True) == False:
                    _dashboard_window.restore()
                else:
                    _dashboard_window.minimize()
            except Exception:
                pass

    def toggle_fullscreen(self):
        global _dashboard_window
        if _dashboard_window:
            try:
                _dashboard_window.toggle_fullscreen()
            except Exception:
                # Fallback for older pywebview versions
                try:
                    if getattr(_dashboard_window, 'fullscreen', False):
                        _dashboard_window.restore()
                    else:
                        _dashboard_window.fullscreen = True
                except Exception:
                    pass

def start_desktop_dashboard():
    global _dashboard_window
    api = DashboardAPI()
    window = webview.create_window(
        title="DevMind Focus Dashboard",
        url=DASHBOARD_HTML,
        width=980,
        height=680,
        resizable=True,
        background_color="#020202",
        js_api=api,
        frameless=True,
        fullscreen=False
    )
    _dashboard_window = window
    webview.start()

if __name__ == "__main__":
    start_desktop_dashboard()
