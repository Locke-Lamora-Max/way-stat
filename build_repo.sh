#!/bin/bash

# .gitignore
cat << 'EOF' > .gitignore
*.db
*.log
*.png
__pycache__/
.venv/
.gemini/
EOF

# README.md
cat << 'EOF' > README.md
# Wayland Analytics Suite (way-stat)

A zero-dependency, high-performance analytics suite for Niri and Hyprland.

## Features
- **Daemons**: Low-footprint background collectors for window focus and hardware telemetry (RAM/VRAM).
- **Markov Engine**: Workflow transition analysis with temporal session splitting and memory delta tracking.
- **TUI Dashboard**: Real-time terminal visualization using Unicode block characters.
- **Global CLI**: A master router to manage the entire system.

## Installation
Run the installer with root privileges:
```bash
sudo ./install.sh
```

## Usage
Start the analytics daemon:
```bash
way-stat daemon --start
```

View the live dashboard:
```bash
way-stat tui --watch
```

Analyze transitions:
```bash
way-stat markov
```
EOF

# niri_daemon.py
cat << 'EOF' > niri_daemon.py
#!/usr/bin/env python3
import socket
import json
import sqlite3
import os
import time
import subprocess
from datetime import datetime

DB_PATH = "niri_analytics.db"
RECONNECT_DELAY = 5

def get_ram_available():
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except Exception: pass
    return 0

def get_vram_used():
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, encoding="utf-8"
        )
        return int(output.strip())
    except Exception: return 0

class NiriAnalyticsDaemon:
    def __init__(self):
        self.socket_path = os.environ.get("NIRI_SOCKET")
        if not self.socket_path: raise EnvironmentError("NIRI_SOCKET not set.")
        self.windows_cache = {}
        self.current_focus_id = None
        self.focus_start_time = None
        self.setup_db()

    def setup_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS window_usage (id INTEGER PRIMARY KEY AUTOINCREMENT, app_id TEXT, workspace_id INTEGER, duration_seconds REAL, timestamp TEXT)")
        for col in ["ram_available_mb INTEGER", "vram_used_mb INTEGER"]:
            try: cursor.execute(f"ALTER TABLE window_usage ADD COLUMN {col}")
            except sqlite3.OperationalError: pass
        conn.commit()
        conn.close()

    def log_usage(self, window_id, duration, ram, vram):
        window_data = self.windows_cache.get(window_id, {})
        app_id = window_data.get("app_id") or "unknown"
        workspace_id = window_data.get("workspace_id")
        timestamp = datetime.now().isoformat()
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO window_usage (app_id, workspace_id, duration_seconds, timestamp, ram_available_mb, vram_used_mb) VALUES (?, ?, ?, ?, ?, ?)", (app_id, workspace_id, duration, timestamp, ram, vram))
            conn.commit()
            conn.close()
        except Exception as e: print(f"DB Error: {e}")

    def update_window_cache(self, window_obj):
        w_id = window_obj.get("id")
        if w_id is not None: self.windows_cache[w_id] = {"app_id": window_obj.get("app_id"), "workspace_id": window_obj.get("workspace_id")}

    def run(self):
        while True:
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.connect(self.socket_path)
                    sock.sendall(b'"EventStream"\n')
                    with sock.makefile('r') as f:
                        if not f.readline(): raise ConnectionError("Handshake failed.")
                        for line in f:
                            if not line: break
                            event = json.loads(line)
                            now = time.time()
                            if "WindowsChanged" in event:
                                for w in event["WindowsChanged"]["windows"]: self.update_window_cache(w)
                            elif "WindowOpenedOrChanged" in event:
                                self.update_window_cache(event["WindowOpenedOrChanged"]["window"])
                            elif "WindowClosed" in event:
                                self.windows_cache.pop(event["WindowClosed"]["id"], None)
                            elif "WindowFocusChanged" in event:
                                new_id = event["WindowFocusChanged"]["id"]
                                if self.current_focus_id is not None and self.focus_start_time is not None:
                                    duration = now - self.focus_start_time
                                    if duration > 0.1: self.log_usage(self.current_focus_id, duration, get_ram_available(), get_vram_used())
                                self.current_focus_id, self.focus_start_time = new_id, (now if new_id is not None else None)
            except Exception:
                self.current_focus_id, self.focus_start_time = None, None
                time.sleep(RECONNECT_DELAY)

