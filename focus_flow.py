import time
import datetime
import os
import sys
import ctypes
import json
import psutil
import msvcrt
import random
import math

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.align import Align
    from rich.text import Text
    from rich import box
    from rich.style import Style
except ImportError:
    print("Error: 'rich' library is required. Install with: pip install rich")
    sys.exit(1)

# Ensure devmind is available for the beautiful fullscreen breathing overlay
try:
    from devmind.tracker import get_active_window_info, show_interception_screen
    from devmind.config import ensure_sound_file
except ImportError:
    print("Error: 'devmind' package is required. Install with: pip install -e .")
    sys.exit(1)

# --- Constants & Paths ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
LOG_PATH = os.path.join(os.path.dirname(__file__), "focus_log.json")
NOTES_PATH = os.path.join(os.path.dirname(__file__), "session_notes.txt")

console = Console()

# --- Data Management ---
def load_config():
    ensure_sound_file() # Ensure procedural ocean sound file exists
    if not os.path.exists(CONFIG_PATH):
        default_config = {
            "blocked_keywords": ["youtube", "facebook", "twitter", "reddit"],
            "blocked_apps": ["Spotify.exe", "Discord.exe"],
            "override_key": "focusnow",
            "xp": 0, "level": 1, "total_focus_minutes": 0.0,
            "sound_enabled": True
        }
        save_config(default_config)
        return default_config
    try:
        with open(CONFIG_PATH, 'r') as f:
            c = json.load(f)
            if "xp" not in c: c["xp"] = 0
            if "level" not in c: c["level"] = 1
            if "total_focus_minutes" not in c: c["total_focus_minutes"] = 0.0
            if "sound_enabled" not in c: c["sound_enabled"] = True
            return c
    except json.JSONDecodeError: return load_config()

def save_config(config):
    with open(CONFIG_PATH, 'w') as f: json.dump(config, f, indent=4)

def log_session(topic, duration_minutes, blocked_count):
    entry = {
        "date": str(datetime.date.today()), "timestamp": str(datetime.datetime.now()),
        "topic": topic, "duration_minutes": round(duration_minutes, 2), "blocked_count": blocked_count
    }
    data = []
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, 'r') as f: data = json.load(f)
        except: pass
    data.append(entry)
    with open(LOG_PATH, 'w') as f: json.dump(data, f, indent=4)

def get_daily_stats():
    if not os.path.exists(LOG_PATH): return {}, 0
    today = str(datetime.date.today())
    stats = {}; total = 0
    try:
        with open(LOG_PATH, 'r') as f:
            for e in json.load(f):
                if e.get("date") == today:
                    t = e.get("topic", "Unknown"); d = e.get("duration_minutes", 0)
                    stats[t] = stats.get(t, 0) + d; total += d
    except: pass
    return stats, total

# --- Gamification ---
def calculate_xp_gain(minutes, blocked_count): return max(0, int((minutes * 10) - (blocked_count * 5)))
def check_level_up(xp, lvl): req = int(100 * (lvl ** 1.5)); return (xp >= req), req

def get_rank_title(level):
    if level < 5: return "NOVICE"
    if level < 10: return "APPRENTICE"
    if level < 20: return "FOCUS ADEPT"
    if level < 30: return "DISCIPLINE MASTER"
    if level < 50: return "TIME LORD"
    return "GODLIKE"

def sync_xp_from_history():
    """Calculates total XP from log file and updates config."""
    if not os.path.exists(LOG_PATH): return 0, 0
    total_mins = 0
    total_xp = 0
    
    try:
        with open(LOG_PATH, 'r') as f:
            data = json.load(f)
            for entry in data:
                dur = entry.get("duration_minutes", 0)
                blocked = entry.get("blocked_count", 0)
                total_mins += dur
                total_xp += calculate_xp_gain(dur, blocked)
    except: return 0, 0
    
    level = 1
    remaining_xp = total_xp
    
    while True:
        req = int(100 * (level ** 1.5))
        if remaining_xp >= req:
            remaining_xp -= req
            level += 1
        else:
            break
            
    config = load_config()
    config['xp'] = int(remaining_xp)
    config['level'] = level
    config['total_focus_minutes'] = total_mins
    save_config(config)
    
    return total_xp, level

