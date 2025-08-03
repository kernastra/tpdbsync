#!/usr/bin/env python3
"""
Simple local-only version of poster sync for testing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Config
from src.file_monitor import PosterScanner
from pathlib import Path

def run_local_sync():
    """Run poster sync simulation without SMB"""
    print("🚀 TPDB Poster Sync - Local Run (SMB Simulation)")
    print("=" * 60)
    
    # Load config
    config = Config("config.yaml")
    print(f"✅ Configuration loaded")
    print(f"   Local base: {config.get('local.base_path')}")
    print(f"   Remote server: {config.get('remote.server')}")
    print(f"   Remote share: {config.get('remote.share')}")
    print(f"   Remote user: {config.get('remote.username')}")
    
    # Initialize scanner
    scanner = PosterScanner(
        config.get_poster_extensions(),
        config.get_poster_names(),
        config.get_season_poster_patterns()
    )
    
    # Get local folders
    local_folders = config.get_local_folders()
    remote_paths = config.get_remote_paths()
    
    print(f"\n📁 Scanning local directories...")
    
    total_files = 0
    total_size_mb = 0
    
    for media_type, local_folder in local_folders.items():
        print(f"\n📂 {media_type.upper()}: {local_folder}")
        
        if not local_folder.exists():
            print("   ❌ Directory does not exist")
            continue
            
        poster_map = scanner.scan_directory(local_folder, recursive=True)
        
        if not poster_map:
            print("   📭 No posters found")
            continue
            
        remote_base = remote_paths.get(media_type, f"jellyfin/metadata/library/{media_type}")
        
        print(f"   🎯 Would sync to: {config.get('remote.share')}/{remote_base}")
        
        for media_name, posters in poster_map.items():
            if posters:
                best_poster = posters[0]
                size_mb = best_poster.stat().st_size / 1024 / 1024
                total_size_mb += size_mb
                total_files += 1
                
                print(f"   ✅ {media_name} ({size_mb:.1f} MB)")
    
    print(f"\n📊 SYNC SUMMARY:")
    print(f"   📄 Total files: {total_files}")
    print(f"   💾 Total size: {total_size_mb:.1f} MB")
    print(f"   🖥️  Remote server: {config.get('remote.server')}")
    print(f"   📁 Remote share: {config.get('remote.share')}")
    print(f"   👤 Username: {config.get('remote.username')}")
    
    print(f"\n🔧 TO ACTUALLY SYNC:")
    print(f"   1. Ensure SMB/CIFS is working on your server")
    print(f"   2. Test network connectivity: ping {config.get('remote.server')}")
    print(f"   3. Test SMB access: smbclient //{config.get('remote.server')}/{config.get('remote.share').lstrip('/')} -U {config.get('remote.username')}")
    print(f"   4. Run: python manage.py test-connection")
    
    print(f"\n✅ Local scan completed successfully!")
    return True

if __name__ == "__main__":
    try:
        run_local_sync()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
