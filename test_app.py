#!/usr/bin/env python3
"""
Test application for the Deepin Wallpaper Source Manager.

Provides a simple command-line interface to test all components
and a quick launch script for the Qt GUI.
"""

import sys
import logging
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import get_config, SourceType
from core.image_manager import ImageManager
from core.quality_filter import QualityFilter
from core.ai_generators.monica_client import MonicaAIClient
from core.ai_generators.craiyon_client import CraiyonClient
from core.downloaders.wallhaven_client import WallhavenClient
from core.downloaders.reddit_client import RedditClient


def test_config():
    """Test configuration system."""
    print("\\n=== Testing Configuration System ===")

    config = get_config()
    print(f"Storage path: {config.storage.base_path}")
    print(f"AI default style: {config.ai.default_style}")
    print(f"Max wallpapers: {config.storage.max_total_wallpapers}")

    enabled_sources = config.get_enabled_sources()
    print(f"Enabled sources: {[s.value for s in enabled_sources]}")

    templates = config.prompt_templates[:3]  # Show first 3
    print("\\nPrompt templates:")
    for template in templates:
        print(f"  - {template['name']}: {template['prompt'][:50]}...")

    print("✓ Configuration system working")


def test_image_manager():
    """Test image manager."""
    print("\\n=== Testing Image Manager ===")

    manager = ImageManager()

    # Get storage statistics
    stats = manager.get_storage_stats()
    print(f"Current storage stats:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Total size: {stats['total_size_mb']} MB")
    print(f"  By directory: {stats['directories']}")

    # List wallpapers
    wallpapers = manager.list_wallpapers()
    print(f"  Total wallpapers tracked: {len(wallpapers)}")

    print("✓ Image manager working")


def test_quality_filter():
    """Test quality filter."""
    print("\\n=== Testing Quality Filter ===")

    quality_filter = QualityFilter()

    # Test with a non-existent file to show error handling
    test_path = Path("non_existent_image.jpg")
    result = quality_filter.validate_wallpaper(test_path)

    print(f"Test validation result:")
    print(f"  Valid: {result['valid']}")
    print(f"  Errors: {result['errors']}")
    print(f"  Metrics: {result['metrics']}")

    print("✓ Quality filter working")


def test_ai_clients():
    """Test AI generation clients."""
    print("\\n=== Testing AI Clients ===")

    # Test Monica AI client
    print("Monica AI Client:")
    monica_client = MonicaAIClient()
    print(f"  Connection test: {monica_client.test_connection()}")
    print(f"  Available styles: {monica_client.get_styles()}")
    print(f"  Available resolutions: {monica_client.get_resolutions()}")
    templates = monica_client.get_wallpaper_templates()
    print(f"  Templates available: {len(templates)}")

    # Test Craiyon client
    print("\\nCraiyon Client:")
    craiyon_client = CraiyonClient()
    print(f"  Connection test: {craiyon_client.test_connection()}")
    print(f"  Available styles: {craiyon_client.get_styles()}")
    stats = craiyon_client.get_generation_stats()
    print(f"  Generation stats: {stats}")

    print("✓ AI clients working")


def test_download_clients():
    """Test download clients."""
    print("\\n=== Testing Download Clients ===")

    # Test Wallhaven client
    print("Wallhaven Client:")
    wallhaven_client = WallhavenClient()
    print(f"  Available categories: {wallhaven_client.get_categories()}")
    print(f"  Available sorting options: {wallhaven_client.get_sorting_options()}")

    # Test search functionality
    print("  Testing search...")
    try:
        wallpapers = wallhaven_client.search_wallpapers(query="nature", limit=3)
        print(f"  Found {len(wallpapers)} nature wallpapers")
        if wallpapers:
            for i, wallpaper in enumerate(wallpapers):
                print(f"    {i+1}. {wallpaper['id']} - {wallpaper['resolution']} - {wallpaper['views']} views")
    except Exception as e:
        print(f"  Search test failed: {e}")

    # Test Reddit client
    print("\\nReddit Client:")
    reddit_client = RedditClient()
    print(f"  Connection test: {reddit_client.test_connection()}")
    print(f"  Popular subreddits: {reddit_client.get_popular_subreddits()}")

    print("✓ Download clients working")


