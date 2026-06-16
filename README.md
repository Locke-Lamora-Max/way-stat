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
