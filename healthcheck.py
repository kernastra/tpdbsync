#!/usr/bin/env python3
"""
Health check script for Docker container
"""

import sys
import os
from pathlib import Path

def check_health():
    """Perform health checks"""
    checks = []
    
    # Check if main application files exist
    required_files = [
        'main.py',
        'src/poster_sync.py',
        'src/config.py'
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            checks.append(f"✅ {file_path}")
        else:
            checks.append(f"❌ {file_path}")
            return False
    
    # Check if config is accessible
    try:
        from src.config import Config
        config = Config()
        checks.append("✅ Configuration loadable")
    except Exception as e:
        checks.append(f"❌ Configuration error: {e}")
        return False
    
    # Check if poster directory is mounted (if configured)
    poster_path = config.get('local.base_path')
    if poster_path and Path(poster_path).exists():
        checks.append(f"✅ Poster directory accessible: {poster_path}")
    else:
        checks.append(f"❌ Poster directory not accessible: {poster_path}")
        return False
    
    # All checks passed
    for check in checks:
        print(check)
    
    return True

if __name__ == "__main__":
    if check_health():
        print("🟢 Health check passed")
        sys.exit(0)
    else:
        print("🔴 Health check failed")
        sys.exit(1)
