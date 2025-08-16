#!/usr/bin/env python3
"""
Launcher script for Modern Zilean
Handles startup, error checking, and environment setup
"""

import sys
import os
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import PySide6
        from jira import JIRA
        return True
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Please install requirements: pip install -r requirements_modern.txt")
        return False

def setup_environment():
    """Setup environment and paths"""
    # Add current directory to Python path
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

def main():
    """Main launcher function"""
    print("🕐 Starting Modern Zilean...")
    
    # Check requirements
    if not check_requirements():
        input("Press Enter to exit...")
        return 1
    
    # Setup environment
    setup_environment()
    
    try:
        # Import and run the modern application
        from modern_zilean import main as run_app
        run_app()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())