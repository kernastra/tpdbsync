#!/usr/bin/env python3
"""
Setup script for TPDB Poster Sync
"""

import sys
import subprocess
import shutil
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def install_dependencies():
    """Install required Python packages"""
    print("Installing dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)


def create_sample_config():
    """Create sample configuration if it doesn't exist"""
    config_path = Path("config.yaml")
    sample_path = Path("config.sample.yaml")
    
    if config_path.exists():
        print("✓ Configuration file already exists")
        return
    
    if sample_path.exists():
        shutil.copy(sample_path, config_path)
        print("✓ Created config.yaml from sample")
    else:
        print("! Please manually create config.yaml (see README for details)")


def check_directories():
    """Check if required directories exist"""
    dirs_to_create = [
        "logs",
    ]
    
    for dir_name in dirs_to_create:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            print(f"✓ Created directory: {dir_name}")


def main():
    """Main setup function"""
    print("Setting up TPDB Poster Sync...")
    print("=" * 40)
    
    check_python_version()
    install_dependencies()
    create_sample_config()
    check_directories()
    
    print("\n" + "=" * 40)
    print("Setup complete!")
    print("\nNext steps:")
    print("1. Edit config.yaml with your settings")
    print("2. Run: python main.py --dry-run (to test)")
    print("3. Run: python main.py (to start syncing)")


if __name__ == "__main__":
    main()
