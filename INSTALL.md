# Installation Guide - Deepin Wallpaper Source Manager

## Quick Installation

### 1. System Requirements
- Deepin Desktop Environment 25+
- Python 3.8+
- Internet connection for downloading wallpapers

### 2. Install Dependencies

#### Option A: Using Virtual Environment (Recommended)
```bash
# Clone or download the project
cd deepin-wallpaper-source-manager

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install core dependencies
pip install Pillow requests click imagehash numpy apify-client praw

# Optional: Install Qt for GUI (large download)
pip install PySide6
```

#### Option B: System Installation
```bash
# Install system dependencies first
sudo apt update
sudo apt install python3-pip python3-venv qt6-base-dev

# Install Python packages
pip install --user -r requirements.txt
```

### 3. Test Installation
```bash
# Activate virtual environment (if using)
source venv/bin/activate

# Test all components
python test_app.py --test all

# Test specific features
python test_app.py --test ai
python test_app.py --demo
```

### 4. Launch Application

#### GUI Mode (requires PySide6)
```bash
source venv/bin/activate
python test_app.py --gui
```

#### Command Line Mode
```bash
source venv/bin/activate
python -c "
from src.core.ai_generators.monica_client import MonicaAIClient
from src.core.downloaders.reddit_client import RedditClient

# Test AI generation
monica = MonicaAIClient()
print('Monica AI templates:', len(monica.get_wallpaper_templates()))

# Test Reddit access
reddit = RedditClient()
print('Reddit connection:', reddit.test_connection())
"
```

## Detailed Setup

### Configure API Keys (Optional)

#### For Enhanced Reddit Access
1. Go to https://www.reddit.com/prefs/apps
2. Create a new application (script type)
3. Note your client ID and secret
4. Set environment variables:
```bash
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
```

#### For Craiyon Unlimited Generation
1. Get Apify token from https://apify.com/
2. Set environment variable:
```bash
export APIFY_TOKEN="your_apify_token"
```

### Configure Deepin Wallpaper Rotation

1. **Open Deepin Control Center**
2. **Go to Personalization → Wallpaper**
3. **Add Wallpaper Folder**:
   - Click the folder icon or "Add Wallpaper"
   - Navigate to `/home/[username]/Pictures/Wallpapers/`
   - Select the folder
4. **Enable Automatic Rotation**:
   - Check "Random playbook"
   - Set your preferred interval (1 hour, 30 minutes, etc.)
5. **Done!** Deepin will now automatically rotate wallpapers

### Troubleshooting

#### Common Issues

**ImportError: No module named 'PIL'**
```bash
pip install Pillow
```

**ImportError: No module named 'PySide6'**
```bash
# PySide6 is large (~500MB), install separately
pip install PySide6
# OR use command-line interface only
```

**Permission errors**
```bash
# Use virtual environment instead of system-wide installation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Qt/GUI not working**
```bash
# Install Qt system dependencies
sudo apt install qt6-base-dev libqt6widgets6
```

**No wallpapers downloading**
- Check internet connection
- Review API credentials
- Check available disk space
- Look at logs with `--verbose` flag

#### Debug Mode
```bash
# Enable verbose logging
python test_app.py --test all --verbose

# Check specific component
python test_app.py --test download --verbose
```

### Performance Tips

1. **Storage Management**: Configure max wallpapers in settings (default: 1000)
2. **Rate Limiting**: Respect API limits to avoid blocking
3. **Quality Filtering**: Enable to avoid low-quality downloads
4. **Virtual Environment**: Use venv to avoid conflicts

### Uninstallation

```bash
# Remove downloaded wallpapers
rm -rf ~/Pictures/Wallpapers/{curated,ai_generated,community,public_domain}

# Remove configuration
rm -rf ~/.config/deepin-wallpaper-source-manager

# Remove virtual environment
rm -rf venv

# Reset Deepin wallpaper settings to default
# (Via Control Center → Personalization → Reset)
```

## Development Setup

### For Contributing

```bash
# Clone repository
git clone [repository-url]
cd deepin-wallpaper-source-manager

# Create development environment
python3 -m venv dev-env
source dev-env/bin/activate

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Code quality checks
flake8 src/
mypy src/
```

### Project Structure
```
deepin-wallpaper-source-manager/
├── src/core/                 # Core functionality
├── src/ui/                   # Qt interface
├── test_app.py              # Test suite & launcher
├── requirements.txt         # Dependencies
├── setup.py                 # Installation script
└── README.md               # Documentation
```

## Next Steps

After installation:

1. **Test the application**: `python test_app.py --test all`
2. **Configure sources**: Launch GUI or edit config files
3. **Generate/download wallpapers**: Use AI generation or curated sources
4. **Configure Deepin**: Point wallpaper rotation to your folder
5. **Enjoy!**: Fresh wallpapers automatically

For questions or issues, refer to the main README.md or create an issue in the project repository.