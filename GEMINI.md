# Project Overview

This project is a wallpaper manager for the Deepin Desktop Environment. It allows users to download wallpapers from various sources, including online communities like Reddit and curated sources like WallpaperHub. It also integrates with AI image generation services like Monica AI and Craiyon to create custom wallpapers.

The application is built in Python and uses the Qt framework (via PySide6) for its graphical user interface. It features a modular architecture, with separate components for handling different wallpaper sources, managing image storage, and filtering for quality.

# Building and Running

## Dependencies

The project's dependencies are listed in the `requirements.txt` file. They can be installed using pip:

```bash
pip install -r requirements.txt
```

## Running the Application

The main entry point for the application is `test_app.py`. To run the GUI, execute the following command:

```bash
./run_gui.sh
```

Alternatively, you can run the application directly using Python:

```bash
python test_app.py --gui
```

## Testing

The project includes a test suite that can be run from the command line. To run all tests, use the following command:

```bash
python test_app.py --test all
```

You can also run specific tests by replacing "all" with the name of the test you want to run (e.g., "config", "manager", "quality", "ai", "download").

# Development Conventions

## Configuration

The application's configuration is handled by the `Config` class in `src/core/config.py`. It uses dataclasses to define the configuration structure, which makes it easy to add new settings. Configuration is stored in `~/.config/deepin-wallpaper-source-manager/config.json`.

## Code Style

The codebase follows the PEP 8 style guide for Python code. It also uses type hints, which are checked with mypy.

## Adding New Sources

To add a new wallpaper source, you need to create a new client in the `src/core/downloaders` or `src/core/ai_generators` directory. The new client must implement the required methods (e.g., `get_wallpapers`, `download_wallpaper`). After creating the client, you need to add it to the configuration system in `src/core/config.py` and update the UI in `src/ui/source_selector.py`.
