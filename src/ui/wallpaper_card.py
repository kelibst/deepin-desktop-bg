"""
Wallpaper Card Widget for displaying individual wallpaper thumbnails.

Provides a card-based UI component showing wallpaper thumbnail,
metadata, and action buttons for download and background setting.
"""

import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QSizePolicy, QToolTip, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QFont, QCursor, QPainter, QPen

from ui.image_loader import AsyncImageLoader, AsyncImageLabel


logger = logging.getLogger(__name__)


class ClickableLabel(QLabel):
    """QLabel that emits clicked signal."""

    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class WallpaperCard(QFrame):
    """
    Card widget displaying a single wallpaper with thumbnail and controls.

    Shows wallpaper thumbnail, metadata (resolution, views, etc.),
    and provides action buttons for download and setting as background.
    """

    # Signals
    download_requested = Signal(dict)      # wallpaper_data
    set_background_requested = Signal(dict) # wallpaper_data
    selection_changed = Signal(bool)       # is_selected
    card_clicked = Signal(dict)            # wallpaper_data

    def __init__(self, wallpaper_data: Dict[str, Any], image_loader: AsyncImageLoader):
        """
        Initialize wallpaper card.

        Args:
            wallpaper_data: Dictionary containing wallpaper metadata
            image_loader: AsyncImageLoader instance for thumbnail loading
        """
        super().__init__()
        self.wallpaper_data = wallpaper_data
        self.image_loader = image_loader
        self.is_selected = False
        self.is_downloading = False

        self.setup_ui()
        self.setup_style()
        self.load_thumbnail()

    def setup_ui(self):
        """Set up the user interface."""
        self.setFixedSize(240, 320)  # Card size
        self.setFrameStyle(QFrame.Box)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Selection checkbox (top-right)
        checkbox_layout = QHBoxLayout()
        checkbox_layout.addStretch()

        self.selection_checkbox = QCheckBox()
        self.selection_checkbox.stateChanged.connect(self._on_selection_changed)
        checkbox_layout.addWidget(self.selection_checkbox)

        layout.addLayout(checkbox_layout)

        # Thumbnail area
        self.thumbnail_label = ClickableLabel()
        self.thumbnail_label.setFixedSize(220, 140)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ddd;
                background-color: #f5f5f5;
                border-radius: 4px;
            }
        """)
        self.thumbnail_label.clicked.connect(self._on_thumbnail_clicked)
        layout.addWidget(self.thumbnail_label, alignment=Qt.AlignCenter)

        # Wallpaper info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # ID and resolution
        id_resolution_layout = QHBoxLayout()

        self.id_label = QLabel(f"ID: {self.wallpaper_data['id']}")
        self.id_label.setFont(QFont("", 9, QFont.Bold))
        id_resolution_layout.addWidget(self.id_label)

        id_resolution_layout.addStretch()

        self.resolution_label = QLabel(self.wallpaper_data.get('resolution', 'Unknown'))
        self.resolution_label.setFont(QFont("", 8))
        self.resolution_label.setStyleSheet("color: #666;")
        id_resolution_layout.addWidget(self.resolution_label)

        info_layout.addLayout(id_resolution_layout)

        # Views and favorites
        stats_layout = QHBoxLayout()

        views = self.wallpaper_data.get('views', 0)
        favorites = self.wallpaper_data.get('favorites', 0)

        self.stats_label = QLabel(f"👁 {views:,} | ❤ {favorites:,}")
        self.stats_label.setFont(QFont("", 8))
        self.stats_label.setStyleSheet("color: #666;")
        stats_layout.addWidget(self.stats_label)

        stats_layout.addStretch()

        # Category
        category = self.wallpaper_data.get('category', 'general')
        self.category_label = QLabel(category.title())
        self.category_label.setFont(QFont("", 8))
        self.category_label.setStyleSheet("""
            QLabel {
                background-color: #e1f5fe;
                color: #0277bd;
                padding: 2px 6px;
                border-radius: 3px;
            }
        """)
        stats_layout.addWidget(self.category_label)

        info_layout.addLayout(stats_layout)

        layout.addLayout(info_layout)

        # Action buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(4)

        # Download button
        self.download_btn = QPushButton("Download")
        self.download_btn.setFont(QFont("", 9))
        self.download_btn.clicked.connect(self._on_download_clicked)
        buttons_layout.addWidget(self.download_btn)

        # Set as background button
        self.set_bg_btn = QPushButton("Set as Background")
        self.set_bg_btn.setFont(QFont("", 9))
        self.set_bg_btn.clicked.connect(self._on_set_background_clicked)
        buttons_layout.addWidget(self.set_bg_btn)

        layout.addLayout(buttons_layout)

    def setup_style(self):
        """Set up card styling."""
        self.setStyleSheet("""
            WallpaperCard {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
                margin: 2px;
            }
            WallpaperCard:hover {
                border-color: #4CAF50;
                background-color: #f8f8f8;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

    def load_thumbnail(self):
        """Load wallpaper thumbnail asynchronously."""
        thumbnail_url = self.wallpaper_data.get('thumbs', {}).get('large')

        if not thumbnail_url:
            self.thumbnail_label.setText("No Preview")
            return

        # Show loading state
        self.thumbnail_label.setText("Loading...")

        # Load thumbnail
        cache_key = self.image_loader.load_image(
            url=thumbnail_url,
            target_size=(220, 140),
            user_data={'card': self}
        )

        # Connect to image loaded signal
        self.image_loader.image_ready.connect(self._on_thumbnail_loaded)
        self.image_loader.image_error.connect(self._on_thumbnail_error)

    def _on_thumbnail_loaded(self, cache_key: str, pixmap: QPixmap, user_data: Any):
        """Handle successful thumbnail loading."""
        if user_data and user_data.get('card') == self:
            self.thumbnail_label.setPixmap(pixmap)
            self.thumbnail_label.setText("")

    def _on_thumbnail_error(self, cache_key: str, error_msg: str, user_data: Any):
        """Handle thumbnail loading error."""
        if user_data and user_data.get('card') == self:
            self.thumbnail_label.setText("Failed to load")
            self.thumbnail_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #f44336;
                    background-color: #ffebee;
                    color: #c62828;
                    border-radius: 4px;
                }
            """)

    def _on_selection_changed(self, state: int):
        """Handle selection checkbox change."""
        self.is_selected = state == Qt.Checked
        self.update_selection_style()
        self.selection_changed.emit(self.is_selected)

    def _on_thumbnail_clicked(self):
        """Handle thumbnail click."""
        self.card_clicked.emit(self.wallpaper_data)

    def _on_download_clicked(self):
        """Handle download button click."""
        if not self.is_downloading:
            self.download_requested.emit(self.wallpaper_data)

    def _on_set_background_clicked(self):
        """Handle set background button click."""
        if not self.is_downloading:
            self.set_background_requested.emit(self.wallpaper_data)

    def set_selected(self, selected: bool):
        """
        Set selection state programmatically.

        Args:
            selected: Whether the card should be selected
        """
        self.selection_checkbox.setChecked(selected)

    def is_card_selected(self) -> bool:
        """Get current selection state."""
        return self.is_selected

    def update_selection_style(self):
        """Update visual style based on selection state."""
        if self.is_selected:
            self.setStyleSheet(self.styleSheet() + """
                WallpaperCard {
                    border: 2px solid #4CAF50;
                    background-color: #f0f8f0;
                }
            """)
        else:
            # Reset to default style
            self.setup_style()

    def set_downloading_state(self, downloading: bool):
        """
        Set downloading state and update UI accordingly.

        Args:
            downloading: Whether download is in progress
        """
        self.is_downloading = downloading

        if downloading:
            self.download_btn.setText("Downloading...")
            self.download_btn.setEnabled(False)
            self.set_bg_btn.setEnabled(False)
        else:
            self.download_btn.setText("Download")
            self.download_btn.setEnabled(True)
            self.set_bg_btn.setEnabled(True)

    def set_already_downloaded(self, downloaded: bool):
        """
        Mark card as already downloaded.

        Args:
            downloaded: Whether this wallpaper is already downloaded
        """
        if downloaded:
            self.download_btn.setText("Downloaded ✓")
            self.download_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        else:
            self.download_btn.setText("Download")
            self.download_btn.setStyleSheet("")  # Reset to default

    def get_wallpaper_data(self) -> Dict[str, Any]:
        """Get wallpaper metadata."""
        return self.wallpaper_data

    def show_tooltip_info(self):
        """Show detailed info in tooltip."""
        tags = self.wallpaper_data.get('tags', [])
        tag_str = ', '.join(tags[:5]) if tags else 'No tags'

        tooltip_text = f"""
        <b>Wallpaper {self.wallpaper_data['id']}</b><br>
        <b>Resolution:</b> {self.wallpaper_data.get('resolution', 'Unknown')}<br>
        <b>Views:</b> {self.wallpaper_data.get('views', 0):,}<br>
        <b>Favorites:</b> {self.wallpaper_data.get('favorites', 0):,}<br>
        <b>Category:</b> {self.wallpaper_data.get('category', 'general').title()}<br>
        <b>File Size:</b> {self.wallpaper_data.get('file_size', 0) / 1024:.1f} KB<br>
        <b>Tags:</b> {tag_str}<br>
        <b>Created:</b> {self.wallpaper_data.get('created_at', 'Unknown')}
        """

        self.setToolTip(tooltip_text)


class WallpaperCardContainer(QWidget):
    """
    Container widget for multiple wallpaper cards with selection management.

    Manages multiple WallpaperCard widgets and provides batch operations
    for selected cards.
    """

    # Signals
    selection_changed = Signal(int)        # number_selected
    download_requested = Signal(list)      # list of wallpaper_data
    set_background_requested = Signal(dict) # single wallpaper_data

    def __init__(self, image_loader: AsyncImageLoader):
        """
        Initialize card container.

        Args:
            image_loader: AsyncImageLoader instance
        """
        super().__init__()
        self.image_loader = image_loader
        self.cards = []

        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def add_wallpaper_card(self, wallpaper_data: Dict[str, Any]) -> 'WallpaperCard':
        """
        Add a new wallpaper card.

        Args:
            wallpaper_data: Wallpaper metadata

        Returns:
            Created WallpaperCard instance
        """
        card = WallpaperCard(wallpaper_data, self.image_loader)

        # Connect signals
        card.selection_changed.connect(self._on_card_selection_changed)
        card.download_requested.connect(self._on_card_download_requested)
        card.set_background_requested.connect(self._on_card_set_background_requested)

        self.cards.append(card)
        return card

    def clear_cards(self):
        """Remove all wallpaper cards."""
        for card in self.cards:
            card.deleteLater()
        self.cards.clear()

        # Clear layout
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def get_selected_cards(self) -> list:
        """Get list of selected wallpaper cards."""
        return [card for card in self.cards if card.is_card_selected()]

    def get_selected_wallpapers(self) -> list:
        """Get wallpaper data for selected cards."""
        return [card.get_wallpaper_data() for card in self.get_selected_cards()]

    def select_all(self, selected: bool = True):
        """Select or deselect all cards."""
        for card in self.cards:
            card.set_selected(selected)

    def _on_card_selection_changed(self, is_selected: bool):
        """Handle card selection change."""
        selected_count = len(self.get_selected_cards())
        self.selection_changed.emit(selected_count)

    def _on_card_download_requested(self, wallpaper_data: Dict[str, Any]):
        """Handle single card download request."""
        self.download_requested.emit([wallpaper_data])

    def _on_card_set_background_requested(self, wallpaper_data: Dict[str, Any]):
        """Handle set background request."""
        self.set_background_requested.emit(wallpaper_data)


class LocalWallpaperCard(WallpaperCard):
    """
    Card widget for displaying local/downloaded wallpapers.

    Similar to WallpaperCard but with different actions:
    - Delete button instead of Download
    - Set as Background button
    - Shows local file information
    """

    # Additional signals for local operations
    delete_requested = Signal(dict)        # wallpaper_data

    def __init__(self, wallpaper_data: Dict[str, Any], thumbnail_generator):
        """
        Initialize local wallpaper card.

        Args:
            wallpaper_data: Dictionary containing local wallpaper metadata
            thumbnail_generator: ThumbnailGenerator instance for local thumbnails
        """
        # Create a minimal image loader for local files
        self.thumbnail_generator = thumbnail_generator

        # Initialize parent without actual image loader for now
        super().__init__(wallpaper_data, None)

    def setup_ui(self):
        """Set up the user interface for local wallpaper card."""
        self.setFixedSize(240, 320)  # Card size
        self.setFrameStyle(QFrame.Box)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Selection checkbox (top-right)
        checkbox_layout = QHBoxLayout()
        checkbox_layout.addStretch()

        self.selection_checkbox = QCheckBox()
        self.selection_checkbox.stateChanged.connect(self._on_selection_changed)
        checkbox_layout.addWidget(self.selection_checkbox)

        layout.addLayout(checkbox_layout)

        # Thumbnail area
        self.thumbnail_label = ClickableLabel()
        self.thumbnail_label.setFixedSize(220, 140)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ddd;
                background-color: #f5f5f5;
                border-radius: 4px;
            }
        """)
        self.thumbnail_label.clicked.connect(self._on_thumbnail_clicked)
        layout.addWidget(self.thumbnail_label, alignment=Qt.AlignCenter)

        # Wallpaper info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Filename and resolution
        filename_resolution_layout = QHBoxLayout()

        # Show filename instead of ID for local files
        filename = Path(self.wallpaper_data.get('path', '')).name
        if len(filename) > 20:
            filename = filename[:17] + "..."

        self.filename_label = QLabel(filename)
        self.filename_label.setFont(QFont("", 9, QFont.Bold))
        filename_resolution_layout.addWidget(self.filename_label)

        filename_resolution_layout.addStretch()

        self.resolution_label = QLabel(self.wallpaper_data.get('resolution', 'Unknown'))
        self.resolution_label.setFont(QFont("", 8))
        self.resolution_label.setStyleSheet("color: #666;")
        filename_resolution_layout.addWidget(self.resolution_label)

        info_layout.addLayout(filename_resolution_layout)

        # File size and source
        details_layout = QHBoxLayout()

        file_size = self.wallpaper_data.get('file_size', 0)
        if file_size > 0:
            size_mb = file_size / (1024 * 1024)
            if size_mb >= 1:
                size_str = f"{size_mb:.1f} MB"
            else:
                size_str = f"{file_size / 1024:.0f} KB"
        else:
            size_str = "Unknown size"

        self.size_label = QLabel(size_str)
        self.size_label.setFont(QFont("", 8))
        self.size_label.setStyleSheet("color: #666;")
        details_layout.addWidget(self.size_label)

        details_layout.addStretch()

        # Source type
        source_type = self.wallpaper_data.get('source_type', 'local')
        source_display = {
            'wallhaven': 'Wallhaven',
            'ai_generated': 'AI Generated',
            'community': 'Community',
            'public_domain': 'Public Domain'
        }.get(source_type, source_type.title())

        self.source_label = QLabel(source_display)
        self.source_label.setFont(QFont("", 8))
        self.source_label.setStyleSheet("""
            QLabel {
                background-color: #fff3e0;
                color: #e65100;
                padding: 2px 6px;
                border-radius: 3px;
            }
        """)
        details_layout.addWidget(self.source_label)

        info_layout.addLayout(details_layout)

        # Added date
        added_date = self.wallpaper_data.get('added_date', '')
        if added_date:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(added_date.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d')
            except:
                date_str = added_date[:10] if len(added_date) >= 10 else added_date
        else:
            date_str = "Unknown date"

        self.date_label = QLabel(f"Added: {date_str}")
        self.date_label.setFont(QFont("", 8))
        self.date_label.setStyleSheet("color: #666; font-style: italic;")
        info_layout.addWidget(self.date_label)

        layout.addLayout(info_layout)

        # Action buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(4)

        # Set as background button
        self.set_bg_btn = QPushButton("Set as Background")
        self.set_bg_btn.setFont(QFont("", 9))
        self.set_bg_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.set_bg_btn.clicked.connect(self._on_set_background_clicked)
        buttons_layout.addWidget(self.set_bg_btn)

        # Delete button
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setFont(QFont("", 9))
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        buttons_layout.addWidget(self.delete_btn)

        layout.addLayout(buttons_layout)

    def load_thumbnail(self):
        """Load thumbnail for local wallpaper file."""
        wallpaper_path = Path(self.wallpaper_data.get('path', ''))

        if not wallpaper_path.exists():
            self.thumbnail_label.setText("File not found")
            self.thumbnail_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #f44336;
                    background-color: #ffebee;
                    color: #c62828;
                    border-radius: 4px;
                }
            """)
            return

        # Show loading state
        self.thumbnail_label.setText("Loading...")

        # Try to load directly first (fast path for small images)
        try:
            self._try_direct_load(wallpaper_path)
            return
        except Exception as e:
            logger.debug(f"Direct load failed for {wallpaper_path}, trying thumbnail generator: {e}")

        # Get thumbnail from generator with proper signal isolation
        if self.thumbnail_generator:
            # Disconnect any previous connections to avoid conflicts
            try:
                self.thumbnail_generator.thumbnail_ready.disconnect(self._on_local_thumbnail_loaded)
                self.thumbnail_generator.thumbnail_error.disconnect(self._on_local_thumbnail_error)
            except TypeError:
                pass  # No connections to disconnect

            # Try to get cached thumbnail first
            thumbnail = self.thumbnail_generator.get_thumbnail(wallpaper_path, async_generation=False)
            if thumbnail:
                self.thumbnail_label.setPixmap(thumbnail)
                self.thumbnail_label.setText("")
                return

            # Connect signals for async generation with unique identifier
            self.thumbnail_generator.thumbnail_ready.connect(self._on_local_thumbnail_loaded)
            self.thumbnail_generator.thumbnail_error.connect(self._on_local_thumbnail_error)

            # Start async generation
            self.thumbnail_generator.generate_thumbnails_async([wallpaper_path])

            # Set timeout for loading state
            self._start_loading_timeout()

        else:
            # Final fallback: direct synchronous load with scaling
            self._try_sync_fallback(wallpaper_path)

    def _try_direct_load(self, wallpaper_path: Path):
        """Try to load image directly with size optimization."""
        # Check file size - if small enough, load directly
        file_size = wallpaper_path.stat().st_size
        if file_size > 5 * 1024 * 1024:  # Skip direct load for files > 5MB
            raise Exception("File too large for direct load")

        pixmap = QPixmap(str(wallpaper_path))
        if not pixmap.isNull() and pixmap.width() > 0 and pixmap.height() > 0:
            # Scale to fit thumbnail size efficiently
            scaled_pixmap = pixmap.scaled(220, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled_pixmap)
            self.thumbnail_label.setText("")
        else:
            raise Exception("Invalid image")

    def _try_sync_fallback(self, wallpaper_path: Path):
        """Synchronous fallback thumbnail loading."""
        try:
            # Use PIL for more reliable image loading
            from PIL import Image

            with Image.open(wallpaper_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Create thumbnail
                img.thumbnail((220, 140), Image.Resampling.LANCZOS)

                # Convert to QPixmap
                import io
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)

                pixmap = QPixmap()
                pixmap.loadFromData(img_byte_arr.getvalue())

                if not pixmap.isNull():
                    self.thumbnail_label.setPixmap(pixmap)
                    self.thumbnail_label.setText("")
                else:
                    self.thumbnail_label.setText("Load failed")

        except Exception as e:
            logger.error(f"Sync fallback failed for {wallpaper_path}: {e}")
            self.thumbnail_label.setText("Load failed")
            self.thumbnail_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #ff9800;
                    background-color: #fff3e0;
                    color: #ef6c00;
                    border-radius: 4px;
                }
            """)

    def _start_loading_timeout(self):
        """Start timeout timer for loading state."""
        if hasattr(self, '_loading_timer'):
            self._loading_timer.stop()

        from PySide6.QtCore import QTimer
        self._loading_timer = QTimer()
        self._loading_timer.setSingleShot(True)
        self._loading_timer.timeout.connect(self._on_loading_timeout)
        self._loading_timer.start(10000)  # 10 second timeout

    def _on_loading_timeout(self):
        """Handle loading timeout."""
        if self.thumbnail_label.text() == "Loading...":
            logger.warning(f"Thumbnail loading timed out for {self.wallpaper_data.get('path', '')}")
            # Try sync fallback as last resort
            wallpaper_path = Path(self.wallpaper_data.get('path', ''))
            self._try_sync_fallback(wallpaper_path)

    def _on_local_thumbnail_loaded(self, file_path: str, pixmap: QPixmap):
        """Handle local thumbnail loading completion."""
        wallpaper_path = str(Path(self.wallpaper_data.get('path', '')))
        if file_path == wallpaper_path:
            # Stop loading timeout
            if hasattr(self, '_loading_timer'):
                self._loading_timer.stop()

            # Disconnect signals to prevent multiple calls
            try:
                self.thumbnail_generator.thumbnail_ready.disconnect(self._on_local_thumbnail_loaded)
                self.thumbnail_generator.thumbnail_error.disconnect(self._on_local_thumbnail_error)
            except (TypeError, AttributeError):
                pass

            # Set the thumbnail
            if not pixmap.isNull():
                self.thumbnail_label.setPixmap(pixmap)
                self.thumbnail_label.setText("")
                # Reset any error styling
                self.thumbnail_label.setStyleSheet("""
                    QLabel {
                        border: 1px solid #ddd;
                        background-color: #f5f5f5;
                        border-radius: 4px;
                    }
                """)
            else:
                # Fallback if pixmap is null
                self._try_sync_fallback(Path(wallpaper_path))

    def _on_local_thumbnail_error(self, file_path: str, error_msg: str):
        """Handle local thumbnail loading error."""
        wallpaper_path = str(Path(self.wallpaper_data.get('path', '')))
        if file_path == wallpaper_path:
            # Stop loading timeout
            if hasattr(self, '_loading_timer'):
                self._loading_timer.stop()

            # Disconnect signals
            try:
                self.thumbnail_generator.thumbnail_ready.disconnect(self._on_local_thumbnail_loaded)
                self.thumbnail_generator.thumbnail_error.disconnect(self._on_local_thumbnail_error)
            except (TypeError, AttributeError):
                pass

            logger.warning(f"Thumbnail generation failed for {file_path}: {error_msg}")

            # Try sync fallback before giving up
            self._try_sync_fallback(Path(wallpaper_path))

    def _on_delete_clicked(self):
        """Handle delete button click."""
        self.delete_requested.emit(self.wallpaper_data)

    def set_deleting_state(self, deleting: bool):
        """
        Set deleting state and update UI accordingly.

        Args:
            deleting: Whether deletion is in progress
        """
        if deleting:
            self.delete_btn.setText("Deleting...")
            self.delete_btn.setEnabled(False)
            self.set_bg_btn.setEnabled(False)
        else:
            self.delete_btn.setText("Delete")
            self.delete_btn.setEnabled(True)
            self.set_bg_btn.setEnabled(True)

    def show_tooltip_info(self):
        """Show detailed info in tooltip for local wallpaper."""
        wallpaper_path = Path(self.wallpaper_data.get('path', ''))
        metadata = self.wallpaper_data.get('metadata', {})

        # Format file size
        file_size = self.wallpaper_data.get('file_size', 0)
        if file_size > 0:
            size_mb = file_size / (1024 * 1024)
            if size_mb >= 1:
                size_str = f"{size_mb:.1f} MB"
            else:
                size_str = f"{file_size / 1024:.0f} KB"
        else:
            size_str = "Unknown"

        tooltip_text = f"""
        <b>{wallpaper_path.name}</b><br>
        <b>Resolution:</b> {self.wallpaper_data.get('resolution', 'Unknown')}<br>
        <b>File Size:</b> {size_str}<br>
        <b>Source:</b> {self.wallpaper_data.get('source_type', 'Unknown').title()}<br>
        <b>Added:</b> {self.wallpaper_data.get('added_date', 'Unknown')[:10]}<br>
        <b>Path:</b> {wallpaper_path.parent}<br>
        """

        # Add metadata if available
        if metadata.get('prompt'):
            tooltip_text += f"<b>Prompt:</b> {metadata['prompt'][:100]}...<br>"
        if metadata.get('tags'):
            tags_str = ', '.join(metadata['tags'][:5])
            tooltip_text += f"<b>Tags:</b> {tags_str}<br>"

        self.setToolTip(tooltip_text)


# Example usage
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QScrollArea, QVBoxLayout, QWidget
    from .image_loader import AsyncImageLoader

    app = QApplication(sys.argv)

    # Create image loader
    loader = AsyncImageLoader(cache_size_mb=10)

    # Sample wallpaper data
    sample_wallpaper = {
        'id': 'sample123',
        'resolution': '1920x1080',
        'views': 15000,
        'favorites': 250,
        'category': 'nature',
        'file_size': 425984,
        'tags': ['landscape', 'mountain', 'sunset'],
        'created_at': '2023-01-15 10:30:00',
        'thumbs': {
            'large': 'https://th.wallhaven.cc/lg/6o/wallhaven-6o3q9d.jpg'
        }
    }

    # Create test window
    window = QWidget()
    window.setWindowTitle("Wallpaper Card Test")
    window.resize(300, 400)

    layout = QVBoxLayout(window)

    # Create wallpaper card
    card = WallpaperCard(sample_wallpaper, loader)
    layout.addWidget(card)

    window.show()

    # Cleanup on exit
    def cleanup():
        loader.shutdown()

    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec())