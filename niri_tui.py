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
