import sys
import re
from enum import Enum
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QMenu, QSystemTrayIcon, QInputDialog, QGraphicsDropShadowEffect,
                             QStyle, QDialog, QFormLayout, QSpinBox, QPushButton, QColorDialog,
                             QSlider, QHBoxLayout, QTabWidget, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, QTime, QPoint, QSettings, QDateTime, QElapsedTimer, QRectF, QSize
from PyQt6.QtGui import (QFont, QMouseEvent, QAction, QPainter, QPainterPath, 
                         QPen, QBrush, QFontMetrics, QColor)

# --- Define the different application modes ---
class AppMode(Enum):
    CLOCK = 0
    STOPWATCH = 1
    TIMER = 2
    POMODORO = 3

# --- Custom Outlined Label for Ghost Mode ---
class OutlinedLabel(QLabel):
    def sizeHint(self):
        font = self.font()
        metrics = QFontMetrics(font)
        text = self.text() if self.text() else "00:00:00"
        
        # Dynamically scale breathing room based on Control Panel slider
        pad = self.parent().config.get("rect_padding", 20) if self.parent() else 20
        width = metrics.horizontalAdvance(text) + (pad * 2)
        height = metrics.height() + (pad * 2)
        return QSize(int(width), int(height))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_hollow = False
        self.hollow_color = QColor("#FFFFFF")
        self.outline_thickness = 2
        self.progress = 0.0 # 0.0 to 1.0
        self.show_ring = False

    def set_hollow_style(self, enabled, color_hex="#FFFFFF", thickness=2):
        self.is_hollow = enabled
        self.hollow_color = QColor(color_hex)
        self.outline_thickness = thickness
        self.update()

    def set_progress(self, progress, show=True):
        self.progress = max(0.0, min(1.0, progress))
        self.show_ring = show
        self.update()

    def paintEvent(self, event):
        # 1. Draw Text (Solid or Hollow)
        if not self.is_hollow:
            super().paintEvent(event)
        else:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            text = self.text()
            font = self.font()
            painter.setFont(font)
            metrics = QFontMetrics(font)
            rect = self.rect()
            x = (rect.width() - metrics.horizontalAdvance(text)) / 2.0
            y = (rect.height() + metrics.ascent() - metrics.descent()) / 2.0
            path = QPainterPath()
            path.addText(x, y, font, text)
            pen = QPen(self.hollow_color)
            pen.setWidth(self.outline_thickness)
            painter.setPen(pen)
            painter.setBrush(QBrush(Qt.GlobalColor.transparent))
            painter.drawPath(path)
            painter.end()

        # 2. Draw the Tracing Progress Rectangle
        if self.show_ring:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.rect()
            
            # The box draws slightly inside the boundaries so shadows don't clip
            draw_rect = QRectF(4, 4, rect.width() - 8, rect.height() - 8)
            radius = 12.0
            
            # Create a path starting from Top-Center going Clockwise
            path = QPainterPath()
            path.moveTo(draw_rect.center().x(), draw_rect.top()) # Start Top Center
            path.lineTo(draw_rect.right() - radius, draw_rect.top())
            path.arcTo(draw_rect.right() - 2*radius, draw_rect.top(), 2*radius, 2*radius, 90, -90)
            path.lineTo(draw_rect.right(), draw_rect.bottom() - radius)
            path.arcTo(draw_rect.right() - 2*radius, draw_rect.bottom() - 2*radius, 2*radius, 2*radius, 0, -90)
            path.lineTo(draw_rect.left() + radius, draw_rect.bottom())
            path.arcTo(draw_rect.left(), draw_rect.bottom() - 2*radius, 2*radius, 2*radius, 270, -90)
            path.lineTo(draw_rect.left(), draw_rect.top() + radius)
            path.arcTo(draw_rect.left(), draw_rect.top(), 2*radius, 2*radius, 180, -90)
            path.lineTo(draw_rect.center().x(), draw_rect.top()) # Back to Top Center

            # Draw Faint Background Track
            bg_color = QColor(self.hollow_color)
            bg_color.setAlpha(40)
            pen = QPen(bg_color)
            pen.setWidthF(4.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawPath(path)

            # Draw Solid Active Progress (Traces the perimeter!)
            if self.progress > 0:
                fg_color = QColor(self.hollow_color)
                fg_color.setAlpha(255)
                pen.setColor(fg_color)
                
                # MAGIC TRICK: We use dashed lines to draw a percentage of the path!
                path_length = path.length()
                dash_len = (path_length * self.progress) / 4.0
                gap_len = (path_length + 50) / 4.0 # Massive gap so it doesn't repeat
                
                pen.setDashPattern([dash_len, gap_len])
                painter.setPen(pen)
                painter.drawPath(path)
                
            painter.end()
    

class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Widget Settings")
        self.setFixedSize(300, 150)
        self.new_config = current_config.copy()

        layout = QFormLayout(self)

        # Font Size Input
        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(10, 150)
        self.font_size_input.setValue(self.new_config["font_size"])
        layout.addRow("Font Size:", self.font_size_input)

        # Color Picker Button
        self.color_btn = QPushButton("Pick Color")
        self.color_btn.clicked.connect(self.pick_color)
        layout.addRow("Text Color:", self.color_btn)

        # Save/Cancel Buttons
        self.save_btn = QPushButton("Save & Apply")
        self.save_btn.clicked.connect(self.accept) # 'accept' closes dialog successfully
        layout.addRow("", self.save_btn)

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.new_config["text_color"] = color.name()

    def get_config(self):
        self.new_config["font_size"] = self.font_size_input.value()
        return self.new_config


# --- REPLACE ENTIRE ControlPanel CLASS ---
class ControlPanel(QDialog):
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.setWindowTitle("Control Panel")
        self.setFixedSize(400, 480) # Increased height for new settings
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #cdd6f4; font-size: 14px; font-weight: 500; }
            QTabWidget::pane { border: 1px solid #313244; border-radius: 8px; background: #181825; }
            QTabBar::tab { background: #1e1e2e; color: #a6adc8; padding: 10px 20px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
            QTabBar::tab:selected { background: #313244; color: #89b4fa; font-weight: bold; }
            QPushButton { background-color: #89b4fa; color: #11111b; border: none; border-radius: 6px; padding: 10px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #b4befe; }
            QPushButton:disabled { background-color: #45475a; color: #a6adc8; }
            QComboBox, QSpinBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 6px; }
            QSlider::groove:horizontal { border-radius: 4px; height: 8px; background: #313244; }
            QSlider::handle:horizontal { background: #89b4fa; width: 16px; height: 16px; margin: -4px 0; border-radius: 8px; }
            QCheckBox { font-size: 14px; font-weight: bold; color: #f38ba8; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; background-color: #313244; border: 1px solid #45475a;}
            QCheckBox::indicator:checked { background-color: #f38ba8; }
        """)
        
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        
        # --- TAB 1: Controls ---
        control_tab = QWidget()
        c_layout = QVBoxLayout(control_tab)
        
        self.ghost_check = QCheckBox("Enable Ghost Mode (Unclickable)")
        self.ghost_check.setChecked(self.app.ghost_mode_enabled)
        self.ghost_check.toggled.connect(self.toggle_ghost)
        c_layout.addWidget(self.ghost_check)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Clock", "Stopwatch", "Timer", "Pomodoro"])
        self.mode_combo.setCurrentIndex(self.app.current_mode.value)
        self.mode_combo.currentIndexChanged.connect(self.change_mode)
        c_layout.addWidget(QLabel("Current Mode:"))
        c_layout.addWidget(self.mode_combo)
        
        self.set_duration_btn = QPushButton("Set Timer Duration")
        self.set_duration_btn.clicked.connect(self.app.action_timer_set)
        
        self.start_btn = QPushButton("Start / Pause")
        self.start_btn.clicked.connect(self.toggle_action)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.app.action_stopwatch_reset if self.app.current_mode == AppMode.STOPWATCH else self.app.action_timer_reset)
        
        c_layout.addWidget(self.set_duration_btn)
        c_layout.addWidget(self.start_btn)
        c_layout.addWidget(self.reset_btn)
        c_layout.addStretch()
        tabs.addTab(control_tab, "Controls")

        # --- TAB 2: Settings ---
        settings_tab = QWidget()
        s_layout = QFormLayout(settings_tab)
        
        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 150)
        self.font_spin.setValue(self.app.config["font_size"])
        
        self.color_btn = QPushButton("Pick Accent Color")
        self.color_btn.clicked.connect(self.pick_color)
        self.temp_color = self.app.config["text_color"]
        
        self.thick_slider = QSlider(Qt.Orientation.Horizontal)
        self.thick_slider.setRange(1, 8)
        self.thick_slider.setValue(self.app.config["outline_thickness"])
        self.thick_slider.valueChanged.connect(self.live_update_settings)
        
        self.shadow_slider = QSlider(Qt.Orientation.Horizontal)
        self.shadow_slider.setRange(0, 15)
        self.shadow_slider.setValue(self.app.config["shadow_depth"])
        self.shadow_slider.valueChanged.connect(self.live_update_settings)
        
        self.pad_slider = QSlider(Qt.Orientation.Horizontal)
        self.pad_slider.setRange(10, 60) # Padding limits
        self.pad_slider.setValue(self.app.config.get("rect_padding", 20))
        self.pad_slider.valueChanged.connect(self.live_update_settings)

        self.pomo_work_spin = QSpinBox()
        self.pomo_work_spin.setRange(1, 120)
        self.pomo_work_spin.setValue(self.app.config["pomo_work_min"])
        
        self.pomo_break_spin = QSpinBox()
        self.pomo_break_spin.setRange(1, 60)
        self.pomo_break_spin.setValue(self.app.config["pomo_break_min"])
        
        s_layout.addRow("Font Size:", self.font_spin)
        s_layout.addRow("Accent Color:", self.color_btn)
        s_layout.addRow("Outline Thickness:", self.thick_slider)
        s_layout.addRow("Shadow Depth:", self.shadow_slider)
        s_layout.addRow("Rectangle Scale:", self.pad_slider) # <--- NEW SLIDER ADDED HERE
        s_layout.addRow("Pomo Work (min):", self.pomo_work_spin)
        s_layout.addRow("Pomo Break (min):", self.pomo_break_spin)
        
        save_btn = QPushButton("Save All Settings")
        save_btn.clicked.connect(self.save_all_settings)
        s_layout.addRow("", save_btn)
        
        tabs.addTab(settings_tab, "Settings")
        layout.addWidget(tabs)

        self.quit_btn = QPushButton("Quit Application")
        self.quit_btn.setStyleSheet("background-color: #f38ba8; color: #11111b; margin-top: 10px;")
        self.quit_btn.clicked.connect(self.app.quit_application)
        layout.addWidget(self.quit_btn)

        self.update_ui_for_mode(self.app.current_mode)

    def toggle_ghost(self, checked):
        self.app.toggle_ghost_mode(checked)
        # Update tray icon to stay in sync
        self.app.ghost_action.setChecked(checked)

    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.temp_color), self)
        if color.isValid():
            self.temp_color = color.name()

    def change_mode(self, index):
        mode = AppMode(index)
        self.app.set_mode(mode)
        if mode == AppMode.POMODORO:
            self.app.pomo_is_work = True
            self.app.timer_paused_duration_ms = self.app.config["pomo_work_min"] * 60000
            self.app.timer_total_duration_ms = self.app.timer_paused_duration_ms
            self.app.update_display()
        self.update_ui_for_mode(mode)

    def update_ui_for_mode(self, mode):
        is_clock = (mode == AppMode.CLOCK)
        self.start_btn.setDisabled(is_clock)
        self.reset_btn.setDisabled(is_clock)
        self.set_duration_btn.setVisible(mode == AppMode.TIMER)

    def toggle_action(self):
        if self.app.current_mode == AppMode.STOPWATCH:
            self.app.action_stopwatch_start_pause()
        elif self.app.current_mode in[AppMode.TIMER, AppMode.POMODORO]:
            if getattr(self.app, 'timer_total_duration_ms', 0) == 0:
                self.app.timer_total_duration_ms = self.app.timer_paused_duration_ms
            self.app.action_timer_start_pause()

    def live_update_settings(self):
        self.app.config["outline_thickness"] = self.thick_slider.value()
        self.app.config["shadow_depth"] = self.shadow_slider.value()
        self.app.config["rect_padding"] = self.pad_slider.value() # Live update padding
        
        self.app.shadow.setOffset(self.app.config["shadow_depth"], self.app.config["shadow_depth"])
        self.app.time_label.set_hollow_style(self.app.ghost_mode_enabled, self.app.config["text_color"], self.app.config["outline_thickness"])
        
        # Force the label to recalculate its sizeHint based on the new padding
        self.app.time_label.updateGeometry()
        self.app.adjustSize()

    def save_all_settings(self):
        self.app.config["font_size"] = self.font_spin.value()
        self.app.config["text_color"] = self.temp_color
        self.app.config["pomo_work_min"] = self.pomo_work_spin.value()
        self.app.config["pomo_break_min"] = self.pomo_break_spin.value()
        self.app.config["rect_padding"] = self.pad_slider.value()
        
        self.app.update_font_and_style()
        self.app.time_label.updateGeometry()
        self.app.adjustSize()
        self.app.save_settings() # NOW THIS ACTUALLY SAVES PERMANENTLY!
        self.accept()

class TimeUtilityApp(QWidget):
    def __init__(self):
        super().__init__()
        self.old_pos = None
        self.current_mode = AppMode.CLOCK
        self.ghost_mode_enabled = False

        # Stopwatch state
        self.stopwatch_timer = QElapsedTimer()
        self.stopwatch_running = False
        self.stopwatch_paused_ms = 0

        # Timer state
        self.timer_end_time = None
        self.timer_running = False
        self.timer_paused_duration_ms = 0
        self.flash_timer = QTimer(self)
        self.flash_timer.timeout.connect(self.on_flash_tick)
        self.flash_count = 0

        # Configuration
        self.config = {
            "font_family": "Segoe UI",
            "font_size": 48,
            "font_weight": QFont.Weight.Bold,
            "text_color": "#FFFFFF",
            "flash_color": "#FFD700",  
            "initial_pos_x": 100,
            "initial_pos_y": 100,
            "outline_thickness": 2,
            "shadow_depth": 3,
            "pomo_work_min": 25,
            "pomo_break_min": 5,
            "rect_padding": 20,
        }
        self.load_settings()

        self.pomo_is_work = True # Tracks if currently in work or break cycle

        self.initUI()
        self.init_tray_icon()

    def load_settings(self):
        settings = QSettings("MyTimeUtility", "TimeApp")
        pos = self.pos()
        self.config["initial_pos_x"] = settings.value("pos_x", pos.x(), type=int)
        self.config["initial_pos_y"] = settings.value("pos_y", pos.y(), type=int)
        
        last_mode = settings.value("last_mode", AppMode.CLOCK.value, type=int)
        self.current_mode = AppMode(last_mode)
        self.ghost_mode_enabled = settings.value("ghost_mode", False, type=bool)
        
        # Load all our new custom configs!
        self.config["font_size"] = settings.value("font_size", 48, type=int)
        self.config["text_color"] = settings.value("text_color", "#FFFFFF", type=str)
        self.config["outline_thickness"] = settings.value("outline_thickness", 2, type=int)
        self.config["shadow_depth"] = settings.value("shadow_depth", 3, type=int)
        self.config["pomo_work_min"] = settings.value("pomo_work_min", 25, type=int)
        self.config["pomo_break_min"] = settings.value("pomo_break_min", 5, type=int)
        self.config["rect_padding"] = settings.value("rect_padding", 20, type=int)

    def save_settings(self):
        settings = QSettings("MyTimeUtility", "TimeApp")
        settings.setValue("pos_x", self.pos().x())
        settings.setValue("pos_y", self.pos().y())
        settings.setValue("last_mode", self.current_mode.value)
        settings.setValue("ghost_mode", self.ghost_mode_enabled)
        
        # Save all custom configs permanently
        settings.setValue("font_size", self.config["font_size"])
        settings.setValue("text_color", self.config["text_color"])
        settings.setValue("outline_thickness", self.config["outline_thickness"])
        settings.setValue("shadow_depth", self.config["shadow_depth"])
        settings.setValue("pomo_work_min", self.config["pomo_work_min"])
        settings.setValue("pomo_break_min", self.config["pomo_break_min"])
        settings.setValue("rect_padding", self.config["rect_padding"])

    def initUI(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")

        # Use our custom OutlinedLabel
        self.time_label = OutlinedLabel(self)
        self.update_font_and_style()
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Apply Drop Shadow for Depth/Visibility
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 200))
        self.shadow.setOffset(self.config["shadow_depth"], self.config["shadow_depth"])
        self.time_label.setGraphicsEffect(self.shadow)

        layout = QVBoxLayout()
        layout.addWidget(self.time_label)
        layout.setContentsMargins(30, 30, 30, 30)
        self.setLayout(layout)

        self.setGeometry(self.config["initial_pos_x"], self.config["initial_pos_y"], 450, 70)
        self.setMinimumSize(200, 60)
        self.adjustSize()

        # Apply Ghost Mode state on boot
        self.toggle_ghost_mode(self.ghost_mode_enabled)

        # Main UI update loop
        self.main_timer = QTimer(self)
        self.main_timer.timeout.connect(self.update_display)
        self.main_timer.start(33)

        self.setWindowTitle("Time Utility")
        self.show()

    def update_font_and_style(self, color=None):
        if color is None:
            color = self.config["text_color"]
            
        font = QFont(self.config["font_family"], self.config["font_size"], self.config["font_weight"])
        self.time_label.setFont(font)
        
        # Apply standard CSS, but also pass color to outline logic for Ghost Mode
        self.time_label.setStyleSheet(f"color: {color}; background:transparent;")
        self.time_label.set_hollow_style(self.ghost_mode_enabled, color)

    def update_display(self):
        display_text = ""
        progress_val = 0.0
        show_ring = False

        if self.current_mode == AppMode.CLOCK:
            display_text = QTime.currentTime().toString("hh:mm:ss AP")

        elif self.current_mode == AppMode.STOPWATCH:
            elapsed = self.stopwatch_timer.elapsed() + self.stopwatch_paused_ms if self.stopwatch_running else self.stopwatch_paused_ms
            time = QTime(0, 0, 0, 0).addMSecs(elapsed)
            display_text = time.toString("HH:mm:ss.zzz")[:-1]

        elif self.current_mode == AppMode.TIMER or self.current_mode == AppMode.POMODORO:
            show_ring = True
            if self.timer_running:
                remaining_ms = QDateTime.currentDateTime().msecsTo(self.timer_end_time)
                if remaining_ms <= 0:
                    remaining_ms = 0
                    self.timer_running = False
                    self.start_flash_animation()
                    # Pomodoro Auto-Switch
                    if self.current_mode == AppMode.POMODORO:
                        self.pomo_is_work = not self.pomo_is_work
                        mins = self.config["pomo_work_min"] if self.pomo_is_work else self.config["pomo_break_min"]
                        self.timer_paused_duration_ms = mins * 60000
                
                # Calculate progress ring
                total_ms = self.timer_paused_duration_ms if not self.timer_running else self.timer_total_duration_ms 
                if total_ms > 0:
                    progress_val = remaining_ms / total_ms
                
                time = QTime(0, 0, 0, 0).addMSecs(max(0, remaining_ms))
                display_text = time.toString("HH:mm:ss")
            else:
                time = QTime(0, 0, 0, 0).addMSecs(self.timer_paused_duration_ms)
                display_text = time.toString("HH:mm:ss")
                progress_val = 1.0

            if self.current_mode == AppMode.POMODORO:
                prefix = "WORK: " if self.pomo_is_work else "BREAK: "
                display_text = prefix + display_text

        if self.time_label.text() != display_text:
            self.time_label.setText(display_text)
            self.time_label.set_progress(progress_val, show_ring)
            self.adjustSize()

    # --- Mode Switching, Context Menu, Actions... ---
    # (Methods: set_mode, contextMenuEvent, action_stopwatch_*, action_timer_* remain unchanged)
    def set_mode(self, mode: AppMode):
        self.current_mode = mode
        if mode != AppMode.STOPWATCH: self.action_stopwatch_reset()
        if mode != AppMode.TIMER: self.action_timer_reset()
        self.update_display()
        self.save_settings()

    def contextMenuEvent(self, event):
        if self.ghost_mode_enabled: return
        self.open_control_panel()

    def action_stopwatch_start_pause(self):
        if self.stopwatch_running:
            self.stopwatch_paused_ms += self.stopwatch_timer.elapsed()
            self.stopwatch_running = False
        else:
            self.stopwatch_timer.start()
            self.stopwatch_running = True

    def action_stopwatch_reset(self):
        self.stopwatch_running = False
        self.stopwatch_paused_ms = 0
        self.update_display()

    def action_timer_set(self):
        self.stop_flash_animation()
        duration_str, ok = QInputDialog.getText(self, "Set Timer", "Enter duration (e.g., '1h 30m', '45s'):")
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
            parts = re.findall(r'(\d+)\s*(h|m|s)?', s)
            if not parts: return int(s) * 1000
            for value, unit in parts:
                value = int(value)
                if unit == 'h': total_ms += value * 3600000
                elif unit == 'm': total_ms += value * 60000
                elif unit == 's' or unit is None: total_ms += value * 1000
            return total_ms
        except (ValueError, TypeError):
            return 0

    def action_timer_start_pause(self):
        if self.timer_running:
            self.timer_paused_duration_ms = QDateTime.currentDateTime().msecsTo(self.timer_end_time)
            self.timer_running = False
        elif self.timer_paused_duration_ms > 0:
            self.timer_end_time = QDateTime.currentDateTime().addMSecs(self.timer_paused_duration_ms)
            self.timer_running = True
            self.stop_flash_animation()

    def action_timer_reset(self):
        self.timer_running = False
        self.stop_flash_animation()
        
        # Logic fix: Pomodoro should refill, standard Timer goes to zero
        if self.current_mode == AppMode.POMODORO:
            mins = self.config["pomo_work_min"] if self.pomo_is_work else self.config["pomo_break_min"]
            self.timer_paused_duration_ms = mins * 60000
            self.timer_total_duration_ms = self.timer_paused_duration_ms # Reset total for progress bar
        else:
            self.timer_paused_duration_ms = 0
            self.timer_total_duration_ms = 0
            
        self.update_display()

    def start_flash_animation(self):
        QApplication.beep()
        self.flash_count = 0
        self.flash_timer.start(250)

    def stop_flash_animation(self):
        self.flash_timer.stop()
        self.update_font_and_style()

    def on_flash_tick(self):
        self.flash_count += 1
        if self.flash_count > 10:
            self.stop_flash_animation()
            return
        if self.flash_count % 2 == 1:
            self.update_font_and_style(color=self.config["flash_color"])
        else:
            self.update_font_and_style()

    # --- System Tray ---
    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)

        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)

        main_menu = QMenu()

        cp_action = QAction("Open Control Panel", self)
        cp_action.triggered.connect(self.open_control_panel)
        main_menu.addAction(cp_action)
        main_menu.addSeparator()

        # Ghost Mode Toggle in Tray Menu
        self.ghost_action = QAction("Ghost Mode (Unclickable)", self, checkable=True)
        self.ghost_action.setChecked(self.ghost_mode_enabled)
        self.ghost_action.triggered.connect(self.toggle_ghost_mode_from_tray)
        main_menu.addAction(self.ghost_action)
        main_menu.addSeparator()

        mode_menu = main_menu.addMenu("Switch Mode")
        mode_menu.addAction("Clock", lambda: self.set_mode(AppMode.CLOCK))
        mode_menu.addAction("Stopwatch", lambda: self.set_mode(AppMode.STOPWATCH))
        mode_menu.addAction("Timer", lambda: self.set_mode(AppMode.TIMER))

        main_menu.addSeparator()
        main_menu.addAction("Quit", self.quit_application)
        self.tray_icon.setContextMenu(main_menu)
        self.tray_icon.show()
        self.tray_icon.setToolTip("Time Utility")

    def toggle_ghost_mode_from_tray(self, enabled):
        self.toggle_ghost_mode(enabled)
        self.save_settings()

    def toggle_ghost_mode(self, enabled):
        """Toggles the click-through property and hollow text styling."""
        self.ghost_mode_enabled = enabled
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, enabled)
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, enabled)
        self.time_label.set_hollow_style(enabled, self.config["text_color"], self.config["outline_thickness"])
        
        # Ensure the Tray Icon checkbox is synced if it was triggered from Control Panel
        if hasattr(self, 'ghost_action'):
            self.ghost_action.setChecked(enabled)
            
        self.show()

    # --- Dynamic Click Interaction (Tactile Feedback) ---
    def mousePressEvent(self, event: QMouseEvent):
        if self.ghost_mode_enabled: return

        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()
            # Compress shadow to simulate "pressing down"
            self.shadow.setOffset(0, 0)
            self.shadow.setBlurRadius(5)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.ghost_mode_enabled: return

        if self.old_pos and event.buttons() == Qt.MouseButton.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.ghost_mode_enabled: return

        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None
            self.save_settings()
            # Expand shadow to simulate "popping up"
            self.shadow.setOffset(3, 3)
            self.shadow.setBlurRadius(15)

    def quit_application(self):
        self.save_settings()
        self.tray_icon.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        self.quit_application()

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec(): # If the user clicked "Save & Apply"
            self.config = dialog.get_config()
            self.update_font_and_style()
            self.adjustSize()
            self.save_settings()
    def open_control_panel(self):
        self.cp = ControlPanel(self)
        self.cp.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    clock = TimeUtilityApp()
    sys.exit(app.exec())