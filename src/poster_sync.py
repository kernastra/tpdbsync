"""
Main poster sync logic
"""


import logging
import shutil
import time
import os
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional

from .config import Config
from .remote_client import create_remote_client, SMB_AVAILABLE
from .mount_remote_client import create_remote_client as create_mount_client
from .file_monitor import FileMonitor, PosterScanner


class PosterSync:
    def try_match_and_move(self, file_path: Path) -> bool:
        """
        Try to match a poster file to a remote folder and move it if possible.
        Returns True if matched and moved, False otherwise.
        """
        # Determine if this is a movie, tv, or season poster by scanning remote folders
        # Use the same normalization logic as sync
        import re
        file_stem = file_path.stem
        file_ext = file_path.suffix
        # Try to match to movies
        local_folders = self.config.get_local_folders()
        remote_paths = self.config.get_remote_paths()
        def normalize(s, remove_year=False):
            s = re.sub(r"[-_:;&']", '', s)
            s = re.sub(r'\s+',' ', s)
            if remove_year:
                s = re.sub(r'\(\d{4}\)', '', s)  # Remove (YYYY)
            return s.strip().lower()
        # Try movies
        if 'movies' in remote_paths:
            remote_base = remote_paths['movies']
            remote_dir = os.path.join(self.remote_client.mount_point, remote_base)
            if os.path.exists(remote_dir):
                for folder in os.listdir(remote_dir):
                    folder_path = os.path.join(remote_dir, folder)
                    if not os.path.isdir(folder_path):
                        continue
                    if normalize(folder) == normalize(file_stem):
                        dest = Path(folder_path) / f"poster{file_ext}"
                        try:
                            shutil.move(str(file_path), str(dest))
                            self.logger.info(f"Matched and moved {file_path.name} to {dest}")
                            return True
                        except Exception as e:
                            self.logger.error(f"Failed to move {file_path} to {dest}: {e}")
                            return False
        # Try TV shows (remove year in parentheses for matching)
        if 'tv' in remote_paths:
            remote_base = remote_paths['tv']
            remote_dir = os.path.join(self.remote_client.mount_point, remote_base)
            if os.path.exists(remote_dir):
                for folder in os.listdir(remote_dir):
                    folder_path = os.path.join(remote_dir, folder)
                    if not os.path.isdir(folder_path):
                        continue
                    if normalize(folder, remove_year=True) == normalize(file_stem, remove_year=True):
                        # Check for season poster
                        season_match = re.search(r'season(\d{1,2})', file_stem, re.IGNORECASE)
                        if season_match:
                            season_num = season_match.group(1).zfill(2)
                            season_folder = Path(folder_path) / f"Season {season_num}"
                            season_folder.mkdir(exist_ok=True)
                            dest = season_folder / f"season{season_num}{file_ext}"
                        else:
                            dest = Path(folder_path) / f"poster{file_ext}"
                        try:
                            shutil.move(str(file_path), str(dest))
                            self.logger.info(f"Matched and moved {file_path.name} to {dest}")
                            return True
                        except Exception as e:
                            self.logger.error(f"Failed to move {file_path} to {dest}: {e}")
                            return False
        return False
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
        if media_type == 'tv':
            # For TV, sync entire folder structure
            for show_folder in local_folder.iterdir():
                if show_folder.is_dir():
                    self.sync_tv_show_folder(show_folder, remote_base)
        else:
            for media_name, poster_files in poster_map.items():
                self.sync_media_item(media_name, poster_files, remote_base, media_type=media_type)

    def sync_tv_show_folder(self, local_show_folder: Path, remote_base: str) -> None:
        """
        Sync an entire TV show folder: main series poster and all season posters.
        """
        import re
        show_name = local_show_folder.name
        # Find matching remote folder
        def normalize(s):
            s = re.sub(r"[-_:;&']", '', s)
            s = re.sub(r'\s+', ' ', s)
            s = re.sub(r'\(\d{4}\)', '', s)
            return s.strip().lower()
        remote_dir = os.path.join(self.remote_client.mount_point, remote_base)
        remote_folder = None
        for folder in os.listdir(remote_dir):
            folder_path = os.path.join(remote_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            if normalize(folder) == normalize(show_name):
                remote_folder = folder_path
                break
        if not remote_folder:
            self.logger.warning(f"No matching remote folder found for {show_name}, skipping full folder sync.")
            return
        # Sync main series poster (named as show.ext)
        for file in local_show_folder.iterdir():
            if file.is_file():
                # Main series poster
                if normalize(file.stem) == normalize(show_name):
                    dest = Path(remote_folder) / f"poster{file.suffix}"
                    shutil.copy2(str(file), str(dest))
                    self.logger.info(f"Copied main series poster {file.name} to {dest}")
                # Season poster (match 'Season X' anywhere in filename)
                import re
                season_match = re.search(r'Season[ _-]?(\d{1,2})', file.stem, re.IGNORECASE)
                if season_match:
                    season_num_raw = season_match.group(1)
                    season_num_zfill = season_num_raw.zfill(2)
                    # Look for both 'Season 1' and 'Season 01' folders
                    possible_folders = [f"Season {season_num_raw}", f"Season {season_num_zfill}"]
                    remote_season_folder = None
                    for folder_name in possible_folders:
                        candidate = Path(remote_folder) / folder_name
                        if candidate.exists():
                            remote_season_folder = candidate
                            break
                    if remote_season_folder is None:
                        # If neither exists, create the zero-padded one
                        remote_season_folder = Path(remote_folder) / f"Season {season_num_zfill}"
                        remote_season_folder.mkdir(exist_ok=True)
                    dest = remote_season_folder / f"season{season_num_zfill}{file.suffix}"
                    shutil.copy2(str(file), str(dest))
                    self.logger.info(f"Copied season poster {file.name} to {dest}")
        """
        Sync an entire TV show folder: main series poster and all season posters.
        """
        import re
        show_name = local_show_folder.name
        # Find matching remote folder
        def normalize(s):
            s = re.sub(r"[-_:;&']", '', s)
            s = re.sub(r'\s+', ' ', s)
            s = re.sub(r'\(\d{4}\)', '', s)
            return s.strip().lower()
        remote_dir = os.path.join(self.remote_client.mount_point, remote_base)
        remote_folder = None
        for folder in os.listdir(remote_dir):
            folder_path = os.path.join(remote_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            if normalize(folder) == normalize(show_name):
                remote_folder = folder_path
                break
        if not remote_folder:
            self.logger.warning(f"No matching remote folder found for {show_name}, skipping full folder sync.")
            return
        # Sync main series poster (named as show.ext)
        for file in local_show_folder.iterdir():
            if file.is_file():
                # If file stem matches show name (case-insensitive, normalized)
                if normalize(file.stem) == normalize(show_name):
                    dest = Path(remote_folder) / f"poster{file.suffix}"
                    shutil.copy2(str(file), str(dest))
                    self.logger.info(f"Copied main series poster {file.name} to {dest}")
        # Sync season folders
        for season_dir in local_show_folder.iterdir():
            if season_dir.is_dir() and re.match(r'season ?\d{1,2}', season_dir.name, re.IGNORECASE):
                # Extract season number
                match = re.search(r'(\d{1,2})', season_dir.name)
                if not match:
                    continue
                season_num = match.group(1).zfill(2)
                remote_season_folder = Path(remote_folder) / f"Season {season_num}"
                remote_season_folder.mkdir(exist_ok=True)
                for poster_file in season_dir.iterdir():
                    if poster_file.is_file():
                        # Place as seasonXX.ext
                        dest = remote_season_folder / f"season{season_num}{poster_file.suffix}"
                        shutil.copy2(str(poster_file), str(dest))
                        self.logger.info(f"Copied season poster {poster_file.name} to {dest}")
    
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
            def find_best_remote_folder(remote_base, media_name, media_type=None):
                """Find an existing remote folder matching media_name, ignoring special chars (-,_,:,;), case-insensitive, and normalizing spaces. For TV, also remove year in parentheses."""
                import re
                def normalize(s, remove_year=False):
                    s = re.sub(r"[-_:;&']", '', s)
                    s = re.sub(r'\s+', ' ', s)  # collapse multiple spaces
                    if remove_year:
                        s = re.sub(r'\(\d{4}\)', '', s)  # Remove (YYYY)
                    return s.strip().lower()
                remove_year = (media_type == 'tv')
                media_name_norm = normalize(media_name, remove_year=remove_year)
                remote_dir = os.path.join(self.remote_client.mount_point, remote_base)
                if not os.path.exists(remote_dir):
                    return media_name  # Default to exact name if base doesn't exist
                for folder in os.listdir(remote_dir):
                    folder_path = os.path.join(remote_dir, folder)
                    if not os.path.isdir(folder_path):
                        continue
                    folder_norm = normalize(folder, remove_year=remove_year)
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
                remote_folder_name = find_best_remote_folder(remote_base, media_name, media_type=media_type)
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
                remote_folder_name = find_best_remote_folder(remote_base, media_name, media_type=media_type)
                if remote_folder_name is not None:
                    if season_folder:
                        # Extract season number from season_folder (e.g., 'Season 01' -> '01')
                        import re
                        match = re.search(r'Season (\d{1,2})', season_folder, re.IGNORECASE)
                        if match:
                            season_num = match.group(1).zfill(2)
                        else:
                            season_num = '01'  # fallback
                        # Always name as 'seasonXX.ext' for Plex compatibility
                        remote_path = str(PurePosixPath(remote_base) / remote_folder_name / season_folder / f"season{season_num}{poster_file.suffix}")
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
