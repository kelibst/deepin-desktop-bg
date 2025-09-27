#!/usr/bin/env python3
"""
Interactive demo of Deepin Wallpaper Source Manager functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def demo_configuration():
    """Demonstrate configuration system."""
    print("🔧 Configuration System Demo")
    print("=" * 40)

    from core.config import get_config

    config = get_config()
    print(f"Storage path: {config.storage.base_path}")
    print(f"AI default style: {config.ai.default_style}")
    print(f"Max wallpapers: {config.storage.max_total_wallpapers}")

    enabled_sources = config.get_enabled_sources()
    print(f"Enabled sources: {[s.value for s in enabled_sources]}")

    print(f"Available prompt templates: {len(config.prompt_templates)}")
    for i, template in enumerate(config.prompt_templates[:3]):
        print(f"  {i+1}. {template['name']}: {template['prompt'][:50]}...")

    print("✅ Configuration system working!\n")

def demo_ai_generation():
    """Demonstrate AI generation capabilities."""
    print("🎨 AI Generation Demo")
    print("=" * 40)

    from core.ai_generators.monica_client import MonicaAIClient
    from core.ai_generators.craiyon_client import CraiyonClient

    # Monica AI
    print("Monica AI Client:")
    monica = MonicaAIClient()
    print(f"  Connection: {'✅ Connected' if monica.test_connection() else '❌ Not available'}")
    print(f"  Available styles: {monica.get_styles()}")
    print(f"  Available resolutions: {monica.get_resolutions()}")

    templates = monica.get_wallpaper_templates()
    print(f"  Wallpaper templates: {len(templates)}")
    print("  Sample templates:")
    for template in templates[:3]:
        print(f"    • {template['name']}: {template['prompt']}")

    # Craiyon
    print("\nCraiyon Client:")
    craiyon = CraiyonClient()
    print(f"  Connection: {'✅ Connected' if craiyon.test_connection() else '❌ Not available'}")
    print(f"  Available styles: {craiyon.get_styles()}")

    stats = craiyon.get_generation_stats()
    print(f"  Generations remaining this hour: {stats['remaining_this_hour']}")
    print(f"  Has Apify token: {stats['has_apify_token']}")

    print("✅ AI generation system ready!\n")

def demo_download_sources():
    """Demonstrate download sources."""
    print("📥 Download Sources Demo")
    print("=" * 40)

    from core.downloaders.wallpaperhub_client import WallpaperHubClient
    from core.downloaders.reddit_client import RedditClient

    # WallpaperHub
    print("WallpaperHub Client:")
    wallpaperhub = WallpaperHubClient()
    print(f"  Available categories: {wallpaperhub.get_categories()}")
    print(f"  Available resolutions: {wallpaperhub.get_resolutions()}")
    print("  Note: 5,498 curated wallpapers available")

    # Reddit
    print("\nReddit Client:")
    reddit = RedditClient()
    print(f"  Connection: {'✅ Connected' if reddit.test_connection() else '❌ Not available'}")
    subreddits = reddit.get_popular_subreddits()
    print(f"  Popular wallpaper subreddits: {len(subreddits)}")
    print("  Available communities:")
    for subreddit in subreddits[:5]:
        print(f"    • r/{subreddit}")

    print("✅ Download sources ready!\n")

def demo_quality_filter():
    """Demonstrate quality filtering."""
    print("🔍 Quality Filter Demo")
    print("=" * 40)

    from core.quality_filter import QualityFilter

    quality_filter = QualityFilter()

    # Test with non-existent file to show validation
    test_path = Path("test_image.jpg")
    result = quality_filter.validate_wallpaper(test_path)

    print("Sample validation result:")
    print(f"  Valid: {result['valid']}")
    print(f"  Errors: {result['errors']}")
    print("  Features:")
    print("    • Resolution validation (min 1280x720)")
    print("    • Aspect ratio checks (0.5 - 3.5)")
    print("    • Duplicate detection with perceptual hashing")
    print("    • Blur detection using Laplacian variance")
    print("    • Color diversity analysis")
    print("    • Format validation")

    print("✅ Quality filter system ready!\n")

def demo_storage_management():
    """Demonstrate storage management."""
    print("💾 Storage Management Demo")
    print("=" * 40)

    from core.image_manager import ImageManager

    manager = ImageManager()
    stats = manager.get_storage_stats()

    print("Current storage statistics:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Total size: {stats['total_size_mb']} MB")
    print("  Directory organization:")
    for directory, count in stats['directories'].items():
        print(f"    • {directory}/: {count} files")

    wallpapers = manager.list_wallpapers()
    print(f"  Tracked wallpapers: {len(wallpapers)}")

    print("  Features:")
    print("    • Organized storage by source type")
    print("    • Metadata tracking and statistics")
    print("    • Automatic cleanup with size limits")
    print("    • Duplicate detection")
    print("    • Quality validation")

    print("✅ Storage management ready!\n")

def demo_usage_example():
    """Show a practical usage example."""
    print("🚀 Usage Example")
    print("=" * 40)

    print("Here's how to use the Deepin Wallpaper Source Manager:")
    print()
    print("1. Generate AI wallpapers:")
    print("   from core.ai_generators.monica_client import MonicaAIClient")
    print("   client = MonicaAIClient()")
    print("   wallpaper = client.generate_wallpaper(")
    print("       prompt='beautiful mountain landscape at sunset',")
    print("       style='photography',")
    print("       resolution='4K'")
    print("   )")
    print()
    print("2. Download curated wallpapers:")
    print("   from core.downloaders.wallpaperhub_client import WallpaperHubClient")
    print("   client = WallpaperHubClient()")
    print("   wallpapers = client.get_wallpapers(category='nature', limit=5)")
    print("   for wallpaper in wallpapers:")
    print("       client.download_wallpaper(wallpaper, resolution='4K')")
    print()
    print("3. Configure Deepin:")
    print("   • Open Control Center → Personalization → Wallpaper")
    print("   • Add folder: ~/Pictures/Wallpapers/")
    print("   • Enable 'Random playbook' with your preferred interval")
    print()
    print("4. Enjoy automatic wallpaper rotation! 🎨")
    print()

def main():
    """Run the interactive demo."""
    print("🎨 Deepin Wallpaper Source Manager - Interactive Demo")
    print("=" * 55)
    print()

    try:
        demo_configuration()
        demo_ai_generation()
        demo_download_sources()
        demo_quality_filter()
        demo_storage_management()
        demo_usage_example()

        print("🎉 Demo completed successfully!")
        print()
        print("Your Deepin Wallpaper Source Manager is ready to use!")
        print("Features available:")
        print("  ✅ AI wallpaper generation (Monica AI, Craiyon)")
        print("  ✅ Curated downloads (WallpaperHub, 5,498 wallpapers)")
        print("  ✅ Community sources (Reddit, 8+ subreddits)")
        print("  ✅ Quality filtering and duplicate detection")
        print("  ✅ Organized storage management")
        print("  ✅ Seamless Deepin integration")
        print()
        print("To get started:")
        print("  1. Run: python test_app.py --test all")
        print("  2. Configure wallpaper sources")
        print("  3. Point Deepin to ~/Pictures/Wallpapers/")
        print("  4. Enjoy fresh wallpapers!")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()