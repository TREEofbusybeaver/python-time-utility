import sys
import re
from enum import Enum
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMenu, QSystemTrayIcon, QInputDialog
from PyQt6.QtCore import Qt, QTimer, QTime, QPoint, QSettings, QDateTime, QElapsedTimer
from PyQt6.QtGui import QFont, QMouseEvent, QAction


# Define the different application modes
class AppMode(Enum):
    CLOCK = 0
    STOPWATCH = 1
    TIMER = 2


class TimeUtilityApp(QWidget):
    def __init__(self):
        super().__init__()
        self.old_pos = None
        self.current_mode = AppMode.CLOCK

        # --- State Variables ---
        # Stopwatch state
        self.stopwatch_timer = QElapsedTimer()
        self.stopwatch_running = False
        self.stopwatch_paused_ms = 0

        # Timer state
        self.timer_end_time = None
        self.timer_running = False
        self.timer_paused_duration_ms = 0
        self.flash_timer = QTimer(self)
        self.flash_timer.timeout.connect(self.stop_flash_animation)
        self.flash_count = 0

        # --- Configuration ---
        self.config = {
            "font_family": "Segoe UI",
            "font_size": 48,
            "font_weight": QFont.Weight.Bold,
            "text_color": "#FFFFFF",
            "flash_color": "#FFD700",  # Gold color for timer finish
            "initial_pos_x": 100,
            "initial_pos_y": 100,
        }
        self.load_settings()

        self.initUI()
        self.init_tray_icon()

    def load_settings(self):
        settings = QSettings("MyTimeUtility", "TimeApp")
        pos = self.pos()
        self.config["initial_pos_x"] = settings.value("pos_x", pos.x(), type=int)
        self.config["initial_pos_y"] = settings.value("pos_y", pos.y(), type=int)
        last_mode = settings.value("last_mode", AppMode.CLOCK.value, type=int)
        self.current_mode = AppMode(last_mode)

    def save_settings(self):
        settings = QSettings("MyTimeUtility", "TimeApp")
        settings.setValue("pos_x", self.pos().x())
        settings.setValue("pos_y", self.pos().y())
        settings.setValue("last_mode", self.current_mode.value)

    def initUI(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")

        self.time_label = QLabel(self)
        self.update_font_and_style()
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.time_label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.setGeometry(self.config["initial_pos_x"], self.config["initial_pos_y"], 450, 70)
        self.setMinimumSize(200, 60)
        self.adjustSize()

        # A faster timer for smooth stopwatch/timer updates (approx 30fps)
        self.main_timer = QTimer(self)
        self.main_timer.timeout.connect(self.update_display)
        self.main_timer.start(33)

        self.setWindowTitle("Time Utility")
        self.show()

    def update_font_and_style(self, color=None):
        """Updates the label's font and color."""
        if color is None:
            color = self.config["text_color"]
        font = QFont(self.config["font_family"], self.config["font_size"], self.config["font_weight"])
        self.time_label.setFont(font)
        self.time_label.setStyleSheet(f"color: {color}; background:transparent;")

    def update_display(self):
        """The main update loop, called every 33ms."""
        display_text = ""
        if self.current_mode == AppMode.CLOCK:
            display_text = QTime.currentTime().toString("hh:mm:ss AP")

        elif self.current_mode == AppMode.STOPWATCH:
            if self.stopwatch_running:
                elapsed = self.stopwatch_timer.elapsed() + self.stopwatch_paused_ms
            else:
                elapsed = self.stopwatch_paused_ms

            time = QTime(0, 0, 0, 0).addMSecs(elapsed)
            display_text = time.toString("HH:mm:ss.zzz")[:-1]  # Show 2 decimal places

        elif self.current_mode == AppMode.TIMER:
            if self.timer_running:
                remaining_ms = QDateTime.currentDateTime().msecsTo(self.timer_end_time)
                if remaining_ms <= 0:
                    self.timer_running = False
                    self.start_flash_animation()
                    remaining_ms = 0

                time = QTime(0, 0, 0, 0).addMSecs(remaining_ms)
                display_text = time.toString("HH:mm:ss")
            elif self.timer_paused_duration_ms > 0:
                time = QTime(0, 0, 0, 0).addMSecs(self.timer_paused_duration_ms)
                display_text = time.toString("HH:mm:ss")
            else:
                display_text = "00:00:00"

        if self.time_label.text() != display_text:
            self.time_label.setText(display_text)
            self.adjustSize()  # Adjust window size to fit text

    # --- Mode Switching and Context Menu ---
    def set_mode(self, mode: AppMode):
        self.current_mode = mode
        # Reset other modes when switching
        if mode != AppMode.STOPWATCH: self.action_stopwatch_reset()
        if mode != AppMode.TIMER: self.action_timer_reset()
        self.update_display()
        self.save_settings()

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)

        if self.current_mode == AppMode.STOPWATCH:
            action_text = "Pause" if self.stopwatch_running else "Start"
            start_pause_action = context_menu.addAction(action_text)
            start_pause_action.triggered.connect(self.action_stopwatch_start_pause)
            reset_action = context_menu.addAction("Reset")
            reset_action.triggered.connect(self.action_stopwatch_reset)

        elif self.current_mode == AppMode.TIMER:
            action_text = "Pause" if self.timer_running else "Start"
            start_pause_action = context_menu.addAction(action_text)
            start_pause_action.triggered.connect(self.action_timer_start_pause)
            set_action = context_menu.addAction("Set Duration...")
            set_action.triggered.connect(self.action_timer_set)
            reset_action = context_menu.addAction("Reset")
            reset_action.triggered.connect(self.action_timer_reset)

        # In any mode, you can still switch
        context_menu.addSeparator()
        mode_menu = context_menu.addMenu("Switch Mode")
        mode_menu.addAction("Clock", lambda: self.set_mode(AppMode.CLOCK))
        mode_menu.addAction("Stopwatch", lambda: self.set_mode(AppMode.STOPWATCH))
        mode_menu.addAction("Timer", lambda: self.set_mode(AppMode.TIMER))

        context_menu.addSeparator()
        context_menu.addAction("Quit", self.quit_application)

        context_menu.exec(self.mapToGlobal(event.pos()))

    # --- Actions ---
    def action_stopwatch_start_pause(self):
        if self.stopwatch_running:  # Pause
            self.stopwatch_paused_ms += self.stopwatch_timer.elapsed()
            self.stopwatch_running = False
        else:  # Start/Resume
            self.stopwatch_timer.start()
            self.stopwatch_running = True

    def action_stopwatch_reset(self):
        self.stopwatch_running = False
        self.stopwatch_paused_ms = 0
        self.update_display()

    def action_timer_set(self):
        # Stop any flashing
        self.stop_flash_animation()
        duration_str, ok = QInputDialog.getText(self, "Set Timer", "Enter duration (e.g., '1h 30m 10s', '45s', '2m'):")
        if ok and duration_str:
            duration_ms = self.parse_duration_string(duration_str)
            if duration_ms > 0:
                self.timer_paused_duration_ms = duration_ms
                self.timer_running = False
                self.update_display()

    def parse_duration_string(self, s: str) -> int:
        total_ms = 0
        s = s.lower()
        try:
            # Match patterns like 1h, 30m, 45s
            parts = re.findall(r'(\d+)\s*(h|m|s)?', s)
            if not parts:  # If no units, assume seconds
                return int(s) * 1000

            for value, unit in parts:
                value = int(value)
                if unit == 'h':
                    total_ms += value * 3600000
                elif unit == 'm':
                    total_ms += value * 60000
                elif unit == 's' or unit is None:
                    total_ms += value * 1000
            return total_ms
        except (ValueError, TypeError):
            return 0

    def action_timer_start_pause(self):
        if self.timer_running:  # Pause
            self.timer_paused_duration_ms = QDateTime.currentDateTime().msecsTo(self.timer_end_time)
            self.timer_running = False
        elif self.timer_paused_duration_ms > 0:  # Start/Resume
            self.timer_end_time = QDateTime.currentDateTime().addMSecs(self.timer_paused_duration_ms)
            self.timer_running = True
            self.stop_flash_animation()

    def action_timer_reset(self):
        self.timer_running = False
        self.timer_paused_duration_ms = 0
        self.stop_flash_animation()
        self.update_display()

    # --- Timer Animation ---
    def start_flash_animation(self):
        QApplication.beep()
        self.flash_count = 0
        self.flash_timer.start(250)  # Flash every 250ms

    def stop_flash_animation(self):
        self.flash_timer.stop()
        self.update_font_and_style()  # Restore original color

    def on_flash_tick(self):
        self.flash_count += 1
        if self.flash_count > 10:  # Stop after 10 flashes
            self.stop_flash_animation()
            return

        if self.flash_count % 2 == 1:  # Odd tick, show flash color
            self.update_font_and_style(color=self.config["flash_color"])
        else:  # Even tick, show original color
            self.update_font_and_style()

    # --- System Tray and Window Events ---
    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        main_menu = QMenu()

        mode_menu = main_menu.addMenu("Switch Mode")
        mode_menu.addAction("Clock", lambda: self.set_mode(AppMode.CLOCK))
        mode_menu.addAction("Stopwatch", lambda: self.set_mode(AppMode.STOPWATCH))
        mode_menu.addAction("Timer", lambda: self.set_mode(AppMode.TIMER))

        main_menu.addSeparator()
        main_menu.addAction("Quit", self.quit_application)
        self.tray_icon.setContextMenu(main_menu)
        self.tray_icon.show()
        self.tray_icon.setToolTip("Time Utility")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.old_pos and event.buttons() == Qt.MouseButton.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.old_pos = None
        self.save_settings()

    def quit_application(self):
        self.save_settings()
        self.tray_icon.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        self.quit_application()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    clock = TimeUtilityApp()
    sys.exit(app.exec())