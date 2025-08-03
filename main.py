#!/usr/bin/env python3
"""
TPDB Poster Sync - Main application entry point
Syncs movie, TV show, and collection posters from local folders to remote server
"""

import sys
import argparse
import logging
from pathlib import Path

from src.config import Config
from src.poster_sync import PosterSync
from src.logger import setup_logging


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description="Sync poster files from local folders to remote server"
    )
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be synced without making changes"
    )
    parser.add_argument(
        "--once", 
        action="store_true",
        help="Run sync once and exit (don't monitor for changes)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = Config(args.config)
        
        # Setup logging
        log_level = "DEBUG" if args.verbose else config.get("logging.level", "INFO")
        setup_logging(
            level=log_level,
            log_file=config.get("logging.file"),
            max_size=config.get("logging.max_size", 10485760),
            backup_count=config.get("logging.backup_count", 5)
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Starting TPDB Poster Sync")
        logger.info(f"Configuration file: {args.config}")
        
        # Show basic configuration info
        local_folders = config.get_local_folders()
        remote_paths = config.get_remote_paths()
        logger.info(f"Local base path: {config.get('local.base_path')}")
        logger.info(f"Remote server: {config.get('remote.server')}:{config.get('remote.share')}")
        logger.info(f"Configured folders: {', '.join(local_folders.keys())}")
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No files will be modified")
        
        # Initialize poster sync
        sync = PosterSync(config, dry_run=args.dry_run)
        
        # Run sync
        if args.once:
            logger.info("Running one-time sync")
            sync.sync_all()
        else:
            logger.info("Starting continuous monitoring")
            sync.start_monitoring()
            
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
