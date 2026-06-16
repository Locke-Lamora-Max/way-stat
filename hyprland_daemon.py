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
