"""
File monitoring and change detection for poster sync
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Callable, Optional
from threading import Event

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class PosterFileHandler(FileSystemEventHandler):
    """File system event handler for poster files"""
    
    def __init__(self, callback: Callable[[Path], None], extensions: List[str]):
        """
        Initialize handler
        
        Args:
            callback: Function to call when poster file changes
            extensions: List of file extensions to monitor
        """
        super().__init__()
        self.callback = callback
        self.extensions = [ext.lower() for ext in extensions]
        self.logger = logging.getLogger(__name__)
    
    def is_poster_file(self, file_path: Path) -> bool:
        """Check if file is a poster file"""
        return file_path.suffix.lower() in self.extensions
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if self.is_poster_file(file_path):
                self.logger.info(f"New poster file detected: {file_path}")
                self.callback(file_path)
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if self.is_poster_file(file_path):
                self.logger.info(f"Poster file modified: {file_path}")
                self.callback(file_path)
    
    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move events"""
        if not event.is_directory:
            dest_path = Path(event.dest_path)
            if self.is_poster_file(dest_path):
                self.logger.info(f"Poster file moved: {dest_path}")
                self.callback(dest_path)


class FileMonitor:
    """Monitor poster directories for changes"""
    
    def __init__(self, poster_extensions: List[str]):
        """
        Initialize file monitor
        
        Args:
            poster_extensions: List of file extensions to monitor
        """
        self.poster_extensions = poster_extensions
        self.observers: List[Observer] = []
        self.stop_event = Event()
        self.logger = logging.getLogger(__name__)
        
        if not WATCHDOG_AVAILABLE:
            self.logger.warning("Watchdog not available - file monitoring disabled")
    
    def add_watch(self, directory: Path, callback: Callable[[Path], None]) -> None:
        """
        Add directory to watch list
        
        Args:
            directory: Directory to monitor
            callback: Function to call when files change
        """
        if not WATCHDOG_AVAILABLE:
            return
        
        if not directory.exists():
            self.logger.warning(f"Directory does not exist: {directory}")
            return
        
        self.logger.info(f"Adding watch for directory: {directory}")
        
        handler = PosterFileHandler(callback, self.poster_extensions)
        observer = Observer()
        observer.schedule(handler, str(directory), recursive=True)
        self.observers.append(observer)
    
    def start(self) -> None:
        """Start monitoring all watched directories"""
        if not WATCHDOG_AVAILABLE:
            self.logger.warning("Cannot start monitoring - watchdog not available")
            return
        
        self.logger.info(f"Starting file monitoring for {len(self.observers)} directories")
        
        for observer in self.observers:
            observer.start()
        
        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self) -> None:
        """Stop monitoring"""
        self.logger.info("Stopping file monitoring")
        self.stop_event.set()
        
        for observer in self.observers:
            observer.stop()
            observer.join()
        
        self.observers.clear()
    
    def is_running(self) -> bool:
        """Check if monitoring is running"""
        return any(observer.is_alive() for observer in self.observers)