# --- Blocking ---
def send_ctrl_w():
    ctypes.windll.user32.keybd_event(0x11, 0, 0, 0); ctypes.windll.user32.keybd_event(0x57, 0, 0, 0)
    ctypes.windll.user32.keybd_event(0x57, 0, 0x0002, 0); ctypes.windll.user32.keybd_event(0x11, 0, 0x0002, 0)

def scan_and_close_windows(blocked_keywords, sound_enabled=True):
    user32 = ctypes.windll.user32
    fg = user32.GetForegroundWindow()
    l = user32.GetWindowTextLengthW(fg); buff = ctypes.create_unicode_buffer(l + 1)
    user32.GetWindowTextW(fg, buff, l + 1); title = buff.value.lower()
    if title:
        for k in blocked_keywords:
            if k in title:
                if sound_enabled: print("\a")
                send_ctrl_w(); return k
    return None

def kill_processes(blocked_apps):
    for p in psutil.process_iter(['name']):
        try:
            if p.info['name'] in blocked_apps: p.terminate(); return p.info['name']
        except: pass
    return None

# --- UI Components (Premium Monochrome Style) ---
def make_layout(zen_mode=False):
    layout = Layout(name="root")
    if zen_mode:
        layout.split_column(Layout(name="header", size=3), Layout(name="main_col", ratio=1), Layout(name="cmd_line", size=3))
    else:
        layout.split_column(Layout(name="header", size=3), Layout(name="body", ratio=1), Layout(name="footer", size=8), Layout(name="cmd_line", size=3))
        layout["body"].split_row(Layout(name="system_col", ratio=1), Layout(name="main_col", ratio=3))
    return layout

def get_sparkline(data, color="white"):
    bars = u"  ▂▃▄▅▆▇█"
    line = ""
    for val in data:
        idx = int((val / 100) * (len(bars) - 1))
        line += f"[{color}]{bars[idx]}[/]"
    return line

def get_system_panel(cpu_history, ram_history):
    grid = Table.grid(expand=True)
    grid.add_column(justify="left"); grid.add_column(justify="right")
    
    cpu_spark = get_sparkline(cpu_history, "white")
    ram_spark = get_sparkline(ram_history, "white")
    
    grid.add_row("[bold white]CPU[/]", f"{cpu_history[-1]:.1f}% {cpu_spark}")
    grid.add_row("[bold white]RAM[/]", f"{ram_history[-1]:.1f}% {ram_spark}")
    grid.add_row("")
    
    net = psutil.net_io_counters()
    grid.add_row("[bold white]UP[/]", f"{net.bytes_sent // 1024 // 1024} MB")
    grid.add_row("[bold white]DOWN[/]", f"{net.bytes_recv // 1024 // 1024} MB")
    
    return Panel(grid, title="[bold white]SYS.MON[/]", border_style="white", box=box.ROUNDED)

def get_log_panel(events):
    text = "\n".join(events[-7:])
    return Panel(text, title="[bold white]SEC.LOG[/]", border_style="white", box=box.SQUARE)

def get_cmd_panel(cmd_buffer):
    return Panel(f"[bold white]USER@DEVMIND > [/][white]{cmd_buffer}[/][blink]_[/]", border_style="white", box=box.HEAVY_EDGE)