if __name__ == "__main__":
    NiriAnalyticsDaemon().run()
EOF

# hyprland_daemon.py
cat << 'EOF' > hyprland_daemon.py
#!/usr/bin/env python3
import socket
import os
import sqlite3
import time
import subprocess
from datetime import datetime

DB_PATH = "niri_analytics.db"
RECONNECT_DELAY = 5

def get_ram_available():
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except Exception: pass
    return 0

def get_vram_used():
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, encoding="utf-8"
        )
        return int(output.strip())
    except Exception: return 0

class HyprlandAnalyticsDaemon:
    def __init__(self):
        his = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        if not his: raise EnvironmentError("HYPRLAND_INSTANCE_SIGNATURE not set.")
        self.socket_path = f"/tmp/hypr/{his}/.socket2.sock"
        self.current_app = None
        self.focus_start_time = None
        self.setup_db()

    def setup_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS window_usage (id INTEGER PRIMARY KEY AUTOINCREMENT, app_id TEXT, workspace_id INTEGER, duration_seconds REAL, timestamp TEXT, ram_available_mb INTEGER, vram_used_mb INTEGER)")
        conn.commit()
        conn.close()

    def log_usage(self, app_id, duration):
        ram, vram, ts = get_ram_available(), get_vram_used(), datetime.now().isoformat()
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO window_usage (app_id, duration_seconds, timestamp, ram_available_mb, vram_used_mb) VALUES (?, ?, ?, ?, ?)", (app_id, duration, ts, ram, vram))
            conn.commit()
            conn.close()
        except Exception: pass

    def run(self):
        while True:
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.connect(self.socket_path)
                    with sock.makefile('r') as f:
                        for line in f:
                            if not line: break
                            now = time.time()
                            line = line.strip()
                            if line.startswith("activewindow>>"):
                                try: app_class = line.split(">>")[1].split(",")[0]
                                except: app_class = "unknown"
                                if self.current_app and self.focus_start_time:
                                    dur = now - self.focus_start_time
                                    if dur > 0.1: self.log_usage(self.current_app, dur)
                                self.current_app, self.focus_start_time = (app_class or "None"), (now if app_class else None)
            except Exception:
                self.current_app, self.focus_start_time = None, None
                time.sleep(RECONNECT_DELAY)

if __name__ == "__main__":
    HyprlandAnalyticsDaemon().run()
EOF

# pure_markov.py
cat << 'EOF' > pure_markov.py
#!/usr/bin/env python3
import sqlite3
import sys
from collections import defaultdict, Counter
from datetime import datetime

DB_PATH = "niri_analytics.db"
MIN_PROB = 0.10
SESSION_GAP = 600

def get_seconds(iso_ts):
    try: return datetime.fromisoformat(iso_ts).timestamp()
    except: return 0

