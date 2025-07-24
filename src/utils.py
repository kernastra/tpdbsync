"""
Utility functions for poster sync
"""

import re
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for cross-platform compatibility
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 255:
        name, ext = Path(filename).stem, Path(filename).suffix
        max_name_len = 255 - len(ext)
        filename = name[:max_name_len] + ext
    
    return filename


def get_file_hash(file_path: Path) -> str:
    """
    Calculate MD5 hash of file
    
    Args:
        file_path: Path to file
        
    Returns:
        MD5 hash as hexadecimal string
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_image_info(file_path: Path) -> Optional[Tuple[int, int, str]]:
    """
    Get image dimensions and format
    
    Args:
        file_path: Path to image file
        
    Returns:
        Tuple of (width, height, format) or None if not a valid image
    """
    try:
        with Image.open(file_path) as img:
            return img.width, img.height, img.format
    except Exception:
        return None


def is_valid_poster_dimensions(width: int, height: int, min_ratio: float = 0.5, max_ratio: float = 2.0) -> bool:
    """
    Check if image dimensions are reasonable for a poster
    
    Args:
        width: Image width
        height: Image height
        min_ratio: Minimum width/height ratio
        max_ratio: Maximum width/height ratio
        
    Returns:
        True if dimensions seem reasonable for a poster
    """
    if width <= 0 or height <= 0:
        return False
    
    ratio = width / height
    return min_ratio <= ratio <= max_ratio


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def normalize_media_name(name: str) -> str:
    """
    Normalize media name for consistent matching
    
    Args:
        name: Original media name
        
    Returns:
        Normalized name
    """
    # Convert to lowercase
    name = name.lower()
    
    # Remove common words and punctuation
    name = re.sub(r'\b(the|a|an)\b', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name