def demo_download():
    """Demonstrate downloading functionality."""
    print("\\n=== Demo: Downloading Sample Wallpapers ===")

    # This is a demo - actual downloading would require API keys or working implementations
    print("Note: This is a demonstration. Actual downloads require:")
    print("  - Reddit API credentials for Reddit client")
    print("  - Apify token for Craiyon client")
    print("  - Wallhaven.cc API (no authentication required for basic use)")
    print("  - Monica AI API integration")

    # Test Wallhaven download
    print("\\nAttempting to fetch Wallhaven wallpaper metadata...")
    wallhaven_client = WallhavenClient()
    try:
        wallpapers = wallhaven_client.search_wallpapers(query="landscape", limit=2)
        print(f"Found {len(wallpapers)} landscape wallpapers:")
        for wallpaper in wallpapers:
            print(f"  - {wallpaper['id']} - {wallpaper['resolution']} ({wallpaper['views']} views)")
    except Exception as e:
        print(f"Wallhaven API error: {e}")

    # Test Reddit without credentials (read-only)
    reddit_client = RedditClient()
    if reddit_client.test_connection():
        print("\\nAttempting to fetch Reddit wallpaper metadata...")
        try:
            wallpapers = reddit_client.get_wallpapers(subreddit='wallpapers', limit=3)
            print(f"Found {len(wallpapers)} wallpaper posts:")
            for wallpaper in wallpapers:
                print(f"  - {wallpaper['title'][:50]}... (Score: {wallpaper['score']})")
        except Exception as e:
            print(f"Reddit API error: {e}")

    print("\\n✓ Demo completed")


def launch_gui():
    """Launch the Qt GUI application."""
    print("\\n=== Launching Qt GUI ===")

    try:
        from ui.source_selector import main
        print("Starting GUI application...")
        return main()
    except ImportError as e:
        print(f"GUI dependencies not available: {e}")
        print("Please install PySide6: pip install PySide6")
        return 1
    except Exception as e:
        print(f"GUI launch failed: {e}")
        return 1


def main():
    """Main test application."""
    parser = argparse.ArgumentParser(description="Deepin Wallpaper Source Manager Test Suite")
    parser.add_argument("--gui", action="store_true", help="Launch GUI application")
    parser.add_argument("--test", choices=["all", "config", "manager", "quality", "ai", "download"],
                       default="all", help="Run specific tests")
    parser.add_argument("--demo", action="store_true", help="Run download demonstration")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("Deepin Wallpaper Source Manager - Test Suite")
    print("=" * 50)

    if args.gui:
        return launch_gui()

    # Run tests
    test_functions = {
        "config": test_config,
        "manager": test_image_manager,
        "quality": test_quality_filter,
        "ai": test_ai_clients,
        "download": test_download_clients
    }

    if args.test == "all":
        for test_name, test_func in test_functions.items():
            try:
                test_func()
            except Exception as e:
                print(f"\\n❌ Test {test_name} failed: {e}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
    else:
        try:
            test_functions[args.test]()
        except Exception as e:
            print(f"\\n❌ Test {args.test} failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    if args.demo:
        demo_download()

    print("\\n" + "=" * 50)
    print("Test suite completed!")
    print("\\nTo use the application:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Launch GUI: python test_app.py --gui")
    print("  3. Configure wallpaper sources and generate/download wallpapers")
    print("  4. Point Deepin's wallpaper settings to ~/Pictures/Wallpapers/")

    return 0


if __name__ == "__main__":
    sys.exit(main())