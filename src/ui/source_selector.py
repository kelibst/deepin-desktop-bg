"""
Qt-based source selector interface with AI prompt input.

Provides a user-friendly interface for selecting wallpaper sources,
configuring AI generation parameters, and managing downloads.
"""

import logging
import sys
from typing import List, Dict, Optional, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QSpinBox, QTextEdit, QProgressBar, QListWidget,
    QListWidgetItem, QScrollArea, QFrame, QSplitter, QMessageBox,
    QFileDialog, QSlider, QMenuBar
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QFont, QIcon, QAction, QKeySequence

# Import our core modules
sys.path.append(str(Path(__file__).parent.parent))
from core.config import get_config, SourceType, AIStyle, Resolution
from core.image_manager import ImageManager
from core.ai_generators.monica_client import MonicaAIClient
from core.ai_generators.craiyon_client import CraiyonClient
from core.downloaders.wallhaven_client import WallhavenClient
from ui.wallhaven_gallery import WallhavenGallery


logger = logging.getLogger(__name__)


class DownloadWorker(QThread):
    """Worker thread for background wallpaper downloading."""

    progress = Signal(int)  # Progress percentage
    status = Signal(str)    # Status message
    finished = Signal(list) # List of downloaded file paths
    error = Signal(str)     # Error message

    def __init__(self, source_type: str, params: Dict[str, Any]):
        super().__init__()
        self.source_type = source_type
        self.params = params
        self.image_manager = ImageManager()

    def run(self):
        """Run the download/generation process."""
        try:
            downloaded_files = []

            # Note: Wallhaven downloads now handled by gallery
            if self.source_type == "wallhaven":
                # Legacy support - redirect to gallery
                logger.info("Wallhaven downloads now handled by gallery interface")
            elif self.source_type == "monica_ai":
                downloaded_files = self._generate_monica_ai()
            elif self.source_type == "craiyon":
                downloaded_files = self._generate_craiyon()

            self.finished.emit(downloaded_files)

        except Exception as e:
            logger.error(f"Download worker error: {e}")
            self.error.emit(str(e))

    # Legacy Wallhaven download method - now handled by gallery
    # def _download_wallhaven(self) -> List[Path]:
    #     """Download wallpapers from Wallhaven - DEPRECATED: Use gallery instead."""
    #     pass

    def _generate_monica_ai(self) -> List[Path]:
        """Generate wallpapers using Monica AI."""
        self.status.emit("Initializing Monica AI...")
        client = MonicaAIClient()

        prompt = self.params.get('prompt', '')
        style = self.params.get('style', 'photography')
        resolution = self.params.get('resolution', '4K')

        self.status.emit(f"Generating wallpaper: {prompt}")
        self.progress.emit(25)

        file_path = client.generate_wallpaper(prompt, style, resolution)

        generated = []
        if file_path:
            self.progress.emit(75)
            self.status.emit("Storing generated wallpaper...")

            stored_path = self.image_manager.store_wallpaper(
                file_path, 'ai_generated',
                metadata={'source': 'monica_ai', 'prompt': prompt, 'style': style}
            )
            if stored_path:
                generated.append(stored_path)

        self.progress.emit(100)
        return generated

    def _generate_craiyon(self) -> List[Path]:
        """Generate wallpapers using Craiyon."""
        self.status.emit("Initializing Craiyon...")
        client = CraiyonClient()

        prompt = self.params.get('prompt', '')
        style = self.params.get('style', 'art')
        count = self.params.get('count', 2)

        self.status.emit(f"Generating {count} wallpaper(s): {prompt}")
        self.progress.emit(25)

        file_paths = client.generate_wallpaper(prompt, style, count)

        generated = []
        for i, file_path in enumerate(file_paths):
            progress = 25 + int((i + 1) / len(file_paths) * 75)
            self.progress.emit(progress)
            self.status.emit(f"Storing wallpaper {i+1}/{len(file_paths)}...")

            stored_path = self.image_manager.store_wallpaper(
                file_path, 'ai_generated',
                metadata={'source': 'craiyon', 'prompt': prompt, 'style': style}
            )
            if stored_path:
                generated.append(stored_path)

        return generated


