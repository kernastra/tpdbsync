"""
Intake and unmatched folder monitoring and processing for poster sync
"""

import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import List
from .poster_sync import PosterSync

class IntakeMonitor:
    """Monitor and process the intake and unmatched folders"""
    def __init__(self, poster_sync: PosterSync, intake_folder: Path, unmatched_folder: Path):
        self.poster_sync = poster_sync
        self.intake_folder = intake_folder
        self.unmatched_folder = unmatched_folder
        self.logger = logging.getLogger(__name__)

    def process_intake(self):
        """Process new files in the intake folder (including .zip)"""
        for item in self.intake_folder.iterdir():
            if item.is_file():
                if item.suffix.lower() == '.zip':
                    self._process_zip(item)
                else:
                    self._process_file(item)

    def _process_zip(self, zip_path: Path):
        """Analyze and extract a zip file to the correct unmatched subfolder"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                namelist = zip_ref.namelist()
                # Check for 'season' in any filename (case-insensitive)
                is_tv = any('season' in name.lower() for name in namelist)
                # Try to extract a series name from the first file with 'season' in it
                series_name = None
                if is_tv:
                    for name in namelist:
                        if 'season' in name.lower():
                            parts = name.split('/')
                            if len(parts) > 1:
                                series_name = parts[0]
                            else:
                                import re
                                match = re.match(r"(.+)[-_ ]season", name, re.IGNORECASE)
                                if match:
                                    series_name = match.group(1).strip()
                            break
                    if not series_name:
                        series_name = zip_path.stem
                    extract_dir = self.unmatched_folder / 'tv' / series_name
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    zip_ref.extractall(extract_dir)
                    self.logger.info(f"Extracted {zip_path} to {extract_dir} (TV series, left for later matching)")
                    # Do NOT process files now; leave them for unmatched processing
                else:
                    extract_dir = self.unmatched_folder / 'movies' / zip_path.stem
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    zip_ref.extractall(extract_dir)
                    self.logger.info(f"Extracted {zip_path} to {extract_dir}")
                    for file in extract_dir.rglob('*'):
                        if file.is_file():
                            self._process_file(file)
            zip_path.unlink()  # Remove zip after processing
        except Exception as e:
            self.logger.error(f"Failed to extract/process {zip_path}: {e}")

    def _process_file(self, file_path: Path):
        """Try to match and move poster file, or move to unmatched/movies"""
        matched = self.poster_sync.try_match_and_move(file_path)
        if not matched:
            # Place unmatched movie posters in unmatched/movies
            movies_dir = self.unmatched_folder / 'movies'
            movies_dir.mkdir(exist_ok=True)
            dest = movies_dir / file_path.name
            self.logger.info(f"No match for {file_path.name}, moving to {dest}")
            shutil.move(str(file_path), str(dest))

    def process_unmatched(self):
        """Retry unmatched files if new folders appear on remote shares. Move any stray files in unmatched root to movies/ first."""
        # Move any files in unmatched root to unmatched/movies
        for file in list(self.unmatched_folder.iterdir()):
            if file.is_file():
                movies_dir = self.unmatched_folder / 'movies'
                movies_dir.mkdir(exist_ok=True)
                dest = movies_dir / file.name
                self.logger.info(f"Moving stray unmatched file {file.name} to {dest}")
                shutil.move(str(file), str(dest))
        # Now process unmatched/movies and unmatched/tv
        for subfolder in ['movies', 'tv']:
            folder = self.unmatched_folder / subfolder
            if folder.exists():
                for root, dirs, files in os.walk(folder):
                    for fname in files:
                        fpath = Path(root) / fname
                        matched = self.poster_sync.try_match_and_move(fpath)
                        if matched:
                            self.logger.info(f"Moved previously unmatched file: {fpath.name}")