# --- Session Runner ---
def run_session():
    console.clear()
    config = load_config()
    rank = get_rank_title(config['level'])
    
    console.print(Panel(f"[bold white]INITIALIZING DEVMIND OS v8.2[/]\n[dim]OPERATOR: {rank} (LVL {config['level']})[/]", border_style="white"))
    topic = console.input("[white]ENTER MISSION OBJECTIVE: [/]").strip() or "General"
    
    progress = Progress(
        SpinnerColumn(), BarColumn(bar_width=None, complete_style="white", finished_style="white", pulse_style="white"),
        TextColumn("[white]{task.fields[status]}[/]"), expand=True
    )
    task_id = progress.add_task("mission", total=None, status="ACTIVE")
    
    layout = make_layout(zen_mode=False)
    cpu_hist = [0] * 20; ram_hist = [0] * 20
    events = [f"[dim]{datetime.datetime.now().strftime('%H:%M:%S')} >> SEQUENCE STARTED[/]"]
    
    start_time = datetime.datetime.now()
    cmd_buffer = ""
    sound_enabled = True; paused = False; zen_enabled = False
    pause_start_time = None; total_pause_duration = datetime.timedelta(0)
    blocked_count = 0; alert_trigger_time = 0
    should_exit = False; save_session = False
    
    with Live(layout, refresh_per_second=10, screen=True) as live:
        while not should_exit:
            current_time = datetime.datetime.now()
            
            if paused:
                if pause_start_time is None: pause_start_time = current_time
                progress.update(task_id, status="[white]PAUSED[/]")
                elapsed = (pause_start_time - start_time) - total_pause_duration
            else:
                if pause_start_time is not None:
                     total_pause_duration += (current_time - pause_start_time)
                     pause_start_time = None
                progress.update(task_id, status="[white]ACTIVE[/]", advance=0.1)
                elapsed = (current_time - start_time) - total_pause_duration
            
            elapsed_str = str(elapsed).split('.')[0]

            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char == '\r':
                    cmd = cmd_buffer.strip(); cmd_buffer = ""
                    events.append(f"[dim]CMD > {cmd}[/]")
                    parts = cmd.split(); base = parts[0].lower() if parts else ""; args = parts[1:] if len(parts)>1 else []
                    
                    if base in ["stop", "exit"]: should_exit=True; save_session=True
                    elif base == "abort": should_exit=True; save_session=False
                    elif base == "pause": paused=True; events.append("[white]>> PAUSED[/]")
                    elif base == "resume": paused=False; events.append("[white]>> RESUMED[/]")
                    elif base == "zen": 
                        zen_enabled = not zen_enabled
                        layout = make_layout(zen_mode=zen_enabled)
                        live.update(layout)
                    elif base == "topic": 
                        if args: topic = " ".join(args); events.append(f"[white]>> NEW TOPIC: {topic}[/]")
                    elif base == "add":
                         if args and args[0] not in config['blocked_keywords']:
                             config['blocked_keywords'].append(args[0]); save_config(config); events.append(f"[white]>> ADDED BLOCK: {args[0]}[/]")
                    elif base == "del":
                         if args and args[0] in config['blocked_keywords']:
                             config['blocked_keywords'].remove(args[0]); save_config(config); events.append(f"[white]>> REMOVED BLOCK: {args[0]}[/]")
                    elif base == "list": events.append(f"[dim]BLOCKS: {', '.join(config['blocked_keywords'][:5])}...[/]")
                    elif base == "apps": events.append(f"[dim]APPS: {', '.join(config['blocked_apps'][:5])}...[/]")
                    elif base == "mute": sound_enabled=False; events.append("[dim]>> MUTED[/]")
                    elif base == "unmute": sound_enabled=True; events.append("[dim]>> UNMUTED[/]")
                    elif base == "kill": 
                         if args:
                             tgt=args[0]; c=0
                             for p in psutil.process_iter(['name']):
                                 if tgt.lower() in p.info['name'].lower():
                                     try: p.terminate(); c+=1
                                     except: pass
                             events.append(f"[white]>> KILLED {c}[/]")
                    elif base == "top": 
                        procs = sorted([(p.info['name'], p.info['cpu_percent']) for p in psutil.process_iter(['name', 'cpu_percent'])], key=lambda x: x[1], reverse=True)
                        if procs: events.append(f"[white]>> TOP: {procs[0][0]} ({procs[0][1]}%)[/]")
                    elif base == "rank": events.append(f"[white]>> RANK: {rank} (LVL {config['level']})[/]")
                    elif base == "xp": events.append(f"[white]>> XP: {config['xp']}[/]")
                    elif base == "note":
                        if args:
                             try:
                                 with open(NOTES_PATH, "a") as f: f.write(f"[{datetime.datetime.now()}] {topic}: {' '.join(args)}\n")
                                 events.append("[white]>> NOTE SAVED[/]")
                             except: events.append("[white]>> ERROR[/]")
                    elif base == "calc":
                        if args:
                             try: res = eval(" ".join(args), {"__builtins__": None}, {}); events.append(f"[white]>> RES: {res}[/]")
                             except: events.append("[white]>> ERR[/]")
                    elif base == "cpu": events.append(f"[dim]>> CPU: {psutil.cpu_percent()}%[/]")
                    elif base == "ram": events.append(f"[dim]>> RAM: {psutil.virtual_memory().percent}%[/]")
                    elif base == "minimize":
                        try: ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6)
                        except: pass
                    elif base == "clear": events = []
                    elif base == "help": events.append("[dim]stop, abort, pause, resume, zen, topic, add, del, list, apps, mute, kill, top, rank, note, calc, minimize, clear[/]")
                elif char == '\b': cmd_buffer = cmd_buffer[:-1]
                elif char == '\x03': should_exit=True; save_session=False 
                elif char.isprintable(): cmd_buffer += char

            cpu_hist.append(psutil.cpu_percent()); ram_hist.append(psutil.virtual_memory().percent)
            cpu_hist = cpu_hist[-20:]; ram_hist = ram_hist[-20:]
            
            border_col = "white"
            if not paused:
                # Upgraded visual breathing takeover matching Photo 2!
                if blocked_site := scan_and_close_windows(config['blocked_keywords'], sound_enabled):
                    events.append(f"[bold white]{current_time.strftime('%H:%M:%S')} >> BLOCKED: {blocked_site.upper()}[/]")
                    blocked_count += 1; alert_trigger_time = time.time()
                    
                    # Pop up the fullscreen breathing screen takeover
                    _, _, proc_name = get_active_window_info()
                    live.stop()
                    show_interception_screen(proc_name, blocked_site)
                    live.start()
                    
                if blocked_app := kill_processes(config['blocked_apps']):
                    events.append(f"[bold white]{current_time.strftime('%H:%M:%S')} >> KILLED: {blocked_app.upper()}[/]")
                    blocked_count += 1; alert_trigger_time = time.time()
                    
                    live.stop()
                    show_interception_screen(blocked_app, blocked_app)
                    live.start()
                    
            if time.time() - alert_trigger_time < 1.0: border_col = "white blink"

            time_str = current_time.strftime("%H:%M:%S")
            layout["header"].update(Panel(Align.center(f"[bold white]DEVMIND OS v8.2   |   {time_str}   |   CMD READY[/]"), style="on black"))
            
            if not zen_enabled:
                layout["system_col"].update(get_system_panel(cpu_hist, ram_hist))
                layout["footer"].update(get_log_panel(events))
            
            state_text = "[white]PAUSED[/]" if paused else "[white]RUNNING[/]"
            main_content = Align.center(f"\n[bold]{topic.upper()}[/]\n\n[bold white size=40]{elapsed_str}[/]\n\n[dim]{state_text}[/]", vertical="middle")
            layout["main_col"].update(Panel(main_content, title="[bold white]MISSION CONTROL[/]", border_style=border_col))
            layout["cmd_line"].update(get_cmd_panel(cmd_buffer))
            
            time.sleep(0.05)

    console.clear()
    final_mins = elapsed.total_seconds() / 60
    if save_session:
        xp_gain = calculate_xp_gain(final_mins, blocked_count)
        config['xp'] += xp_gain; config['total_focus_minutes'] += final_mins
        leveled, xp_req = check_level_up(config['xp'], config['level'])
        if leveled: config['level'] += 1; config['xp'] -= xp_req
        save_config(config); log_session(topic, final_mins, blocked_count)
        
        grid = Table.grid(expand=True); grid.add_column(justify="center")
        grid.add_row("[bold white size=20]MISSION ACCOMPLISHED[/]")
        grid.add_row(f"[white]TOPIC: {topic}[/]"); grid.add_row(f"[white]DURATION: {final_mins:.2f} min[/]")
        grid.add_row(""); grid.add_row(f"[bold white size=16]+{xp_gain} XP[/]")
        if leveled: grid.add_row("[bold white blink]*** LEVEL UP! ***[/]"); grid.add_row(f"[white]NEW RANK: {get_rank_title(config['level'])} (LVL {config['level']})[/]")
        grid.add_row(""); grid.add_row(f"[white]DISTRACTIONS NEUTRALIZED: {blocked_count}[/]")
        console.print(Panel(grid, border_style="white", padding=(2, 4)))
    else:
        console.print(f"\n[bold white]MISSION ABORTED.[/]"); console.print(f"[dim]Data Discarded.[/]")
    time.sleep(4); console.input("Press Enter...")

