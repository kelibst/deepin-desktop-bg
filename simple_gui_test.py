#!/usr/bin/env python3
"""
Simple GUI test for Deepin Wallpaper Source Manager.
Tests the Qt interface with better error handling.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set Qt platform plugin (for Linux compatibility)
os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton, QTextEdit, QMessageBox
    from PySide6.QtCore import Qt

    class SimpleWallpaperManager(QMainWindow):
        """Simple test interface for wallpaper manager."""

        def __init__(self):
            super().__init__()
            self.init_ui()

        def init_ui(self):
            self.setWindowTitle("Deepin Wallpaper Source Manager - Test GUI")
            self.setGeometry(100, 100, 600, 400)

            # Create central widget
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)

            # Title
            title = QLabel("🎨 Deepin Wallpaper Source Manager")
            title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            # Status area
            self.status_text = QTextEdit()
            self.status_text.setMaximumHeight(200)
            self.status_text.setReadOnly(True)
            layout.addWidget(self.status_text)

            # Test buttons
            test_config_btn = QPushButton("Test Configuration System")
            test_config_btn.clicked.connect(self.test_config)
            layout.addWidget(test_config_btn)

            test_ai_btn = QPushButton("Test AI Clients")
            test_ai_btn.clicked.connect(self.test_ai_clients)
            layout.addWidget(test_ai_btn)

            test_downloads_btn = QPushButton("Test Download Clients")
            test_downloads_btn.clicked.connect(self.test_download_clients)
            layout.addWidget(test_downloads_btn)

            open_folder_btn = QPushButton("Open Wallpaper Folder")
            open_folder_btn.clicked.connect(self.open_wallpaper_folder)
            layout.addWidget(open_folder_btn)

            # Initial status
            self.log("Deepin Wallpaper Source Manager initialized successfully!")
            self.log("Click buttons above to test different components.")

        def log(self, message):
            """Add message to status area."""
            self.status_text.append(f"• {message}")

        def test_config(self):
            """Test configuration system."""
            try:
                from core.config import get_config

                self.log("Testing configuration system...")
                config = get_config()
                self.log(f"✓ Storage path: {config.storage.base_path}")
                self.log(f"✓ AI default style: {config.ai.default_style}")
                self.log(f"✓ Enabled sources: {len(config.get_enabled_sources())}")
                self.log(f"✓ Prompt templates: {len(config.prompt_templates)}")
                self.log("Configuration system test completed!")

            except Exception as e:
                self.log(f"❌ Configuration test failed: {e}")

        def test_ai_clients(self):
            """Test AI generation clients."""
            try:
                from core.ai_generators.monica_client import MonicaAIClient
                from core.ai_generators.craiyon_client import CraiyonClient

                self.log("Testing AI clients...")

                # Test Monica AI
                monica = MonicaAIClient()
                self.log(f"✓ Monica AI connection: {monica.test_connection()}")
                self.log(f"✓ Monica AI styles: {monica.get_styles()}")
                self.log(f"✓ Monica AI templates: {len(monica.get_wallpaper_templates())}")

                # Test Craiyon
                craiyon = CraiyonClient()
                self.log(f"✓ Craiyon connection: {craiyon.test_connection()}")
                stats = craiyon.get_generation_stats()
                self.log(f"✓ Craiyon remaining generations: {stats['remaining_this_hour']}")

                self.log("AI clients test completed!")

            except Exception as e:
                self.log(f"❌ AI clients test failed: {e}")

        def test_download_clients(self):
            """Test download clients."""
            try:
                from core.downloaders.wallpaperhub_client import WallpaperHubClient
                from core.downloaders.reddit_client import RedditClient

                self.log("Testing download clients...")

                # Test WallpaperHub
                wallpaperhub = WallpaperHubClient()
                self.log(f"✓ WallpaperHub categories: {len(wallpaperhub.get_categories())}")
                self.log(f"✓ WallpaperHub resolutions: {len(wallpaperhub.get_resolutions())}")

                # Test Reddit
                reddit = RedditClient()
                self.log(f"✓ Reddit connection: {reddit.test_connection()}")
                self.log(f"✓ Reddit subreddits: {len(reddit.get_popular_subreddits())}")

                self.log("Download clients test completed!")

            except Exception as e:
                self.log(f"❌ Download clients test failed: {e}")

        def open_wallpaper_folder(self):
            """Open wallpaper folder in file manager."""
            try:
                import subprocess
                from core.config import get_config

                config = get_config()
                wallpaper_path = Path(config.storage.base_path)

                if not wallpaper_path.exists():
                    wallpaper_path.mkdir(parents=True, exist_ok=True)
                    self.log(f"Created wallpaper directory: {wallpaper_path}")

                # Open in file manager
                subprocess.run(["xdg-open", str(wallpaper_path)])
                self.log(f"Opened wallpaper folder: {wallpaper_path}")

            except Exception as e:
                self.log(f"❌ Failed to open wallpaper folder: {e}")
                QMessageBox.warning(self, "Error", f"Could not open folder: {e}")

    def main():
        """Main application entry point."""
        app = QApplication(sys.argv)

        # Set application properties
        app.setApplicationName("Deepin Wallpaper Source Manager")
        app.setApplicationVersion("0.1.0")

        # Create and show main window
        window = SimpleWallpaperManager()
        window.show()

        return app.exec()

    if __name__ == "__main__":
        sys.exit(main())

except ImportError as e:
    print(f"Qt dependencies not available: {e}")
    print("Please install PySide6: pip install PySide6")
    print("Or run tests in command-line mode: python test_app.py --test all")
    sys.exit(1)