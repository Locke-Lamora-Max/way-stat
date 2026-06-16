#!/usr/bin/env python3
"""
Niri Usage Analytics Reporter
Loads data from the SQLite database and generates a usage visualization.
Requires: pandas, matplotlib
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import sys

# Configuration
DB_PATH = "niri_analytics.db"

def load_data():
    """Load the usage data from SQLite into a Pandas DataFrame."""
    try:
        conn = sqlite3.connect(DB_PATH)
        # Query total duration per app_id
        query = "SELECT app_id, duration_seconds FROM window_usage"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except sqlite3.Error as e:
        print(f"Error reading database: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def analyze_and_plot(df):
    """Aggregate data and generate a bar chart."""
    if df is None or df.empty:
        print("No data found in the database. Please ensure the daemon has been running.")
        return

    # Clean data: Replace None/NaN app_id with 'unknown'
    df['app_id'] = df['app_id'].fillna('unknown')

    # Group by app_id and sum duration
    usage_stats = df.groupby('app_id')['duration_seconds'].sum().reset_index()
    
    # Convert seconds to minutes for better readability
    usage_stats['duration_minutes'] = usage_stats['duration_seconds'] / 60
    
    # Sort and take top 10
    top_10 = usage_stats.sort_values(by='duration_minutes', ascending=False).head(10)

    print("\n--- Top 10 Most Used Applications ---")
    print(top_10[['app_id', 'duration_minutes']].to_string(index=False))

    # Plotting
    plt.figure(figsize=(12, 7))
    bars = plt.bar(top_10['app_id'], top_10['duration_minutes'], color='skyblue', edgecolor='navy')
    
    # Add data labels on top of bars
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.1, f'{yval:.1f}m', ha='center', va='bottom')

    plt.title('Top 10 Applications by Focus Duration', fontsize=16, fontweight='bold')
    plt.xlabel('Application ID', fontsize=12)
    plt.ylabel('Total Duration (Minutes)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    # Save and show
    output_file = "niri_usage_chart.png"
    plt.savefig(output_file)
    print(f"\nChart saved to {output_file}")
    
    # Note: plt.show() might not work in all CLI environments, 
    # so we prioritize saving the file.
    try:
        plt.show()
    except Exception:
        print("Could not display plot window (likely no X11/Wayland display for this process).")

if __name__ == "__main__":
    print("Niri Window Analytics - Data Analysis")
    usage_df = load_data()
    analyze_and_plot(usage_df)
