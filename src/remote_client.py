"""
SMB/CIFS client for remote server connections.
"""
import os
import uuid
import logging
from pathlib import Path, PurePosixPath
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

try:
    from smbprotocol.connection import Connection
    from smbprotocol.session import Session
    from smbprotocol.tree import TreeConnect
    from smbprotocol.open import Open, CreateDisposition
    from smbprotocol.exceptions import SMBException
    
    # File access and attribute constants
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    GENERIC_ALL = 0x10000000
    FILE_ATTRIBUTE_NORMAL = 0x00000080
    FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    
    SMB_AVAILABLE = True
except ImportError as e:
    print(f"SMB import error: {e}")
    SMB_AVAILABLE = False


class RemoteClient:
    """Client for connecting to remote SMB/CIFS shares"""
    
    def __init__(self, server: str, share: str, username: str, password: str, domain: str = ""):
        """
        Initialize SMB client
        
        Args:
            server: Server hostname or IP address
            share: Share name
            username: Username for authentication
            password: Password for authentication
            domain: Domain name (optional)
        """
        if not SMB_AVAILABLE:
            raise RuntimeError("SMB support not available (install smbprotocol)")
        
        self.server = server
        self.share = share
        self.username = username
        self.password = password
        self.domain = domain
        
        self.connection = None
        self.session = None
        self.tree = None
        
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> None:
        """Connect to SMB share"""
        try:
            self.logger.info(f"Connecting to SMB share {self.server}/{self.share}")
            
            # Create connection
            self.connection = Connection(uuid.uuid4(), self.server, 445)
            self.connection.connect()
            
            # Create session with domain handling
            if self.domain:
                full_username = f"{self.domain}\\{self.username}"
            else:
                full_username = self.username
                
            self.session = Session(self.connection, full_username, self.password, require_encryption=False)
            self.session.connect()
            
            # Connect to tree (share)
            self.tree = TreeConnect(self.session, f"\\\\{self.server}\\{self.share}")
            self.tree.connect()
            
            self.logger.info("Successfully connected to SMB share")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to SMB share: {e}")
            self.disconnect()
            raise
    
    def disconnect(self) -> None:
        """Disconnect from SMB share"""
        try:
            if self.tree:
                self.tree.disconnect()
                self.tree = None
            
            if self.session:
                self.session.disconnect()
                self.session = None
            
            if self.connection:
                self.connection.disconnect()
                self.connection = None
                
            self.logger.info("Disconnected from SMB share")
            
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
        if not self.tree:
            raise RuntimeError("Not connected to SMB share")
        
        try:
            file_open = Open(self.tree, remote_path)
            file_open.create(
                CreateDisposition.FILE_OPEN,
                GENERIC_READ,
                FILE_ATTRIBUTE_NORMAL
            )
            file_open.close()
            return True
        except SMBException:
            return False
    
    def create_directory(self, remote_path: str) -> None:
        """Create directory on remote share"""
        if not self.tree:
            raise RuntimeError("Not connected to SMB share")
        
        try:
            # Normalize path
            path_parts = PurePosixPath(remote_path).parts
            current_path = ""
            
            for part in path_parts:
                current_path = str(PurePosixPath(current_path) / part)
                
                if not self.path_exists(current_path):
                    self.logger.debug(f"Creating directory: {current_path}")
                    
                    file_open = Open(self.tree, current_path)
                    file_open.create(
                        CreateDisposition.FILE_CREATE,
                        GENERIC_ALL,
                        FILE_ATTRIBUTE_DIRECTORY
                    )
                    file_open.close()
                    
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
        if not self.tree:
            raise RuntimeError("Not connected to SMB share")
        
        try:
            # Check if file exists and handle overwrite
            if self.path_exists(remote_path) and not overwrite:
                self.logger.info(f"Remote file exists, skipping: {remote_path}")
                return False
            
            # Create parent directory if needed
            parent_path = str(PurePosixPath(remote_path).parent)
            if parent_path != "." and not self.path_exists(parent_path):
                self.create_directory(parent_path)
            
            # Upload file
            self.logger.info(f"Uploading {local_path} -> {remote_path}")
            
            with open(local_path, 'rb') as local_file:
                file_open = Open(self.tree, remote_path)
                file_open.create(
                    CreateDisposition.FILE_OVERWRITE_IF if overwrite else CreateDisposition.FILE_CREATE,
                    GENERIC_WRITE,
                    FILE_ATTRIBUTE_NORMAL
                )
                
                # Write file data
                data = local_file.read()
                file_open.write(data)
                file_open.close()
            
            self.logger.info(f"Successfully uploaded {remote_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload {local_path} to {remote_path}: {e}")
            return False
    
    def list_directory(self, remote_path: str) -> List[Dict[str, Any]]:
        """List contents of remote directory"""
        if not self.tree:
            raise RuntimeError("Not connected to SMB share")
        
        try:
            file_open = Open(self.tree, remote_path)
            file_open.create(
                CreateDisposition.FILE_OPEN,
                GENERIC_READ,
                FILE_ATTRIBUTE_DIRECTORY
            )
            
            files = []
            for file_info in file_open.query_directory():
                files.append({
                    'name': file_info['file_name'].get_value(),
                    'size': file_info['end_of_file'].get_value(),
                    'is_directory': bool(file_info['file_attributes'].get_value() & FILE_ATTRIBUTE_DIRECTORY),
                    'created': file_info['creation_time'].get_value(),
                    'modified': file_info['last_write_time'].get_value()
                })
            
            file_open.close()
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to list directory {remote_path}: {e}")
            return []


# Fallback implementation for when smbprotocol is not available
class MockRemoteClient:
    """Mock client for testing when SMB is not available"""
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.warning("Using mock SMB client - smbprotocol not available")
    
    def connect(self):
        pass
    
    def disconnect(self):
        pass
    
    @contextmanager
    def connection_context(self):
        yield self
    
    def path_exists(self, remote_path: str) -> bool:
        return False
    
    def create_directory(self, remote_path: str) -> None:
        self.logger.info(f"Mock: Would create directory {remote_path}")
    
    def upload_file(self, local_path: Path, remote_path: str, overwrite: bool = False) -> bool:
        self.logger.info(f"Mock: Would upload {local_path} to {remote_path}")
        return True
    
    def list_directory(self, remote_path: str) -> List[Dict[str, Any]]:
        return []


def create_remote_client(server: str, share: str, username: str, password: str, domain: str = "") -> 'RemoteClient':
    """
    Factory function to create remote client
    
    Returns RemoteClient if SMB available, MockRemoteClient otherwise
    """
    if SMB_AVAILABLE:
        return RemoteClient(server, share, username, password, domain)
    else:
        return MockRemoteClient(server, share, username, password, domain)
