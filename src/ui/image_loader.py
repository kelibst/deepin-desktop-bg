"""
Asynchronous Image Loader for Qt applications.

Provides efficient thumbnail loading with caching, progressive loading,
and background processing to maintain smooth UI responsiveness.
"""

import logging
import hashlib
import time
from typing import Dict, Optional, Callable, Any
from pathlib import Path
from urllib.parse import urlparse

import requests
from PySide6.QtCore import QThread, Signal, QObject, QTimer, QMutex, QMutexLocker
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel


logger = logging.getLogger(__name__)


class ImageCache:
    """Thread-safe in-memory image cache with size limits."""

    def __init__(self, max_size_mb: int = 50):
        """
        Initialize image cache.

        Args:
            max_size_mb: Maximum cache size in megabytes
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.cache: Dict[str, QPixmap] = {}
        self.cache_sizes: Dict[str, int] = {}
        self.access_times: Dict[str, float] = {}
        self.total_size = 0
        self.mutex = QMutex()

    def _estimate_pixmap_size(self, pixmap: QPixmap) -> int:
        """Estimate memory size of a QPixmap in bytes."""
        if pixmap.isNull():
            return 0
        # Rough estimate: width * height * 4 bytes per pixel (RGBA)
        return pixmap.width() * pixmap.height() * 4

    def _cleanup_if_needed(self):
        """Clean up old entries if cache is too large."""
        while self.total_size > self.max_size_bytes and self.cache:
            # Remove oldest accessed item
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            self._remove_item(oldest_key)

    def _remove_item(self, key: str):
        """Remove an item from cache."""
        if key in self.cache:
            self.total_size -= self.cache_sizes.get(key, 0)
            del self.cache[key]
            del self.cache_sizes[key]
            del self.access_times[key]

    def get(self, key: str) -> Optional[QPixmap]:
        """
        Get cached pixmap.

        Args:
            key: Cache key

        Returns:
            Cached QPixmap or None if not found
        """
        with QMutexLocker(self.mutex):
            if key in self.cache:
                self.access_times[key] = time.time()
                return self.cache[key]
            return None

    def put(self, key: str, pixmap: QPixmap):
        """
        Store pixmap in cache.

        Args:
            key: Cache key
            pixmap: QPixmap to store
        """
        with QMutexLocker(self.mutex):
            if key in self.cache:
                self._remove_item(key)

            size = self._estimate_pixmap_size(pixmap)
            self.cache[key] = pixmap
            self.cache_sizes[key] = size
            self.access_times[key] = time.time()
            self.total_size += size

            self._cleanup_if_needed()

    def clear(self):
        """Clear all cached items."""
        with QMutexLocker(self.mutex):
            self.cache.clear()
            self.cache_sizes.clear()
            self.access_times.clear()
            self.total_size = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with QMutexLocker(self.mutex):
            return {
                'total_items': len(self.cache),
                'total_size_mb': round(self.total_size / (1024 * 1024), 2),
                'max_size_mb': round(self.max_size_bytes / (1024 * 1024), 2)
            }


class ImageLoadRequest:
    """Represents a single image loading request."""

    def __init__(self, url: str, cache_key: str, target_size: tuple = None,
                 callback: Callable = None, user_data: Any = None):
        """
        Initialize image load request.

        Args:
            url: URL or file path to load
            cache_key: Unique cache key for this image
            target_size: Optional (width, height) to resize image
            callback: Function to call when loading completes
            user_data: Optional data to pass to callback
        """
        self.url = url
        self.cache_key = cache_key
        self.target_size = target_size
        self.callback = callback
        self.user_data = user_data
        self.timestamp = time.time()


class ImageLoadWorker(QThread):
    """Background worker thread for loading images."""

    # Signals
    image_loaded = Signal(str, QPixmap, object)  # cache_key, pixmap, user_data
    image_failed = Signal(str, str, object)      # cache_key, error_msg, user_data

    def __init__(self, cache: ImageCache):
        super().__init__()
        self.cache = cache
        self.requests_queue = []
        self.queue_mutex = QMutex()
        self.running = True

    def add_request(self, request: ImageLoadRequest):
        """Add a loading request to the queue."""
        with QMutexLocker(self.queue_mutex):
            # Check if already cached
            cached_pixmap = self.cache.get(request.cache_key)
            if cached_pixmap:
                # Emit immediately with cached result
                self.image_loaded.emit(request.cache_key, cached_pixmap, request.user_data)
                return

            # Add to queue if not already there
            existing = [req for req in self.requests_queue if req.cache_key == request.cache_key]
            if not existing:
                self.requests_queue.append(request)

    def stop(self):
        """Stop the worker thread."""
        self.running = False
        self.wait()

    def run(self):
        """Main worker thread loop."""
        while self.running:
            request = None

            # Get next request
            with QMutexLocker(self.queue_mutex):
                if self.requests_queue:
                    # Sort by timestamp (oldest first)
                    self.requests_queue.sort(key=lambda r: r.timestamp)
                    request = self.requests_queue.pop(0)

            if request:
                self._process_request(request)
            else:
                # No requests, sleep briefly
                self.msleep(50)

    def _process_request(self, request: ImageLoadRequest):
        """Process a single image loading request."""
        try:
            # Check cache again (in case it was loaded by another request)
            cached_pixmap = self.cache.get(request.cache_key)
            if cached_pixmap:
                self.image_loaded.emit(request.cache_key, cached_pixmap, request.user_data)
                return

            # Load the image
            pixmap = self._load_image(request.url, request.target_size)

            if not pixmap.isNull():
                # Cache the loaded image
                self.cache.put(request.cache_key, pixmap)
                self.image_loaded.emit(request.cache_key, pixmap, request.user_data)
            else:
                self.image_failed.emit(request.cache_key, "Failed to load image", request.user_data)

        except Exception as e:
            logger.error(f"Error loading image {request.url}: {e}")
            self.image_failed.emit(request.cache_key, str(e), request.user_data)

    def _load_image(self, url: str, target_size: tuple = None) -> QPixmap:
        """
        Load image from URL or file path.

        Args:
            url: URL or file path
            target_size: Optional (width, height) for resizing

        Returns:
            Loaded QPixmap
        """
        pixmap = QPixmap()

        try:
            if url.startswith(('http://', 'https://')):
                # Download from URL
                response = requests.get(url, timeout=10, stream=True)
                response.raise_for_status()

                # Load from bytes
                pixmap.loadFromData(response.content)

            else:
                # Load from local file
                file_path = Path(url)
                if file_path.exists():
                    pixmap.load(str(file_path))

            # Resize if requested
            if target_size and not pixmap.isNull():
                from PySide6.QtCore import Qt
                width, height = target_size
                pixmap = pixmap.scaled(
                    width, height,
                    Qt.KeepAspectRatio,      # aspectRatioMode
                    Qt.SmoothTransformation  # transformMode
                )

        except Exception as e:
            logger.error(f"Failed to load image from {url}: {e}")

        return pixmap


class AsyncImageLoader(QObject):
    """
    High-level asynchronous image loader with caching.

    Provides simple interface for loading images asynchronously
    while maintaining cache and handling failures gracefully.
    """

    # Signals
    image_ready = Signal(str, QPixmap, object)    # cache_key, pixmap, user_data
    image_error = Signal(str, str, object)        # cache_key, error_msg, user_data

    def __init__(self, cache_size_mb: int = 50, max_workers: int = 3):
        """
        Initialize async image loader.

        Args:
            cache_size_mb: Maximum cache size in megabytes
            max_workers: Maximum number of worker threads
        """
        super().__init__()
        self.cache = ImageCache(cache_size_mb)
        self.workers = []
        self.current_worker = 0

        # Create worker threads
        for i in range(max_workers):
            worker = ImageLoadWorker(self.cache)
            worker.image_loaded.connect(self.image_ready)
            worker.image_failed.connect(self.image_error)
            worker.start()
            self.workers.append(worker)

    def load_image(self, url: str, cache_key: str = None, target_size: tuple = None,
                   callback: Callable = None, user_data: Any = None) -> str:
        """
        Load image asynchronously.

        Args:
            url: URL or file path to load
            cache_key: Optional cache key (auto-generated if None)
            target_size: Optional (width, height) for resizing
            callback: Optional callback function
            user_data: Optional data to pass to callback

        Returns:
            Cache key for this request
        """
        if cache_key is None:
            # Generate cache key from URL and size
            size_str = f"_{target_size[0]}x{target_size[1]}" if target_size else ""
            cache_key = hashlib.md5(f"{url}{size_str}".encode()).hexdigest()

        # Create request
        request = ImageLoadRequest(url, cache_key, target_size, callback, user_data)

        # Distribute requests across workers (round-robin)
        worker = self.workers[self.current_worker]
        self.current_worker = (self.current_worker + 1) % len(self.workers)

        worker.add_request(request)
        return cache_key

    def get_cached_image(self, cache_key: str) -> Optional[QPixmap]:
        """Get image from cache if available."""
        return self.cache.get(cache_key)

    def clear_cache(self):
        """Clear image cache."""
        self.cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()

    def shutdown(self):
        """Shutdown all worker threads."""
        for worker in self.workers:
            worker.stop()


class AsyncImageLabel(QLabel):
    """
    QLabel that loads images asynchronously with loading state.

    Displays placeholder while loading and handles load failures gracefully.
    """

    def __init__(self, loader: AsyncImageLoader, placeholder_text: str = "Loading..."):
        """
        Initialize async image label.

        Args:
            loader: AsyncImageLoader instance
            placeholder_text: Text to show while loading
        """
        super().__init__()
        self.loader = loader
        self.placeholder_text = placeholder_text
        self.current_cache_key = None

        # Connect loader signals
        self.loader.image_ready.connect(self._on_image_loaded)
        self.loader.image_error.connect(self._on_image_error)

        # Set initial placeholder
        self.setText(placeholder_text)
        self.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")

    def load_image(self, url: str, target_size: tuple = None):
        """
        Load and display image asynchronously.

        Args:
            url: URL or file path to load
            target_size: Optional (width, height) for resizing
        """
        # Reset to loading state
        self.setText(self.placeholder_text)
        self.setPixmap(QPixmap())

        # Load image
        self.current_cache_key = self.loader.load_image(
            url=url,
            target_size=target_size,
            user_data={'label': self}
        )

    def _on_image_loaded(self, cache_key: str, pixmap: QPixmap, user_data: Any):
        """Handle successful image loading."""
        if (user_data and user_data.get('label') == self and
            cache_key == self.current_cache_key):
            self.setPixmap(pixmap)
            self.setText("")

    def _on_image_error(self, cache_key: str, error_msg: str, user_data: Any):
        """Handle image loading error."""
        if (user_data and user_data.get('label') == self and
            cache_key == self.current_cache_key):
            self.setText("Failed to load")
            self.setStyleSheet("border: 1px solid #f00; background-color: #ffe0e0;")


# Example usage
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton

    app = QApplication(sys.argv)

    # Create image loader
    loader = AsyncImageLoader(cache_size_mb=10, max_workers=2)

    # Create test widget
    widget = QWidget()
    layout = QVBoxLayout(widget)

    # Create async image label
    image_label = AsyncImageLabel(loader, "Click button to load image")
    image_label.setMinimumSize(200, 150)
    layout.addWidget(image_label)

    # Test button
    def load_test_image():
        # Test with a Wallhaven thumbnail
        test_url = "https://th.wallhaven.cc/lg/6o/wallhaven-6o3q9d.jpg"
        image_label.load_image(test_url, target_size=(200, 150))

    button = QPushButton("Load Test Image")
    button.clicked.connect(load_test_image)
    layout.addWidget(button)

    widget.show()

    # Shutdown loader when app exits
    def cleanup():
        loader.shutdown()

    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec())