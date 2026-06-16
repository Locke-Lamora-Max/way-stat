# Wayland Analytics Suite (way-stat)

A zero-dependency, high-performance analytics suite for Niri and Hyprland.

## Features
- **Daemons**: Low-footprint background collectors for window focus and hardware telemetry (RAM/VRAM).
- **Markov Engine**: Workflow transition analysis with temporal session splitting and memory delta tracking.
- **TUI Dashboard**: Real-time terminal visualization using Unicode block characters.
- **Global CLI**: A master router to manage the entire system.

## Installation
First, clone the repository to your local machine:
```bash
git clone https://github.com/yourusername/way-stat.git
cd way-stat
```

Then, run the installer with root privileges:
```bash
sudo ./install.sh
```

## Usage

### Managing Daemons
Start the analytics daemon for your window manager (defaults to Niri):
```bash
way-stat daemon --start
```

To switch between window managers, stop the current daemon and start the new one using the `--wm` flag:
```bash
# Example: Switching to Hyprland
way-stat daemon --stop
way-stat daemon --wm hyprland --start
```

### Visuals and Analysis
View the live dashboard (refreshes every 5s):
```bash
way-stat tui --watch
```

Analyze your application transitions:
```bash
way-stat markov
```
