# Desktop Time Utility v2.0

A premium, minimalist, always-on-top desktop widget for Windows. Built with Python and PyQt6, featuring a modern dark-themed Control Panel, Pomodoro tracking, and a click-through "Ghost Mode".

## 🚀 New in v2.0
- **Ghost Mode (Click-Through):** Make the widget completely unclickable. The text hollows out into a sleek outline, allowing you to click through it into your apps (Photoshop, VS Code, Games) while keeping the time visible.
- **Perimeter-Tracing Progress:** In Timer and Pomodoro modes, a dynamic visual progress line smoothly traces the perimeter of the widget as time depletes.
- **Command Center Control Panel:** A premium dark-mode settings dialog to control all aspects of the app.
- **Live Customization:** Use sliders to dynamically adjust Font Size, Accent Colors, Shadow Depth, Outline Thickness, and Rectangle Scale in real-time.
- **Persistent Settings:** All your UI and timer configurations are permanently saved between sessions.

## ⚙️ Features
- **Modes:** Clock, Stopwatch, Timer, and Pomodoro (Customizable Work/Break intervals).
- **Tactile Physics:** Dragging the widget compresses its drop shadow, mimicking physical depth.
- **System Tray Integration:** Run quietly in the background with full control from the Windows taskbar.

## 📥 Installation (For Users)
1. Go to the[Releases](../../releases) page.
2. Download the latest `TimeUtility.exe`.
3. Place it anywhere on your PC and double-click to run! (No installation required).

## 💻 Running from Source (For Developers)
```bash
git clone https://github.com/YourUsername/your-repo-name.git
cd your-repo-name
pip install -r requirements.txt
python time_utility.py