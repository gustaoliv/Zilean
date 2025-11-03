#!/usr/bin/env python3
"""
Modern Zilean - Floating Jira Time Tracker Widget
A sleek, always-on-top time tracking widget for Jira integration with time tracking reports
"""
import sys
import json
import time
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QComboBox, QSystemTrayIcon, 
    QMenu, QDialog, QFormLayout, QLineEdit, QMessageBox,
    QGraphicsDropShadowEffect, QTextEdit, QScrollArea
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, 
    QRect, Signal, QThread
)
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor

# Import existing domain models
from Domain.Models.Card import Card
from Domain.Interfaces.IBoardIntegration import IBoardIntegration
from Infraestructure.JiraIntegration import JiraIntegration

@dataclass
class TimeEntry:
    """Represents a time log entry"""
    card_id: str
    card_name: str
    duration_seconds: int
    timestamp: str  # ISO format datetime
    
    def to_dict(self):
        return {
            'card_id': self.card_id,
            'card_name': self.card_name,
            'duration_seconds': self.duration_seconds,
            'timestamp': self.timestamp
        }
    
    @staticmethod
    def from_dict(data):
        return TimeEntry(
            card_id=data['card_id'],
            card_name=data['card_name'],
            duration_seconds=data['duration_seconds'],
            timestamp=data['timestamp']
        )

class TimeLogger:
    """Handles time logging to local file"""
    
    def __init__(self, log_path: str = "time_logs.json"):
        self.log_path = Path(log_path)
        self.entries: List[TimeEntry] = []
        self.load_entries()
    
    def load_entries(self):
        """Load entries from file"""
        if self.log_path.exists():
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = [TimeEntry.from_dict(entry) for entry in data]
            except Exception as e:
                print(f"Error loading time logs: {e}")
                self.entries = []
    
    def save_entries(self):
        """Save entries to file"""
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                data = [entry.to_dict() for entry in self.entries]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving time logs: {e}")
    
    def add_entry(self, card_id: str, card_name: str, duration_seconds: int):
        """Add a new time entry"""
        entry = TimeEntry(
            card_id=card_id,
            card_name=card_name,
            duration_seconds=duration_seconds,
            timestamp=datetime.now().isoformat()
        )
        self.entries.append(entry)
        self.save_entries()
    
    def get_entries_by_date_range(self, start_date: datetime, end_date: datetime) -> List[TimeEntry]:
        """Get entries within a date range"""
        filtered_entries = []
        for entry in self.entries:
            entry_date = datetime.fromisoformat(entry.timestamp)
            if start_date <= entry_date <= end_date:
                filtered_entries.append(entry)
        return filtered_entries