# --- Menus ---
def get_main_menu_panel():
    config = load_config()
    rank = get_rank_title(config['level'])
    xp_req = int(100 * (config['level'] ** 1.5))
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Key", style="white bold"); table.add_column("Action", style="white")
    table.add_row("[1]", "START SESSION"); table.add_row("[2]", "VIEW STATS"); table.add_row("[3]", "SETTINGS"); table.add_row("[4]", "EXIT")
    table.add_row("", ""); table.add_row("[5]", "SYNC XP (HISTORY)")
    stat_block = f"\n[bold white]{rank}[/] (LVL {config['level']})\n[dim]XP: {config['xp']} / {xp_req}[/]"
    return Panel(Align.center(table, vertical="middle"), title="[bold white]DEVMIND OS v8.2[/]", subtitle=stat_block, border_style="white", height=16)

def settings_menu():
    while True:
        console.clear()
        config = load_config()
        table = Table(title="CONFIGURATION", box=box.ROUNDED)
        table.add_column("ID", style="white"); table.add_column("VALUE", justify="right") 
        table.add_row("1. BLOCKED SITES", str(len(config['blocked_keywords']))); table.add_row("2. BLOCKED APPS", str(len(config['blocked_apps']))); table.add_row("3. RETURN", "")
        console.print(Panel(table, border_style="white"))
        choice = console.input("[bold white]CMD: [/]")
        if choice == '1': manage_list(config, 'blocked_keywords', "KEYWORD: ")
        elif choice == '2': manage_list(config, 'blocked_apps', "APP: ")
        elif choice == '3': break

