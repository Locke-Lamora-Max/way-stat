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
