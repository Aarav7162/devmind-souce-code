import ctypes
import time
import sys
import os
import webview
import psutil
from devmind.config import get_blocklist, can_block, record_block, load_config, save_config, DEVMIND_HOME, get_resource_path

# DPI Awareness for razor-sharp fonts
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def send_ctrl_w():
    """Simulate CTRL+W with robust delays to ensure reliable active tab closure in Windows."""
    import time
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)  # ctrl down
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(0x57, 0, 0, 0)  # w down
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(0x57, 0, 0x0002, 0)  # w up
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(0x11, 0, 0x0002, 0)  # ctrl up

def get_process_name_from_hwnd(hwnd):
    """Retrieve process name from window HWND using high-performance Win32 API calls."""
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == 0:
        return "unknown.exe"
    
    # Open process with query permissions: PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h_process = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid.value)
    if not h_process:
        return "unknown.exe"
    
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = ctypes.c_ulong(1024)
        if ctypes.windll.kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value)
    except Exception:
        pass
    finally:
        ctypes.windll.kernel32.CloseHandle(h_process)
    
    return "unknown.exe"

def get_active_window_info():
    """Return the lower-cased title of the currently foreground window, its HWND, and process name."""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "", 0, "unknown.exe"
        
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    
    # Fast process name retrieval using C-level query instead of slow psutil process instantiation!
    proc_name = get_process_name_from_hwnd(hwnd)
    return buf.value.lower(), hwnd, proc_name

_intercept_window = None

class InterceptAPI:
    def __init__(self, proc_name, site_name, count):
        self.allow = False
        self.proc_name = proc_name
        self.site_name = site_name
        self.count = count

    def get_details(self):
        import json
        return json.dumps({
            "proc": self.proc_name,
            "site": self.site_name,
            "count": self.count
        })

    def close_distraction(self):
        global _intercept_window
        self.allow = False
        if _intercept_window:
            _intercept_window.destroy()

    def allow_session(self):
        global _intercept_window
        self.allow = True
        if _intercept_window:
            _intercept_window.destroy()

def show_interception_screen(proc_name, distraction_name):
    """Shows the stunning, Vercel-like guided breathing screen using PyWebView."""
    global _intercept_window
    record_block(proc_name, distraction_name)
    config = load_config()
    sound_enabled = config.get("sound_enabled", True)
    sound_path = DEVMIND_HOME / "ocean.wav"
    
    # Play procedural ocean sound with 2s fade-in
    if sound_enabled and sound_path.exists():
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(str(sound_path))
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(loops=-1, fade_ms=2000)
        except Exception:
            pass

    # Resolve how many times this distraction was intercepted today
    blocks_today = config.get("blocks_today", 0)

    # Build local path to intercept.html
    ui_dir = get_resource_path("ui")
    intercept_html = os.path.join(ui_dir, "intercept.html")
    
    # Clean URL file format strictly avoiding any query parameters that break local file resolving in WebView2
    url = f"file:///{intercept_html.replace('\\', '/')}"

    # Open full-screen topmost frameless window!
    api = InterceptAPI(proc_name, distraction_name, blocks_today)
    _intercept_window = webview.create_window(
        title="DevMind Focus Takeover",
        url=url,
        fullscreen=True,
        on_top=True,
        background_color="#030305",
        js_api=api
    )
    
    webview.start()

    # Turn off sounds smoothly after close
    if sound_enabled:
        try:
            import pygame
            pygame.mixer.music.fadeout(1500)
            time.sleep(1.6)
            pygame.mixer.quit()
        except Exception:
            pass

    allow = api.allow
    if not allow:
        # Averted distraction! Award Focus XP and compute level up!
        try:
            cfg = load_config()
            xp = cfg.get("xp", 0) + 15
            level = cfg.get("level", 1)
            while True:
                req = int(100 * (level ** 1.5))
                if xp >= req:
                    xp -= req
                    level += 1
                else:
                    break
            cfg["xp"] = xp
            cfg["level"] = level
            save_config(cfg)
        except Exception:
            pass

    return allow

def main():
    if sys.platform != "win32":
        return

    while True:
        # Check 5-minute grace period cooldown
        config = load_config()
        grace_until = config.get("grace_until", 0.0)
        if time.time() < grace_until:
            time.sleep(2)
            continue

        title, hwnd, proc_name = get_active_window_info()
        distractions = get_blocklist()
        
        if title:
            matched_distraction = None
            for d in distractions:
                if d.lower() in title:
                    matched_distraction = d
                    break
            
            # Also scan blocked apps explicitly
            # We can treat keywords ending in .exe as apps
            for d in distractions:
                if d.lower().endswith(".exe") and d.lower() == proc_name.lower():
                    matched_distraction = d
                    break

            if matched_distraction:
                if can_block():
                    # Launch screen!
                    allow = show_interception_screen(proc_name, matched_distraction)
                    
                    if allow:
                        # Write 5-minute grace period to config
                        config = load_config()
                        config["grace_until"] = time.time() + 300.0 # 5 minutes grace
                        save_config(config)
                    else:
                        # Bring browser to front and send close tab
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                        time.sleep(0.3)
                        
                        # Close the window/tab
                        if matched_distraction.lower().endswith(".exe"):
                            # Terminate process if it's a blocked app
                            try:
                                for p in psutil.process_iter(['name']):
                                    if p.info['name'].lower() == proc_name.lower():
                                        p.terminate()
                            except Exception:
                                pass
                        else:
                            send_ctrl_w()
                            
                    time.sleep(5)  # Cooldown before checking again
                else:
                    time.sleep(10)
                    
        time.sleep(0.5)

if __name__ == "__main__":
    main()