class PosterScanner:
    """Scan directories for poster files"""
    
    def __init__(self, poster_extensions: List[str], poster_names: List[str], season_patterns: List[str] = None):
        """
        Initialize scanner
        
        Args:
            poster_extensions: List of supported file extensions
            poster_names: List of common poster filenames
            season_patterns: List of regex patterns for season posters
        """
        self.poster_extensions = [ext.lower() for ext in poster_extensions]
        self.poster_names = [name.lower() for name in poster_names]
        self.season_patterns = season_patterns or [
            r'season\d{2}-?poster',      # season01-poster, season01poster
            r's\d{2}-?poster',           # s01-poster, s01poster  
            r'season\d{1,2}-?poster',    # season1-poster, season12-poster
            r's\d{1,2}-?poster',         # s1-poster, s12-poster
            r'season\d{2}-?folder',      # season01-folder
            r's\d{2}-?folder',           # s01-folder
            r'season\d{2}-?cover',       # season01-cover
            r's\d{2}-?cover',            # s01-cover
        ]
        self.logger = logging.getLogger(__name__)
    
    def is_poster_file(self, file_path: Path) -> bool:
        """
        Check if file is likely a poster
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file appears to be a poster
        """
        # Check extension
        if file_path.suffix.lower() not in self.poster_extensions:
            return False
        
        # Check filename (without extension)
        filename = file_path.stem.lower()
        
        # Exact match with poster names
        if filename in self.poster_names:
            return True
        
        # Check if filename contains poster keywords
        for poster_name in self.poster_names:
            if poster_name in filename:
                return True
        
        # Check for season poster patterns
        if self.is_season_poster(filename):
            return True
        
        return False
    
    def is_season_poster(self, filename: str) -> bool:
        """
        Check if filename matches season poster patterns
        
        Args:
            filename: Filename to check (without extension)
            
        Returns:
            True if filename appears to be a season poster
        """
        import re
        
        for pattern in self.season_patterns:
            if re.match(pattern, filename):
                return True
        
        return False
    
    def scan_directory(self, directory: Path, recursive: bool = True) -> Dict[str, List[Path]]:
        """
        Scan directory for poster files organized by media folder
        
        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            Dictionary mapping media folder names to poster file paths
        """
        result = {}
        
        if not directory.exists():
            self.logger.warning(f"Directory does not exist: {directory}")
            return result
        
        self.logger.info(f"Scanning directory: {directory}")
        
        if recursive:
            # Scan subdirectories (each subfolder represents a media item)
            for subdir in directory.iterdir():
                if subdir.is_dir():
                    posters = self.find_posters_in_folder(subdir)
                    if posters:
                        result[subdir.name] = posters
        else:
            # Scan current directory only
            posters = self.find_posters_in_folder(directory)
            if posters:
                result[directory.name] = posters
        
        self.logger.info(f"Found posters for {len(result)} media items")
        return result
    
    def find_posters_in_folder(self, folder: Path) -> List[Path]:
        """
        Find poster files in a specific folder
        
        Args:
            folder: Folder to search
            
        Returns:
            List of poster file paths
        """
        posters = []
        
        for file_path in folder.iterdir():
            if file_path.is_file() and self.is_poster_file(file_path):
                posters.append(file_path)
        
        # Sort by preference (poster.jpg > folder.png > cover.jpg, etc.)
        posters.sort(key=lambda p: (
            self.poster_names.index(p.stem.lower()) if p.stem.lower() in self.poster_names else 999,
            self.poster_extensions.index(p.suffix.lower())
        ))
        
        return posters
    
    def find_posters_and_seasons_in_folder(self, folder: Path) -> tuple:
        """
        Find both series posters and season posters in a specific folder
        
        Args:
            folder: Folder to search
            
        Returns:
            Tuple of (series_posters, season_posters_dict)
            where season_posters_dict maps season identifiers to poster lists
        """
        import re
        
        series_posters = []
        season_posters = {}
        
        for file_path in folder.iterdir():
            if file_path.is_file() and self.is_poster_file(file_path):
                filename = file_path.stem.lower()
                
                # Check if this is a season poster
                if self.is_season_poster(filename):
                    # Extract season identifier
                    season_id = self.extract_season_identifier(filename)
                    if season_id:
                        if season_id not in season_posters:
                            season_posters[season_id] = []
                        season_posters[season_id].append(file_path)
                else:
                    # This is a series poster
                    series_posters.append(file_path)
        
        # Sort series posters by preference
        series_posters.sort(key=lambda p: (
            self.poster_names.index(p.stem.lower()) if p.stem.lower() in self.poster_names else 999,
            self.poster_extensions.index(p.suffix.lower())
        ))
        
        # Sort season posters within each season by preference
        for season_id in season_posters:
            season_posters[season_id].sort(key=lambda p: (
                self.poster_extensions.index(p.suffix.lower())
            ))
        
        return series_posters, season_posters
    
    def extract_season_identifier(self, filename: str) -> str:
        """
        Extract season identifier from filename
        
        Args:
            filename: Filename to analyze
            
        Returns:
            Season identifier (e.g., "01", "1") or empty string if not found
        """
        import re
        
        # Patterns to extract season numbers
        patterns = [
            r'season(\d{2})',     # season01
            r's(\d{2})',          # s01
            r'season(\d{1,2})',   # season1, season12
            r's(\d{1,2})',        # s1, s12
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                season_num = match.group(1)
                # Normalize to 2-digit format
                return season_num.zfill(2)
        
        return ""
    
    def get_best_poster(self, folder: Path) -> Optional[Path]:
        """
        Get the best poster file from a folder
        
        Args:
            folder: Folder to search
            
        Returns:
            Path to best poster file, or None if none found
        """
        posters = self.find_posters_in_folder(folder)
        return posters[0] if posters else None
