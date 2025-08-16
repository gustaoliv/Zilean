# Modern Zilean - Floating Jira Time Tracker

A sleek, modern floating widget for tracking time on Jira issues. Designed to be always-on-top, minimal, and Windows-friendly.

## ✨ Features

### 🎯 Core Functionality
- **Floating Widget**: Always-on-top, draggable widget that stays visible while you work
- **Collapsible Interface**: Switch between minimal timer view and full control panel
- **Live Timer**: Real-time timer updates without needing to maximize the app
- **Jira Integration**: Seamless integration with Jira for card fetching and time logging
- **System Tray**: Minimize to system tray for complete invisibility when needed

### 🎨 Modern Design
- **Sleek UI**: Modern, dark-themed interface with smooth animations
- **Responsive**: Adapts to different screen sizes and DPI settings
- **Minimal Performance Impact**: Lightweight and efficient
- **Windows Native**: Proper Windows 10/11 integration

### ⚡ Smart Features
- **Auto-save Configuration**: Remembers your settings and window position
- **Background Card Loading**: Non-blocking Jira API calls
- **Smart Time Logging**: Only logs time sessions longer than 1 minute
- **Card Status Management**: View and change card statuses directly from the widget

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Windows 10/11
- Jira account with API access

### Installation

1. **Clone or download the project**
   ```bash
   git clone <your-repo-url>
   cd zilean
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements_modern.txt
   ```

3. **Run the application**
   ```bash
   python launch_modern.py
   ```

### First-Time Setup

1. **Get your Jira API token**:
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Create a new API token
   - Copy the token (you won't see it again!)

2. **Configure the app**:
   - Click the ⚙️ settings button in the widget
   - Enter your Jira server URL (e.g., `https://yourcompany.atlassian.net`)
   - Enter your email address
   - Paste your API token
   - Click "Save"

3. **Start tracking**:
   - Select a card from the dropdown
   - Click ▶️ to start timing
   - The widget will stay on top while you work
   - Click ⏹️ to stop and log time to Jira

## 🎮 Usage

### Widget States

**Collapsed Mode** (Minimal):
```
┌─────────────────┐
│ ⏱️ 01:23:45 ⚙️ │
└─────────────────┘
```

**Expanded Mode** (Full Controls):
```
┌──────────────────────────────┐
│ ⏱️ 01:23:45        ⚙️ ⬆️    │
│ PROJ-123: Fix login bug      │
│ ▶️ ⏸️ ⏹️     [Card Selector] │
└──────────────────────────────┘
```

### Controls

- **⚙️ Settings**: Open configuration dialog
- **⬆️/⬇️ Toggle**: Switch between collapsed/expanded modes
- **▶️ Play**: Start timing the selected card
- **⏸️ Pause**: Pause the current timer
- **⏹️ Stop**: Stop timer and log time to Jira
- **Card Selector**: Choose which Jira card to track

### Keyboard Shortcuts

- **Drag**: Click and drag anywhere on the widget to move it
- **Right-click**: Access context menu (when available)
- **System Tray**: Right-click tray icon for quick actions

## 🔧 Advanced Configuration

### Configuration File
Settings are automatically saved to `config.json`:

```json
{
  "jira_server": "https://yourcompany.atlassian.net",
  "email": "your.email@company.com",
  "token": "your-api-token",
  "widget_position": [100, 100],
  "always_on_top": true,
  "collapsed": false
}
```

### Customization

The widget appearance can be customized by modifying the `setup_style()` method in `modern_zilean.py`. The styling uses Qt Style Sheets (QSS), similar to CSS.

## 📦 Building Executable

To create a standalone executable:

```bash
python build_modern.py
```

This creates `dist/ModernZilean.exe` that can run without Python installed.

## 🏗️ Architecture

### Framework Choice: PySide6 (Qt6)

**Why PySide6 over CustomTkinter?**
- ✅ Superior Windows integration
- ✅ Better always-on-top behavior
- ✅ Modern styling capabilities
- ✅ Built-in system tray support
- ✅ Better performance for floating widgets
- ✅ Professional look and feel
- ✅ Better DPI scaling

### Project Structure

```
modern_zilean.py          # Main application
launch_modern.py          # Launcher with error handling
build_modern.py           # Build script for executable
requirements_modern.txt   # Modern dependencies

Domain/                   # Existing domain models
├── Models/
│   └── Card.py
└── Interfaces/
    └── IBoardIntegration.py

Infraestructure/          # Existing Jira integration
└── JiraIntegration.py
```

### Key Components

1. **FloatingWidget**: Main UI widget with dragging and always-on-top behavior
2. **ConfigManager**: Handles configuration persistence
3. **SettingsDialog**: Modern settings interface
4. **JiraWorker**: Background thread for Jira operations
5. **System Tray Integration**: Minimize to tray functionality

## 🔄 Migration from Old Version

The new version maintains compatibility with your existing Jira integration code while providing a completely new UI. Your existing `Domain` and `Infrastructure` code works without changes.

### What's Different:
- **UI Framework**: CustomTkinter → PySide6
- **Architecture**: Monolithic → Modular with background workers
- **User Experience**: Traditional window → Floating widget
- **Performance**: Blocking operations → Non-blocking background tasks

### What's the Same:
- **Jira Integration**: Same API calls and authentication
- **Domain Models**: Same Card and IBoardIntegration interfaces
- **Configuration**: Same config.json format (with additions)

## 🐛 Troubleshooting

### Common Issues

**Widget not staying on top:**
- Ensure Windows allows the app to stay on top
- Check if other applications are forcing themselves on top

**Jira connection fails:**
- Verify your API token is correct and not expired
- Check your Jira server URL format
- Ensure your account has proper permissions

**Widget disappears:**
- Check system tray - it might be minimized
- Right-click tray icon and select "Show"

**Performance issues:**
- Close other resource-heavy applications
- Check if antivirus is scanning the executable

### Debug Mode

Run with debug output:
```bash
python modern_zilean.py --debug
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on Windows 10/11
5. Submit a pull request

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- Built with PySide6 (Qt6)
- Uses the existing Jira Python library
- Inspired by modern floating widget designs
- Thanks to the original Zilean project for the foundation