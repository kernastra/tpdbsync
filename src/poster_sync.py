"""
Main poster sync logic
"""


import logging
import time
import os
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
            self.config.get_poster_names(),
            self.config.get_season_poster_patterns()
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
        
        # Log which folders will be synced
        self.logger.info(f"Syncing {len(local_folders)} folder(s):")
        for media_type, local_folder in local_folders.items():
            if local_folder.exists():
                remote_base = remote_paths.get(media_type, "NOT_CONFIGURED")
                self.logger.info(f"  📁 {media_type.upper()}: {local_folder} → {remote_base}")
            else:
                self.logger.warning(f"  ❌ {media_type.upper()}: {local_folder} (does not exist)")
        
        # Show TV season poster status
        if self.config.get_sync_tv_seasons():
            self.logger.info("  📺 TV season poster syncing: ENABLED")
        else:
            self.logger.info("  📺 TV season poster syncing: DISABLED")
        
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
            self.sync_media_item(media_name, poster_files, remote_base, media_type=media_type)
    
    def sync_media_item(self, media_name: str, poster_files: List[Path], remote_base: str, media_type: str = None) -> None:
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
        
        # Check if this is a TV show that might have season posters
        media_folder = None
        local_folders = self.config.get_local_folders()
        
        # Only check for seasons if TV season syncing is enabled
        if self.config.get_sync_tv_seasons():
            # Find the source folder for this media item
            for media_type, folder in local_folders.items():
                if media_type == 'tv':  # Only check for seasons in TV folders
                    potential_folder = folder / media_name
                    if potential_folder.exists():
                        media_folder = potential_folder
                        break
        
        if media_folder and media_folder.exists():
            # Use enhanced scanning for TV shows to separate series and season posters
            series_posters, season_posters = self.scanner.find_posters_and_seasons_in_folder(media_folder)
            
            # Sync series poster (main show poster)
            if series_posters:
                self.sync_single_poster(media_name, series_posters[0], remote_base, "poster", media_type=media_type)
            
            # Sync season posters
            for season_id, season_poster_list in season_posters.items():
                if season_poster_list:
                    # Create season subfolder path
                    season_folder = f"Season {season_id}"
                    self.sync_single_poster(media_name, season_poster_list[0], remote_base, "poster", season_folder, media_type=media_type)
        else:
            # Regular sync for movies and collections (or TV shows without season detection)
            best_poster = poster_files[0]  # Already sorted by preference
            self.sync_single_poster(media_name, best_poster, remote_base, "poster", media_type=media_type)
    
    def sync_single_poster(self, media_name: str, poster_file: Path, remote_base: str, 
                          poster_name: str = "poster", season_folder: str = None, media_type: str = None) -> None:
        """
        Sync a single poster file
        
        Args:
            media_name: Name of the media item (folder name)
            poster_file: Path to the poster file
            remote_base: Remote base path
            poster_name: Name for the poster file (default: "poster")
            season_folder: Optional season folder name for TV season posters
            media_type: Type of media (movies, tv, collections)
        """
        try:
            import re
            def find_best_remote_folder(remote_base, media_name):
                """Find an existing remote folder matching media_name, ignoring special chars (-,_,:,;), case-insensitive, and normalizing spaces. Only create if no match exists."""
                import re
                def normalize(s):
                    s = re.sub(r'[-_:;]', '', s)
                    s = re.sub(r'\s+', ' ', s)  # collapse multiple spaces
                    return s.strip().lower()
                media_name_norm = normalize(media_name)
                remote_dir = os.path.join(self.remote_client.mount_point, remote_base)
                if not os.path.exists(remote_dir):
                    return media_name  # Default to exact name if base doesn't exist
                for folder in os.listdir(remote_dir):
                    folder_path = os.path.join(remote_dir, folder)
                    if not os.path.isdir(folder_path):
                        continue
                    folder_norm = normalize(folder)
                    if folder_norm == media_name_norm:
                        return folder  # Use the existing folder
                # If no match, do NOT create a new folder, just return None
                return None

            # If config says to place poster in movie folder and this is a movie
            if self.config.get('sync.poster_in_movie_folder', False) and (media_type == 'movies' and not season_folder):
                # Find the movie file in the movie folder
                movie_folder = None
                local_folders = self.config.get_local_folders()
                if 'movies' in local_folders:
                    movie_folder = local_folders['movies'] / media_name
                # Use best-matching remote folder
                remote_folder_name = find_best_remote_folder(remote_base, media_name)
                if remote_folder_name is not None:
                    if movie_folder and movie_folder.exists():
                        # Find a movie file (by extension)
                        movie_exts = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.m4v']
                        movie_files = [f for f in movie_folder.iterdir() if f.is_file() and f.suffix.lower() in movie_exts]
                        if movie_files:
                            # Place poster as poster.jpg in the same folder as the movie file
                            remote_path = str(PurePosixPath(remote_base) / remote_folder_name / f"poster{poster_file.suffix}")
                        else:
                            self.logger.warning(f"No movie file found in {movie_folder}, placing poster in default location.")
                            remote_path = str(PurePosixPath(remote_base) / remote_folder_name / f"{poster_name}{poster_file.suffix}")
                    else:
                        self.logger.warning(f"Movie folder not found for {media_name}, placing poster in default location.")
                        remote_path = str(PurePosixPath(remote_base) / remote_folder_name / f"{poster_name}{poster_file.suffix}")
                else:
                    self.logger.warning(f"No matching remote folder found for {media_name}, skipping poster placement.")
                    self.stats['skipped'] += 1
                    return
            elif media_type in ('tv', 'movies'):
                # For TV and movies, use best-matching remote folder
                remote_folder_name = find_best_remote_folder(remote_base, media_name)
                if remote_folder_name is not None:
                    if season_folder:
                        remote_path = str(PurePosixPath(remote_base) / remote_folder_name / season_folder / f"{poster_name}{poster_file.suffix}")
                    else:
                        remote_path = str(PurePosixPath(remote_base) / remote_folder_name / f"{poster_name}{poster_file.suffix}")
                else:
                    self.logger.warning(f"No matching remote folder found for {media_name}, skipping poster placement.")
                    self.stats['skipped'] += 1
                    return
            else:
                # Regular poster: media/jellyfin/metadata/library/collections/Collection Name/poster.jpg
                remote_path = str(PurePosixPath(remote_base) / media_name / f"{poster_name}{poster_file.suffix}")
            
            # Check file size constraints
            file_size = poster_file.stat().st_size
            min_size = self.config.get('sync.min_file_size', 1024)
            max_size = self.config.get('sync.max_file_size', 10485760)
            
            if file_size < min_size:
                self.logger.warning(f"File too small ({file_size} bytes): {poster_file}")
                self.stats['skipped'] += 1
                return
            
            if file_size > max_size:
                self.logger.warning(f"File too large ({file_size} bytes): {poster_file}")
                self.stats['skipped'] += 1
                return
            
            # Check if we should overwrite existing files
            overwrite = self.config.get('sync.overwrite_existing', False)
            
            if self.dry_run:
                season_info = f" (Season {season_folder})" if season_folder else ""
                self.logger.info(f"DRY RUN: Would upload {poster_file}{season_info} -> {remote_path}")
                self.stats['uploaded'] += 1
            else:
                # Upload the poster
                success = self.remote_client.upload_file(
                    poster_file, 
                    remote_path, 
                    overwrite=overwrite
                )
                
                if success:
                    season_info = f" (Season {season_folder})" if season_folder else ""
                    self.logger.info(f"Uploaded {media_name}{season_info} poster: {poster_file.name}")
                    self.stats['uploaded'] += 1
                else:
                    self.stats['skipped'] += 1
                    
        except Exception as e:
            self.logger.error(f"Error syncing {media_name} poster: {e}")
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
        
        # Log which folders will be monitored
        self.logger.info(f"Monitoring {len(local_folders)} folder(s) for changes:")
        for media_type, folder in local_folders.items():
            if folder.exists():
                self.logger.info(f"  📁 {media_type.upper()}: {folder}")
                self.monitor.add_watch(folder, self.sync_single_file)
            else:
                self.logger.warning(f"  ❌ {media_type.upper()}: {folder} (does not exist)")
        
        # Show TV season poster status
        if self.config.get_sync_tv_seasons():
            self.logger.info("  📺 TV season poster syncing: ENABLED")
        else:
            self.logger.info("  📺 TV season poster syncing: DISABLED")
        
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