class WallpaperSourceSelector(QMainWindow):
    """Main application window for wallpaper source selection."""

    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.image_manager = ImageManager()
        self.download_worker = None

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Deepin Wallpaper Source Manager")
        self.setGeometry(100, 100, 800, 600)

        # Create menu bar
        self.create_menu_bar()

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget for different sources
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Add tabs
        self.create_ai_generation_tab()
        self.create_curated_sources_tab()
        self.create_settings_tab()

        # Add status area
        self.create_status_area(main_layout)

        # Add action buttons
        self.create_action_buttons(main_layout)

    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)  # Ctrl+Q
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        # About action
        about_action = QAction("&About", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # How to Configure Deepin action (moved from button)
        deepin_action = QAction("Configure &Deepin", self)
        deepin_action.setStatusTip("How to configure Deepin wallpaper rotation")
        deepin_action.triggered.connect(self.show_deepin_instructions)
        help_menu.addAction(deepin_action)

    def create_ai_generation_tab(self):
        """Create the AI generation tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # AI Service Selection
        service_group = QGroupBox("AI Service")
        service_layout = QVBoxLayout(service_group)

        self.ai_service_combo = QComboBox()
        self.ai_service_combo.addItems(["Monica AI (4K)", "Craiyon (Unlimited)", "Stable Diffusion (Local)"])
        self.ai_service_combo.currentTextChanged.connect(self.on_ai_service_changed)
        service_layout.addWidget(self.ai_service_combo)

        layout.addWidget(service_group)

        # Prompt Input
        prompt_group = QGroupBox("Wallpaper Prompt")
        prompt_layout = QVBoxLayout(prompt_group)

        self.prompt_input = QTextEdit()
        self.prompt_input.setMaximumHeight(80)
        self.prompt_input.setPlaceholderText("Describe the wallpaper you want to generate...")
        prompt_layout.addWidget(self.prompt_input)

        # Template buttons
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Quick Templates:"))

        templates = [
            ("Nature", "beautiful mountain landscape with lake reflection at sunset"),
            ("Space", "colorful nebula in deep space with stars"),
            ("Abstract", "geometric shapes in gradient colors"),
            ("Minimal", "calm ocean horizon line minimalist")
        ]

        for name, prompt in templates:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, p=prompt: self.prompt_input.setPlainText(p))
            template_layout.addWidget(btn)

        prompt_layout.addLayout(template_layout)
        layout.addWidget(prompt_group)

        # Generation Options
        options_group = QGroupBox("Generation Options")
        options_layout = QHBoxLayout(options_group)

        # Style selection
        style_layout = QVBoxLayout()
        style_layout.addWidget(QLabel("Style:"))
        self.ai_style_combo = QComboBox()
        self.ai_style_combo.addItems(["Photography", "Digital Art", "Abstract", "Minimal"])
        style_layout.addWidget(self.ai_style_combo)
        options_layout.addLayout(style_layout)

        # Resolution selection
        resolution_layout = QVBoxLayout()
        resolution_layout.addWidget(QLabel("Resolution:"))
        self.ai_resolution_combo = QComboBox()
        self.ai_resolution_combo.addItems(["4K", "Ultrawide", "Mobile"])
        resolution_layout.addWidget(self.ai_resolution_combo)
        options_layout.addLayout(resolution_layout)

        # Count for Craiyon
        count_layout = QVBoxLayout()
        count_layout.addWidget(QLabel("Count:"))
        self.ai_count_spin = QSpinBox()
        self.ai_count_spin.setMinimum(1)
        self.ai_count_spin.setMaximum(5)
        self.ai_count_spin.setValue(2)
        count_layout.addWidget(self.ai_count_spin)
        options_layout.addLayout(count_layout)

        layout.addWidget(options_group)

        # Generate button
        self.generate_btn = QPushButton("Generate Wallpaper")
        self.generate_btn.clicked.connect(self.generate_ai_wallpaper)
        layout.addWidget(self.generate_btn)

        layout.addStretch()
        self.tab_widget.addTab(tab, "AI Generation")

    def create_curated_sources_tab(self):
        """Create the curated sources tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Wallhaven Gallery section
        wallhaven_group = QGroupBox("Wallhaven Gallery (High-Quality Wallpapers)")
        wallhaven_layout = QVBoxLayout(wallhaven_group)

        # Description
        description = QLabel("""
        Browse thousands of high-quality wallpapers from Wallhaven.cc
        • Preview thumbnails before downloading
        • Select specific wallpapers you want
        • Set wallpaper as background instantly
        • Search by keywords, categories, and more
        """)
        description.setStyleSheet("color: #666; font-size: 12px; padding: 10px;")
        description.setWordWrap(True)
        wallhaven_layout.addWidget(description)

        # Browse button
        self.browse_wallhaven_btn = QPushButton("🖼️ Browse Wallhaven Gallery")
        self.browse_wallhaven_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.browse_wallhaven_btn.clicked.connect(self.open_wallhaven_gallery)
        wallhaven_layout.addWidget(self.browse_wallhaven_btn)

        # Quick stats (if gallery has been opened)
        self.wallhaven_stats_label = QLabel("")
        self.wallhaven_stats_label.setStyleSheet("color: #666; font-size: 11px; font-style: italic;")
        self.wallhaven_stats_label.setAlignment(Qt.AlignCenter)
        wallhaven_layout.addWidget(self.wallhaven_stats_label)

        layout.addWidget(wallhaven_group)

        # Community sources placeholder
        community_group = QGroupBox("Community Sources (Reddit, Wikimedia, NASA)")
        community_layout = QVBoxLayout(community_group)
        community_layout.addWidget(QLabel("Coming soon in the next update..."))
        layout.addWidget(community_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Curated Sources")

    def create_settings_tab(self):
        """Create the settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Storage settings
        storage_group = QGroupBox("Storage Settings")
        storage_layout = QVBoxLayout(storage_group)

        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Wallpaper Directory:"))
        self.storage_path_input = QLineEdit(self.config.storage.base_path)
        path_layout.addWidget(self.storage_path_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_storage_path)
        path_layout.addWidget(browse_btn)
        storage_layout.addLayout(path_layout)

        max_wallpapers_layout = QHBoxLayout()
        max_wallpapers_layout.addWidget(QLabel("Max Wallpapers:"))
        self.max_wallpapers_spin = QSpinBox()
        self.max_wallpapers_spin.setMinimum(100)
        self.max_wallpapers_spin.setMaximum(10000)
        self.max_wallpapers_spin.setValue(self.config.storage.max_total_wallpapers)
        max_wallpapers_layout.addWidget(self.max_wallpapers_spin)
        storage_layout.addLayout(max_wallpapers_layout)

        layout.addWidget(storage_group)

        # Current statistics
        stats_group = QGroupBox("Current Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_label = QLabel("Loading statistics...")
        stats_layout.addWidget(self.stats_label)

        refresh_stats_btn = QPushButton("Refresh Statistics")
        refresh_stats_btn.clicked.connect(self.refresh_statistics)
        stats_layout.addWidget(refresh_stats_btn)

        layout.addWidget(stats_group)

        # Cleanup
        cleanup_group = QGroupBox("Storage Cleanup")
        cleanup_layout = QVBoxLayout(cleanup_group)

        cleanup_btn = QPushButton("Clean Up Old Wallpapers")
        cleanup_btn.clicked.connect(self.cleanup_old_wallpapers)
        cleanup_layout.addWidget(cleanup_btn)

        layout.addWidget(cleanup_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Settings")

    def create_status_area(self, main_layout):
        """Create the status area with progress bar."""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.StyledPanel)
        status_layout = QVBoxLayout(status_frame)

        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)

        main_layout.addWidget(status_frame)

    def create_action_buttons(self, main_layout):
        """Create action buttons at the bottom."""
        button_layout = QHBoxLayout()

        self.open_wallpaper_folder_btn = QPushButton("📁 Open Wallpaper Folder")
        self.open_wallpaper_folder_btn.clicked.connect(self.open_wallpaper_folder)
        button_layout.addWidget(self.open_wallpaper_folder_btn)

        button_layout.addStretch()

        self.configure_deepin_btn = QPushButton("⚙️ How to Configure Deepin")
        self.configure_deepin_btn.clicked.connect(self.show_deepin_instructions)
        button_layout.addWidget(self.configure_deepin_btn)

        # Exit button
        self.exit_btn = QPushButton("❌ Exit")
        self.exit_btn.setStyleSheet("""
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
            QPushButton:pressed {
                background-color: #c62828;
            }
        """)
        self.exit_btn.clicked.connect(self.close)
        button_layout.addWidget(self.exit_btn)

        main_layout.addLayout(button_layout)

    def on_ai_service_changed(self, service_name):
        """Handle AI service selection change."""
        if "Monica AI" in service_name:
            self.ai_count_spin.setEnabled(False)
            self.ai_count_spin.setValue(1)
        elif "Craiyon" in service_name:
            self.ai_count_spin.setEnabled(True)
        elif "Stable Diffusion" in service_name:
            self.ai_count_spin.setEnabled(True)

    def generate_ai_wallpaper(self):
        """Generate wallpaper using AI service."""
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Warning", "Please enter a prompt for wallpaper generation.")
            return

        service = self.ai_service_combo.currentText()
        style = self.ai_style_combo.currentText().lower().replace(" ", "_")
        resolution = self.ai_resolution_combo.currentText()
        count = self.ai_count_spin.value()

        if "Monica AI" in service:
            source_type = "monica_ai"
        elif "Craiyon" in service:
            source_type = "craiyon"
        else:
            source_type = "stable_diffusion"

        params = {
            'prompt': prompt,
            'style': style,
            'resolution': resolution,
            'count': count
        }

        self.start_download(source_type, params)

    def open_wallhaven_gallery(self):
        """Open Wallhaven gallery in a new window."""
        try:
            # Create gallery window if it doesn't exist
            if not hasattr(self, 'wallhaven_gallery_window') or not self.wallhaven_gallery_window:
                from PySide6.QtWidgets import QDialog

                self.wallhaven_gallery_window = QDialog(self)
                self.wallhaven_gallery_window.setWindowTitle("Wallhaven Gallery - Browse & Download Wallpapers")
                self.wallhaven_gallery_window.setModal(False)  # Allow interaction with main window
                self.wallhaven_gallery_window.resize(1200, 800)

                # Create gallery widget
                self.wallhaven_gallery = WallhavenGallery()

                # Connect gallery signals
                self.wallhaven_gallery.wallpaper_downloaded.connect(self.on_wallpaper_downloaded)
                self.wallhaven_gallery.background_changed.connect(self.on_background_changed)
                self.wallhaven_gallery.status_changed.connect(self.update_wallhaven_stats)

                # Set up dialog layout
                from PySide6.QtWidgets import QVBoxLayout
                dialog_layout = QVBoxLayout(self.wallhaven_gallery_window)
                dialog_layout.setContentsMargins(0, 0, 0, 0)
                dialog_layout.addWidget(self.wallhaven_gallery)

            # Show the gallery window
            self.wallhaven_gallery_window.show()
            self.wallhaven_gallery_window.raise_()
            self.wallhaven_gallery_window.activateWindow()

        except Exception as e:
            logger.error(f"Failed to open Wallhaven gallery: {e}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to open Wallhaven gallery:\n{str(e)}"
            )

    def on_wallpaper_downloaded(self, file_path: str):
        """Handle wallpaper download from gallery."""
        self.refresh_statistics()
        logger.info(f"Wallpaper downloaded from gallery: {file_path}")

    def on_background_changed(self, wallpaper_id: str):
        """Handle background change from gallery."""
        self.update_wallhaven_stats(f"Background set to wallpaper {wallpaper_id}")

    def update_wallhaven_stats(self, message: str):
        """Update Wallhaven stats label."""
        self.wallhaven_stats_label.setText(message)

    def start_download(self, source_type: str, params: Dict[str, Any]):
        """Start download/generation in background thread."""
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.warning(self, "Warning", "Another download is already in progress.")
            return

        self.download_worker = DownloadWorker(source_type, params)
        self.download_worker.progress.connect(self.progress_bar.setValue)
        self.download_worker.status.connect(self.status_label.setText)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.error.connect(self.on_download_error)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.generate_btn.setEnabled(False)
        self.browse_wallhaven_btn.setEnabled(False)

        self.download_worker.start()

    def on_download_finished(self, downloaded_files: List[Path]):
        """Handle download completion."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.browse_wallhaven_btn.setEnabled(True)

        count = len(downloaded_files)
        if count > 0:
            self.status_label.setText(f"Successfully downloaded {count} wallpaper(s)")
            QMessageBox.information(
                self, "Success",
                f"Downloaded {count} wallpaper(s) to your wallpaper folder.\\n\\n"
                "Configure Deepin to use the wallpaper folder for automatic rotation."
            )
        else:
            self.status_label.setText("No wallpapers were downloaded")
            QMessageBox.warning(self, "Warning", "No wallpapers were downloaded. Please check your settings.")

        self.refresh_statistics()

    def on_download_error(self, error_message: str):
        """Handle download error."""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.browse_wallhaven_btn.setEnabled(True)
        self.status_label.setText("Download failed")

        QMessageBox.critical(self, "Error", f"Download failed: {error_message}")

    def browse_storage_path(self):
        """Browse for wallpaper storage directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Wallpaper Directory",
            self.storage_path_input.text()
        )
        if path:
            self.storage_path_input.setText(path)

    def refresh_statistics(self):
        """Refresh storage statistics."""
        try:
            stats = self.image_manager.get_storage_stats()
            stats_text = f"""
Total Files: {stats['total_files']}
Total Size: {stats['total_size_mb']} MB

By Source:
• Curated: {stats['directories']['curated']}
• AI Generated: {stats['directories']['ai_generated']}
• Community: {stats['directories']['community']}
• Public Domain: {stats['directories']['public_domain']}
            """.strip()
            self.stats_label.setText(stats_text)
        except Exception as e:
            self.stats_label.setText(f"Error loading statistics: {e}")

    def cleanup_old_wallpapers(self):
        """Clean up old wallpapers."""
        try:
            max_wallpapers = self.max_wallpapers_spin.value()
            removed_count = self.image_manager.cleanup_old_wallpapers(max_wallpapers)

            if removed_count > 0:
                QMessageBox.information(
                    self, "Cleanup Complete",
                    f"Removed {removed_count} old wallpaper(s)."
                )
            else:
                QMessageBox.information(
                    self, "Cleanup Complete",
                    "No cleanup needed. Wallpaper count is within limits."
                )

            self.refresh_statistics()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cleanup failed: {e}")

    def open_wallpaper_folder(self):
        """Open the wallpaper folder in file manager."""
        import subprocess
        import platform

        path = Path(self.storage_path_input.text())
        try:
            if platform.system() == "Linux":
                subprocess.run(["xdg-open", str(path)])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(path)])
            elif platform.system() == "Windows":
                subprocess.run(["explorer", str(path)])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open folder: {e}")

    def show_deepin_instructions(self):
        """Show instructions for configuring Deepin wallpaper rotation."""
        instructions = """
How to Configure Deepin for Automatic Wallpaper Rotation:

1. Open Deepin Control Center
2. Go to Personalization → Wallpaper
3. Click "Add Wallpaper" or folder icon
4. Navigate to your wallpaper folder:
   {wallpaper_path}
5. Select the folder containing your downloaded wallpapers
6. Enable "Random playback" for automatic rotation
7. Set your preferred time interval

Your wallpapers will now rotate automatically using Deepin's built-in functionality!
        """.format(wallpaper_path=self.storage_path_input.text())

        QMessageBox.information(self, "Deepin Configuration", instructions)

    def show_about(self):
        """Show about dialog."""
        about_text = """
<h2>Deepin Wallpaper Source Manager</h2>
<p><b>Version:</b> 0.1.0</p>
<p><b>Description:</b> A lightweight wallpaper manager that downloads and organizes wallpapers for Deepin's automatic rotation.</p>

<h3>Features:</h3>
<ul>
<li>🤖 AI Wallpaper Generation (Monica AI, Craiyon)</li>
<li>🖼️ High-quality wallpapers from Wallhaven.cc</li>
<li>📁 Organized storage in ~/Pictures/Wallpapers/</li>
<li>🔄 Automatic duplicate detection</li>
<li>⚙️ Easy Deepin integration</li>
</ul>

<h3>Keyboard Shortcuts:</h3>
<ul>
<li><b>Ctrl+Q:</b> Exit application</li>
</ul>

<p><i>Developed for the Deepin community</i></p>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("About")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def load_settings(self):
        """Load settings from configuration."""
        self.refresh_statistics()

    def save_settings(self):
        """Save current settings to configuration."""
        self.config.storage.base_path = self.storage_path_input.text()
        self.config.storage.max_total_wallpapers = self.max_wallpapers_spin.value()
        self.config.save_config()

    def closeEvent(self, event):
        """Handle application close event."""
        self.save_settings()

        # Check for running downloads
        if self.download_worker and self.download_worker.isRunning():
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "A download is in progress. Do you want to exit anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return

        # Close wallhaven gallery window if open
        if hasattr(self, 'wallhaven_gallery_window') and self.wallhaven_gallery_window:
            self.wallhaven_gallery_window.close()

        # Cleanup workers
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.terminate()
            self.download_worker.wait()

        event.accept()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Deepin Wallpaper Source Manager")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("Deepin Community")

    # Create and show main window
    window = WallpaperSourceSelector()
    window.show()

    return app.exec()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())