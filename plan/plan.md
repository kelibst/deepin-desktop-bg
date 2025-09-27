# Deepin Wallpaper Source Manager Project Plan

## Project Overview
Lightweight image source manager for Deepin 25 that downloads wallpapers to a local folder, leveraging Deepin's existing automatic wallpaper rotation capabilities.

## Strategy Change
After research, we discovered that:
1. **Deepin already has excellent wallpaper management** - automatic rotation, folder selection, intervals
2. **Major APIs prohibit wallpaper apps** - Unsplash, Pexels, Pixabay all restrict wallpaper applications
3. **Simpler approach works better** - Download to folder, let Deepin handle the rest

## Technical Architecture

### Core Technology Stack
- **Language**: Python 3.8+
- **UI Framework**: Qt/PySide6 (minimal interface)
- **Image Sources**:
  - **Curated**: WallpaperHub.app (5,498 high-quality wallpapers)
  - **Community**: Reddit (r/wallpapers, r/EarthPorn)
  - **Public Domain**: Wikimedia Commons, NASA
  - **AI Generated**: Monica AI (4K), Craiyon (unlimited free), Stable Diffusion
- **Storage**: `~/Pictures/Wallpapers/` (user configures Deepin to use this folder)

### System Integration Points
- **No direct wallpaper setting** - Users configure Deepin's settings manually
- **Storage Location**: `~/Pictures/Wallpapers/`
- **Deepin Integration**: Users point Control Center → Personalization to our download folder

## Development Phases (Revised Timeline: 2-3 weeks)

### Phase 1: Core Functionality (Week 1)
**Goal**: Working downloaders with basic UI

#### Days 1-2: Foundation & Primary Sources
- [ ] Project structure setup (simplified)
- [ ] Python environment and dependencies
- [ ] WallpaperHub.app client (5,498 curated wallpapers)
- [ ] Monica AI wallpaper generator (4K output)
- [ ] Basic image download and storage system

#### Days 3-4: AI Generation & Free Sources
- [ ] Craiyon API integration (unlimited free generation)
- [ ] Basic prompt input interface for AI generation
- [ ] Reddit API client (r/wallpapers, r/EarthPorn)
- [ ] Image quality filtering and duplicate detection

#### Days 5-7: Interface & Additional Sources
- [ ] Qt source selection interface with AI prompts
- [ ] Stable Diffusion integration (optional local generation)
- [ ] Wikimedia Commons and NASA clients
- [ ] Preview system for generated/downloaded images

### Phase 2: Polish & Integration (Week 2)
**Goal**: Complete user experience

#### Days 1-3: Enhanced AI Features
- [ ] Advanced prompt templates for AI generation
- [ ] Style selection (photography, digital art, abstract)
- [ ] Batch AI generation with queue system
- [ ] Resolution preferences for AI output (4K, ultrawide, mobile)
- [ ] Content filtering for appropriate wallpapers

#### Days 4-5: Traditional Sources & Management
- [ ] Complete Reddit, Wikimedia, NASA integration
- [ ] Advanced category filtering (nature, space, tech, minimal)
- [ ] Storage management (cleanup, size limits, organization)
- [ ] Download preferences and scheduling

#### Days 6-7: Background Service
- [ ] Background downloader daemon with AI generation queue
- [ ] Configuration persistence for all sources
- [ ] Rate limiting for AI APIs and error handling
- [ ] Progress indicators and status updates

### Phase 3: Distribution (Week 3)
**Goal**: Package and document

- [ ] Debian package creation
- [ ] User documentation (how to configure Deepin)
- [ ] Installation/uninstallation scripts
- [ ] Testing and bug fixes

## Project Structure (Simplified)

