#!/usr/bin/env python3
"""
Niri Analytics Dashboard Generator (Pure Python)
Generates a static HTML dashboard with Chart.js using SQLite data.
"""

import sqlite3
import json
from datetime import datetime
from collections import defaultdict

# Configuration
DB_PATH = "niri_analytics.db"
TOTAL_RAM_MB = 8192
SESSION_GAP_LIMIT = 600
OUTPUT_HTML = "niri_dashboard.html"

def get_seconds(iso_ts):
    try:
        return datetime.fromisoformat(iso_ts).timestamp()
    except Exception:
        return 0

def fetch_and_process():
    """Aggregates time and memory data from SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT app_id, timestamp, ram_available_mb, vram_used_mb 
            FROM window_usage 
            ORDER BY timestamp ASC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("No data found in database.")
            return None

        # {app_id: {'total_seconds': 0, 'ram_samples': [], 'vram_samples': []}}
        stats = defaultdict(lambda: {'total_seconds': 0, 'ram_samples': [], 'vram_samples': []})
        
        for i in range(len(rows) - 1):
            curr = rows[i]
            nxt = rows[i+1]
            
            app_id = curr[0] or "unknown"
            curr_ts = get_seconds(curr[1])
            nxt_ts = get_seconds(nxt[1])
            
            # 1. Total Time Calculation (Session Splitting)
            duration = nxt_ts - curr_ts
            if 0 < duration <= SESSION_GAP_LIMIT:
                stats[app_id]['total_seconds'] += duration
            
            # 2. Memory Profiling
            if curr[2] is not None:
                # ram_used = Total - Available
                stats[app_id]['ram_samples'].append(TOTAL_RAM_MB - curr[2])
            if curr[3] is not None:
                stats[app_id]['vram_samples'].append(curr[3])

        # Final pass for the last row's telemetry
        last_row = rows[-1]
        last_app = last_row[0] or "unknown"
        if last_row[2] is not None:
            stats[last_app]['ram_samples'].append(TOTAL_RAM_MB - last_row[2])
        if last_row[3] is not None:
            stats[last_app]['vram_samples'].append(last_row[3])

        # Formatting for Chart.js
        aggregated = []
        for app, data in stats.items():
            ram_avg = sum(data['ram_samples']) / len(data['ram_samples']) if data['ram_samples'] else 0
            vram_avg = sum(data['vram_samples']) / len(data['vram_samples']) if data['vram_samples'] else 0
            aggregated.append({
                'app_id': app,
                'minutes': round(data['total_seconds'] / 60, 2),
                'ram_avg': round(ram_avg, 1),
                'vram_avg': round(vram_avg, 1)
            })

        # Sort by usage for the charts
        return sorted(aggregated, key=lambda x: x['minutes'], reverse=True)

    except Exception as e:
        print(f"Data Processing Error: {e}")
        return None

def generate_html(data):
    """Embeds data into a Chart.js HTML template."""
    if not data:
        return

    # Prepare JSON strings for injection
    labels = json.dumps([item['app_id'] for item in data])
    minutes = json.dumps([item['minutes'] for item in data])
    ram_data = json.dumps([item['ram_avg'] for item in data])
    vram_data = json.dumps([item['vram_avg'] for item in data])

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Niri Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f4f7f6; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        h1 {{ text-align: center; color: #2c3e50; margin-bottom: 40px; }}
        .chart-box {{ margin-bottom: 50px; padding: 20px; border: 1px solid #eee; border-radius: 8px; }}
        h2 {{ font-size: 1.2rem; color: #7f8c8d; border-bottom: 2px solid #3498db; display: inline-block; padding-bottom: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Niri Window Analytics</h1>
        
        <div class="chart-box">
            <h2>Total Time Spent (Minutes)</h2>
            <canvas id="timeChart"></canvas>
        </div>

        <div class="chart-box">
            <h2>Average Resource Footprint (MB)</h2>
            <canvas id="memoryChart"></canvas>
        </div>
    </div>

    <script>
        const appLabels = {labels};
        
        // Time Spent Chart
        new Chart(document.getElementById('timeChart'), {{
            type: 'bar',
            data: {{
                labels: appLabels,
                datasets: [{{
                    label: 'Minutes',
                    data: {minutes},
                    backgroundColor: 'rgba(52, 152, 219, 0.7)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{ scales: {{ y: {{ beginAtZero: true }} }} }}
        }});

        // Resource Footprint Chart
        new Chart(document.getElementById('memoryChart'), {{
            type: 'bar',
            data: {{
                labels: appLabels,
                datasets: [
                    {{
                        label: 'Avg RAM Used',
                        data: {ram_data},
                        backgroundColor: 'rgba(46, 204, 113, 0.7)',
                        borderColor: 'rgba(46, 204, 113, 1)',
                        borderWidth: 1
                    }},
                    {{
                        label: 'Avg VRAM Used',
                        data: {vram_data},
                        backgroundColor: 'rgba(231, 76, 60, 0.7)',
                        borderColor: 'rgba(231, 76, 60, 1)',
                        borderWidth: 1
                    }}
                ]
            }},
            options: {{ scales: {{ y: {{ beginAtZero: true }} }} }}
        }});
    </script>
</body>
</html>
"""
    with open(OUTPUT_HTML, "w") as f:
        f.write(html_template)
    print(f"Dashboard successfully generated: {OUTPUT_HTML}")

if __name__ == "__main__":
    data = fetch_and_process()
    generate_html(data)
