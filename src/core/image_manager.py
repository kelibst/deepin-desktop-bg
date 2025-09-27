"""
Image Manager for coordinating downloads and organizing storage.

Handles storage organization, duplicate detection, cleanup, and
coordination between different wallpaper sources.
"""

import logging
import hashlib
import shutil
from typing import List, Dict, Optional, Set
from pathlib import Path
from PIL import Image
import json
from datetime import datetime


logger = logging.getLogger(__name__)


class ImageManager:
    """Manages wallpaper storage, organization, and cleanup."""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize the image manager.

        Args:
            base_path: Base directory for wallpaper storage.
                      Defaults to ~/Pictures/Wallpapers/
        """
        if base_path is None:
            base_path = Path.home() / "Pictures" / "Wallpapers"

        self.base_path = Path(base_path)
        self.setup_directories()

        # Storage organization
        self.directories = {
            'wallhaven': self.base_path / 'wallhaven',
            'ai_generated': self.base_path / 'ai_generated',
            'community': self.base_path / 'community',
            'public_domain': self.base_path / 'public_domain'
        }

        # Metadata storage
        self.metadata_file = self.base_path / '.metadata.json'
        self.metadata = self.load_metadata()

        # Duplicate tracking
        self.known_hashes: Set[str] = set()
        self.load_known_hashes()

    def setup_directories(self) -> None:
        """Create the organized directory structure."""
        directories = [
            'wallhaven',      # Wallhaven.cc wallpapers
            'ai_generated',   # AI-generated wallpapers
            'community',      # Reddit and community sources
            'public_domain'   # Wikimedia, NASA, etc.
        ]

        for directory in directories:
            dir_path = self.base_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {dir_path}")

        # Create metadata directory
        (self.base_path / '.metadata').mkdir(exist_ok=True)

    def load_metadata(self) -> Dict:
        """Load metadata about stored wallpapers."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load metadata: {e}")

        return {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'wallpapers': {},
            'stats': {
                'total_downloads': 0,
                'by_source': {},
                'by_category': {}
            }
        }

    def save_metadata(self) -> None:
        """Save metadata to disk."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save metadata: {e}")

    def load_known_hashes(self) -> None:
        """Load hashes of known images for duplicate detection."""
        for wallpaper_info in self.metadata.get('wallpapers', {}).values():
            if 'hash' in wallpaper_info:
                self.known_hashes.add(wallpaper_info['hash'])

    def calculate_image_hash(self, image_path: Path) -> Optional[str]:
        """Calculate hash of an image for duplicate detection."""
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except IOError as e:
            logger.error(f"Failed to calculate hash for {image_path}: {e}")
            return None

    def is_duplicate(self, image_path: Path) -> bool:
        """Check if an image is a duplicate of an existing one."""
        image_hash = self.calculate_image_hash(image_path)
        if image_hash is None:
            return False

        return image_hash in self.known_hashes

    def validate_image(self, image_path: Path) -> bool:
        """
        Validate that an image file is valid and suitable for wallpapers.

        Args:
            image_path: Path to the image file

        Returns:
            True if image is valid, False otherwise
        """
        try:
            with Image.open(image_path) as img:
                # Check if image can be opened
                img.verify()

                # Re-open for further checks (verify() closes the image)
                with Image.open(image_path) as img:
                    width, height = img.size

                    # Minimum resolution check (at least 1280x720)
                    if width < 1280 or height < 720:
                        logger.warning(f"Image too small: {width}x{height} at {image_path}")
                        return False

                    # Check aspect ratio (should be reasonable for wallpapers)
                    aspect_ratio = width / height
                    if aspect_ratio < 0.5 or aspect_ratio > 3.0:
                        logger.warning(f"Unusual aspect ratio: {aspect_ratio} at {image_path}")
                        return False

                    return True

        except Exception as e:
            logger.error(f"Image validation failed for {image_path}: {e}")
            return False

    def store_wallpaper(self,
                       source_path: Path,
                       source_type: str,
                       metadata: Dict = None,
                       target_name: Optional[str] = None) -> Optional[Path]:
        """
        Store a wallpaper in the organized directory structure.

        Args:
            source_path: Path to the source image file
            source_type: Type of source ('curated', 'ai_generated', 'community', 'public_domain')
            metadata: Additional metadata about the wallpaper
            target_name: Custom filename (without extension)

        Returns:
            Path to the stored wallpaper, or None if failed
        """
        if source_type not in self.directories:
            logger.error(f"Invalid source type: {source_type}")
            return None

        if not source_path.exists():
            logger.error(f"Source file does not exist: {source_path}")
            return None

        # Validate the image
        if not self.validate_image(source_path):
            logger.warning(f"Image validation failed for: {source_path}")
            return None

        # Check for duplicates
        if self.is_duplicate(source_path):
            logger.info(f"Duplicate image, skipping: {source_path}")
            return None

        # Determine target filename
        if target_name:
            # Sanitize the target name
            safe_name = "".join(c for c in target_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            target_filename = f"{safe_name}{source_path.suffix}"
        else:
            target_filename = source_path.name

        target_path = self.directories[source_type] / target_filename

        # Handle filename conflicts
        counter = 1
        original_target = target_path
        while target_path.exists():
            stem = original_target.stem
            suffix = original_target.suffix
            target_path = original_target.parent / f"{stem}_{counter}{suffix}"
            counter += 1

        try:
            # Copy the file
            shutil.copy2(source_path, target_path)

            # Calculate and store hash
            image_hash = self.calculate_image_hash(target_path)
            if image_hash:
                self.known_hashes.add(image_hash)

            # Store metadata
            wallpaper_id = str(target_path.relative_to(self.base_path))
            self.metadata['wallpapers'][wallpaper_id] = {
                'path': str(target_path),
                'source_type': source_type,
                'added_date': datetime.now().isoformat(),
                'hash': image_hash,
                'metadata': metadata or {}
            }

            # Update stats
            self.metadata['stats']['total_downloads'] += 1
            source_stats = self.metadata['stats']['by_source']
            source_stats[source_type] = source_stats.get(source_type, 0) + 1

            self.save_metadata()

            logger.info(f"Stored wallpaper: {target_path}")
            return target_path

        except Exception as e:
            logger.error(f"Failed to store wallpaper: {e}")
            return None

    def cleanup_old_wallpapers(self, max_total: int = 1000) -> int:
        """
        Clean up old wallpapers to keep storage manageable.

        Args:
            max_total: Maximum number of wallpapers to keep

        Returns:
            Number of wallpapers removed
        """
        wallpapers = list(self.metadata.get('wallpapers', {}).items())

        if len(wallpapers) <= max_total:
            return 0

        # Sort by date (oldest first)
        wallpapers.sort(key=lambda x: x[1].get('added_date', ''))

        # Remove oldest wallpapers
        removed_count = 0
        to_remove = wallpapers[:len(wallpapers) - max_total]

        for wallpaper_id, wallpaper_info in to_remove:
            try:
                wallpaper_path = Path(wallpaper_info['path'])
                if wallpaper_path.exists():
                    wallpaper_path.unlink()

                # Remove from metadata
                del self.metadata['wallpapers'][wallpaper_id]

                # Remove hash
                if 'hash' in wallpaper_info:
                    self.known_hashes.discard(wallpaper_info['hash'])

                removed_count += 1
                logger.info(f"Removed old wallpaper: {wallpaper_path}")

            except Exception as e:
                logger.error(f"Failed to remove wallpaper {wallpaper_id}: {e}")

        if removed_count > 0:
            self.save_metadata()

        return removed_count

    def get_storage_stats(self) -> Dict:
        """Get storage statistics."""
        total_size = 0
        file_count = 0

        for directory in self.directories.values():
            if directory.exists():
                for file_path in directory.rglob('*'):
                    if file_path.is_file():
                        try:
                            total_size += file_path.stat().st_size
                            file_count += 1
                        except OSError:
                            pass

        return {
            'total_files': file_count,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'by_source': self.metadata['stats']['by_source'],
            'directories': {
                name: len(list(directory.glob('*'))) if directory.exists() else 0
                for name, directory in self.directories.items()
            }
        }

    def list_wallpapers(self, source_type: Optional[str] = None) -> List[Dict]:
        """
        List stored wallpapers, optionally filtered by source type.

        Args:
            source_type: Filter by source type, or None for all

        Returns:
            List of wallpaper information dictionaries
        """
        wallpapers = []

        for wallpaper_id, wallpaper_info in self.metadata.get('wallpapers', {}).items():
            if source_type is None or wallpaper_info.get('source_type') == source_type:
                # Verify file still exists
                wallpaper_path = Path(wallpaper_info['path'])
                if wallpaper_path.exists():
                    wallpapers.append({
                        'id': wallpaper_id,
                        'path': wallpaper_path,
                        **wallpaper_info
                    })

        return wallpapers


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = ImageManager()
    stats = manager.get_storage_stats()
    print(f"Storage stats: {stats}")

    wallpapers = manager.list_wallpapers()
    print(f"Total wallpapers: {len(wallpapers)}")