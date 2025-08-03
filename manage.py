#!/usr/bin/env python3
"""
Command-line utility for TPDB Poster Sync management
"""

import argparse
import os
import sys
from pathlib import Path

from src.config import Config
from src.poster_sync import PosterSync
from src.file_monitor import PosterScanner
from src.logger import setup_logging


def cmd_test_connection(config: Config) -> None:
    """Test connection to remote server"""
    print("Testing connection to remote server...")
    
    try:
        from src.remote_client import RemoteClient, SMB_AVAILABLE
        
        if not SMB_AVAILABLE:
            print("❌ SMB support not available (install smbprotocol)")
            return
        
        client = RemoteClient(
            server=config.get('remote.server'),
            share=config.get('remote.share'),
            username=config.get('remote.username'),
            password=config.get('remote.password'),
            domain=config.get('remote.domain', '')
        )
        
        with client.connection_context():
            print("✅ Connection successful!")
            
            # Test listing root directory
            files = client.list_directory('/')
            print(f"Found {len(files)} items in share root")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")


def cmd_scan_local(config: Config) -> None:
    """Scan local directories and show what would be synced"""
    print("Scanning local poster directories...")
    
    scanner = PosterScanner(
        config.get_poster_extensions(),
        config.get_poster_names(),
        config.get_season_poster_patterns()
    )
    
    local_folders = config.get_local_folders()
    total_items = 0
    
    for media_type, folder in local_folders.items():
        print(f"\n📁 {media_type.upper()}: {folder}")
        
        if not folder.exists():
            print("   ❌ Directory does not exist")
            continue
        
        poster_map = scanner.scan_directory(folder, recursive=True)
        
        if not poster_map:
            print("   📭 No posters found")
            continue
        
        for media_name, posters in poster_map.items():
            print(f"   📄 {media_name}: {len(posters)} poster(s)")
            for poster in posters[:1]:  # Show only the best poster
                size = poster.stat().st_size
                print(f"      → {poster.name} ({size:,} bytes)")
        
        total_items += len(poster_map)
    
    print(f"\n📊 Total: {total_items} media items with posters")


def cmd_dry_run(config: Config) -> None:
    """Perform dry run sync"""
    print("Performing dry run sync...")
    
    sync = PosterSync(config, dry_run=True)
    sync.sync_all()


def cmd_docker_info() -> None:
    """Show Docker-related information"""
    import platform
    
    print("🐳 Docker Environment Information")
    print("=" * 40)
    
    # Check if running in container
    if os.path.exists('/.dockerenv'):
        print("✅ Running inside Docker container")
        
        # Show container info
        hostname = platform.node()
        print(f"   Container hostname: {hostname}")
        
        # Check mounted volumes
        print("\n📁 Mounted volumes:")
        mounts = [
            ("/app/posters", "Local posters"),
            ("/app/config.yaml", "Configuration"),
            ("/app/logs", "Log directory")
        ]
        
        for path, description in mounts:
            if os.path.exists(path):
                print(f"   ✅ {path} - {description}")
            else:
                print(f"   ❌ {path} - {description} (not mounted)")
        
        # Check environment variables
        print("\n🔧 Environment overrides:")
        env_vars = [
            'REMOTE_SERVER', 'REMOTE_SHARE', 'REMOTE_USERNAME',
            'WATCH_FOLDERS', 'LOG_LEVEL', 'LOCAL_POSTERS_PATH'
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                if 'PASSWORD' in var or 'USERNAME' in var:
                    value = '*' * len(value)
                print(f"   {var}: {value}")
    else:
        print("❌ Not running in Docker container")
        print("   Use 'docker-compose up' to run in Docker")
    
    print("\n🛠️  Docker commands:")
    print("   docker-compose up -d     # Start service")
    print("   docker-compose logs -f   # View logs")
    print("   docker-compose exec tpdb-poster-sync python manage.py <command>")


def cmd_validate_config(config_path: str) -> None:
    """Validate configuration file"""
    print(f"Validating configuration: {config_path}")
    
    try:
        config = Config(config_path)
        config.validate()
        print("✅ Configuration is valid")
        
        # Show key settings
        print("\nKey settings:")
        print(f"  Local base: {config.get('local.base_path')}")
        print(f"  Remote server: {config.get('remote.server')}")
        print(f"  Remote share: {config.get('remote.share')}")
        print(f"  Watch folders: {config.get('sync.watch_folders', True)}")
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="TPDB Poster Sync management utility"
    )
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="Path to configuration file"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Test connection command
    subparsers.add_parser('test-connection', help='Test connection to remote server')
    
    # Scan local command
    subparsers.add_parser('scan-local', help='Scan local directories for posters')
    
    # Dry run command
    subparsers.add_parser('dry-run', help='Perform dry run sync')
    
    # Validate config command
    subparsers.add_parser('validate-config', help='Validate configuration file')
    
    # Docker info command
    subparsers.add_parser('docker-info', help='Show Docker environment information')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Setup basic logging
    setup_logging(level="INFO")
    
    try:
        if args.command == 'validate-config':
            cmd_validate_config(args.config)
        elif args.command == 'docker-info':
            cmd_docker_info()
        else:
            # Load config for other commands
            config = Config(args.config)
            
            if args.command == 'test-connection':
                cmd_test_connection(config)
            elif args.command == 'scan-local':
                cmd_scan_local(config)
            elif args.command == 'dry-run':
                cmd_dry_run(config)
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
