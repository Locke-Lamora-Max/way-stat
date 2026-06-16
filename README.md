# Wayland Analytics Suite (way-stat)

  A zero-dependency, high-performance analytics suite for Niri and Hyprland.

  Features
   - Daemons: Low-footprint background collectors for window focus and hardware telemetry (RAM/VRAM).
   - Markov Engine: Workflow transition analysis with temporal session splitting and memory delta tracking.
   - TUI Dashboard: Real-time terminal visualization using Unicode block characters.
   - Global CLI: A master router to manage the entire system.

  Installation

  First, clone the repository to your local machine:

   1 git clone https://github.com/yourusername/way-stat.git
   2 cd way-stat

  Then, run the installer with root privileges:
   1 sudo ./install.sh

  Usage

  Managing Daemons
  Start the analytics daemon for your window manager (defaults to Niri):

   1 way-stat daemon --start

  To switch between window managers, stop the current daemon and start the new one using the --wm flag:

   1 # Example: Switching to Hyprland
   2 way-stat daemon --stop
   3 way-stat daemon --wm hyprland --start

  Visuals and Analysis
  View the live terminal dashboard (refreshes every 5s):
   1 way-stat tui --watch

  Analyze your application transitions and memory deltas:
   1 way-stat markov

  Viewing Logs
  To monitor the daemon's activity in real-time:
   1 way-stat daemon --log