class ReportDialog(QDialog):
    """Dialog to display time tracking reports"""
    
    def __init__(self, time_logger: TimeLogger, primary_color: str, parent=None):
        super().__init__(parent)
        self.time_logger = time_logger
        self.primary_color = primary_color
        self.setup_ui()
        self.generate_weekly_report()
    
    def setup_ui(self):
        """Setup the report dialog UI"""
        self.setWindowTitle("Relatório de Tempo")
        self.resize(700, 600)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("📊 Relatório de Tempo Registrado")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.primary_color};
            padding: 10px;
        """)
        layout.addWidget(title)
        
        # Period selector
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Período:"))
        
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "Semana Atual",
            "Semana Passada",
            "Últimos 7 dias",
            "Últimos 30 dias",
            "Mês Atual"
        ])
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        period_layout.addWidget(self.period_combo)
        period_layout.addStretch()
        
        layout.addLayout(period_layout)
        
        # Report text area with scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        scroll_area.setWidget(self.report_text)
        
        layout.addWidget(scroll_area)
        
        # Close button
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        self.apply_style()
    
    def apply_style(self):
        """Apply styling to the dialog"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #2b2b2b;
                color: white;
            }}
            QLabel {{
                color: white;
            }}
            QComboBox {{
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: white;
                min-width: 200px;
            }}
            QComboBox:hover {{
                background-color: #4a4a4a;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: #3a3a3a;
                border: 1px solid #555;
                selection-background-color: {self.primary_color};
                color: white;
            }}
            QTextEdit {{
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 15px;
                color: white;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
                line-height: 1.6;
            }}
            QPushButton {{
                background-color: {self.primary_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.adjust_color_brightness(self.primary_color, 1.2)};
            }}
            QScrollArea {{
                border: none;
            }}
        """)
    
    def adjust_color_brightness(self, hex_color: str, factor: float) -> str:
        """Adjust color brightness by a factor"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def on_period_changed(self, period: str):
        """Handle period selection change"""
        if period == "Semana Atual":
            self.generate_weekly_report()
        elif period == "Semana Passada":
            self.generate_last_week_report()
        elif period == "Últimos 7 dias":
            self.generate_last_n_days_report(7)
        elif period == "Últimos 30 dias":
            self.generate_last_n_days_report(30)
        elif period == "Mês Atual":
            self.generate_current_month_report()
    
    def get_week_start_end(self, date: datetime = None) -> tuple:
        """Get the start and end of the week (Monday to Sunday)"""
        if date is None:
            date = datetime.now()
        
        # Get Monday of the current week
        start = date - timedelta(days=date.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get Sunday of the current week
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        return start, end
    
    def generate_weekly_report(self):
        """Generate report for current week"""
        start_date, end_date = self.get_week_start_end()
        self.generate_report(start_date, end_date, f"Semana Atual ({start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')})")
    
    def generate_last_week_report(self):
        """Generate report for last week"""
        today = datetime.now()
        last_week = today - timedelta(days=7)
        start_date, end_date = self.get_week_start_end(last_week)
        self.generate_report(start_date, end_date, f"Semana Passada ({start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')})")
    
    def generate_last_n_days_report(self, n: int):
        """Generate report for last N days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=n-1)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        self.generate_report(start_date, end_date, f"Últimos {n} dias ({start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')})")
    
    def generate_current_month_report(self):
        """Generate report for current month"""
        today = datetime.now()
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Last day of current month
        if today.month == 12:
            end_date = today.replace(year=today.year+1, month=1, day=1) - timedelta(seconds=1)
        else:
            end_date = today.replace(month=today.month+1, day=1) - timedelta(seconds=1)
        
        self.generate_report(start_date, end_date, f"Mês Atual ({start_date.strftime('%B %Y')})")
    
    def format_duration(self, seconds: int) -> str:
        """Format duration in seconds to readable format"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def generate_report(self, start_date: datetime, end_date: datetime, period_name: str):
        """Generate and display report for given date range"""
        entries = self.time_logger.get_entries_by_date_range(start_date, end_date)
        
        if not entries:
            self.report_text.setHtml(f"""
                <h2 style='color: {self.primary_color};'>{period_name}</h2>
                <p style='color: #999; font-size: 14px;'>Nenhum registro encontrado para este período.</p>
            """)
            return
        
        # Calculate totals
        total_seconds = sum(entry.duration_seconds for entry in entries)
        unique_cards = set(entry.card_id for entry in entries)
        
        # Group by date
        entries_by_date = {}
        for entry in entries:
            entry_date = datetime.fromisoformat(entry.timestamp).date()
            if entry_date not in entries_by_date:
                entries_by_date[entry_date] = []
            entries_by_date[entry_date].append(entry)
        
        # Build HTML report
        html = f"""
        <div style='font-family: "Segoe UI", Arial, sans-serif;'>
            <h2 style='color: {self.primary_color}; margin-bottom: 20px;'>{period_name}</h2>
            
            <div style='background-color: #2a2a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px;'>
                <h3 style='color: {self.primary_color}; margin-top: 0;'>📈 Resumo Geral</h3>
                <p style='margin: 8px 0;'><strong>⏱️ Total Registrado:</strong> {self.format_duration(total_seconds)}</p>
                <p style='margin: 8px 0;'><strong>📋 Tarefas Trabalhadas:</strong> {len(unique_cards)}</p>
            </div>
        """
        
        # Sort dates
        sorted_dates = sorted(entries_by_date.keys(), reverse=True)
        
        # Add daily breakdown
        weekday_names = {
            0: 'Segunda-feira',
            1: 'Terça-feira',
            2: 'Quarta-feira',
            3: 'Quinta-feira',
            4: 'Sexta-feira',
            5: 'Sábado',
            6: 'Domingo'
        }
        
        for date in sorted_dates:
            date_entries = entries_by_date[date]
            weekday = weekday_names[date.weekday()]
            date_str = date.strftime('%d/%m/%Y')
            
            # Calculate total for the day
            day_total_seconds = sum(entry.duration_seconds for entry in date_entries)
            
            html += f"""
            <div style='background-color: #252525; padding: 12px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid {self.primary_color};'>
                <h4 style='color: {self.primary_color}; margin: 0 0 10px 0;'>
                    📅 {weekday} - {date_str}
                    <span style='color: #999; font-weight: normal; font-size: 12px;'>({self.format_duration(day_total_seconds)})</span>
                </h4>
            """
            
            # Group by card for the day
            card_times = {}
            for entry in date_entries:
                if entry.card_id not in card_times:
                    card_times[entry.card_id] = {
                        'name': entry.card_name,
                        'total_seconds': 0
                    }
                card_times[entry.card_id]['total_seconds'] += entry.duration_seconds
            
            # Display cards for the day
            for card_id, data in card_times.items():
                html += f"""
                <div style='margin-left: 15px; margin-bottom: 8px;'>
                    <span style='color: #aaa;'>({card_id})</span> 
                    <span style='color: white;'>{data['name'][:60]}{'...' if len(data['name']) > 60 else ''}</span>
                    <span style='color: {self.primary_color}; font-weight: bold;'> → {self.format_duration(data['total_seconds'])}</span>
                </div>
                """
            
            html += "</div>"
        
        html += "</div>"
        
        self.report_text.setHtml(html)

@dataclass
class AppConfig:
    """Application configuration"""
    jira_server: str = ""
    email: str = ""
    token: str = ""
    widget_position: tuple = (50, 50)
    always_on_top: bool = True
    collapsed: bool = False
    primary_color: str = "#8A2BE2"  # Default purple color

class ConfigManager:
    """Handles configuration persistence"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = AppConfig()
    
    def load(self) -> AppConfig:
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.config = AppConfig(**data)
            except Exception as e:
                print(f"Error loading config: {e}")
        return self.config
    
    def save(self, config: AppConfig):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config.__dict__, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

class SettingsDialog(QDialog):
    """Settings dialog for Jira configuration"""
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Zilean Settings")
        self.setModal(True)
        self.resize(400, 200)
        
        layout = QFormLayout()
        
        self.server_input = QLineEdit(self.config.jira_server)
        self.server_input.setPlaceholderText("https://your-domain.atlassian.net")
        layout.addRow("Jira Server:", self.server_input)
        
        self.email_input = QLineEdit(self.config.email)
        self.email_input.setPlaceholderText("your-email@company.com")
        layout.addRow("Email:", self.email_input)
        
        self.token_input = QLineEdit(self.config.token)
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setPlaceholderText("Your Jira API token")
        layout.addRow("API Token:", self.token_input)
        
        # Primary color selection
        color_layout = QHBoxLayout()
        self.color_input = QLineEdit(self.config.primary_color)
        self.color_input.setPlaceholderText("#8A2BE2")
        color_preview = QPushButton()
        color_preview.setFixedSize(30, 25)
        color_preview.setStyleSheet(f"background-color: {self.config.primary_color}; border: 1px solid #ccc; border-radius: 4px;")
        color_preview.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_input)
        color_layout.addWidget(color_preview)
        self.color_preview = color_preview
        layout.addRow("Primary Color:", color_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        
        save_btn.clicked.connect(self.save_settings)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addRow(button_layout)
        self.setLayout(layout)
    
    def choose_color(self):
        """Open color picker dialog"""
        from PySide6.QtWidgets import QColorDialog
        from PySide6.QtGui import QColor
        
        current_color = QColor(self.config.primary_color)
        color = QColorDialog.getColor(current_color, self, "Choose Primary Color")
        
        if color.isValid():
            color_hex = color.name()
            self.color_input.setText(color_hex)
            self.color_preview.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #ccc; border-radius: 4px;")
    
    def save_settings(self):
        self.config.jira_server = self.server_input.text().strip()
        self.config.email = self.email_input.text().strip()
        self.config.token = self.token_input.text().strip()
        self.config.primary_color = self.color_input.text().strip() or "#8A2BE2"
        
        if not all([self.config.jira_server, self.config.email, self.config.token]):
            QMessageBox.warning(self, "Warning", "All fields are required!")
            return
        
        self.accept()

class JiraWorker(QThread):
    """Background worker for Jira operations"""
    cards_loaded = Signal(list)
    error_occurred = Signal(str)
    
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.jira_integration: Optional[IBoardIntegration] = None
    
    def run(self):
        try:
            self.jira_integration = JiraIntegration(
                self.config.jira_server,
                self.config.email,
                self.config.token
            )
            cards = self.jira_integration.get_cards()
            self.cards_loaded.emit(cards)
        except Exception as e:
            self.error_occurred.emit(str(e))

class FloatingWidget(QWidget):
    """Main floating widget for time tracking"""
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()
        
        # Time logger
        self.time_logger = TimeLogger()
        
        # State
        self.cards: List[Card] = []
        self.current_card: Optional[Card] = None
        self.is_collapsed = self.config.collapsed
        self.is_running = False
        self.is_paused = False
        self.elapsed_time = 0
        self.start_time = 0
        self.rebuilding_ui = False
        
        # Jira integration
        self.jira_integration: Optional[IBoardIntegration] = None
        self.jira_worker: Optional[JiraWorker] = None
        
        # UI setup
        self.setup_ui()
        self.setup_style()
        self.setup_timers()
        self.setup_system_tray()
        
        # Load cards if configured
        if self.is_configured():
            self.load_cards()
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)
        
        # Main layout
        self.main_layout = QVBoxLayout()
        if self.is_collapsed:
            self.main_layout.setContentsMargins(6, 4, 6, 4)
            self.main_layout.setSpacing(2)
        else:
            self.main_layout.setContentsMargins(12, 8, 12, 8)
            self.main_layout.setSpacing(6)
        
        # Header (always visible)
        self.setup_header()
        
        # Expandable content
        self.setup_content()
        
        self.setLayout(self.main_layout)
        
        # Set initial size and position
        self.resize(450 if not self.is_collapsed else 180, 140 if not self.is_collapsed else 60)
        self.position_widget()
        
        # Update visibility
        self.update_visibility()
    
    def position_widget(self):
        """Position widget in top-right corner or use saved position"""
        if self.config.widget_position == (50, 50):
            screen = QApplication.primaryScreen().geometry()
            widget_width = 130 if self.is_collapsed else 450
            x = screen.width() - widget_width - 20
            y = 20
            self.move(x, y)
            self.config.widget_position = (x, y)
            self.config_manager.save(self.config)
        else:
            self.move(*self.config.widget_position)
    
    def setup_header(self):
        """Setup the header with timer and buttons"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 4, 4, 4)
        header_layout.setSpacing(4 if self.is_collapsed else 8)
        
        # Timer display
        current_time = self.get_current_time_display()
        self.timer_label = QLabel(current_time)
        self.timer_label.setObjectName("timer")
        header_layout.addWidget(self.timer_label)
        
        if not self.is_collapsed:
            header_layout.addStretch()
        
        # Report button (only show when expanded)
        if not self.is_collapsed:
            self.report_btn = QPushButton("📊")
            self.report_btn.setObjectName("iconButton")
            self.report_btn.setFixedSize(24, 24)
            self.report_btn.setToolTip("Ver Relatórios")
            self.report_btn.clicked.connect(self.show_reports)
            header_layout.addWidget(self.report_btn)
        
        # Settings button (only show when expanded)
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setObjectName("iconButton")
        self.settings_btn.setFixedSize(20 if self.is_collapsed else 24, 20 if self.is_collapsed else 24)
        self.settings_btn.clicked.connect(self.show_settings)
        if not self.is_collapsed:
            header_layout.addWidget(self.settings_btn)
        
        # Reload button (only show when expanded)
        if not self.is_collapsed:
            self.reload_btn = QPushButton("🔄")
            self.reload_btn.setObjectName("iconButton")
            self.reload_btn.setFixedSize(24, 24)
            self.reload_btn.clicked.connect(self.reload_cards)
            header_layout.addWidget(self.reload_btn)
        
        # Close button (only show when expanded)
        if not self.is_collapsed:
            self.close_btn = QPushButton("✕")
            self.close_btn.setObjectName("iconButton")
            self.close_btn.setFixedSize(24, 24)
            self.close_btn.clicked.connect(self.quit_app)
            header_layout.addWidget(self.close_btn)
        
        # Toggle button
        self.toggle_btn = QPushButton("+" if self.is_collapsed else "-")
        self.toggle_btn.setObjectName("iconButton")
        self.toggle_btn.setFixedSize(28 if self.is_collapsed else 24, 28 if self.is_collapsed else 24)
        self.toggle_btn.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.toggle_btn)
        
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        self.main_layout.addWidget(header_widget)
    
    def setup_content(self):
        """Setup the expandable content area"""
        self.content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(4)
        
        # Card info
        self.card_label = QLabel("No card selected")
        self.card_label.setObjectName("cardInfo")
        content_layout.addWidget(self.card_label)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(10, 10, 10, 10)
        
        self.play_btn = QPushButton("▶️")
        self.play_btn.setObjectName("controlButton")
        self.play_btn.clicked.connect(self.start_timer)
        
        self.pause_btn = QPushButton("⏸️")
        self.pause_btn.setObjectName("controlButton")
        self.pause_btn.clicked.connect(self.pause_timer)
        
        self.stop_btn = QPushButton("⏹️")
        self.stop_btn.setObjectName("controlButton")
        self.stop_btn.clicked.connect(self.stop_timer)
        
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)
        
        controls_layout.addStretch()
        
        # Card selector
        self.card_combo = QComboBox()
        self.card_combo.setObjectName("cardSelector")
        self.card_combo.setMinimumWidth(250)
        self.card_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.card_combo.currentTextChanged.connect(self.on_card_selected)
        controls_layout.addWidget(self.card_combo)
        
        content_layout.addLayout(controls_layout)
        self.content_widget.setLayout(content_layout)
        self.main_layout.addWidget(self.content_widget)
    
    def setup_style(self):
        """Apply modern styling"""
        primary_color = self.config.primary_color
        
        if self.is_collapsed:
            style = f"""
            QWidget {{
                background-color: rgba(25, 25, 25, 200);
                border-radius: 15px;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            
            QLabel#timer {{
                font-size: 15px;
                font-weight: bold;
                color: {primary_color};
                padding: 3px 6px;
            }}
            
            QPushButton#iconButton {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 1px;
                font-size: 10px;
            }}
            
            QPushButton#iconButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            """
        else:
            # Convert hex color to RGB for alpha variations
            hex_color = primary_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            style = f"""
            QWidget {{
                background-color: rgba(35, 35, 35, 240);
                border-radius: 12px;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            
            QLabel#timer {{
                font-size: 16px;
                font-weight: bold;
                color: {primary_color};
                padding: 4px;
            }}
            
            QLabel#cardInfo {{
                font-size: 11px;
                color: #cccccc;
                padding: 2px;
            }}
            
            QPushButton {{
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            
            QPushButton#iconButton {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 2px;
            }}
            
            QPushButton#iconButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            
            QPushButton#controlButton {{
                background-color: rgba({r}, {g}, {b}, 0.8);
                min-width: 24px;
                min-height: 24px;
            }}
            
            QPushButton#controlButton:hover {{
                background-color: rgba({r}, {g}, {b}, 1.0);
            }}
            
            QPushButton#controlButton:pressed {{
                background-color: rgba({max(0, r-20)}, {max(0, g-20)}, {max(0, b-20)}, 1.0);
            }}
            
            QPushButton#controlButtonDisabled {{
                background-color: rgba(128, 128, 128, 0.5);
                min-width: 24px;
                min-height: 24px;
                color: rgba(255, 255, 255, 0.5);
            }}
            
            QPushButton#controlButtonDisabled:hover {{
                background-color: rgba(128, 128, 128, 0.5);
            }}
            
            QComboBox {{
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                padding: 4px 8px;
                min-width: 250px;
            }}
            
            QComboBox:hover {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: rgba(45, 45, 45, 250);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                selection-background-color: rgba({r}, {g}, {b}, 0.8);
                color: white;
                padding: 4px;
            }}
            """
        
        self.setStyleSheet(style)
    
    def setup_timers(self):
        """Setup update timers"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)
    
    def setup_system_tray(self):
        """Setup system tray icon"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(138, 43, 226))
            icon = QIcon(pixmap)
            self.tray_icon.setIcon(icon)
            
            tray_menu = QMenu()
            show_action = tray_menu.addAction("Show")
            show_action.triggered.connect(self.show)
            
            settings_action = tray_menu.addAction("Settings")
            settings_action.triggered.connect(self.show_settings)
            
            reports_action = tray_menu.addAction("Reports")
            reports_action.triggered.connect(self.show_reports)
            
            tray_menu.addSeparator()
            quit_action = tray_menu.addAction("Quit")
            quit_action.triggered.connect(self.quit_app)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
    
    def is_configured(self) -> bool:
        """Check if Jira is properly configured"""
        return all([
            self.config.jira_server,
            self.config.email,
            self.config.token
        ])
    
    def show_reports(self):
        """Show the reports dialog"""
        dialog = ReportDialog(self.time_logger, self.config.primary_color, self)
        dialog.exec()
    
    def load_cards(self):
        """Load cards from Jira in background"""
        if not self.is_configured():
            return
        
        self.set_loading_state()
        
        self.jira_worker = JiraWorker(self.config)
        self.jira_worker.cards_loaded.connect(self.on_cards_loaded)
        self.jira_worker.error_occurred.connect(self.on_jira_error)
        self.jira_worker.start()
    
    def reload_cards(self):
        """Reload cards from Jira"""
        if not self.is_configured():
            QMessageBox.warning(self, "Warning", "Please configure Jira settings first!")
            return
        
        if hasattr(self, 'reload_btn'):
            self.reload_btn.setEnabled(False)
            self.reload_btn.setText("⏳")
        
        current_card_id = self.current_card.id if self.current_card else None
        
        self.set_loading_state()
        
        self.jira_worker = JiraWorker(self.config)
        self.jira_worker.cards_loaded.connect(lambda cards: self.on_cards_reloaded(cards, current_card_id))
        self.jira_worker.error_occurred.connect(self.on_reload_error)
        self.jira_worker.start()
    
    def on_cards_reloaded(self, cards: List[Card], previous_card_id: str):
        """Handle reloaded cards"""
        self.cards = cards
        
        if hasattr(self, 'reload_btn'):
            self.reload_btn.setEnabled(True)
            self.reload_btn.setText("🔄")
        
        if self.is_configured():
            self.jira_integration = JiraIntegration(
                self.config.jira_server,
                self.config.email,
                self.config.token
            )
        
        if hasattr(self, 'card_combo'):
            self.card_combo.clear()
            
            if cards:
                card_names = [f"{card.id}: {card.name[:60]}..." if len(card.name) > 60 
                             else f"{card.id}: {card.name}" for card in cards]
                self.card_combo.addItems(card_names)
                
                if previous_card_id:
                    for i, card in enumerate(cards):
                        if card.id == previous_card_id:
                            self.card_combo.setCurrentIndex(i)
                            self.current_card = card
                            self.elapsed_time = card.time_spent
                            break
                    else:
                        self.current_card = cards[0]
                        self.elapsed_time = cards[0].time_spent
                else:
                    self.current_card = cards[0]
                    self.elapsed_time = cards[0].time_spent
                
                self.update_card_display()
        
        QMessageBox.information(self, "Success", f"Reloaded {len(cards)} cards from Jira")
    
    def on_reload_error(self, error: str):
        """Handle reload errors"""
        if hasattr(self, 'reload_btn'):
            self.reload_btn.setEnabled(True)
            self.reload_btn.setText("🔄")
        
        if hasattr(self, 'card_combo'):
            self.card_combo.setEnabled(True)
            self.card_combo.clear()
            self.card_combo.addItem("Failed to reload issues")
        
        if hasattr(self, 'card_label'):
            self.card_label.setText("Failed to reload issues")
        
        QMessageBox.warning(self, "Reload Error", f"Failed to reload cards: {error}")
    
    def on_cards_loaded(self, cards: List[Card]):
        """Handle loaded cards"""
        self.cards = cards
        
        if hasattr(self, 'card_combo'):
            self.card_combo.setEnabled(True)
            self.card_combo.clear()
        
        if self.is_configured():
            self.jira_integration = JiraIntegration(
                self.config.jira_server,
                self.config.email,
                self.config.token
            )
        
        if cards:
            card_names = [f"{card.id}: {card.name[:60]}..." if len(card.name) > 60 
                         else f"{card.id}: {card.name}" for card in cards]
            self.card_combo.addItems(card_names)
            self.current_card = cards[0]
            self.elapsed_time = cards[0].time_spent
            self.update_card_display()
        else:
            self.card_combo.addItem("No issues found")
            self.current_card = None
            self.elapsed_time = 0
            if hasattr(self, 'card_label'):
                self.card_label.setText("No issues found")
            self.update_play_button_state()
    
    def set_loading_state(self):
        """Set the UI to loading state"""
        self.current_card = None
        self.elapsed_time = 0
        
        if hasattr(self, 'card_combo'):
            self.card_combo.clear()
            self.card_combo.addItem("Loading issues...")
            self.card_combo.setEnabled(False)
        
        if hasattr(self, 'card_label'):
            self.card_label.setText("Loading issues...")
        
        self.update_play_button_state()
        self.update_display()
    
    def on_jira_error(self, error: str):
        """Handle Jira errors"""
        if hasattr(self, 'card_combo'):
            self.card_combo.setEnabled(True)
            self.card_combo.clear()
            self.card_combo.addItem("Failed to load issues")
        
        if hasattr(self, 'card_label'):
            self.card_label.setText("Failed to load issues")
        
        QMessageBox.warning(self, "Jira Error", f"Failed to load cards: {error}")
    
    def on_card_selected(self, card_text: str):
        """Handle card selection"""
        if not card_text or not self.cards or self.rebuilding_ui:
            return
        
        card_id = card_text.split(":")[0]
        new_card = next((card for card in self.cards if card.id == card_id), None)
        
        if new_card and self.current_card and new_card.id != self.current_card.id:
            if self.is_running or self.is_paused:
                self.stop_timer()
        
        self.current_card = new_card
        
        if self.current_card:
            self.elapsed_time = self.current_card.time_spent
            self.update_card_display()
    
    def update_card_display(self):
        """Update card information display"""
        if self.current_card:
            self.card_label.setText(f"{self.current_card.id}: {self.current_card.name[:80]}...")
        else:
            self.card_label.setText("No card selected")
        
        self.update_play_button_state()
    
    def update_play_button_state(self):
        """Update play button appearance"""
        if hasattr(self, 'play_btn'):
            if self.is_running:
                self.play_btn.setEnabled(False)
                self.play_btn.setObjectName("controlButton")
            elif self.is_paused:
                self.play_btn.setText("▶️")
                self.play_btn.setEnabled(True)
                self.play_btn.setObjectName("controlButton")
            else:
                self.play_btn.setText("▶️")
                if self.current_card:
                    self.play_btn.setEnabled(True)
                    self.play_btn.setObjectName("controlButton")
                else:
                    self.play_btn.setEnabled(False)
                    self.play_btn.setObjectName("controlButton")
            
            self.setup_style()
    
    def toggle_collapse(self):
        """Toggle between collapsed and expanded states"""
        self.is_collapsed = not self.is_collapsed
        self.config.collapsed = self.is_collapsed
        self.config_manager.save(self.config)
        
        self.rebuild_ui()
        
        new_width = 180 if self.is_collapsed else 450
        new_height = 60 if self.is_collapsed else 140
        self.resize(new_width, new_height)
        
        self.updateGeometry()
        self.update()
        
        QTimer.singleShot(50, lambda: self.resize(new_width, new_height))
    
    def rebuild_ui(self):
        """Rebuild the UI when toggling"""
        self.rebuilding_ui = True
        
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if self.is_collapsed:
            self.main_layout.setContentsMargins(6, 4, 6, 4)
            self.main_layout.setSpacing(2)
        else:
            self.main_layout.setContentsMargins(12, 8, 12, 8)
            self.main_layout.setSpacing(6)
        
        self.setup_header()
        self.setup_content()
        
        if self.cards and hasattr(self, 'card_combo'):
            card_names = [f"{card.id}: {card.name[:60]}..." if len(card.name) > 60 
                         else f"{card.id}: {card.name}" for card in self.cards]
            self.card_combo.addItems(card_names)
            if self.current_card:
                for i, card in enumerate(self.cards):
                    if card.id == self.current_card.id:
                        self.card_combo.setCurrentIndex(i)
                        break
                self.update_card_display()
        
        self.update_visibility()
        self.setup_style()
        self.update_display()
        
        self.rebuilding_ui = False
    
    def update_visibility(self):
        """Update widget visibility"""
        self.content_widget.setVisible(not self.is_collapsed)
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.Accepted:
            self.config_manager.save(self.config)
            self.load_cards()
    
    def start_timer(self):
        """Start the timer"""
        if not self.current_card or not self.current_card.id:
            QMessageBox.warning(self, "Warning", "Please select a card first!")
            return
        
        if self.is_paused:
            self.is_paused = False
            self.is_running = True
            self.start_time = time.time() - self.elapsed_time
        else:
            if not self.is_running:
                self.is_running = True
                self.elapsed_time = 0
                self.start_time = time.time() - self.current_card.time_spent
        
        self.update_play_button_state()
    
    def pause_timer(self):
        """Pause the timer"""
        if self.is_running:
            self.is_running = False
            self.is_paused = True
            self.elapsed_time = time.time() - self.start_time
            self.update_play_button_state()
    
    def stop_timer(self):
        """Stop the timer and log time"""
        if self.is_running or self.is_paused:
            original_running_state = self.is_running
            self.is_running = False
            self.is_paused = False
            
            print(f"Finished working on card: {self.current_card.name if self.current_card else 'None'}")
            
            if self.current_card:
                if original_running_state:
                    self.elapsed_time = time.time() - self.start_time
                
                new_elapsed_time = self.elapsed_time - self.current_card.time_spent
                
                print(f"Register elapsed time: {new_elapsed_time}")
                
                if new_elapsed_time < 60:
                    self.is_paused = True
                    self.update_play_button_state()
                    QMessageBox.warning(self, "Warning", "It's only possible to register times greater than 60 seconds")
                    return
                
                time_to_log = new_elapsed_time
                
                if self.log_time_to_jira_session(time_to_log):
                    # Log to local file
                    self.time_logger.add_entry(
                        self.current_card.id,
                        self.current_card.name,
                        int(time_to_log)
                    )
                    
                    self.current_card.time_spent += int(time_to_log)
                    self.elapsed_time = self.current_card.time_spent
                else:
                    pass
            
            self.update_play_button_state()
            self.update_display()
    
    def log_time_to_jira_session(self, time_to_log):
        """Log time to Jira"""
        if self.jira_integration and self.current_card and time_to_log > 0:
            try:
                original_time_spent = self.current_card.time_spent
                self.current_card.time_spent = int(time_to_log)
                
                success = self.jira_integration.add_timespent_to_card(self.current_card)
                
                if success:
                    self.current_card.time_spent = original_time_spent
                    QMessageBox.information(self, "Success", f"Logged {int(time_to_log)} seconds to Jira")
                    return True
                else:
                    self.current_card.time_spent = original_time_spent
                    QMessageBox.warning(self, "Error", "Failed to log time to Jira")
                    return False
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error logging time to Jira: {str(e)}")
                if 'original_time_spent' in locals():
                    self.current_card.time_spent = original_time_spent
                return False
        return False
    
    def get_current_time_display(self):
        """Get current time display string"""
        if self.is_running:
            current_elapsed = time.time() - self.start_time
        else:
            current_elapsed = self.elapsed_time
        
        hours, remainder = divmod(int(current_elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def update_display(self):
        """Update timer display"""
        if self.is_running:
            self.elapsed_time = time.time() - self.start_time
        
        time_str = self.get_current_time_display()
        
        if hasattr(self, 'timer_label'):
            self.timer_label.setText(time_str)
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_position'):
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            self.config.widget_position = (new_pos.x(), new_pos.y())
            event.accept()
    
    def closeEvent(self, event):
        """Handle close event"""
        self.stop_timer()
        event.ignore()
        self.hide()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.showMessage(
                "Zilean",
                "Application successfully closed",
                QSystemTrayIcon.Information,
                2000
            )
    
    def quit_app(self):
        """Quit the application"""
        self.config_manager.save(self.config)
        QApplication.quit()

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    widget = FloatingWidget()
    widget.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()