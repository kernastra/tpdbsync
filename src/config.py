"""
Configuration management for TPDB Poster Sync
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Configuration manager for the poster sync application"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration from YAML file
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        self.data = {}
        self.load()
    
    def load(self) -> None:
        """Load configuration from file"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = yaml.safe_load(f) or {}
            
            # Override with environment variables if running in Docker
            self._apply_env_overrides()
                
            logging.getLogger(__name__).info(f"Loaded configuration from {self.config_path}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides (useful for Docker)"""
        env_mappings = {
            'REMOTE_SERVER': 'remote.server',
            'REMOTE_SHARE': 'remote.share', 
            'REMOTE_USERNAME': 'remote.username',
            'REMOTE_PASSWORD': 'remote.password',
            'REMOTE_DOMAIN': 'remote.domain',
            'WATCH_FOLDERS': 'sync.watch_folders',
            'SYNC_INTERVAL': 'sync.sync_interval',
            'OVERWRITE_EXISTING': 'sync.overwrite_existing',
            'LOG_LEVEL': 'logging.level',
            'LOCAL_POSTERS_PATH': 'local.base_path'
        }
        
        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert string values to appropriate types
                if env_var in ['WATCH_FOLDERS', 'OVERWRITE_EXISTING']:
                    env_value = env_value.lower() in ('true', '1', 'yes', 'on')
                elif env_var in ['SYNC_INTERVAL']:
                    try:
                        env_value = int(env_value)
                    except ValueError:
                        continue
                
                self.set(config_key, env_value)
                logging.getLogger(__name__).info(f"Applied environment override: {config_key} = {env_value}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'remote.server')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'remote.server')
            value: Value to set
        """
        keys = key.split('.')
        data = self.data
        
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        
        data[keys[-1]] = value
    
    def validate(self) -> None:
        """Validate required configuration values"""
        required_keys = [
            'local.base_path',
            'remote.server',
            'remote.share',
            'remote.username',
            'remote.password'
        ]
        
        missing_keys = []
        for key in required_keys:
            if self.get(key) is None:
                missing_keys.append(key)
        
        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {', '.join(missing_keys)}")
    
    def get_local_folders(self) -> Dict[str, Path]:
        """Get local poster folder paths"""
        base_path = Path(self.get('local.base_path'))
        folders = self.get('local.folders', {})
        
        return {
            media_type: base_path / folder_name
            for media_type, folder_name in folders.items()
        }
    
    def get_remote_paths(self) -> Dict[str, str]:
        """Get remote poster paths"""
        return self.get('remote.paths', {})
    
    def get_poster_extensions(self) -> list:
        """Get list of supported poster file extensions"""
        return self.get('sync.poster_extensions', ['.jpg', '.jpeg', '.png'])
    
    def get_poster_names(self) -> list:
        """Get list of common poster filenames"""
        return self.get('sync.poster_names', ['poster', 'folder', 'cover'])
    
    def get_sync_tv_seasons(self) -> bool:
        """Get whether to sync TV season posters"""
        return self.get('sync.tv_season_posters', True)
    
    def get_season_poster_patterns(self) -> list:
        """Get list of season poster filename patterns"""
        return self.get('sync.season_poster_patterns', [
            r'season\d{2}-?poster',      # season01-poster, season01poster
            r's\d{2}-?poster',           # s01-poster, s01poster  
            r'season\d{1,2}-?poster',    # season1-poster, season12-poster
            r's\d{1,2}-?poster',         # s1-poster, s12-poster
            r'season\d{2}-?folder',      # season01-folder
            r's\d{2}-?folder',           # s01-folder
            r'season\d{2}-?cover',       # season01-cover
            r's\d{2}-?cover',            # s01-cover
        ])
