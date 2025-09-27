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