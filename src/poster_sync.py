"""
Main poster sync logic
"""

import logging
import time
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional

from .config import Config
from .remote_client import create_remote_client, SMB_AVAILABLE
from .mount_remote_client import create_remote_client as create_mount_client
from .file_monitor import FileMonitor, PosterScanner


class PosterSync:
    """Main poster synchronization class"""
    
    def __init__(self, config: Config, dry_run: bool = False):
        """
        Initialize poster sync
        
        Args:
            config: Configuration object
            dry_run: If True, don't make actual changes
        """
        self.config = config
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)
        
        # Validate configuration
        self.config.validate()
        
        # Initialize components
        self.scanner = PosterScanner(
            self.config.get_poster_extensions(),
            self.config.get_poster_names()
        )
        
        self.monitor = FileMonitor(self.config.get_poster_extensions())
        
        # Initialize remote client - use mount-based approach
        self.logger.info("Initializing mount-based remote client")
        self.remote_client = create_mount_client(
            server=self.config.get("remote.server"),
            share=self.config.get("remote.share"),
            username=self.config.get("remote.username"),
            password=self.config.get("remote.password"),
            domain=self.config.get("remote.domain", "")
        )
        
        self.stats = {
            'processed': 0,
            'uploaded': 0,
            'skipped': 0,
            'errors': 0
        }
    
    def sync_all(self) -> None:
        """Perform one-time sync of all poster folders"""
        self.logger.info("Starting full poster sync")
        
        local_folders = self.config.get_local_folders()
        remote_paths = self.config.get_remote_paths()
        
        with self.remote_client.connection_context():
            for media_type, local_folder in local_folders.items():
                if media_type not in remote_paths:
                    self.logger.warning(f"No remote path configured for {media_type}")
                    continue
                
                remote_base = remote_paths[media_type]
                self.sync_media_type(media_type, local_folder, remote_base)
        
        self.log_stats()
    
    def sync_media_type(self, media_type: str, local_folder: Path, remote_base: str) -> None:
        """
        Sync posters for a specific media type
        
        Args:
            media_type: Type of media (movies, tv, collections)
            local_folder: Local folder containing poster subdirectories
            remote_base: Remote base path for this media type
        """
        self.logger.info(f"Syncing {media_type} posters from {local_folder}")
        
        if not local_folder.exists():
            self.logger.warning(f"Local folder does not exist: {local_folder}")
            return
        
        # Scan for posters organized by media item folders
        poster_map = self.scanner.scan_directory(local_folder, recursive=True)
        
        # If this is a shared folder (movies and TV in same folder), 
        # we need to sync all items for each media type
        for media_name, poster_files in poster_map.items():
            self.sync_media_item(media_name, poster_files, remote_base)
    
    def sync_media_item(self, media_name: str, poster_files: List[Path], remote_base: str) -> None:
        """
        Sync posters for a specific media item
        
        Args:
            media_name: Name of the media item (folder name)
            poster_files: List of poster files for this item
            remote_base: Remote base path
        """
        self.stats['processed'] += 1
        
        if not poster_files:
            self.logger.debug(f"No posters found for {media_name}")
            return
        
        # Use the best poster file
        best_poster = poster_files[0]  # Already sorted by preference
        
        # Construct remote path
        remote_path = str(PurePosixPath(remote_base) / media_name / f"poster{best_poster.suffix}")
        
        try:
            # Check file size constraints
            file_size = best_poster.stat().st_size
            min_size = self.config.get('sync.min_file_size', 1024)
            max_size = self.config.get('sync.max_file_size', 10485760)
            
            if file_size < min_size:
                self.logger.warning(f"File too small ({file_size} bytes): {best_poster}")
                self.stats['skipped'] += 1
                return
            
            if file_size > max_size:
                self.logger.warning(f"File too large ({file_size} bytes): {best_poster}")
                self.stats['skipped'] += 1
                return
            
            # Check if we should overwrite existing files
            overwrite = self.config.get('sync.overwrite_existing', False)
            
            if self.dry_run:
                self.logger.info(f"DRY RUN: Would upload {best_poster} -> {remote_path}")
                self.stats['uploaded'] += 1
            else:
                # Upload the poster
                success = self.remote_client.upload_file(
                    best_poster, 
                    remote_path, 
                    overwrite=overwrite
                )
                
                if success:
                    self.stats['uploaded'] += 1
                else:
                    self.stats['skipped'] += 1
                    
        except Exception as e:
            self.logger.error(f"Error syncing {media_name}: {e}")
            self.stats['errors'] += 1
    
    def sync_single_file(self, file_path: Path) -> None:
        """
        Sync a single poster file (called by file monitor)
        
        Args:
            file_path: Path to the changed poster file
        """
        self.logger.info(f"Syncing single file: {file_path}")
        
        # Determine media type and item from file path
        local_folders = self.config.get_local_folders()
        remote_paths = self.config.get_remote_paths()
        
        # Find which media type this file belongs to
        media_type = None
        relative_path = None
        
        for mt, folder in local_folders.items():
            try:
                relative_path = file_path.relative_to(folder)
                media_type = mt
                break
            except ValueError:
                continue
        
        if not media_type or not relative_path:
            self.logger.warning(f"Could not determine media type for {file_path}")
            return
        
        if media_type not in remote_paths:
            self.logger.warning(f"No remote path configured for {media_type}")
            return
        
        # Get media item name (parent directory)
        media_name = relative_path.parts[0] if len(relative_path.parts) > 1 else file_path.stem
        
        # Sync this specific item
        with self.remote_client.connection_context():
            poster_files = self.scanner.find_posters_in_folder(file_path.parent)
            self.sync_media_item(media_name, poster_files, remote_paths[media_type])
    
    def start_monitoring(self) -> None:
        """Start file monitoring for continuous sync"""
        if not self.config.get('sync.watch_folders', True):
            self.logger.info("File watching disabled, using periodic sync")
            self.periodic_sync()
            return
        
        self.logger.info("Starting file monitoring")
        
        # Add watches for all local folders
        local_folders = self.config.get_local_folders()
        for media_type, folder in local_folders.items():
            self.monitor.add_watch(folder, self.sync_single_file)
        
        # Start monitoring
        try:
            self.monitor.start()
        except KeyboardInterrupt:
            self.logger.info("Monitoring interrupted")
        finally:
            self.monitor.stop()
    
    def periodic_sync(self) -> None:
        """Run periodic sync instead of file monitoring"""
        sync_interval = self.config.get('sync.sync_interval', 300)  # 5 minutes default
        
        self.logger.info(f"Starting periodic sync (interval: {sync_interval}s)")
        
        try:
            while True:
                self.sync_all()
                self.logger.info(f"Sleeping for {sync_interval} seconds")
                time.sleep(sync_interval)
        except KeyboardInterrupt:
            self.logger.info("Periodic sync interrupted")
    
    def log_stats(self) -> None:
        """Log synchronization statistics"""
        self.logger.info(
            f"Sync completed - Processed: {self.stats['processed']}, "
            f"Uploaded: {self.stats['uploaded']}, "
            f"Skipped: {self.stats['skipped']}, "
            f"Errors: {self.stats['errors']}"
        )
        
        # Reset stats for next run
        self.stats = {key: 0 for key in self.stats}
