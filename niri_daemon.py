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
