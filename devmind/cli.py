import click
from devmind.config import add_block, remove_block, get_blocklist, load_config, save_config, verify_license_key, get_machine_id, set_license

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """DevMind Focus — Ruthless deep-work daemon & gamified dashboard."""
    if ctx.invoked_subcommand is None:
        # Default to launching the premium native desktop dashboard!
        from devmind.desktop import start_desktop_dashboard
        start_desktop_dashboard()

@cli.command()
@click.argument("keyword")
def block(keyword):
    """Add a website or app to your blocklist."""
    if add_block(keyword):
        print(f"\n  + '{keyword}' added to blocklist.\n")
    else:
        print(f"\n  '{keyword}' is already in the blocklist.\n")

@cli.command()
@click.argument("keyword")
def unblock(keyword):
    """Remove a website or app from your blocklist."""
    if remove_block(keyword):
        print(f"\n  - '{keyword}' removed from blocklist.\n")
    else:
        print(f"\n  x '{keyword}' not found in blocklist.\n")

@cli.command(name="list")
def list_blocked():
    """List all blocked websites and apps."""
    blocked = get_blocklist()
    print("")
    print("  blocked sites")
    print("  -------------")
    for b in blocked:
        print(f"    {b.lower()}")
    print("")

@cli.command()
def start():
    """Start the DevMind Focus daemon in the background."""
    import subprocess
    import sys
    import os

    if getattr(sys, 'frozen', False):
        devmind_exe = sys.executable
    else:
        devmind_exe = sys.executable

    print("")
    print("  starting daemon...")

    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        
        if getattr(sys, 'frozen', False):
            cmd = [str(devmind_exe), "daemon"]
        else:
            cmd = [str(devmind_exe), sys.argv[0], "daemon"]
            
        # Clean PyInstaller environment to prevent child process from locking parent's temp directory
        import os
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

    print("  devmind focus is now watching in the background.")
    print("")

@cli.command()
def stop():
    """Stop the DevMind Focus daemon."""
    import psutil

    killed = False
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            name = p.info.get('name') or ''
            cmdline = p.info.get('cmdline') or []
            cmdline_lower = [arg.lower() for arg in cmdline]
            
            is_devmind = False
            if name.lower() == 'devmind.exe' and 'daemon' in cmdline_lower:
                is_devmind = True
            elif 'python' in name.lower() and 'daemon' in cmdline_lower and any('devmind' in arg or 'run_devmind.py' in arg for arg in cmdline_lower):
                is_devmind = True
                
            if is_devmind:
                p.kill()
                killed = True
        except Exception:
            pass

    if killed:
        print("\n  daemon stopped.\n")
    else:
        print("\n  daemon is not running.\n")

@cli.command()
def status():
    """Check the status of the DevMind Focus daemon."""
    import psutil
    from devmind.config import load_config, verify_license_key

    daemon_pid = None
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            name = p.info.get('name') or ''
            cmdline = p.info.get('cmdline') or []
            cmdline_lower = [arg.lower() for arg in cmdline]
            
            is_devmind = False
            if name.lower() == 'devmind.exe' and 'daemon' in cmdline_lower:
                is_devmind = True
            elif 'python' in name.lower() and 'daemon' in cmdline_lower and any('devmind' in arg or 'run_devmind.py' in arg for arg in cmdline_lower):
                is_devmind = True
                
            if is_devmind:
                daemon_pid = p.pid
                break
        except Exception:
            pass

    daemon_status = f"running    (pid {daemon_pid})" if daemon_pid else "stopped"

    config = load_config()
    blocks_today = config.get("blocks_today", 0)
    is_pro = verify_license_key(config.get("license_key", ""))

    limit_text = "unlimited" if is_pro else "100"
    tier_text = "pro" if is_pro else "free"
    license_text = "pro" if is_pro else "free"

    print(f"daemon          : {daemon_status}")
    print(f"interceptions   : {blocks_today} / {limit_text}      (today | {tier_text})")
    print(f"license         : {license_text}")

@cli.command()
@click.argument("state", type=click.Choice(["on", "off"], case_sensitive=False))
def sound(state):
    """Enable or disable calming ocean sounds (on/off)."""
    config = load_config()
    enabled = state.lower() == "on"
    config["sound_enabled"] = enabled
    save_config(config)
    print(f"\n  Calming ocean sounds turned {'ON' if enabled else 'OFF'}.\n")

@cli.command(name="daemon", hidden=True)
def run_daemon():
    """Hidden command — runs the background tracker loop."""
    from devmind.tracker import main
    main()

@cli.command(name="get-id")
def get_id():
    """Get your unique Machine ID for license activation."""
    mid = get_machine_id()
    print("\n  Your Hardware Machine ID:")
    print(f"  {mid}\n")
    print("  Provide this ID when purchasing your Pro license to bind it to this device.\n")

@cli.command()
@click.argument("key")
def license(key):
    """Activate your Pro license key."""
    if set_license(key):
        print("\n  license activated. unlimited interceptions enabled.\n")
    else:
        print("\n  invalid license key or key is bound to another machine.\n")

@cli.command()
def terminal():
    """Launch the retro-futuristic monochrome terminal dashboard."""
    from devmind.dashboard import start_dashboard
    start_dashboard()