def analyze():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT app_id, timestamp, ram_available_mb, vram_used_mb FROM window_usage ORDER BY timestamp ASC")
        rows = cursor.fetchall()
        conn.close()
        if len(rows) < 2: return
        usage_counts, trans_counts, outward_totals, deltas = Counter(), defaultdict(Counter), Counter(), defaultdict(lambda: [0.0, 0.0])
        for i in range(len(rows) - 1):
            curr, nxt = rows[i], rows[i+1]
            c_app, n_app = (curr[0] or "unknown"), (nxt[0] or "unknown")
            usage_counts[c_app] += 1
            if (get_seconds(nxt[1]) - get_seconds(curr[1])) > SESSION_GAP: continue
            trans_counts[c_app][n_app] += 1
            outward_totals[c_app] += 1
            if curr[2] is not None and nxt[2] is not None: deltas[(c_app, n_app)][0] += (nxt[2] - curr[2])
            if curr[3] is not None and nxt[3] is not None: deltas[(c_app, n_app)][1] += (nxt[3] - curr[3])
        print("\n" + "="*85 + f"\n{'ADVANCED WORKFLOW & TELEMETRY ANALYSIS':^85}\n" + "="*85)
        print(f"{'Source App':<22} | {'Next App':<18} | {'Prob':>6} | {'Avg RAM Δ':>12} | {'Avg VRAM Δ':>11}\n" + "-"*85)
        for source in [a for a, _ in usage_counts.most_common()]:
            if source not in trans_counts: continue
            print(f"\033[1;32m{source:<22}\033[0m")
            for target, count in trans_counts[source].most_common():
                prob = count / outward_totals[source]
                if prob >= MIN_PROB:
                    r_avg, v_avg = deltas[(source, target)][0]/count, deltas[(source, target)][1]/count
                    clr = "\033[1;31m" if (r_avg < -50 or v_avg > 50) else ""
                    print(f"  {clr}{'--->':<19} | {target:<18} | {prob*100:>5.1f}% | {r_avg:>+10.1f} MB | {v_avg:>+9.1f} MB\033[0m")
            print("-" * 85)
    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    analyze()
EOF

# niri_tui.py
cat << 'EOF' > niri_tui.py
#!/usr/bin/env python3
import sqlite3
from datetime import datetime
from collections import defaultdict

DB_PATH = "niri_analytics.db"
TOTAL_RAM, TOTAL_VRAM, SESSION_GAP, BAR_WIDTH = 8192, 4096, 600, 40

def get_seconds(iso_ts):
    try: return datetime.fromisoformat(iso_ts).timestamp()
    except: return 0

def make_bar(value, max_value, width):
    if max_value == 0: return " " * width
    fl = min(int(width * value / max_value), width)
    return '█' * fl + '░' * (width - fl)

def run():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT app_id, timestamp, ram_available_mb, vram_used_mb FROM window_usage ORDER BY timestamp ASC")
        rows = cursor.fetchall()
        conn.close()
        if not rows: return
        time_spent, spikes = defaultdict(float), []
        for i in range(len(rows) - 1):
            curr, nxt = rows[i], rows[i+1]
            c_app, n_app = (curr[0] or "unknown"), (nxt[0] or "unknown")
            dur = get_seconds(nxt[1]) - get_seconds(curr[1])
            if 0 < dur <= SESSION_GAP:
                time_spent[c_app] += dur
                if all(v is not None for v in [curr[2], nxt[2], curr[3], nxt[3]]):
                    rs, vs = (TOTAL_RAM - nxt[2]) - (TOTAL_RAM - curr[2]), nxt[3] - curr[3]
                    if rs > 0 or vs > 0: spikes.append((f"{c_app} -> {n_app}", rs, vs))
        last = rows[-1]
        cur_app, cur_ram, cur_vram = (last[0] or "None"), (TOTAL_RAM - (last[2] or TOTAL_RAM)), (last[3] or 0)
        print("\033[H\033[J" + "="*70 + f"\n NIRI ANALYTICS TERMINAL DASHBOARD | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n" + "="*70)
        print(f"\n[ CURRENT STATE ]\nActive App: \033[1;32m{cur_app}\033[0m")
        print(f"System RAM:  [{make_bar(cur_ram, TOTAL_RAM, BAR_WIDTH)}] {cur_ram:>4} / {TOTAL_RAM} MB")
        print(f"GPU VRAM:    [{make_bar(cur_vram, TOTAL_VRAM, BAR_WIDTH)}] {cur_vram:>4} / {TOTAL_VRAM} MB")
        print(f"\n[ TOP APP USAGE (MINUTES) ]")
        usage = sorted(time_spent.items(), key=lambda x: x[1], reverse=True)[:5]
        max_t = usage[0][1] if usage else 1
        for app, sec in usage: print(f"{app:<15} [{make_bar(sec, max_t, BAR_WIDTH)}] {int(sec/60)}m")
        print(f"\n[ TOP MEMORY SPIKES (DEATH SPIRALS) ]")
        top = sorted(spikes, key=lambda x: x[1] + x[2], reverse=True)[:3]
        if not top: print("No significant spikes.")
        else:
            print(f"{'Transition Path':<35} | {'RAM Spike':<12} | {'VRAM Spike'}\n" + "-"*70)
            for p, r, v in top: print(f"{p:<35} | \033[1;31m+{r:>4.0f} MB\033[0m     | \033[1;31m+{v:>4.0f} MB\033[0m")
        print("\n" + "="*70)
    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__": run()
