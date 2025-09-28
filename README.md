# Deepin Wallpaper Source Manager

A lightweight wallpaper downloader with AI generation capabilities that integrates with Deepin's existing wallpaper rotation system.

## Features

### 🎨 AI Wallpaper Generation
- **Monica AI**: 4K wallpaper generation with wallpaper-focused prompts
- **Craiyon**: Unlimited free AI generation with commercial use rights
- **Stable Diffusion**: Optional local generation for advanced users
- Pre-made prompt templates for common themes

### 📸 Curated Sources
- **WallpaperHub.app**: Access to 5,498 high-quality curated wallpapers
- **Reddit Communities**: r/wallpapers, r/EarthPorn, r/SpacePorn, and more
- **Public Domain**: Wikimedia Commons, NASA image galleries

### 🛠️ Smart Management
- **Organized Storage**: Automatic categorization (curated/ai_generated/community/public_domain)
- **Quality Filtering**: Resolution, aspect ratio, and content validation
- **Duplicate Detection**: Perceptual hashing to avoid duplicate downloads
- **Intelligent Cleanup**: Configurable storage limits and automatic cleanup

### 🖥️ Deepin Integration
- Stores wallpapers in `~/Pictures/Wallpapers/` for easy Deepin configuration
- Leverages Deepin's existing excellent wallpaper rotation system
- No direct wallpaper setting - respects user control

## Installation

### Prerequisites
- Python 3.8+
- Qt6 development libraries
- Deepin Desktop Environment

### Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies (Debian/Ubuntu)
sudo apt install qt6-base-dev python3-pil

# Optional: For advanced AI features
pip install torch diffusers transformers
```

### Optional API Keys
- **Reddit API**: For higher rate limits and search functionality
- **Apify Token**: For Craiyon unlimited generation
- **Monica AI**: For premium features (free tier available)

## Quick Start

### 1. Launch the Application
```bash
#activiate the environment
source venv/bin/activate

# Run the Qt GUI
python test_app.py --gui

# Or test all components
python test_app.py --test all
```

### 2. Generate/Download Wallpapers
- **AI Generation Tab**: Enter prompts, select styles, generate wallpapers
- **Curated Sources Tab**: Download from WallpaperHub or Reddit
- **Settings Tab**: Configure storage and cleanup preferences

### 3. Configure Deepin Wallpaper Rotation
1. Open Deepin Control Center
2. Go to Personalization → Wallpaper
3. Click "Add Wallpaper" or folder icon
4. Navigate to `~/Pictures/Wallpapers/`
5. Select the folder containing your wallpapers
6. Enable "Random playback" for automatic rotation
7. Set your preferred time interval

## Usage Examples

### AI Generation
```python
from src.core.ai_generators.monica_client import MonicaAIClient

client = MonicaAIClient()
wallpaper_path = client.generate_wallpaper(
    prompt="beautiful mountain landscape at sunset",
    style="photography",
    resolution="4K"
)
```

### Download from WallpaperHub
```python
from src.core.downloaders.wallpaperhub_client import WallpaperHubClient

client = WallpaperHubClient()
wallpapers = client.get_wallpapers(category='nature', limit=5)
for wallpaper in wallpapers:
    client.download_wallpaper(wallpaper, resolution='4K')
```

### Quality Filtering
```python
from src.core.quality_filter import QualityFilter

quality_filter = QualityFilter()
result = quality_filter.validate_wallpaper(Path("image.jpg"))
print(f"Valid: {result['valid']}")
print(f"Recommendations: {result['recommendations']}")
```

## Project Structure

```
deepin-wallpaper-source-manager/
├── src/
│   ├── core/
│   │   ├── downloaders/           # Traditional downloaders
│   │   │   ├── wallpaperhub_client.py
│   │   │   ├── reddit_client.py
│   │   │   ├── wikimedia_client.py
│   │   │   └── nasa_client.py
│   │   ├── ai_generators/         # AI generators
│   │   │   ├── monica_client.py
│   │   │   ├── craiyon_client.py
│   │   │   └── stablediff_client.py
│   │   ├── image_manager.py       # Storage management
│   │   ├── config.py             # Configuration system
│   │   └── quality_filter.py     # Quality validation
│   ├── ui/
│   │   └── source_selector.py    # Qt interface
│   └── daemon/
│       └── downloader_service.py # Background service
├── test_app.py                   # Test suite and launcher
├── requirements.txt              # Dependencies
└── README.md                     # This file
```

## Configuration

Configuration is stored in `~/.config/deepin-wallpaper-source-manager/config.json`

### Key Settings
- **Storage Path**: Where wallpapers are stored (default: `~/Pictures/Wallpapers/`)
- **Max Wallpapers**: Maximum number of wallpapers to keep
- **AI Settings**: Default styles, rate limits, content filtering
- **Source Priorities**: Enable/disable sources and set priorities

### AI Prompt Templates
The application includes pre-made templates for common wallpaper themes:
- Nature landscapes
- Space/cosmic scenes
- Abstract designs
- Minimal compositions
- Urban photography

## API Rate Limits

### Free Tier Limits
- **Monica AI**: Free tier with daily limits
- **Craiyon**: 10 generations/hour (conservative limit)
- **Reddit**: 60 requests/minute (with credentials)
- **WallpaperHub**: No explicit limits (respectful usage)

### Avoiding Rate Limits
- Enable intelligent caching
- Use batch operations
- Configure rate limiting in settings
- Consider API keys for higher limits

## Development

### Running Tests
```bash
# Test all components
python test_app.py --test all

# Test specific component
python test_app.py --test ai

# Verbose logging
python test_app.py --test all --verbose

# Demo download functionality
python test_app.py --demo
```

### Adding New Sources
1. Create client in appropriate directory (`downloaders/` or `ai_generators/`)
2. Implement required methods (`get_wallpapers`, `download_wallpaper`)
3. Add to configuration system in `config.py`
4. Update UI in `source_selector.py`

## Legal Compliance

### Source Licensing
- **WallpaperHub**: "For wallpaper use only" - explicit permission
- **Monica AI**: Free tier usage allowed
- **Craiyon**: Commercial use allowed with attribution
- **Reddit**: Community content, respects original creators
- **Public Domain**: Wikimedia Commons, NASA - no restrictions

### Usage Guidelines
- All sources explicitly allow wallpaper applications
- Attribution provided where required
- Rate limiting respects service terms
- No redistribution of downloaded content

## Troubleshooting

### Common Issues

**GUI won't start**
- Install PySide6: `pip install PySide6`
- Check Qt6 system libraries

**API errors**
- Check internet connection
- Verify API credentials
- Review rate limiting settings

**Download failures**
- Check storage permissions
- Verify disk space
- Review quality filter settings

**Deepin integration**
- Ensure wallpapers are in correct folder
- Check Deepin wallpaper settings
- Verify folder permissions

### Debug Mode
```bash
# Enable verbose logging
python test_app.py --verbose

# Check specific component
python test_app.py --test manager --verbose
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Acknowledgments

- **WallpaperHub.app**: For providing curated wallpaper collection
- **Monica AI**: For 4K wallpaper generation capabilities
- **Craiyon**: For unlimited free AI generation
- **Reddit Communities**: For community-sourced wallpapers
- **Deepin Team**: For excellent desktop environment

---

**Note**: This application is designed to work with Deepin's existing wallpaper management system. It downloads wallpapers to a local folder and relies on Deepin's built-in rotation features for the best user experience.