def manage_list(config, list_key, prompt):
    while True:
        console.clear()
        table = Table(title=f"EDIT {list_key}", box=box.SIMPLE)
        table.add_column("#"); table.add_column("VAL");
        for i, v in enumerate(config[list_key]): table.add_row(str(i+1), v)
        console.print(table)
        ch = console.input("\n[A]DD / [D]EL / [B]ACK: ").upper()
        if ch == 'A':
            v = console.input(prompt).lower()
            if v and v not in config[list_key]: config[list_key].append(v); save_config(config)
        elif ch == 'D':
            try: config[list_key].pop(int(console.input("#: "))-1); save_config(config)
            except: pass
        elif ch == 'B': break

def stats_menu():
    console.clear()
    stats, total = get_daily_stats()
    table = Table(title=f"STATS: {datetime.date.today()}", box=box.HEAVY_EDGE)
    table.add_column("TOPIC"); table.add_column("TIME")
    for t, m in stats.items(): table.add_row(t, f"{m:.2f}m")
    console.print(Panel(table, subtitle=f"TOTAL: {total:.2f}m"))
    console.input("Enter...")

def do_xp_sync():
    console.clear()
    console.print(Panel("[bold white]ANALYZING HISTORICAL DATA...[/]", border_style="white"))
    time.sleep(1)
    xp, lvl = sync_xp_from_history()
    console.print(f"\n[bold white]SYNC COMPLETE.[/]")
    console.print(f"Total XP Recovered: [white]{xp}[/]")
    console.print(f"New Rank Level: [white]{lvl}[/]")
    time.sleep(3)

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    while True:
        console.clear(); console.print(get_main_menu_panel())
        c = console.input("\n[bold white]CMD: [/]")
        if c=='1': run_session()
        elif c=='2': stats_menu()
        elif c=='3': settings_menu()
        elif c=='4': sys.exit()
        elif c=='5': do_xp_sync()

if __name__ == "__main__":
    main()
