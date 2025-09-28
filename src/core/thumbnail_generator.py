"""
Thumbnail Generator for creating and caching thumbnails of local wallpaper files.

Generates thumbnails for stored wallpapers to display in the downloaded images gallery.
Supports async generation and caching for performance.
"""

import logging
import hashlib
from typing import Dict, Optional, Tuple, List
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime

from PIL import Image, ImageOps
from PySide6.QtCore import QObject, Signal, QThread, QTimer, Qt
from PySide6.QtGui import QPixmap


logger = logging.getLogger(__name__)


class ThumbnailWorker(QThread):
    """Worker thread for generating thumbnails."""

    thumbnail_ready = Signal(str, QPixmap)  # file_path, thumbnail_pixmap
    thumbnail_error = Signal(str, str)      # file_path, error_message
    progress = Signal(int, int)             # current, total

    def __init__(self, files_to_process: List[Path], target_size: Tuple[int, int], cache_dir: Path):
        """
        Initialize thumbnail worker.

        Args:
            files_to_process: List of image files to process
            target_size: Target thumbnail size (width, height)
            cache_dir: Directory to cache thumbnails
        """
        super().__init__()
        self.files_to_process = files_to_process
        self.target_size = target_size
        self.cache_dir = cache_dir
        self.should_stop = False

    def run(self):
        """Run thumbnail generation process."""
        total_files = len(self.files_to_process)

        for i, file_path in enumerate(self.files_to_process):
            if self.should_stop:
                break

            try:
                thumbnail = self._generate_thumbnail(file_path)
                if thumbnail:
                    self.thumbnail_ready.emit(str(file_path), thumbnail)
                else:
                    self.thumbnail_error.emit(str(file_path), "Failed to generate thumbnail")

            except Exception as e:
                logger.error(f"Error generating thumbnail for {file_path}: {e}")
                self.thumbnail_error.emit(str(file_path), str(e))

            self.progress.emit(i + 1, total_files)

    def stop(self):
        """Stop the thumbnail generation process."""
        self.should_stop = True

    def _generate_thumbnail(self, image_path: Path) -> Optional[QPixmap]:
        """
        Generate thumbnail for a single image.

        Args:
            image_path: Path to the image file

        Returns:
            QPixmap thumbnail or None if failed
        """
        try:
            # Check cache first
            cache_path = self._get_cache_path(image_path)
            if cache_path.exists():
                # Load from cache
                pixmap = QPixmap(str(cache_path))
                if not pixmap.isNull():
                    return pixmap

            # Generate new thumbnail
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Create thumbnail maintaining aspect ratio
                img.thumbnail(self.target_size, Image.Resampling.LANCZOS)

                # Create a new image with the exact target size and center the thumbnail
                thumbnail = Image.new('RGB', self.target_size, (255, 255, 255))
                offset = ((self.target_size[0] - img.width) // 2,
                         (self.target_size[1] - img.height) // 2)
                thumbnail.paste(img, offset)

                # Save to cache
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                thumbnail.save(cache_path, 'JPEG', quality=85)

                # Convert to QPixmap
                pixmap = QPixmap(str(cache_path))
                return pixmap

        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {image_path}: {e}")
            return None

    def _get_cache_path(self, image_path: Path) -> Path:
        """
        Get cache path for an image thumbnail.

        Args:
            image_path: Path to the original image

        Returns:
            Path to cached thumbnail
        """
        # Create a hash of the file path and modification time for cache key
        file_stat = image_path.stat()
        cache_key = hashlib.md5(
            f"{image_path}_{file_stat.st_mtime}_{file_stat.st_size}".encode()
        ).hexdigest()

        return self.cache_dir / f"{cache_key}.jpg"


class ThumbnailGenerator(QObject):
    """
    Manages thumbnail generation and caching for wallpaper images.

    Provides async thumbnail generation with caching for efficient display
    in the downloaded images gallery.
    """

    # Signals
    thumbnail_ready = Signal(str, QPixmap)  # file_path, thumbnail_pixmap
    thumbnail_error = Signal(str, str)      # file_path, error_message
    generation_progress = Signal(int, int)  # current, total
    generation_finished = Signal()

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize thumbnail generator.

        Args:
            cache_dir: Directory for caching thumbnails. Defaults to base_path/.metadata/thumbnails/
        """
        super().__init__()

        if cache_dir is None:
            from .config import get_config
            config = get_config()
            cache_dir = Path(config.storage.base_path) / '.metadata' / 'thumbnails'

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Default thumbnail size
        self.thumbnail_size = (220, 140)

        # Worker thread
        self.worker = None

        # Cache metadata
        self.cache_metadata_file = self.cache_dir / 'cache_metadata.json'
        self.cache_metadata = self.load_cache_metadata()

    def load_cache_metadata(self) -> Dict:
        """Load cache metadata."""
        if self.cache_metadata_file.exists():
            try:
                with open(self.cache_metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache metadata: {e}")

        return {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'thumbnails': {}
        }

    def save_cache_metadata(self):
        """Save cache metadata."""
        try:
            with open(self.cache_metadata_file, 'w') as f:
                json.dump(self.cache_metadata, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def get_thumbnail(self, image_path: Path, async_generation: bool = True) -> Optional[QPixmap]:
        """
        Get thumbnail for an image, generating if necessary.

        Args:
            image_path: Path to the image file
            async_generation: Whether to generate thumbnail asynchronously

        Returns:
            QPixmap thumbnail if available immediately, None if async generation is needed
        """
        if not image_path.exists():
            logger.warning(f"Image file does not exist: {image_path}")
            return None

        # Check cache first
        cache_path = self._get_cache_path(image_path)
        if cache_path.exists():
            try:
                pixmap = QPixmap(str(cache_path))
                if not pixmap.isNull():
                    logger.debug(f"Loaded cached thumbnail for: {image_path}")
                    return pixmap
                else:
                    # Cached file is corrupted, remove it
                    logger.warning(f"Corrupted cached thumbnail, removing: {cache_path}")
                    cache_path.unlink()
            except Exception as e:
                logger.error(f"Error loading cached thumbnail {cache_path}: {e}")
                try:
                    cache_path.unlink()
                except:
                    pass

        if async_generation:
            # Start async generation if not already running
            if not self.worker or not self.worker.isRunning():
                self.generate_thumbnails_async([image_path])
            return None
        else:
            # Generate synchronously
            return self._generate_thumbnail_sync(image_path)

    def generate_thumbnails_async(self, image_paths: List[Path]):
        """
        Generate thumbnails asynchronously for multiple images.

        Args:
            image_paths: List of image file paths
        """
        if self.worker and self.worker.isRunning():
            logger.warning("Thumbnail generation already in progress")
            return

        # Filter to only process images that need thumbnails
        files_to_process = []
        for image_path in image_paths:
            if image_path.exists():
                cache_path = self._get_cache_path(image_path)
                if not cache_path.exists():
                    files_to_process.append(image_path)

        if not files_to_process:
            self.generation_finished.emit()
            return

        logger.info(f"Starting async thumbnail generation for {len(files_to_process)} files")

        # Create and start worker
        self.worker = ThumbnailWorker(files_to_process, self.thumbnail_size, self.cache_dir)
        self.worker.thumbnail_ready.connect(self.thumbnail_ready)
        self.worker.thumbnail_error.connect(self.thumbnail_error)
        self.worker.progress.connect(self.generation_progress)
        self.worker.finished.connect(self.generation_finished)
        self.worker.start()

    def _generate_thumbnail_sync(self, image_path: Path) -> Optional[QPixmap]:
        """Generate thumbnail synchronously with robust error handling."""
        try:
            cache_path = self._get_cache_path(image_path)

            # Try PIL for thumbnail generation
            with Image.open(image_path) as img:
                # Get original dimensions for logging
                orig_width, orig_height = img.size
                logger.debug(f"Generating thumbnail for {image_path} ({orig_width}x{orig_height})")

                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Create thumbnail maintaining aspect ratio
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)

                # Create a new image with the exact target size and center the thumbnail
                thumbnail = Image.new('RGB', self.thumbnail_size, (240, 240, 240))  # Light gray background
                offset = ((self.thumbnail_size[0] - img.width) // 2,
                         (self.thumbnail_size[1] - img.height) // 2)
                thumbnail.paste(img, offset)

                # Ensure cache directory exists
                cache_path.parent.mkdir(parents=True, exist_ok=True)

                # Save to cache with error handling
                try:
                    thumbnail.save(cache_path, 'JPEG', quality=85, optimize=True)
                    logger.debug(f"Saved thumbnail cache: {cache_path}")
                except Exception as save_error:
                    logger.warning(f"Failed to save thumbnail cache: {save_error}")

                # Convert PIL image to QPixmap directly
                import io
                img_byte_arr = io.BytesIO()
                thumbnail.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)

                pixmap = QPixmap()
                success = pixmap.loadFromData(img_byte_arr.getvalue())

                if success and not pixmap.isNull():
                    logger.debug(f"Successfully generated thumbnail for {image_path}")
                    return pixmap
                else:
                    logger.error(f"Failed to convert PIL image to QPixmap for {image_path}")
                    return None

        except ImportError:
            logger.error("PIL not available for thumbnail generation")
            return None
        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {image_path}: {e}")

            # Fallback: try direct QPixmap loading and scaling
            try:
                logger.debug(f"Trying QPixmap fallback for {image_path}")
                pixmap = QPixmap(str(image_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        self.thumbnail_size[0],
                        self.thumbnail_size[1],
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    if not scaled.isNull():
                        logger.debug(f"QPixmap fallback succeeded for {image_path}")
                        return scaled

            except Exception as fallback_error:
                logger.error(f"QPixmap fallback failed for {image_path}: {fallback_error}")

            return None

    def _get_cache_path(self, image_path: Path) -> Path:
        """Get cache path for an image thumbnail."""
        try:
            file_stat = image_path.stat()
            cache_key = hashlib.md5(
                f"{image_path}_{file_stat.st_mtime}_{file_stat.st_size}".encode()
            ).hexdigest()
            return self.cache_dir / f"{cache_key}.jpg"
        except OSError:
            # Fallback if stat fails
            cache_key = hashlib.md5(str(image_path).encode()).hexdigest()
            return self.cache_dir / f"{cache_key}.jpg"

    def clear_cache(self):
        """Clear all cached thumbnails."""
        try:
            for cache_file in self.cache_dir.glob('*.jpg'):
                cache_file.unlink()

            # Clear metadata
            self.cache_metadata = {
                'version': '1.0',
                'created': datetime.now().isoformat(),
                'thumbnails': {}
            }
            self.save_cache_metadata()

            logger.info("Thumbnail cache cleared")

        except Exception as e:
            logger.error(f"Failed to clear thumbnail cache: {e}")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.glob('*.jpg'))
        total_size = sum(f.stat().st_size for f in cache_files if f.is_file())

        return {
            'total_thumbnails': len(cache_files),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_dir': str(self.cache_dir)
        }

    def cleanup_old_cache(self, max_age_days: int = 30):
        """
        Clean up old cached thumbnails.

        Args:
            max_age_days: Maximum age in days for cached thumbnails
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 3600
            removed_count = 0

            for cache_file in self.cache_dir.glob('*.jpg'):
                try:
                    file_age = current_time - cache_file.stat().st_mtime
                    if file_age > max_age_seconds:
                        cache_file.unlink()
                        removed_count += 1
                except OSError:
                    continue

            logger.info(f"Cleaned up {removed_count} old cached thumbnails")
            return removed_count

        except Exception as e:
            logger.error(f"Failed to cleanup old cache: {e}")
            return 0

    def stop_generation(self):
        """Stop any running thumbnail generation."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)  # Wait up to 3 seconds


# Example usage
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
    from PySide6.QtCore import QTimer

    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)

    # Test thumbnail generation
    generator = ThumbnailGenerator()

    # Create test window
    window = QWidget()
    window.setWindowTitle("Thumbnail Generator Test")
    layout = QVBoxLayout(window)

    label = QLabel("Generating thumbnails...")
    layout.addWidget(label)

    def on_thumbnail_ready(file_path, pixmap):
        print(f"Thumbnail ready for: {file_path}")
        label.setPixmap(pixmap)

    def on_generation_finished():
        print("Thumbnail generation finished")

    generator.thumbnail_ready.connect(on_thumbnail_ready)
    generator.generation_finished.connect(on_generation_finished)

    # Test with some sample images (replace with actual paths)
    # test_images = [Path("/path/to/test/image1.jpg"), Path("/path/to/test/image2.jpg")]
    # generator.generate_thumbnails_async(test_images)

    window.show()
    sys.exit(app.exec())