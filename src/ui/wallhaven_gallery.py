"""
Wallhaven Gallery Widget for browsing and selecting wallpapers.

Provides a comprehensive gallery interface with search, filtering,
thumbnail grid, and batch operations for wallpaper management.
"""

import logging
import random
from typing import Dict, List, Any, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QScrollArea, QFrame, QGridLayout, QProgressBar,
    QGroupBox, QCheckBox, QMessageBox, QSplitter, QTextEdit, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QSize
from PySide6.QtGui import QFont, QPixmap

from ui.image_loader import AsyncImageLoader
from ui.wallpaper_card import WallpaperCard
from core.downloaders.wallhaven_client import WallhavenClient
from core.image_manager import ImageManager
from core.background_manager import BackgroundManager


logger = logging.getLogger(__name__)


class WallpaperSearchWorker(QThread):
    """Background worker for searching wallpapers."""

    # Signals
    search_finished = Signal(list)  # wallpapers list
    search_error = Signal(str)      # error message
    progress_update = Signal(str)   # status message

    def __init__(self, client: WallhavenClient):
        super().__init__()
        self.client = client
        self.search_params = {}

    def set_search_params(self, **params):
        """Set search parameters."""
        self.search_params = params

    def run(self):
        """Execute search in background."""
        try:
            self.progress_update.emit("Searching wallpapers...")

            wallpapers = self.client.search_wallpapers(**self.search_params)

            self.progress_update.emit(f"Found {len(wallpapers)} wallpapers")
            self.search_finished.emit(wallpapers)

        except Exception as e:
            logger.error(f"Search failed: {e}")
            self.search_error.emit(str(e))


class WallpaperDownloadWorker(QThread):
    """Background worker for downloading wallpapers."""

    # Signals
    download_finished = Signal(dict, str)  # wallpaper_data, file_path
    download_error = Signal(dict, str)     # wallpaper_data, error_message
    download_skipped = Signal(dict, str)   # wallpaper_data, reason (e.g., "duplicate")
    progress_update = Signal(str)          # status message

    def __init__(self, client: WallhavenClient, image_manager: ImageManager):
        super().__init__()
        self.client = client
        self.image_manager = image_manager
        self.download_queue = []

    def add_download(self, wallpaper_data: Dict[str, Any]):
        """Add wallpaper to download queue."""
        self.download_queue.append(wallpaper_data)

    def run(self):
        """Execute downloads in background."""
        total = len(self.download_queue)
        skipped_count = 0

        for i, wallpaper_data in enumerate(self.download_queue):
            try:
                wallpaper_id = wallpaper_data['id']
                self.progress_update.emit(f"Processing {wallpaper_id} ({i+1}/{total})...")

                # Check for existing wallpaper before download
                existing_wallpapers = self.image_manager.list_wallpapers('wallhaven')
                is_duplicate = False

                for existing in existing_wallpapers:
                    existing_metadata = existing.get('metadata', {})
                    if existing_metadata.get('wallpaper_id') == wallpaper_id:
                        self.download_skipped.emit(wallpaper_data, "Already in collection")
                        is_duplicate = True
                        skipped_count += 1
                        break

                if not is_duplicate:
                    # Download wallpaper
                    file_path = self.client.download_wallpaper(wallpaper_data, check_duplicates=False)

                    if file_path:
                        # Store in organized directory
                        stored_path = self.image_manager.store_wallpaper(
                            file_path, 'wallhaven',
                            metadata={'source': 'wallhaven', 'wallpaper_id': wallpaper_id}
                        )

                        if stored_path:
                            self.download_finished.emit(wallpaper_data, str(stored_path))
                        else:
                            self.download_error.emit(wallpaper_data, "Failed to store wallpaper")
                    else:
                        self.download_error.emit(wallpaper_data, "Failed to download wallpaper")

            except Exception as e:
                logger.error(f"Download failed for {wallpaper_data['id']}: {e}")
                self.download_error.emit(wallpaper_data, str(e))

        # Final status update
        downloaded_count = total - skipped_count
        if skipped_count > 0:
            self.progress_update.emit(f"Completed: {downloaded_count} downloaded, {skipped_count} skipped (duplicates)")
        else:
            self.progress_update.emit(f"Completed: {downloaded_count} downloaded")

        self.download_queue.clear()


