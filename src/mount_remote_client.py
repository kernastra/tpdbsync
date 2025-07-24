"""
Mount-based SMB client for remote server connections.
This version uses system-mounted CIFS shares instead of direct SMB protocol.
"""
import os
import subprocess
import shutil
import logging
from pathlib import Path, PurePosixPath
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class MountRemoteClient:
    """Client for connecting to remote SMB/CIFS shares via system mount"""
    
    def __init__(self, server: str, share: str, username: str, password: str, domain: str = ""):
        """
        Initialize mount-based SMB client
        
        Args:
            server: Server hostname or IP address
            share: Share name
            username: Username for authentication
            password: Password for authentication
            domain: Domain name (optional)
        """
        self.server = server
        self.share = share
        self.username = username
        self.password = password
        self.domain = domain
        
        self.mount_point = f"/tmp/tpdbsync_mount_{share}"
        self.is_mounted = False
        
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> None:
        """Mount the SMB share"""
        try:
            self.logger.info(f"Mounting SMB share {self.server}/{self.share} at {self.mount_point}")
            
            # Create mount point
            os.makedirs(self.mount_point, exist_ok=True)
            
            # Build mount command
            mount_cmd = [
                "sudo", "mount", "-t", "cifs",
                f"//{self.server}/{self.share}",
                self.mount_point,
                "-o",
                f"username={self.username},password={self.password},uid={os.getuid()},gid={os.getgid()},iocharset=utf8,file_mode=0755,dir_mode=0755"
            ]
            
            # Execute mount
            result = subprocess.run(mount_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.is_mounted = True
                self.logger.info("Successfully mounted SMB share")
            else:
                raise RuntimeError(f"Mount failed: {result.stderr}")
                
        except Exception as e:
            self.logger.error(f"Failed to mount SMB share: {e}")
            self.disconnect()
            raise
    
    def disconnect(self) -> None:
        """Unmount the SMB share"""
        try:
            if self.is_mounted and os.path.ismount(self.mount_point):
                self.logger.info("Unmounting SMB share")
                result = subprocess.run(["sudo", "umount", self.mount_point], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.logger.info("Successfully unmounted SMB share")
                else:
                    self.logger.warning(f"Unmount warning: {result.stderr}")
                
                self.is_mounted = False
                
            # Clean up mount point
            if os.path.exists(self.mount_point):
                try:
                    os.rmdir(self.mount_point)
                except OSError:
                    pass  # Directory not empty or other issue
                    
        except Exception as e:
            self.logger.warning(f"Error during disconnect: {e}")
    
    @contextmanager
    def connection_context(self):
        """Context manager for SMB connection"""
        try:
            self.connect()
            yield self
        finally:
            self.disconnect()
    
    def path_exists(self, remote_path: str) -> bool:
        """Check if remote path exists"""
        if not self.is_mounted:
            raise RuntimeError("Not connected to SMB share")
        
        full_path = os.path.join(self.mount_point, remote_path.lstrip('/'))
        return os.path.exists(full_path)
    
    def create_directory(self, remote_path: str) -> None:
        """Create directory on remote share"""
        if not self.is_mounted:
            raise RuntimeError("Not connected to SMB share")
        
        try:
            full_path = os.path.join(self.mount_point, remote_path.lstrip('/'))
            self.logger.debug(f"Creating directory: {full_path}")
            os.makedirs(full_path, exist_ok=True)
                    
        except Exception as e:
            self.logger.error(f"Failed to create directory {remote_path}: {e}")
            raise
    
    def upload_file(self, local_path: Path, remote_path: str, overwrite: bool = False) -> bool:
        """
        Upload file to remote share
        
        Args:
            local_path: Local file path
            remote_path: Remote file path
            overwrite: Whether to overwrite existing files
            
        Returns:
            True if upload successful, False otherwise
        """
        if not self.is_mounted:
            raise RuntimeError("Not connected to SMB share")
        
        try:
            full_remote_path = os.path.join(self.mount_point, remote_path.lstrip('/'))
            
            # Check if file exists and handle overwrite
            if os.path.exists(full_remote_path) and not overwrite:
                self.logger.info(f"Remote file exists, skipping: {remote_path}")
                return False
            
            # Create parent directory if needed
            parent_dir = os.path.dirname(full_remote_path)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            
            # Copy file
            self.logger.info(f"Uploading {local_path} -> {remote_path}")
            shutil.copy2(local_path, full_remote_path)
            
            self.logger.info(f"Successfully uploaded {remote_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload {local_path} to {remote_path}: {e}")
            return False
    
    def list_directory(self, remote_path: str) -> List[Dict[str, Any]]:
        """List contents of remote directory"""
        if not self.is_mounted:
            raise RuntimeError("Not connected to SMB share")
        
        try:
            full_path = os.path.join(self.mount_point, remote_path.lstrip('/'))
            
            if not os.path.exists(full_path):
                return []
            
            files = []
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                stat = os.stat(item_path)
                
                files.append({
                    'name': item,
                    'size': stat.st_size,
                    'is_directory': os.path.isdir(item_path),
                    'created': stat.st_ctime,
                    'modified': stat.st_mtime
                })
            
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to list directory {remote_path}: {e}")
            return []


def create_remote_client(server: str, share: str, username: str, password: str, domain: str = "") -> 'MountRemoteClient':
    """
    Factory function to create mount-based remote client
    """
    return MountRemoteClient(server, share, username, password, domain)
