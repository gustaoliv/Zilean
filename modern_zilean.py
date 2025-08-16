#!/usr/bin/env python3
"""
Modern Zilean - Floating Jira Time Tracker Widget
A sleek, always-on-top time tracking widget for Jira integration
"""

import sys
import json
import time
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QComboBox, QSystemTrayIcon, 
    QMenu, QDialog, QFormLayout, QLineEdit, QMessageBox,
    QGraphicsDropShadowEffect
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
        
        # State
        self.cards: List[Card] = []
        self.current_card: Optional[Card] = None
        self.is_collapsed = self.config.collapsed
        self.is_running = False
        self.is_paused = False
        self.elapsed_time = 0
        self.start_time = 0
        self.rebuilding_ui = False  # Flag to prevent card selection during UI rebuild
        
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
        
        # Main layout - minimal padding for collapsed mode
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
        if self.config.widget_position == (50, 50):  # Default position, move to top-right
            screen = QApplication.primaryScreen().geometry()
            widget_width = 130 if self.is_collapsed else 450
            x = screen.width() - widget_width - 20  # 20px margin from right edge
            y = 20  # 20px margin from top edge
            self.move(x, y)
            self.config.widget_position = (x, y)
            self.config_manager.save(self.config)
        else:
            self.move(*self.config.widget_position)
    
    def setup_header(self):
        """Setup the header with timer and settings button"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4 if self.is_collapsed else 8)  # Minimal spacing when collapsed
        
        # Timer display - show current time if running
        current_time = self.get_current_time_display()
        self.timer_label = QLabel(current_time)
        self.timer_label.setObjectName("timer")
        header_layout.addWidget(self.timer_label)
        
        # Only add stretch when expanded, not when collapsed
        if not self.is_collapsed:
            header_layout.addStretch()
        
        # Settings button (only show when expanded)
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setObjectName("iconButton")
        self.settings_btn.setFixedSize(20 if self.is_collapsed else 24, 20 if self.is_collapsed else 24)
        self.settings_btn.clicked.connect(self.show_settings)
        if not self.is_collapsed:  # Only show settings button when expanded
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
            self.close_btn.setObjectName("iconButton")  # Use same style as other icon buttons
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
        
        # Card selector with better width for full issue titles
        self.card_combo = QComboBox()
        self.card_combo.setObjectName("cardSelector")
        self.card_combo.setMinimumWidth(250)  # Much wider to show full titles
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
                border-radius: 8px;
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
        self.update_timer.start(1000)  # Update every second
    
    def setup_system_tray(self):
        """Setup system tray icon"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            
            # Create a simple icon for the system tray
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(138, 43, 226))  # Purple color
            icon = QIcon(pixmap)
            self.tray_icon.setIcon(icon)
            
            # Create tray menu
            tray_menu = QMenu()
            show_action = tray_menu.addAction("Show")
            show_action.triggered.connect(self.show)
            
            settings_action = tray_menu.addAction("Settings")
            settings_action.triggered.connect(self.show_settings)
            
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
    
    def load_cards(self):
        """Load cards from Jira in background"""
        if not self.is_configured():
            return
        
        self.jira_worker = JiraWorker(self.config)
        self.jira_worker.cards_loaded.connect(self.on_cards_loaded)
        self.jira_worker.error_occurred.connect(self.on_jira_error)
        self.jira_worker.start()
    
    def reload_cards(self):
        """Reload cards from Jira and refresh the interface"""
        if not self.is_configured():
            QMessageBox.warning(self, "Warning", "Please configure Jira settings first!")
            return
        
        # Disable reload button during reload
        if hasattr(self, 'reload_btn'):
            self.reload_btn.setEnabled(False)
            self.reload_btn.setText("⏳")
        
        # Store current card ID to restore selection after reload
        current_card_id = self.current_card.id if self.current_card else None
        
        # Load cards
        self.jira_worker = JiraWorker(self.config)
        self.jira_worker.cards_loaded.connect(lambda cards: self.on_cards_reloaded(cards, current_card_id))
        self.jira_worker.error_occurred.connect(self.on_reload_error)
        self.jira_worker.start()
    
    def on_cards_reloaded(self, cards: List[Card], previous_card_id: str):
        """Handle reloaded cards and restore selection"""
        self.cards = cards
        
        # Re-enable reload button
        if hasattr(self, 'reload_btn'):
            self.reload_btn.setEnabled(True)
            self.reload_btn.setText("🔄")
        
        # Initialize Jira integration for time logging
        if self.is_configured():
            self.jira_integration = JiraIntegration(
                self.config.jira_server,
                self.config.email,
                self.config.token
            )
        
        # Update combo box
        if hasattr(self, 'card_combo'):
            self.card_combo.clear()
            
            if cards:
                # Show more of the issue title - up to 60 characters
                card_names = [f"{card.id}: {card.name[:60]}..." if len(card.name) > 60 
                             else f"{card.id}: {card.name}" for card in cards]
                self.card_combo.addItems(card_names)
                
                # Try to restore previous selection
                if previous_card_id:
                    for i, card in enumerate(cards):
                        if card.id == previous_card_id:
                            self.card_combo.setCurrentIndex(i)
                            self.current_card = card
                            # Update elapsed time with refreshed card data
                            self.elapsed_time = card.time_spent
                            break
                    else:
                        # Previous card not found, select first card
                        self.current_card = cards[0]
                        self.elapsed_time = cards[0].time_spent
                else:
                    # No previous card, select first
                    self.current_card = cards[0]
                    self.elapsed_time = cards[0].time_spent
                
                self.update_card_display()
        
        QMessageBox.information(self, "Success", f"Reloaded {len(cards)} cards from Jira")
    
    def on_reload_error(self, error: str):
        """Handle reload errors"""
        # Re-enable reload button
        if hasattr(self, 'reload_btn'):
            self.reload_btn.setEnabled(True)
            self.reload_btn.setText("🔄")
        
        QMessageBox.warning(self, "Reload Error", f"Failed to reload cards: {error}")
    
    def on_cards_loaded(self, cards: List[Card]):
        """Handle loaded cards"""
        self.cards = cards
        self.card_combo.clear()
        
        # Initialize Jira integration for time logging
        if self.is_configured():
            self.jira_integration = JiraIntegration(
                self.config.jira_server,
                self.config.email,
                self.config.token
            )
        
        if cards:
            # Show more of the issue title - up to 60 characters
            card_names = [f"{card.id}: {card.name[:60]}..." if len(card.name) > 60 
                         else f"{card.id}: {card.name}" for card in cards]
            self.card_combo.addItems(card_names)
            self.current_card = cards[0]
            self.update_card_display()
    
    def on_jira_error(self, error: str):
        """Handle Jira errors"""
        QMessageBox.warning(self, "Jira Error", f"Failed to load cards: {error}")
    
    def on_card_selected(self, card_text: str):
        """Handle card selection"""
        if not card_text or not self.cards or self.rebuilding_ui:
            return
        
        # Extract card ID from combo text
        card_id = card_text.split(":")[0]
        new_card = next((card for card in self.cards if card.id == card_id), None)
        
        # Only stop timer if actually changing to a different card
        if new_card and self.current_card and new_card.id != self.current_card.id:
            if self.is_running or self.is_paused:
                self.stop_timer()
        
        self.current_card = new_card
        
        if self.current_card:
            # Set elapsed time to current card's time spent (accumulated time)
            self.elapsed_time = self.current_card.time_spent
            
            self.update_card_display()
    
    def update_card_display(self):
        """Update card information display"""
        if self.current_card:
            self.card_label.setText(f"{self.current_card.id}: {self.current_card.name[:40]}...")
        else:
            self.card_label.setText("No card selected")
        
        # Update play button state
        self.update_play_button_state()
    
    def update_play_button_state(self):
        """Update play button appearance based on timer state"""
        if hasattr(self, 'play_btn'):
            if self.is_running:
                self.play_btn.setText("⏸️")
                self.play_btn.setEnabled(True)
                self.play_btn.setObjectName("controlButton")
            elif self.is_paused:
                self.play_btn.setText("▶️")
                self.play_btn.setEnabled(True)
                self.play_btn.setObjectName("controlButton")
            else:
                # Stopped state
                self.play_btn.setText("▶️")
                if self.current_card:
                    self.play_btn.setEnabled(True)
                    self.play_btn.setObjectName("controlButton")
                else:
                    self.play_btn.setEnabled(False)
                    self.play_btn.setObjectName("controlButtonDisabled")
            
            # Re-apply styling to update appearance
            self.setup_style()
    
    def toggle_collapse(self):
        """Toggle between collapsed and expanded states"""
        self.is_collapsed = not self.is_collapsed
        self.config.collapsed = self.is_collapsed
        self.config_manager.save(self.config)
        
        # Rebuild the entire UI to properly handle layout changes
        self.rebuild_ui()
        
        # Resize to appropriate dimensions
        new_width = 180 if self.is_collapsed else 450  # Better size when collapsed
        new_height = 60 if self.is_collapsed else 140   # Better height too
        self.resize(new_width, new_height)
        
        # Force the widget to update its geometry and maintain size
        self.updateGeometry()
        self.update()
        
        # Use a timer to ensure the size sticks after UI rebuild
        QTimer.singleShot(50, lambda: self.resize(new_width, new_height))
    
    def rebuild_ui(self):
        """Rebuild the UI when toggling between states"""
        self.rebuilding_ui = True  # Set flag to prevent card selection events
        
        # Clear the current layout
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Update layout margins based on state
        if self.is_collapsed:
            self.main_layout.setContentsMargins(6, 4, 6, 4)
            self.main_layout.setSpacing(2)
        else:
            self.main_layout.setContentsMargins(12, 8, 12, 8)
            self.main_layout.setSpacing(6)
        
        # Rebuild header and content
        self.setup_header()
        self.setup_content()
        
        # Repopulate card combo if we have cards
        if self.cards and hasattr(self, 'card_combo'):
            card_names = [f"{card.id}: {card.name[:60]}..." if len(card.name) > 60 
                         else f"{card.id}: {card.name}" for card in self.cards]
            self.card_combo.addItems(card_names)
            if self.current_card:
                # Find and select the current card
                for i, card in enumerate(self.cards):
                    if card.id == self.current_card.id:
                        self.card_combo.setCurrentIndex(i)
                        break
                # Update the card display after setting selection
                self.update_card_display()
        
        # Update visibility and styling
        self.update_visibility()
        self.setup_style()
        
        # Immediately update timer display to prevent showing 00:00:00
        self.update_display()
        
        self.rebuilding_ui = False  # Clear flag after rebuild is complete
    
    def update_visibility(self):
        """Update widget visibility based on collapse state"""
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
            # Resume from pause
            self.is_paused = False
            self.is_running = True
            self.start_time = time.time() - self.elapsed_time
        else:
            if not self.is_running:
                # Start new timer
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
                # Calculate current elapsed time if timer was running
                if original_running_state:
                    self.elapsed_time = time.time() - self.start_time
                
                # Calculate only the new time worked (excluding already logged time)
                new_elapsed_time = self.elapsed_time - self.current_card.time_spent
                
                print(f"Register elapsed time: {new_elapsed_time}")
                
                # Only log if more than 60 seconds
                if new_elapsed_time < 60:
                    self.is_paused = True
                    self.update_play_button_state()
                    QMessageBox.warning(self, "Warning", "It's only possible to register times greater than 60 seconds")
                    return
                
                # Store the new elapsed time for logging
                time_to_log = new_elapsed_time
                
                # Log time to Jira
                if self.log_time_to_jira_session(time_to_log):
                    # Update the card's total time spent
                    self.current_card.time_spent += int(time_to_log)
                    # Set elapsed time to show total accumulated time
                    self.elapsed_time = self.current_card.time_spent
                else:
                    # If logging failed, keep the current elapsed time
                    pass
            
            # Don't reset elapsed_time to 0 - keep showing accumulated time
            self.update_play_button_state()
            self.update_display()
    
    def log_time_to_jira_session(self, time_to_log):
        """Log a specific time session to Jira"""
        if self.jira_integration and self.current_card and time_to_log > 0:
            try:
                # Save the current time spent temporarily
                original_time_spent = self.current_card.time_spent
                
                # Set the time to log for this session
                self.current_card.time_spent = int(time_to_log)
                
                # Log the time to Jira
                success = self.jira_integration.add_timespent_to_card(self.current_card)
                
                if success:
                    # Restore original time (will be updated by caller)
                    self.current_card.time_spent = original_time_spent
                    QMessageBox.information(self, "Success", f"Logged {int(time_to_log)} seconds to Jira")
                    return True
                else:
                    # Restore original time if failed
                    self.current_card.time_spent = original_time_spent
                    QMessageBox.warning(self, "Error", "Failed to log time to Jira")
                    return False
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error logging time to Jira: {str(e)}")
                # Restore original time if error occurred
                if 'original_time_spent' in locals():
                    self.current_card.time_spent = original_time_spent
                return False
        return False
    
    def log_time_to_jira(self):
        """Log elapsed time to Jira (legacy method for compatibility)"""
        return self.log_time_to_jira_session(self.elapsed_time)
    
    def get_current_time_display(self):
        """Get the current time display string"""
        if self.is_running:
            current_elapsed = time.time() - self.start_time
        else:
            current_elapsed = self.elapsed_time
        
        # Format time
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
        event.ignore()
        self.hide()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.showMessage(
                "Zilean",
                "Application was minimized to tray",
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
    
    # Create and show the floating widget
    widget = FloatingWidget()
    widget.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()