class WallhavenGallery(QWidget):
    """
    Main gallery widget for browsing Wallhaven wallpapers.

    Provides search interface, thumbnail grid, and batch operations
    for downloading and setting wallpapers as background.
    """

    # Signals
    status_changed = Signal(str)           # status message
    wallpaper_downloaded = Signal(str)     # file path
    background_changed = Signal(str)       # wallpaper id

    def __init__(self):
        """Initialize Wallhaven gallery."""
        super().__init__()

        # Core components
        self.client = WallhavenClient()
        self.image_manager = ImageManager()
        self.background_manager = BackgroundManager()
        self.image_loader = AsyncImageLoader(cache_size_mb=30, max_workers=4)

        # Workers
        self.search_worker = WallpaperSearchWorker(self.client)
        self.download_worker = WallpaperDownloadWorker(self.client, self.image_manager)

        # State
        self.current_wallpapers = []
        self.wallpaper_cards = []
        self.current_page = 1

        self.setup_ui()
        self.connect_signals()

        # Load initial wallpapers with variety
        QTimer.singleShot(500, self.load_initial_content)

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Search controls
        search_group = self.create_search_controls()
        layout.addWidget(search_group)

        # Gallery controls
        controls_group = self.create_gallery_controls()
        layout.addWidget(controls_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Gallery area
        gallery_area = self.create_gallery_area()
        layout.addWidget(gallery_area)

        # Status bar
        self.status_label = QLabel("Ready to browse wallpapers")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)

    def create_search_controls(self) -> QGroupBox:
        """Create search controls section."""
        group = QGroupBox("Search Wallpapers")
        layout = QVBoxLayout(group)

        # Search query row
        query_layout = QHBoxLayout()

        query_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter keywords (e.g., nature, abstract, city)")
        self.search_input.returnPressed.connect(lambda: self.search_wallpapers(reset_page=True))
        query_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(lambda: self.search_wallpapers(reset_page=True))
        query_layout.addWidget(self.search_btn)

        layout.addLayout(query_layout)

        # Quick search presets
        presets_layout = QHBoxLayout()
        presets_layout.addWidget(QLabel("Quick Search:"))

        presets = [
            ("🌿 Nature", "nature landscape mountain forest"),
            ("🌌 Space", "space galaxy nebula astronomy"),
            ("🏙️ City", "city urban architecture skyline"),
            ("🎨 Abstract", "abstract geometric minimalist"),
            ("🌊 Ocean", "ocean sea beach water"),
            ("🔥 Random", "")  # Special case for random
        ]

        for name, query in presets:
            btn = QPushButton(name)
            btn.setMaximumWidth(100)
            if query:
                btn.clicked.connect(lambda checked, q=query: self.apply_preset_search(q))
            else:
                btn.clicked.connect(self.apply_random_search)
            btn.setToolTip(f"Search for {query if query else 'random wallpapers'}")
            presets_layout.addWidget(btn)

        presets_layout.addStretch()
        layout.addLayout(presets_layout)

        # Filters row
        filters_layout = QHBoxLayout()

        # Category filter
        filters_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["general", "anime", "people"])
        filters_layout.addWidget(self.category_combo)

        # Sorting
        filters_layout.addWidget(QLabel("Sort by:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["relevance", "date_added", "views", "favorites", "random"])
        filters_layout.addWidget(self.sort_combo)

        # Results count
        filters_layout.addWidget(QLabel("Count:"))
        self.count_spin = QSpinBox()
        self.count_spin.setMinimum(6)
        self.count_spin.setMaximum(24)
        self.count_spin.setValue(12)
        filters_layout.addWidget(self.count_spin)

        filters_layout.addStretch()

        layout.addLayout(filters_layout)

        return group

    def create_gallery_controls(self) -> QGroupBox:
        """Create gallery controls section."""
        group = QGroupBox("Gallery Controls")
        layout = QVBoxLayout(group)

        # Top row: Selection and batch operations
        top_layout = QHBoxLayout()

        # Selection info
        self.selection_label = QLabel("0 wallpapers selected")
        self.selection_label.setFont(QFont("", 10, QFont.Bold))
        top_layout.addWidget(self.selection_label)

        top_layout.addStretch()

        # Batch operations
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_wallpapers)
        top_layout.addWidget(self.select_all_btn)

        self.clear_selection_btn = QPushButton("Clear Selection")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        top_layout.addWidget(self.clear_selection_btn)

        self.download_selected_btn = QPushButton("Download Selected")
        self.download_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.download_selected_btn.clicked.connect(self.download_selected_wallpapers)
        self.download_selected_btn.setEnabled(False)
        top_layout.addWidget(self.download_selected_btn)

        layout.addLayout(top_layout)

        # Bottom row: Pagination and refresh controls
        bottom_layout = QHBoxLayout()

        # Refresh/Shuffle button
        self.shuffle_btn = QPushButton("🎲 Shuffle")
        self.shuffle_btn.setToolTip("Get fresh wallpapers with random content")
        self.shuffle_btn.clicked.connect(self.shuffle_wallpapers)
        bottom_layout.addWidget(self.shuffle_btn)

        bottom_layout.addStretch()

        # Pagination controls
        self.prev_page_btn = QPushButton("← Previous")
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.prev_page_btn.setEnabled(False)
        bottom_layout.addWidget(self.prev_page_btn)

        self.page_label = QLabel("Page 1")
        self.page_label.setFont(QFont("", 10, QFont.Bold))
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setMinimumWidth(80)
        bottom_layout.addWidget(self.page_label)

        self.next_page_btn = QPushButton("Next →")
        self.next_page_btn.clicked.connect(self.next_page)
        bottom_layout.addWidget(self.next_page_btn)

        layout.addLayout(bottom_layout)

        return group

    def create_gallery_area(self) -> QWidget:
        """Create the main gallery area with wallpaper grid."""
        # Scroll area for wallpaper grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Gallery container
        self.gallery_widget = QWidget()
        self.gallery_layout = QGridLayout(self.gallery_widget)
        self.gallery_layout.setSpacing(10)
        self.gallery_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.gallery_widget)

        return self.scroll_area

    def connect_signals(self):
        """Connect signals and slots."""
        # Search worker signals
        self.search_worker.search_finished.connect(self.on_search_finished)
        self.search_worker.search_error.connect(self.on_search_error)
        self.search_worker.progress_update.connect(self.update_status)

        # Download worker signals
        self.download_worker.download_finished.connect(self.on_download_finished)
        self.download_worker.download_error.connect(self.on_download_error)
        self.download_worker.download_skipped.connect(self.on_download_skipped)
        self.download_worker.progress_update.connect(self.update_status)
        self.download_worker.finished.connect(self.on_download_worker_finished)

    def load_initial_content(self):
        """Load initial wallpapers with varied content strategies."""
        # Define various initial loading strategies for variety
        strategies = [
            # Random popular wallpapers
            {
                'query': None,
                'sorting': 'random',
                'category': 'general'
            },
            # Recent high-quality additions
            {
                'query': None,
                'sorting': 'date_added',
                'category': 'general'
            },
            # Popular nature wallpapers
            {
                'query': 'nature',
                'sorting': 'favorites',
                'category': 'general'
            },
            # Random space/astronomy content
            {
                'query': 'space',
                'sorting': 'random',
                'category': 'general'
            },
            # Abstract/artistic wallpapers
            {
                'query': 'abstract',
                'sorting': 'views',
                'category': 'general'
            },
            # Architecture and cityscapes
            {
                'query': 'city',
                'sorting': 'favorites',
                'category': 'general'
            }
        ]

        # Select a random strategy
        strategy = random.choice(strategies)

        # Apply the strategy to UI controls
        if strategy['query']:
            self.search_input.setText(strategy['query'])
        else:
            self.search_input.clear()

        self.sort_combo.setCurrentText(strategy['sorting'])
        self.category_combo.setCurrentText(strategy['category'])

        # Reset page and search
        self.current_page = 1
        self.search_wallpapers()

        # Update status to show what strategy was used
        strategy_name = strategy['query'] if strategy['query'] else f"{strategy['sorting']} wallpapers"
        self.update_status(f"Loading {strategy_name}...")

    def search_wallpapers(self, reset_page: bool = False):
        """Start wallpaper search."""
        if self.search_worker.isRunning():
            return

        # Reset to page 1 for new searches (unless it's pagination)
        if reset_page:
            self.current_page = 1

        # Get search parameters
        query = self.search_input.text().strip()
        category = self.category_combo.currentText()
        sorting = self.sort_combo.currentText()
        count = self.count_spin.value()

        # Set category codes
        category_codes = {
            'general': '100',
            'anime': '010',
            'people': '001'
        }

        search_params = {
            'query': query if query else None,
            'categories': category_codes.get(category, '100'),
            'sorting': sorting,
            'limit': count,
            'page': self.current_page,
            'atleast': '1920x1080'  # Minimum resolution
        }

        # Start search
        self.search_worker.set_search_params(**search_params)
        self.show_loading(True)
        self.search_worker.start()

    def on_search_finished(self, wallpapers: List[Dict[str, Any]]):
        """Handle search completion."""
        self.show_loading(False)
        self.current_wallpapers = wallpapers

        if wallpapers:
            self.populate_gallery(wallpapers)
            self.update_status(f"Found {len(wallpapers)} wallpapers")
            self.update_pagination_controls()
        else:
            self.clear_gallery()
            self.update_status("No wallpapers found")
            self.update_pagination_controls()

    def on_search_error(self, error_msg: str):
        """Handle search error."""
        self.show_loading(False)
        self.clear_gallery()
        self.update_status(f"Search failed: {error_msg}")
        QMessageBox.warning(self, "Search Error", f"Failed to search wallpapers:\n{error_msg}")

    def populate_gallery(self, wallpapers: List[Dict[str, Any]]):
        """Populate gallery with wallpaper cards."""
        self.clear_gallery()

        # Calculate grid dimensions
        cards_per_row = max(1, self.scroll_area.width() // 260)  # Card width + margin

        # Get existing wallpapers for duplicate checking
        existing_wallpapers = self.image_manager.list_wallpapers('wallhaven')
        existing_ids = set()
        for existing in existing_wallpapers:
            existing_metadata = existing.get('metadata', {})
            wallpaper_id = existing_metadata.get('wallpaper_id')
            if wallpaper_id:
                existing_ids.add(wallpaper_id)

        # Create wallpaper cards
        for i, wallpaper_data in enumerate(wallpapers):
            card = WallpaperCard(wallpaper_data, self.image_loader)

            # Check if already downloaded and mark accordingly
            if wallpaper_data['id'] in existing_ids:
                card.set_already_downloaded(True)

            # Connect card signals
            card.selection_changed.connect(self.on_card_selection_changed)
            card.download_requested.connect(self.on_single_download_requested)
            card.set_background_requested.connect(self.on_set_background_requested)

            # Add to grid
            row = i // cards_per_row
            col = i % cards_per_row
            self.gallery_layout.addWidget(card, row, col)

            self.wallpaper_cards.append(card)

    def clear_gallery(self):
        """Clear all wallpaper cards from gallery."""
        for card in self.wallpaper_cards:
            card.deleteLater()

        self.wallpaper_cards.clear()

        # Clear layout
        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.update_selection_display()

    def on_card_selection_changed(self, is_selected: bool):
        """Handle card selection change."""
        self.update_selection_display()

    def update_selection_display(self):
        """Update selection count display and button states."""
        selected_cards = self.get_selected_cards()
        count = len(selected_cards)

        self.selection_label.setText(f"{count} wallpaper{'s' if count != 1 else ''} selected")
        self.download_selected_btn.setEnabled(count > 0)

    def get_selected_cards(self) -> List[WallpaperCard]:
        """Get list of selected wallpaper cards."""
        return [card for card in self.wallpaper_cards if card.is_card_selected()]

    def select_all_wallpapers(self):
        """Select all wallpaper cards."""
        for card in self.wallpaper_cards:
            card.set_selected(True)

    def clear_selection(self):
        """Clear all wallpaper selections."""
        for card in self.wallpaper_cards:
            card.set_selected(False)

    def download_selected_wallpapers(self):
        """Download all selected wallpapers."""
        selected_cards = self.get_selected_cards()

        if not selected_cards:
            return

        # Set downloading state
        for card in selected_cards:
            card.set_downloading_state(True)

        # Add to download queue
        for card in selected_cards:
            self.download_worker.add_download(card.get_wallpaper_data())

        # Start download worker
        if not self.download_worker.isRunning():
            self.show_loading(True)
            self.download_worker.start()

    def on_single_download_requested(self, wallpaper_data: Dict[str, Any]):
        """Handle single wallpaper download request."""
        # Find the card and set downloading state
        for card in self.wallpaper_cards:
            if card.get_wallpaper_data()['id'] == wallpaper_data['id']:
                card.set_downloading_state(True)
                break

        # Add to download queue
        self.download_worker.add_download(wallpaper_data)

        # Start download worker
        if not self.download_worker.isRunning():
            self.show_loading(True)
            self.download_worker.start()

    def on_set_background_requested(self, wallpaper_data: Dict[str, Any]):
        """Handle set background request."""
        wallpaper_id = wallpaper_data['id']

        # First, download the wallpaper if not already downloaded
        try:
            file_path = self.client.download_wallpaper(wallpaper_data)

            if file_path:
                # Set as background
                success = self.background_manager.set_background(file_path)

                if success:
                    self.update_status(f"Set wallpaper {wallpaper_id} as background")
                    self.background_changed.emit(wallpaper_id)
                    QMessageBox.information(
                        self, "Success",
                        f"Wallpaper {wallpaper_id} has been set as your desktop background!"
                    )
                else:
                    QMessageBox.warning(
                        self, "Background Setting Failed",
                        "Failed to set wallpaper as background. Please check system permissions."
                    )
            else:
                QMessageBox.warning(
                    self, "Download Failed",
                    f"Failed to download wallpaper {wallpaper_id}."
                )

        except Exception as e:
            logger.error(f"Failed to set background: {e}")
            QMessageBox.critical(
                self, "Error",
                f"An error occurred while setting the background:\n{str(e)}"
            )

    def on_download_finished(self, wallpaper_data: Dict[str, Any], file_path: str):
        """Handle successful download."""
        wallpaper_id = wallpaper_data['id']

        # Reset downloading state and mark as downloaded
        for card in self.wallpaper_cards:
            if card.get_wallpaper_data()['id'] == wallpaper_id:
                card.set_downloading_state(False)
                card.set_already_downloaded(True)
                break

        self.wallpaper_downloaded.emit(file_path)
        logger.info(f"Downloaded wallpaper {wallpaper_id} to {file_path}")

        # Check if download worker is finished with queue
        self._check_download_completion()

    def on_download_error(self, wallpaper_data: Dict[str, Any], error_msg: str):
        """Handle download error."""
        wallpaper_id = wallpaper_data['id']

        # Reset downloading state
        for card in self.wallpaper_cards:
            if card.get_wallpaper_data()['id'] == wallpaper_id:
                card.set_downloading_state(False)
                break

        self.update_status(f"Download failed: {wallpaper_id}")
        logger.error(f"Download failed for {wallpaper_id}: {error_msg}")

        # Check if download worker is finished with queue
        self._check_download_completion()

    def on_download_skipped(self, wallpaper_data: Dict[str, Any], reason: str):
        """Handle skipped download (e.g., duplicate)."""
        wallpaper_id = wallpaper_data['id']

        # Reset downloading state
        for card in self.wallpaper_cards:
            if card.get_wallpaper_data()['id'] == wallpaper_id:
                card.set_downloading_state(False)
                break

        logger.info(f"Skipped wallpaper {wallpaper_id}: {reason}")

        # Check if download worker is finished with queue
        self._check_download_completion()

    def _check_download_completion(self):
        """Check if all downloads are complete and reset UI state."""
        # Check if any cards are still downloading
        downloading_cards = [card for card in self.wallpaper_cards if card.is_downloading]

        if not downloading_cards and not self.download_worker.isRunning():
            # All downloads complete, hide loading state
            self.show_loading(False)
            self.update_status("All downloads completed")

    def on_download_worker_finished(self):
        """Handle download worker completion."""
        # Ensure all cards have their downloading state reset
        for card in self.wallpaper_cards:
            if card.is_downloading:
                card.set_downloading_state(False)

        # Hide loading state
        self.show_loading(False)
        self.update_status("Download queue processed")

    def show_loading(self, loading: bool):
        """Show or hide loading state."""
        if loading:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.search_btn.setEnabled(False)
        else:
            self.progress_bar.setVisible(False)
            self.search_btn.setEnabled(True)

    def update_status(self, message: str):
        """Update status message."""
        self.status_label.setText(message)
        self.status_changed.emit(message)

    def prev_page(self):
        """Go to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self.search_wallpapers()

    def next_page(self):
        """Go to next page."""
        self.current_page += 1
        self.search_wallpapers()

    def update_pagination_controls(self):
        """Update pagination button states and page label."""
        self.page_label.setText(f"Page {self.current_page}")
        self.prev_page_btn.setEnabled(self.current_page > 1)

        # Enable next button if we have wallpapers (assume more pages exist)
        # Wallhaven API doesn't provide total page count, so we enable next
        # until we get an empty result
        self.next_page_btn.setEnabled(len(self.current_wallpapers) > 0)

    def shuffle_wallpapers(self):
        """Shuffle/refresh wallpapers with random content."""
        # Reset to page 1 and use random sorting
        self.current_page = 1
        original_sorting = self.sort_combo.currentText()

        # Set to random sorting temporarily
        self.sort_combo.setCurrentText("random")
        self.search_wallpapers()

        # Restore original sorting
        self.sort_combo.setCurrentText(original_sorting)

        self.update_status("Shuffled wallpapers - showing fresh content!")

    def apply_preset_search(self, query: str):
        """Apply a preset search query."""
        self.search_input.setText(query)
        self.current_page = 1
        self.search_wallpapers()
        self.update_status(f"Searching for: {query}")

    def apply_random_search(self):
        """Apply random search settings."""
        # Random queries for variety
        random_queries = [
            "", "landscape", "abstract", "nature", "space", "minimal",
            "city", "art", "architecture", "fantasy", "digital", "colors"
        ]

        # Set random query and sorting
        self.search_input.setText(random.choice(random_queries))
        self.sort_combo.setCurrentText("random")
        self.current_page = 1
        self.search_wallpapers()
        self.update_status("Loading random wallpapers...")

    def closeEvent(self, event):
        """Handle widget close event."""
        # Shutdown workers and image loader
        if self.search_worker.isRunning():
            self.search_worker.terminate()
            self.search_worker.wait()

        if self.download_worker.isRunning():
            self.download_worker.terminate()
            self.download_worker.wait()

        self.image_loader.shutdown()
        super().closeEvent(event)


# Example usage
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)

    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Wallhaven Gallery")
    window.resize(1000, 700)

    # Create gallery
    gallery = WallhavenGallery()
    window.setCentralWidget(gallery)

    window.show()
    sys.exit(app.exec())