EOF

# way-stat
cat << 'EOF' > way-stat
#!/usr/bin/env python3
import argparse, subprocess, os, sys

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "way-stat.log")
SCRIPTS = {
    "niri_daemon": os.path.join(BASE_DIR, "niri_daemon.py"),
    "hyprland_daemon": os.path.join(BASE_DIR, "hyprland_daemon.py"),
    "markov": os.path.join(BASE_DIR, "pure_markov.py"),
    "tui": os.path.join(BASE_DIR, "niri_tui.py"),
}

def main():
    parser = argparse.ArgumentParser(description="Wayland Analytics Master CLI (way-stat)")
    subparsers = parser.add_subparsers(dest="command")
    daemon = subparsers.add_parser("daemon")
    daemon.add_argument("--wm", choices=["niri", "hyprland"], default="niri")
    daemon.add_argument("--start", action="store_true")
    daemon.add_argument("--stop", action="store_true")
    daemon.add_argument("--log", action="store_true")
    subparsers.add_parser("markov")
    tui = subparsers.add_parser("tui")
    tui.add_argument("--watch", action="store_true")
    args = parser.parse_args()

    if args.command == "daemon":
        script = SCRIPTS[f"{args.wm}_daemon"]
        if args.start:
            print(f"Starting {args.wm} daemon...")
            with open(LOG_FILE, "a") as log:
                subprocess.Popen([sys.executable, script], stdout=log, stderr=log, preexec_fn=os.setpgrp)
        elif args.stop:
            print("Stopping daemons..."); subprocess.run(["pkill", "-f", SCRIPTS["niri_daemon"]]); subprocess.run(["pkill", "-f", SCRIPTS["hyprland_daemon"]])
        elif args.log: subprocess.run(["tail", "-f", LOG_FILE])
    elif args.command == "markov": subprocess.run([sys.executable, SCRIPTS["markov"]])
    elif args.command == "tui":
        if args.watch: subprocess.run(["watch", "-n", "5", "-c", sys.executable, SCRIPTS["tui"]])
        else: subprocess.run([sys.executable, SCRIPTS["tui"]])
    else: parser.print_help()

if __name__ == "__main__": main()
EOF

# install.sh
cat << 'EOF' > install.sh
#!/bin/bash
if [[ $EUID -ne 0 ]]; then echo "Must be run as root."; exit 1; fi
if command -v pacman &> /dev/null; then pacman -Sy --needed --noconfirm python sqlite
elif command -v dnf &> /dev/null; then dnf install -y python3 sqlite
else echo "Unsupported distro."; exit 1; fi
chmod +x way-stat *.py
ln -sf "$(pwd)/way-stat" "/usr/local/bin/way-stat"
echo "Installation complete. Run 'way-stat' to begin."
EOF

# Post-generation setup
chmod +x niri_daemon.py hyprland_daemon.py pure_markov.py niri_tui.py way-stat install.sh
git init
git add .
git commit -m "Initial release: Wayland analytics daemons, Markov transition engine, and TUI"

echo -e "\nDeployment Finished!"
echo "Please manually run the following to sync with your remote repository:"
echo -e "  git remote add origin <URL>"
echo -e "  git push -u origin main"
echo -e "\nRun 'sudo ./install.sh' to finalize the system installation."
