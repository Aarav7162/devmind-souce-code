import json
import os
import sys
import uuid
import hashlib
from pathlib import Path

DEVMIND_HOME = Path(os.path.expanduser("~/.devmind"))
CONFIG_FILE = DEVMIND_HOME / "focus_config.json"

DEFAULT_BLOCKLIST = ["youtube", "facebook", "twitter", "reddit"]

PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAENx/a993l5w0DuVGQGAAb/Nc/xlwyHszD
cYwm0X539ZhoVaObWpj6/1cfWhFEsXTMg6gyXNg+Fw75pdSuAuftZw==
-----END PUBLIC KEY-----"""

def ensure_sound_file():
    """Generates a procedural calming low-pass filtered ocean wave WAV file inside ~/.devmind/ if not present."""
    sound_path = DEVMIND_HOME / "ocean.wav"
    if not sound_path.exists():
        try:
            import wave
            import struct
            import random
            import math
            
            lp_state = 0.0
            alpha = 0.1
            sample_rate = 22050
            duration_secs = 15
            num_samples = int(sample_rate * duration_secs)
            wave_period = 4.5
            
            DEVMIND_HOME.mkdir(parents=True, exist_ok=True)
            with wave.open(str(sound_path), 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                
                for i in range(num_samples):
                    t = i / sample_rate
                    noise = random.uniform(-1.0, 1.0)
                    lp_state = lp_state + alpha * (noise - lp_state)
                    mod = 0.5 + 0.4 * math.sin(2 * math.pi * t / wave_period)
                    sample_val = lp_state * mod * 0.35
                    sample_val = max(-1.0, min(1.0, sample_val))
                    int_val = int(sample_val * 32767)
                    wav.writeframes(struct.pack('<h', int_val))
        except Exception:
            pass
    return sound_path

def load_config():
    """Load the focus configuration."""
    DEVMIND_HOME.mkdir(parents=True, exist_ok=True)
    ensure_sound_file()
    
    default_cfg = {
        "blocked": DEFAULT_BLOCKLIST,
        "sound_enabled": True
    }
    
    if not CONFIG_FILE.exists():
        save_config(default_cfg)
        return default_cfg
        
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            updated = False
            if "blocked" not in cfg:
                cfg["blocked"] = DEFAULT_BLOCKLIST
                updated = True
            if "sound_enabled" not in cfg:
                cfg["sound_enabled"] = True
                updated = True
            if updated:
                save_config(cfg)
            return cfg
    except Exception:
        return default_cfg

def save_config(config):
    """Save the focus configuration."""
    DEVMIND_HOME.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception:
        pass

def get_blocklist():
    """Get the active blocklist."""
    cfg = load_config()
    return cfg.get("blocked", DEFAULT_BLOCKLIST)

def add_block(keyword):
    """Add a keyword to the blocklist."""
    cfg = load_config()
    blocked = cfg.get("blocked", DEFAULT_BLOCKLIST)
    kw = keyword.strip().lower()
    if kw and kw not in blocked:
        blocked.append(kw)
        cfg["blocked"] = blocked
        save_config(cfg)
        return True
    return False

def remove_block(keyword):
    """Remove a keyword from the blocklist."""
    cfg = load_config()
    blocked = cfg.get("blocked", DEFAULT_BLOCKLIST)
    kw = keyword.strip().lower()
    if kw in blocked:
        blocked.remove(kw)
        cfg["blocked"] = blocked
        save_config(cfg)
        return True
    return False

def get_machine_id():
    """Returns a stable, unique 16-character hardware Machine ID bound to this Windows device."""
    try:
        import subprocess
        # Query Windows Product UUID
        cmd = "wmic csproduct get uuid"
        output = subprocess.check_output(cmd, shell=True, universal_newlines=True)
        lines = [line.strip() for line in output.split('\n') if line.strip()]
        if len(lines) > 1:
            raw_id = lines[1]
            if raw_id and "uuid" not in raw_id.lower() and len(raw_id) > 10:
                h = hashlib.sha256(raw_id.encode('utf-8')).hexdigest().upper()
                return f"DM-{h[:4]}-{h[4:8]}-{h[8:12]}"
    except Exception:
        pass
    
    # Fallback to local UUID
    node_str = str(uuid.getnode())
    h = hashlib.sha256(node_str.encode('utf-8')).hexdigest().upper()
    return f"DM-{h[:4]}-{h[4:8]}-{h[8:12]}"

def verify_license_key(key):
    """Verifies a Pro license key cryptographically."""
    if not key:
        return False
        
    try:
        from ecdsa import VerifyingKey, BadSignatureError
        import base64
        
        # Decode the license key
        parts = key.split('-')
        if len(parts) < 2:
            return False
            
        machine_id = get_machine_id()
        payload = f"PRO_LICENSE:{machine_id}"
        
        sig_b64 = parts[-1]
        sig = base64.b64decode(sig_b64)
        
        vk = VerifyingKey.from_pem(PUBLIC_KEY_PEM)
        return vk.verify(sig, payload.encode('utf-8'))
    except Exception:
        return False

def set_license(key):
    """Activates the license key if valid."""
    if verify_license_key(key):
        cfg = load_config()
        cfg["license_key"] = key
        save_config(cfg)
        return True
    return False

def record_interception(proc_name, site_name):
    """Records an interception event to interceptions_log.json for the Neutralization Feed."""
    import datetime
    import json
    from pathlib import Path
    
    DEVMIND_HOME = Path(os.path.expanduser("~/.devmind"))
    log_file = DEVMIND_HOME / "interceptions_log.json"
    
    target = site_name if site_name else proc_name
    entry = {
        "date": str(datetime.date.today()),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target": target,
        "action": "Averted"
    }
    
    logs = []
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                logs = json.load(f)
        except Exception:
            pass
    logs.append(entry)
    
    # Keep only last 100 entries to prevent memory bloating
    if len(logs) > 100:
        logs = logs[-100:]
        
    try:
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=4)
    except Exception:
        pass

def record_block(proc_name="unknown.exe", distraction_name="Unknown"):
    """Increments the daily distraction block count and logs the interception event."""
    import datetime
    cfg = load_config()
    today_str = str(datetime.date.today())
    
    if cfg.get("last_block_date") != today_str:
        cfg["last_block_date"] = today_str
        cfg["blocks_today"] = 1
    else:
        cfg["blocks_today"] = cfg.get("blocks_today", 0) + 1
        
    save_config(cfg)
    
    # Register the interception event dynamically!
    record_interception(proc_name, distraction_name)

def can_block():
    """Enforces rate-limits: Free tier is limited to 100 blocks per day; Pro tier is unlimited."""
    cfg = load_config()
    is_pro = verify_license_key(cfg.get("license_key", ""))
    if is_pro:
        return True
        
    import datetime
    today_str = str(datetime.date.today())
    if cfg.get("last_block_date") != today_str:
        return True
        
    return cfg.get("blocks_today", 0) < 100

def get_resource_path(relative_path):
    """Resolve resource path for developer environment and PyInstaller compiled executable."""
    try:
        base_path = sys._MEIPASS
        return os.path.join(base_path, "devmind", relative_path)
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)
