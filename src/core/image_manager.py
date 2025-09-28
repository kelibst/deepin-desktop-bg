"""
Image Manager for coordinating downloads and organizing storage.

Handles storage organization, duplicate detection, cleanup, and
coordination between different wallpaper sources.
"""

import logging
import hashlib
import shutil
from typing import List, Dict, Optional, Set, Tuple
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

    def find_duplicate(self, image_path: Path) -> Optional[Path]:
        """
        Find if an image is a duplicate and return the path to the existing file.

        Args:
            image_path: Path to the image file to check

        Returns:
            Path to existing duplicate file, or None if no duplicate found
        """
        image_hash = self.calculate_image_hash(image_path)
        if image_hash is None:
            return None

        if image_hash not in self.known_hashes:
            return None

        # Find the wallpaper with matching hash
        for wallpaper_info in self.metadata.get('wallpapers', {}).values():
            if wallpaper_info.get('hash') == image_hash:
                existing_path = Path(wallpaper_info['path'])
                if existing_path.exists():
                    return existing_path

        return None

    def find_wallpaper_by_id(self, wallpaper_id: str, source_type: Optional[str] = None) -> Optional[Path]:
        """
        Find a wallpaper by its ID in the metadata.

        Args:
            wallpaper_id: The wallpaper ID to search for
            source_type: Optionally filter by source type

        Returns:
            Path to existing wallpaper file, or None if not found
        """
        for wallpaper_info in self.metadata.get('wallpapers', {}).values():
            # Check source type if specified
            if source_type and wallpaper_info.get('source_type') != source_type:
                continue

            # Check if wallpaper ID matches
            metadata = wallpaper_info.get('metadata', {})
            if metadata.get('wallpaper_id') == wallpaper_id:
                existing_path = Path(wallpaper_info['path'])
                if existing_path.exists():
                    return existing_path

        return None

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

        # Check for duplicates and return existing path if found
        existing_duplicate = self.find_duplicate(source_path)
        if existing_duplicate:
            logger.info(f"Duplicate image found, returning existing path: {existing_duplicate}")
            return existing_duplicate

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

    def get_wallpapers_with_thumbnails(self, source_type: Optional[str] = None) -> List[Dict]:
        """
        Get stored wallpapers with additional thumbnail and display information.

        Args:
            source_type: Filter by source type, or None for all

        Returns:
            List of wallpaper dictionaries with thumbnail info
        """
        wallpapers = []

        for wallpaper_id, wallpaper_info in self.metadata.get('wallpapers', {}).items():
            if source_type is None or wallpaper_info.get('source_type') == source_type:
                wallpaper_path = Path(wallpaper_info['path'])
                if wallpaper_path.exists():
                    # Get image dimensions and file size
                    try:
                        with Image.open(wallpaper_path) as img:
                            width, height = img.size
                            resolution = f"{width}x{height}"
                            file_size = wallpaper_path.stat().st_size
                    except Exception as e:
                        logger.warning(f"Failed to get image info for {wallpaper_path}: {e}")
                        resolution = "Unknown"
                        file_size = 0

                    # Create display data compatible with wallpaper cards
                    display_data = {
                        'id': wallpaper_id,
                        'path': wallpaper_path,
                        'resolution': resolution,
                        'file_size': file_size,
                        'source_type': wallpaper_info.get('source_type', 'unknown'),
                        'added_date': wallpaper_info.get('added_date', ''),
                        'metadata': wallpaper_info.get('metadata', {}),

                        # For display compatibility
                        'views': wallpaper_info.get('metadata', {}).get('views', 0),
                        'favorites': wallpaper_info.get('metadata', {}).get('favorites', 0),
                        'category': wallpaper_info.get('metadata', {}).get('category', 'local'),
                        'tags': wallpaper_info.get('metadata', {}).get('tags', []),
                        'created_at': wallpaper_info.get('added_date', ''),

                        # Thumbnail placeholder - will be handled by thumbnail generator
                        'thumbs': {
                            'large': str(wallpaper_path)  # Use full path for local files
                        }
                    }

                    wallpapers.append(display_data)

        # Sort by added date (newest first)
        wallpapers.sort(key=lambda x: x.get('added_date', ''), reverse=True)
        return wallpapers

    def delete_wallpaper(self, wallpaper_id: str) -> bool:
        """
        Delete a wallpaper from storage and metadata.

        Args:
            wallpaper_id: ID of the wallpaper to delete

        Returns:
            True if successfully deleted, False otherwise
        """
        if wallpaper_id not in self.metadata.get('wallpapers', {}):
            logger.warning(f"Wallpaper not found in metadata: {wallpaper_id}")
            return False

        wallpaper_info = self.metadata['wallpapers'][wallpaper_id]
        wallpaper_path = Path(wallpaper_info['path'])

        try:
            # Remove the file if it exists
            if wallpaper_path.exists():
                wallpaper_path.unlink()
                logger.info(f"Deleted wallpaper file: {wallpaper_path}")

            # Remove hash from known hashes
            if 'hash' in wallpaper_info:
                self.known_hashes.discard(wallpaper_info['hash'])

            # Remove from metadata
            del self.metadata['wallpapers'][wallpaper_id]

            # Update stats
            source_type = wallpaper_info.get('source_type', 'unknown')
            if source_type in self.metadata['stats']['by_source']:
                self.metadata['stats']['by_source'][source_type] = max(
                    0, self.metadata['stats']['by_source'][source_type] - 1
                )

            # Save updated metadata
            self.save_metadata()

            logger.info(f"Successfully deleted wallpaper: {wallpaper_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete wallpaper {wallpaper_id}: {e}")
            return False

    def delete_multiple_wallpapers(self, wallpaper_ids: List[str]) -> Tuple[int, int]:
        """
        Delete multiple wallpapers.

        Args:
            wallpaper_ids: List of wallpaper IDs to delete

        Returns:
            Tuple of (successful_deletions, total_requested)
        """
        successful = 0
        total = len(wallpaper_ids)

        for wallpaper_id in wallpaper_ids:
            if self.delete_wallpaper(wallpaper_id):
                successful += 1

        logger.info(f"Deleted {successful}/{total} wallpapers")
        return successful, total

    def get_wallpaper_info(self, wallpaper_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific wallpaper.

        Args:
            wallpaper_id: ID of the wallpaper

        Returns:
            Wallpaper info dictionary or None if not found
        """
        if wallpaper_id not in self.metadata.get('wallpapers', {}):
            return None

        wallpaper_info = self.metadata['wallpapers'][wallpaper_id].copy()
        wallpaper_path = Path(wallpaper_info['path'])

        if not wallpaper_path.exists():
            logger.warning(f"Wallpaper file no longer exists: {wallpaper_path}")
            return None

        # Add current file system info
        try:
            stat_info = wallpaper_path.stat()
            wallpaper_info['current_size'] = stat_info.st_size
            wallpaper_info['current_mtime'] = stat_info.st_mtime

            # Get image dimensions
            with Image.open(wallpaper_path) as img:
                wallpaper_info['dimensions'] = img.size
                wallpaper_info['mode'] = img.mode
                wallpaper_info['format'] = img.format

        except Exception as e:
            logger.warning(f"Failed to get current file info for {wallpaper_path}: {e}")

        return wallpaper_info

    def search_wallpapers(self, query: str, source_type: Optional[str] = None) -> List[Dict]:
        """
        Search wallpapers by filename, metadata, or tags.

        Args:
            query: Search query string
            source_type: Optional source type filter

        Returns:
            List of matching wallpaper dictionaries
        """
        query_lower = query.lower()
        results = []

        for wallpaper_id, wallpaper_info in self.metadata.get('wallpapers', {}).items():
            if source_type and wallpaper_info.get('source_type') != source_type:
                continue

            wallpaper_path = Path(wallpaper_info['path'])
            if not wallpaper_path.exists():
                continue

            # Search in filename
            if query_lower in wallpaper_path.name.lower():
                results.append({
                    'id': wallpaper_id,
                    'path': wallpaper_path,
                    **wallpaper_info
                })
                continue

            # Search in metadata
            metadata = wallpaper_info.get('metadata', {})

            # Search in tags
            tags = metadata.get('tags', [])
            if any(query_lower in tag.lower() for tag in tags):
                results.append({
                    'id': wallpaper_id,
                    'path': wallpaper_path,
                    **wallpaper_info
                })
                continue

            # Search in category
            category = metadata.get('category', '')
            if query_lower in category.lower():
                results.append({
                    'id': wallpaper_id,
                    'path': wallpaper_path,
                    **wallpaper_info
                })
                continue

            # Search in prompt (for AI-generated images)
            prompt = metadata.get('prompt', '')
            if query_lower in prompt.lower():
                results.append({
                    'id': wallpaper_id,
                    'path': wallpaper_path,
                    **wallpaper_info
                })

        return results

    def get_source_type_stats(self) -> Dict[str, Dict]:
        """
        Get detailed statistics for each source type.

        Returns:
            Dictionary with stats for each source type
        """
        stats = {}

        for source_type, directory in self.directories.items():
            wallpapers = self.list_wallpapers(source_type)
            total_size = 0

            for wallpaper in wallpapers:
                try:
                    total_size += wallpaper['path'].stat().st_size
                except OSError:
                    pass

            stats[source_type] = {
                'count': len(wallpapers),
                'size_mb': round(total_size / (1024 * 1024), 2),
                'directory': str(directory)
            }

        return stats

    def export_wallpaper_list(self, output_path: Path, format: str = 'json') -> bool:
        """
        Export wallpaper list to a file.

        Args:
            output_path: Path to output file
            format: Export format ('json' or 'csv')

        Returns:
            True if successful, False otherwise
        """
        try:
            wallpapers = self.get_wallpapers_with_thumbnails()

            if format.lower() == 'json':
                # Convert Path objects to strings for JSON serialization
                export_data = []
                for wallpaper in wallpapers:
                    wallpaper_copy = wallpaper.copy()
                    wallpaper_copy['path'] = str(wallpaper_copy['path'])
                    export_data.append(wallpaper_copy)

                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)

            elif format.lower() == 'csv':
                import csv

                if wallpapers:
                    with open(output_path, 'w', newline='') as f:
                        fieldnames = ['id', 'path', 'source_type', 'resolution', 'file_size', 'added_date']
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()

                        for wallpaper in wallpapers:
                            row = {key: wallpaper.get(key, '') for key in fieldnames}
                            row['path'] = str(row['path'])
                            writer.writerow(row)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False

            logger.info(f"Exported {len(wallpapers)} wallpapers to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export wallpaper list: {e}")
            return False


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = ImageManager()
    stats = manager.get_storage_stats()
    print(f"Storage stats: {stats}")

    wallpapers = manager.list_wallpapers()
    print(f"Total wallpapers: {len(wallpapers)}")