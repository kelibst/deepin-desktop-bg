# Claude AI Assistant Guidelines

## Project Context
This is the **Deepin Wallpaper Source Manager** project - a lightweight image downloader that provides wallpapers to a local folder, leveraging Deepin's existing automatic wallpaper rotation capabilities.

## Strategy Overview
**Key Change**: Instead of directly managing wallpapers, we download to `~/Pictures/Wallpapers/` and let users configure Deepin's built-in wallpaper rotation to use that folder.

## Core Technology Stack
- **Language**: Python 3.8+
- **UI Framework**: Qt/PySide6 (minimal interface)
- **Image Sources**:
  - **Curated**: WallpaperHub.app (5,498 high-quality wallpapers)
  - **AI Generated**: Monica AI (4K), Craiyon (unlimited free), Stable Diffusion
  - **Community**: Reddit (r/wallpapers, r/EarthPorn)
  - **Public Domain**: Wikimedia Commons, NASA
- **Storage**: `~/Pictures/Wallpapers/` (user configures Deepin manually)

## Development Rules

### Code Standards
- Follow existing Python conventions and PEP 8
- Use type hints for all function parameters and returns
- Implement proper error handling and logging
- Keep functions focused and modular
- Add docstrings for classes and complex functions

### Project Structure Adherence
Follow the enhanced structure in `plan/plan.md`:
```
src/core/downloaders/    # WallpaperHub, Reddit, Wikimedia, NASA clients
src/core/ai_generators/  # Monica AI, Craiyon, Stable Diffusion clients
src/core/               # image_manager.py, config.py
src/ui/                # Qt source selector with AI prompt interface
src/daemon/            # Background download service with AI generation queue
```

### Source Guidelines
**AVOID**: Unsplash, Pexels, Pixabay (prohibit wallpaper applications)
**USE**:
- **WallpaperHub.app** - 5,498 curated wallpapers, "wallpaper use only" licensing
- **AI Generators**:
  - Monica AI - 4K resolution, free tier, dedicated wallpaper focus
  - Craiyon - Unlimited free generation, commercial use with attribution
  - Stable Diffusion - Open source, no restrictions, local generation
- **Traditional Sources**:
  - Reddit API (r/wallpapers, r/EarthPorn) - Free, allows wallpaper use
  - Wikimedia Commons - Public domain, no restrictions
  - NASA Image Gallery - Public domain, no restrictions

### Storage & Integration
- **No direct wallpaper setting** - Users configure Deepin manually
- Store images in: `~/Pictures/Wallpapers/`
- Implement intelligent storage cleanup (size limits, duplicate detection)
- Organize by source type (curated/ai_generated/community/public_domain)
- Ensure reasonable resource usage (< 75MB RAM with AI features)

### AI Generation Guidelines
- **Rate Limiting**: Respect free tier limits for all AI services
- **Content Filtering**: Ensure appropriate wallpaper content (no NSFW/inappropriate)
- **Prompt Templates**: Provide common wallpaper themes (nature, space, abstract, minimal)
- **Error Handling**: Graceful fallbacks when AI services are unavailable
- **Caching**: Store generated images locally to avoid regenerating
- **Resolution Management**: Support multiple resolutions (4K, ultrawide, mobile)

### Development Phases
Currently in **Phase 1: Core Downloads + AI Generation** (Week 1)
- Focus on WallpaperHub.app integration and AI generators
- Build Qt interface with AI prompt input capabilities
- Implement storage management for mixed content sources

## Commands to Run
- **Linting**: `python -m flake8 src/` (verify in project)
- **Type Check**: `python -m mypy src/` (verify in project)
- **Tests**: `python -m pytest tests/` (verify in project)

## Activity Tracking
Use `plan/ACTIVITIES.md` to track completed work and current progress against the revised 2-3 week timeline.

## Key Priorities
1. **Legal Compliance**: Only use APIs and sources that allow wallpaper applications
2. **AI Integration**: Seamless AI wallpaper generation with quality filtering
3. **Content Variety**: Balance between curated (WallpaperHub), AI-generated, and community content
4. **Resource Efficiency**: Lightweight operation (< 75MB RAM with AI features)
5. **User Experience**: Simple setup with AI prompts, clear Deepin configuration guide
6. **Rate Limiting**: Respect all API limits to maintain service availability