```
deepin-wallpaper-source-manager/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── downloaders/
│   │   │   ├── __init__.py
│   │   │   ├── wallpaperhub_client.py   # 5,498 curated wallpapers
│   │   │   ├── reddit_client.py         # r/wallpapers, r/EarthPorn
│   │   │   ├── wikimedia_client.py      # Public domain images
│   │   │   └── nasa_client.py           # NASA image gallery
│   │   ├── ai_generators/
│   │   │   ├── __init__.py
│   │   │   ├── monica_client.py         # 4K AI wallpapers
│   │   │   ├── craiyon_client.py        # Free unlimited generation
│   │   │   └── stablediff_client.py     # Open source generation
│   │   ├── image_manager.py             # Download & organize images
│   │   └── config.py                    # Source preferences & AI prompts
│   ├── ui/
│   │   ├── __init__.py
│   │   └── source_selector.py        # Qt dialog for source selection
│   └── daemon/
│       ├── __init__.py
│       └── downloader_service.py     # Background downloading
├── config/
│   └── systemd/
│       └── deepin-wallpaper-source-manager.service
├── debian/
│   ├── control
│   ├── install
│   └── postinst
├── docs/
│   └── USER_GUIDE.md
├── tests/
│   ├── test_downloaders.py
│   └── test_ui.py
├── plan/
│   ├── ACTIVITIES.md              # Development tracking
│   └── plan.md                    # This file
├── requirements.txt
├── setup.py
├── CLAUDE.md                      # AI assistant guidelines
└── README.md
```

## Dependencies (Simplified)

### Python Packages
```
PySide6>=6.4.0          # Qt bindings for simple UI
requests>=2.28.0        # HTTP client for APIs
Pillow>=9.0.0           # Image processing and validation
praw>=7.6.0             # Reddit API wrapper
click>=8.0.0            # CLI interface (optional)

# AI Generation Dependencies
openai>=1.0.0           # For Monica AI integration (if needed)
apify-client>=1.0.0     # For Craiyon API access
diffusers>=0.21.0       # For Stable Diffusion (optional)
torch>=2.0.0            # For local Stable Diffusion (optional)
```

### System Dependencies
```
qt6-base-dev           # Qt development
python3-pil            # Pillow dependencies
```

## Key Milestones (Revised)

### Milestone 1: Core Downloads + AI Generation (End Week 1)
- WallpaperHub.app integration (5,498 wallpapers)
- Monica AI + Craiyon AI wallpaper generation working
- Reddit downloader for community content
- Basic storage in `~/Pictures/Wallpapers/`
- Qt interface with AI prompt input

### Milestone 2: Enhanced Features (End Week 2)
- Stable Diffusion integration (local generation)
- Complete traditional sources (Wikimedia, NASA)
- Advanced AI features (templates, styles, batch generation)
- Background service with AI generation queue
- Storage management and cleanup

### Milestone 3: Distribution Ready (End Week 3)
- Debian package created
- User documentation (Deepin configuration + AI usage guide)
- Rate limiting and error handling polished
- Installation tested

## Risk Mitigation (Updated)

### Technical Risks
- **API Rate Limits**: Use free APIs (Reddit, Wikimedia) with generous limits
- **Legal Issues**: Avoid prohibited APIs, use public domain sources
- **Storage Management**: Implement size limits and cleanup

### Timeline Risks
- **Scope Creep**: Focus on simple download manager only
- **Deepin Changes**: Minimal integration reduces compatibility risks
- **Dependencies**: Stick to common Python packages

## Success Criteria (Revised)

### Functional Requirements
- [ ] Downloads wallpapers from WallpaperHub.app (5,498 curated)
- [ ] Generates AI wallpapers via Monica AI, Craiyon, Stable Diffusion
- [ ] Downloads community content from Reddit, Wikimedia, NASA
- [ ] Stores all images in `~/Pictures/Wallpapers/`
- [ ] Provides Qt interface with AI prompt input and source selection
- [ ] Manages local storage with intelligent cleanup
- [ ] Works with Deepin's existing wallpaper rotation

### Quality Requirements
- [ ] Lightweight operation (< 75MB RAM with AI features)
- [ ] Minimal CPU usage when idle (excludes local AI generation)
- [ ] Graceful error handling for network and AI API issues
- [ ] Simple, intuitive interface with AI prompt guidance
- [ ] No system stability impact

### User Experience
- [ ] Easy setup: install app, configure sources and AI, point Deepin to folder
- [ ] Clear documentation on Deepin configuration and AI usage
- [ ] Respects API rate limits and user bandwidth preferences
- [ ] Provides image quality filtering and AI content filtering
- [ ] AI prompt templates for common wallpaper themes