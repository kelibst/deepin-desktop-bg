"""
Downloaded Wallpaper Gallery for displaying and managing local wallpapers.

Provides a gallery interface for viewing, deleting, and setting downloaded
wallpapers as desktop backgrounds.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QMessageBox,
    QProgressBar, QFrame, QGroupBox, QCheckBox, QSpinBox,
    QSplitter, QTextEdit, QFileDialog, QMenuBar, QMenu
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QFileSystemWatcher
from PySide6.QtGui import QFont, QAction, QKeySequence

# Import our core modules
import sys
sys.path.append(str(Path(__file__).parent.parent))
from core.image_manager import ImageManager
from core.thumbnail_generator import ThumbnailGenerator
from core.background_setter import BackgroundSetter
from ui.wallpaper_card import LocalWallpaperCard


logger = logging.getLogger(__name__)


class DeleteWorker(QThread):
    """Worker thread for deleting wallpapers in background."""

    progress = Signal(int, int)  # current, total
    finished = Signal(int, int)  # successful, total
    error = Signal(str)

    def __init__(self, image_manager: ImageManager, wallpaper_ids: List[str]):
        super().__init__()
        self.image_manager = image_manager
        self.wallpaper_ids = wallpaper_ids

    def run(self):
        try:
            successful, total = self.image_manager.delete_multiple_wallpapers(self.wallpaper_ids)

            for i, wallpaper_id in enumerate(self.wallpaper_ids):
                self.progress.emit(i + 1, len(self.wallpaper_ids))
                self.msleep(50)  # Small delay for UI updates

            self.finished.emit(successful, total)
        except Exception as e:
            self.error.emit(str(e))


class DownloadedWallpaperGallery(QWidget):
    """
    Gallery widget for displaying and managing downloaded wallpapers.

    Features:
    - Grid display of wallpapers with thumbnails
    - Search and filter functionality
    - Bulk operations (select multiple, delete)
    - Set wallpaper as background
    - Source type filtering
    """

    # Signals
    wallpaper_deleted = Signal(str)        # wallpaper_id
    background_set = Signal(str)           # wallpaper_path
    selection_changed = Signal(int)        # selected_count

    def __init__(self):
        super().__init__()

        # Core components
        self.image_manager = ImageManager()
        self.thumbnail_generator = ThumbnailGenerator()
        self.background_setter = BackgroundSetter()

        # UI state
        self.wallpaper_cards = []
        self.current_wallpapers = []
        self.selected_cards = []

        # Worker threads
        self.delete_worker = None

        # File system watcher for automatic updates
        self.file_watcher = QFileSystemWatcher()
        self.setup_file_watcher()

        # Debounce timer for file system changes
        self.fs_update_timer = QTimer()
        self.fs_update_timer.setSingleShot(True)
        self.fs_update_timer.timeout.connect(self.on_filesystem_update)

        self.setup_ui()
        self.load_wallpapers()

        # Connect thumbnail generator signals
        self.thumbnail_generator.thumbnail_ready.connect(self.on_thumbnail_ready)
        self.thumbnail_generator.generation_finished.connect(self.on_thumbnail_generation_finished)

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header section
        self.create_header_section(layout)

        # Filter and search section
        self.create_filter_section(layout)

        # Main content area
        self.create_content_area(layout)

        # Status and actions section
        self.create_status_section(layout)

    def create_header_section(self, main_layout):
        """Create header with title and stats."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)

        # Title
        title_label = QLabel("Downloaded Wallpapers")
        title_label.setFont(QFont("", 16, QFont.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Stats
        self.stats_label = QLabel("Loading...")
        self.stats_label.setFont(QFont("", 10))
        self.stats_label.setStyleSheet("color: #666;")
        header_layout.addWidget(self.stats_label)

        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_wallpapers)
        header_layout.addWidget(self.refresh_btn)

        main_layout.addWidget(header_frame)

    def create_filter_section(self, main_layout):
        """Create filter and search controls."""
        filter_frame = QFrame()
        filter_frame.setFrameStyle(QFrame.StyledPanel)
        filter_layout = QHBoxLayout(filter_frame)

        # Source type filter
        filter_layout.addWidget(QLabel("Source:"))
        self.source_filter = QComboBox()
        self.source_filter.addItems([
            "All Sources", "Wallhaven", "AI Generated",
            "Community", "Public Domain"
        ])
        self.source_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.source_filter)

        filter_layout.addWidget(QLabel("    Search:"))

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by filename, tags, or metadata...")
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_layout.addWidget(self.search_input)

        # Clear search
        clear_search_btn = QPushButton("Clear")
        clear_search_btn.clicked.connect(self.clear_search)
        filter_layout.addWidget(clear_search_btn)

        main_layout.addWidget(filter_frame)

    def create_content_area(self, main_layout):
        """Create main content area with scrollable wallpaper grid."""
        # Create scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Content widget for scroll area
        self.content_widget = QWidget()
        self.scroll_area.setWidget(self.content_widget)

        # Grid layout for wallpaper cards
        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        # Loading label
        self.loading_label = QLabel("Loading wallpapers...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setFont(QFont("", 12))
        self.loading_label.setStyleSheet("color: #666; padding: 50px;")
        self.grid_layout.addWidget(self.loading_label, 0, 0, 1, -1)

        main_layout.addWidget(self.scroll_area, 1)  # Stretch factor 1

    def create_status_section(self, main_layout):
        """Create status and action buttons section."""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_layout = QVBoxLayout(status_frame)

        # Selection info and bulk actions
        actions_layout = QHBoxLayout()

        # Selection info
        self.selection_label = QLabel("No wallpapers selected")
        self.selection_label.setFont(QFont("", 10))
        actions_layout.addWidget(self.selection_label)

        actions_layout.addStretch()

        # Bulk actions
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_wallpapers)
        actions_layout.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self.select_no_wallpapers)
        actions_layout.addWidget(self.select_none_btn)

        self.delete_selected_btn = QPushButton("🗑️ Delete Selected")
        self.delete_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.delete_selected_btn.clicked.connect(self.delete_selected_wallpapers)
        self.delete_selected_btn.setEnabled(False)
        actions_layout.addWidget(self.delete_selected_btn)

        status_layout.addLayout(actions_layout)

        # Progress bar for operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)

        # Status message
        self.status_message = QLabel("Ready")
        self.status_message.setFont(QFont("", 9))
        self.status_message.setStyleSheet("color: #666;")
        status_layout.addWidget(self.status_message)

        main_layout.addWidget(status_frame)

    def load_wallpapers(self):
        """Load wallpapers from image manager."""
        self.status_message.setText("Loading wallpapers...")

        try:
            # Get wallpapers with thumbnail info
            wallpapers = self.image_manager.get_wallpapers_with_thumbnails()
            self.current_wallpapers = wallpapers

            # Update stats
            self.update_stats()

            # Display wallpapers
            self.display_wallpapers(wallpapers)

            # Generate thumbnails asynchronously
            if wallpapers:
                wallpaper_paths = [Path(w['path']) for w in wallpapers]
                self.thumbnail_generator.generate_thumbnails_async(wallpaper_paths)

            self.status_message.setText(f"Loaded {len(wallpapers)} wallpapers")

        except Exception as e:
            logger.error(f"Failed to load wallpapers: {e}")
            self.status_message.setText(f"Error loading wallpapers: {e}")

    def display_wallpapers(self, wallpapers: List[Dict]):
        """Display wallpapers in grid layout."""
        # Clear existing cards
        self.clear_wallpaper_cards()

        if not wallpapers:
            # Show no wallpapers message
            self.loading_label.setText("No wallpapers found. Try downloading some wallpapers first!")
            self.loading_label.setVisible(True)
            return

        # Hide loading label
        self.loading_label.setVisible(False)

        # Create cards for wallpapers
        columns = 4  # Number of columns in grid

        for i, wallpaper_data in enumerate(wallpapers):
            try:
                # Create local wallpaper card
                card = LocalWallpaperCard(wallpaper_data, self.thumbnail_generator)

                # Connect signals
                card.selection_changed.connect(self.on_card_selection_changed)
                card.delete_requested.connect(self.on_card_delete_requested)
                card.set_background_requested.connect(self.on_card_background_requested)
                card.card_clicked.connect(self.on_card_clicked)

                # Add to grid
                row = i // columns
                col = i % columns
                self.grid_layout.addWidget(card, row, col)

                # Store card reference
                self.wallpaper_cards.append(card)

            except Exception as e:
                logger.error(f"Failed to create card for wallpaper {wallpaper_data.get('id', 'unknown')}: {e}")

    def clear_wallpaper_cards(self):
        """Clear all wallpaper cards from layout."""
        # Remove and delete existing cards
        for card in self.wallpaper_cards:
            self.grid_layout.removeWidget(card)
            card.deleteLater()

        self.wallpaper_cards.clear()
        self.selected_cards.clear()
        self.update_selection_display()

    def on_filter_changed(self):
        """Handle source filter change."""
        self.apply_filters()

    def on_search_changed(self):
        """Handle search input change."""
        # Debounce search to avoid too many updates
        if hasattr(self, 'search_timer'):
            self.search_timer.stop()

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filters)
        self.search_timer.start(300)  # 300ms delay

    def apply_filters(self):
        """Apply current filters and search."""
        source_filter = self.source_filter.currentText()
        search_query = self.search_input.text().strip()

        # Get base wallpapers
        try:
            if search_query:
                # Use search functionality
                source_type = None
                if source_filter != "All Sources":
                    source_map = {
                        "Wallhaven": "wallhaven",
                        "AI Generated": "ai_generated",
                        "Community": "community",
                        "Public Domain": "public_domain"
                    }
                    source_type = source_map.get(source_filter)

                wallpapers = self.image_manager.search_wallpapers(search_query, source_type)

                # Convert to display format
                filtered_wallpapers = []
                for wallpaper in wallpapers:
                    display_data = self.image_manager.get_wallpapers_with_thumbnails()
                    matching = [w for w in display_data if w['id'] == wallpaper['id']]
                    if matching:
                        filtered_wallpapers.extend(matching)

            else:
                # Use source filter only
                source_type = None
                if source_filter != "All Sources":
                    source_map = {
                        "Wallhaven": "wallhaven",
                        "AI Generated": "ai_generated",
                        "Community": "community",
                        "Public Domain": "public_domain"
                    }
                    source_type = source_map.get(source_filter)

                filtered_wallpapers = self.image_manager.get_wallpapers_with_thumbnails(source_type)

            # Update display
            self.current_wallpapers = filtered_wallpapers
            self.display_wallpapers(filtered_wallpapers)

            # Update status
            total_count = len(self.image_manager.get_wallpapers_with_thumbnails())
            if len(filtered_wallpapers) != total_count:
                self.status_message.setText(
                    f"Showing {len(filtered_wallpapers)} of {total_count} wallpapers"
                )
            else:
                self.status_message.setText(f"Showing all {total_count} wallpapers")

        except Exception as e:
            logger.error(f"Failed to apply filters: {e}")
            self.status_message.setText(f"Filter error: {e}")

    def clear_search(self):
        """Clear search input."""
        self.search_input.clear()

    def refresh_wallpapers(self):
        """Refresh wallpaper display."""
        self.load_wallpapers()

    def update_stats(self):
        """Update statistics display."""
        try:
            stats = self.image_manager.get_source_type_stats()
            total_count = sum(source_stats['count'] for source_stats in stats.values())
            total_size = sum(source_stats['size_mb'] for source_stats in stats.values())

            self.stats_label.setText(f"{total_count} wallpapers • {total_size:.1f} MB")

        except Exception as e:
            logger.error(f"Failed to update stats: {e}")
            self.stats_label.setText("Stats unavailable")

    def on_card_selection_changed(self, is_selected: bool):
        """Handle wallpaper card selection change."""
        # Update selected cards list
        sender_card = self.sender()
        if is_selected and sender_card not in self.selected_cards:
            self.selected_cards.append(sender_card)
        elif not is_selected and sender_card in self.selected_cards:
            self.selected_cards.remove(sender_card)

        self.update_selection_display()

    def update_selection_display(self):
        """Update selection count display and button states."""
        count = len(self.selected_cards)

        if count == 0:
            self.selection_label.setText("No wallpapers selected")
        elif count == 1:
            self.selection_label.setText("1 wallpaper selected")
        else:
            self.selection_label.setText(f"{count} wallpapers selected")

        self.delete_selected_btn.setEnabled(count > 0)
        self.selection_changed.emit(count)

    def select_all_wallpapers(self):
        """Select all visible wallpapers."""
        for card in self.wallpaper_cards:
            card.set_selected(True)

    def select_no_wallpapers(self):
        """Deselect all wallpapers."""
        for card in self.wallpaper_cards:
            card.set_selected(False)

    def on_card_delete_requested(self, wallpaper_data: Dict):
        """Handle delete request for single wallpaper."""
        wallpaper_path = Path(wallpaper_data.get('path', ''))
        filename = wallpaper_path.name

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete this wallpaper?\n\n{filename}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.delete_wallpapers([wallpaper_data['id']])

    def delete_selected_wallpapers(self):
        """Delete all selected wallpapers."""
        if not self.selected_cards:
            return

        count = len(self.selected_cards)
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete {count} selected wallpaper(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            wallpaper_ids = [card.get_wallpaper_data()['id'] for card in self.selected_cards]
            self.delete_wallpapers(wallpaper_ids)

    def delete_wallpapers(self, wallpaper_ids: List[str]):
        """Delete wallpapers by IDs."""
        if not wallpaper_ids:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_message.setText(f"Deleting {len(wallpaper_ids)} wallpaper(s)...")

        # Start delete worker
        self.delete_worker = DeleteWorker(self.image_manager, wallpaper_ids)
        self.delete_worker.progress.connect(self.on_delete_progress)
        self.delete_worker.finished.connect(self.on_delete_finished)
        self.delete_worker.error.connect(self.on_delete_error)
        self.delete_worker.start()

    def on_delete_progress(self, current: int, total: int):
        """Handle delete progress update."""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)

    def on_delete_finished(self, successful: int, total: int):
        """Handle delete operation completion."""
        self.progress_bar.setVisible(False)

        if successful == total:
            self.status_message.setText(f"Successfully deleted {successful} wallpaper(s)")
        else:
            self.status_message.setText(
                f"Deleted {successful} of {total} wallpaper(s) ({total - successful} failed)"
            )

        # Refresh display
        self.refresh_wallpapers()

        # Emit signal
        for wallpaper_id in getattr(self.delete_worker, 'wallpaper_ids', []):
            self.wallpaper_deleted.emit(wallpaper_id)

    def on_delete_error(self, error_msg: str):
        """Handle delete operation error."""
        self.progress_bar.setVisible(False)
        self.status_message.setText("Delete operation failed")
        QMessageBox.critical(self, "Delete Error", f"Failed to delete wallpapers:\n{error_msg}")

    def on_card_background_requested(self, wallpaper_data: Dict):
        """Handle set background request for wallpaper."""
        wallpaper_path = Path(wallpaper_data.get('path', ''))

        if not wallpaper_path.exists():
            QMessageBox.warning(self, "Error", "Wallpaper file no longer exists.")
            return

        self.status_message.setText("Setting wallpaper as background...")

        try:
            success, message = self.background_setter.set_wallpaper(wallpaper_path)

            if success:
                self.status_message.setText("Background set successfully")
                QMessageBox.information(self, "Success", message)
                self.background_set.emit(str(wallpaper_path))
            else:
                self.status_message.setText("Failed to set background")
                QMessageBox.warning(self, "Error", message)

        except Exception as e:
            logger.error(f"Failed to set background: {e}")
            self.status_message.setText("Failed to set background")
            QMessageBox.critical(self, "Error", f"Failed to set background:\n{str(e)}")

    def on_card_clicked(self, wallpaper_data: Dict):
        """Handle wallpaper card click (for future preview functionality)."""
        # Could implement preview dialog here
        pass

    def on_thumbnail_ready(self, file_path: str, pixmap):
        """Handle thumbnail generation completion."""
        # Thumbnails are handled by individual cards
        pass

    def on_thumbnail_generation_finished(self):
        """Handle thumbnail generation batch completion."""
        self.status_message.setText("Thumbnail generation completed")

    def setup_file_watcher(self):
        """Set up file system watcher for automatic gallery updates."""
        try:
            # Watch all wallpaper directories
            directories_to_watch = []
            for directory in self.image_manager.directories.values():
                if directory.exists():
                    directories_to_watch.append(str(directory))

            if directories_to_watch:
                self.file_watcher.addPaths(directories_to_watch)
                self.file_watcher.directoryChanged.connect(self.on_directory_changed)
                logger.info(f"File system watcher monitoring {len(directories_to_watch)} directories")
            else:
                logger.warning("No wallpaper directories found to watch")

        except Exception as e:
            logger.error(f"Failed to set up file system watcher: {e}")

    def on_directory_changed(self, path: str):
        """Handle directory change detection."""
        logger.debug(f"Directory changed: {path}")

        # Debounce multiple rapid changes (e.g., during bulk downloads)
        self.fs_update_timer.stop()
        self.fs_update_timer.start(2000)  # 2 second delay

    def on_filesystem_update(self):
        """Handle debounced file system update."""
        try:
            logger.info("File system change detected, refreshing gallery")

            # Store current scroll position
            scroll_bar = self.scroll_area.verticalScrollBar()
            scroll_position = scroll_bar.value()

            # Refresh wallpapers
            self.load_wallpapers()

            # Restore scroll position after a short delay
            def restore_scroll():
                scroll_bar.setValue(scroll_position)

            QTimer.singleShot(500, restore_scroll)

            # Update status
            import time
            current_time = time.strftime("%H:%M:%S")
            self.status_message.setText(f"Auto-refreshed at {current_time}")

        except Exception as e:
            logger.error(f"Error during filesystem update: {e}")
            self.status_message.setText("Auto-refresh failed")


# Example usage
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)

    gallery = DownloadedWallpaperGallery()
    gallery.setWindowTitle("Downloaded Wallpapers Gallery")
    gallery.resize(1000, 700)
    gallery.show()

    sys.exit(app.exec())