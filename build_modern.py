#!/usr/bin/env python3
"""
Build script for creating a standalone Zilean executable
"""

import os
import sys
import subprocess
from pathlib import Path

def create_spec_file():
    """Create PyInstaller spec file for Modern Zilean"""
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['modern_zilean.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Domain', 'Domain'),
        ('Infraestructure', 'Infraestructure'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtWidgets', 
        'PySide6.QtGui',
        'jira',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'customtkinter',
        'matplotlib',
        'numpy',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Zilean',  # Changed from 'ModernZilean' to 'Zilean'
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    with open('modern_zilean.spec', 'w') as f:
        f.write(spec_content.strip())

def build_executable():
    """Build the executable using PyInstaller"""
    print("🔨 Building Zilean executable...")
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
    
    # Create spec file
    create_spec_file()
    
    # Build the executable
    cmd = [sys.executable, '-m', 'PyInstaller', 'modern_zilean.spec', '--clean']
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build completed successfully!")
        print(f"Executable created at: {Path('dist/Zilean.exe').absolute()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main build function"""
    if not Path('modern_zilean.py').exists():
        print("❌ modern_zilean.py not found!")
        return 1
    
    if build_executable():
        print("\n🎉 Zilean is ready!")
        print("Run the executable from: dist/Zilean.exe")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
