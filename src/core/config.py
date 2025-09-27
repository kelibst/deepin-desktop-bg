"""
Configuration management for the Deepin Wallpaper Source Manager.

Handles user preferences, source settings, AI prompt templates,
and application configuration.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Enumeration of available wallpaper sources."""
    WALLPAPER_HUB = "wallpaper_hub"
    MONICA_AI = "monica_ai"
    CRAIYON = "craiyon"
    STABLE_DIFFUSION = "stable_diffusion"
    REDDIT = "reddit"
    WIKIMEDIA = "wikimedia"
    NASA = "nasa"


class AIStyle(Enum):
    """Enumeration of AI generation styles."""
    PHOTOGRAPHY = "photography"
    DIGITAL_ART = "digital_art"
    ABSTRACT = "abstract"
    MINIMAL = "minimal"


class Resolution(Enum):
    """Enumeration of target resolutions."""
    MOBILE = "mobile"
    HD_1080P = "1080p"
    QHD_1440P = "1440p"
    UHD_4K = "4K"
    ULTRAWIDE = "ultrawide"


@dataclass
class SourceConfig:
    """Configuration for a specific wallpaper source."""
    enabled: bool = True
    priority: int = 1  # 1-10, higher is more important
    rate_limit_delay: float = 2.0  # Seconds between requests
    max_downloads_per_session: int = 10
    categories: List[str] = None
    resolutions: List[str] = None

    def __post_init__(self):
        if self.categories is None:
            self.categories = []
        if self.resolutions is None:
            self.resolutions = ["4K"]


@dataclass
class AIConfig:
    """Configuration for AI wallpaper generation."""
    default_style: str = AIStyle.PHOTOGRAPHY.value
    default_resolution: str = Resolution.UHD_4K.value
    content_filter: bool = True
    max_generations_per_day: int = 20
    save_prompts: bool = True
    auto_enhance_prompts: bool = True


@dataclass
class StorageConfig:
    """Configuration for wallpaper storage."""
    base_path: str = ""  # Will be set to ~/Pictures/Wallpapers if empty
    max_total_wallpapers: int = 1000
    cleanup_enabled: bool = True
    organize_by_date: bool = False
    duplicate_detection: bool = True
    image_quality_filter: bool = True
    min_resolution_width: int = 1280
    min_resolution_height: int = 720


@dataclass
class UIConfig:
    """Configuration for the user interface."""
    theme: str = "auto"  # auto, light, dark
    show_previews: bool = True
    preview_size: int = 200
    remember_last_selections: bool = True
    auto_close_after_download: bool = False


class Config:
    """Main configuration manager for the application."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Path to the configuration file.
                        Defaults to ~/.config/deepin-wallpaper-source-manager/config.json
        """
        if config_path is None:
            config_dir = Path.home() / ".config" / "deepin-wallpaper-source-manager"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "config.json"

        self.config_path = config_path
        self.config_data = self.load_config()

        # Initialize sub-configurations
        self.sources = self._load_sources_config()
        self.ai = self._load_ai_config()
        self.storage = self._load_storage_config()
        self.ui = self._load_ui_config()

        # AI prompt templates
        self.prompt_templates = self._load_prompt_templates()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")

        return self._get_default_config()

    def save_config(self) -> None:
        """Save configuration to file."""
        config_data = {
            "version": "1.0",
            "sources": {
                source_type.value: asdict(config)
                for source_type, config in self.sources.items()
            },
            "ai": asdict(self.ai),
            "storage": asdict(self.storage),
            "ui": asdict(self.ui),
            "prompt_templates": self.prompt_templates
        }

        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            logger.debug(f"Saved configuration to {self.config_path}")
        except IOError as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "version": "1.0",
            "sources": {},
            "ai": {},
            "storage": {},
            "ui": {},
            "prompt_templates": []
        }

    def _load_sources_config(self) -> Dict[SourceType, SourceConfig]:
        """Load source-specific configurations."""
        sources_data = self.config_data.get("sources", {})
        sources = {}

        for source_type in SourceType:
            source_data = sources_data.get(source_type.value, {})

            # Set source-specific defaults
            if source_type == SourceType.WALLPAPER_HUB:
                config = SourceConfig(
                    enabled=True,
                    priority=9,
                    rate_limit_delay=1.0,
                    max_downloads_per_session=20,
                    categories=["photography", "nature", "tech"],
                    resolutions=["4K", "ultrawide"]
                )
            elif source_type in [SourceType.MONICA_AI, SourceType.CRAIYON]:
                config = SourceConfig(
                    enabled=True,
                    priority=8,
                    rate_limit_delay=3.0,
                    max_downloads_per_session=5,
                    categories=["nature", "abstract", "minimal"],
                    resolutions=["4K"]
                )
            elif source_type == SourceType.STABLE_DIFFUSION:
                config = SourceConfig(
                    enabled=False,  # Disabled by default (requires setup)
                    priority=7,
                    rate_limit_delay=5.0,
                    max_downloads_per_session=3,
                    categories=["any"],
                    resolutions=["4K", "ultrawide"]
                )
            else:  # Reddit, Wikimedia, NASA
                config = SourceConfig(
                    enabled=True,
                    priority=6,
                    rate_limit_delay=2.0,
                    max_downloads_per_session=10,
                    categories=["nature", "space"],
                    resolutions=["4K", "1080p"]
                )

            # Override with saved values
            for key, value in source_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)

            sources[source_type] = config

        return sources

    def _load_ai_config(self) -> AIConfig:
        """Load AI generation configuration."""
        ai_data = self.config_data.get("ai", {})
        config = AIConfig()

        for key, value in ai_data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return config

    def _load_storage_config(self) -> StorageConfig:
        """Load storage configuration."""
        storage_data = self.config_data.get("storage", {})
        config = StorageConfig()

        # Set default base path if not specified
        if not config.base_path:
            config.base_path = str(Path.home() / "Pictures" / "Wallpapers")

        for key, value in storage_data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return config

    def _load_ui_config(self) -> UIConfig:
        """Load UI configuration."""
        ui_data = self.config_data.get("ui", {})
        config = UIConfig()

        for key, value in ui_data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return config

    def _load_prompt_templates(self) -> List[Dict[str, str]]:
        """Load AI prompt templates."""
        saved_templates = self.config_data.get("prompt_templates", [])

        # Default templates
        default_templates = [
            {
                "name": "Nature Landscape",
                "prompt": "beautiful mountain landscape with lake reflection at sunset",
                "style": "photography",
                "category": "nature"
            },
            {
                "name": "Space Nebula",
                "prompt": "colorful nebula in deep space with stars and cosmic dust",
                "style": "digital_art",
                "category": "space"
            },
            {
                "name": "Abstract Geometric",
                "prompt": "geometric shapes in gradient colors, modern abstract design",
                "style": "abstract",
                "category": "abstract"
            },
            {
                "name": "Minimal Ocean",
                "prompt": "calm ocean horizon line, minimalist composition",
                "style": "minimal",
                "category": "minimal"
            },
            {
                "name": "Forest Path",
                "prompt": "sunlit forest path with tall trees and dappled light",
                "style": "photography",
                "category": "nature"
            },
            {
                "name": "City Skyline",
                "prompt": "modern city skyline at night with illuminated buildings",
                "style": "photography",
                "category": "urban"
            },
            {
                "name": "Abstract Flow",
                "prompt": "flowing liquid abstract shapes in blue and purple gradients",
                "style": "abstract",
                "category": "abstract"
            },
            {
                "name": "Desert Dunes",
                "prompt": "sand dunes with dramatic shadows and golden light",
                "style": "photography",
                "category": "nature"
            }
        ]

        # Merge default and saved templates
        template_names = {t["name"] for t in saved_templates}
        for default_template in default_templates:
            if default_template["name"] not in template_names:
                saved_templates.append(default_template)

        return saved_templates

    def add_prompt_template(self, name: str, prompt: str, style: str, category: str = "custom") -> None:
        """Add a new AI prompt template."""
        template = {
            "name": name,
            "prompt": prompt,
            "style": style,
            "category": category
        }

        # Remove existing template with same name
        self.prompt_templates = [t for t in self.prompt_templates if t["name"] != name]
        self.prompt_templates.append(template)

        self.save_config()

    def remove_prompt_template(self, name: str) -> bool:
        """Remove an AI prompt template by name."""
        original_count = len(self.prompt_templates)
        self.prompt_templates = [t for t in self.prompt_templates if t["name"] != name]

        if len(self.prompt_templates) < original_count:
            self.save_config()
            return True
        return False

    def get_prompt_templates_by_category(self, category: str) -> List[Dict[str, str]]:
        """Get prompt templates filtered by category."""
        return [t for t in self.prompt_templates if t.get("category") == category]

    def get_enabled_sources(self) -> List[SourceType]:
        """Get list of enabled wallpaper sources."""
        return [
            source_type for source_type, config in self.sources.items()
            if config.enabled
        ]

    def get_sources_by_priority(self) -> List[SourceType]:
        """Get enabled sources sorted by priority (highest first)."""
        enabled_sources = self.get_enabled_sources()
        return sorted(
            enabled_sources,
            key=lambda s: self.sources[s].priority,
            reverse=True
        )

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self.config_data = self._get_default_config()
        self.sources = self._load_sources_config()
        self.ai = self._load_ai_config()
        self.storage = self._load_storage_config()
        self.ui = self._load_ui_config()
        self.prompt_templates = self._load_prompt_templates()
        self.save_config()


# Global configuration instance
_config_instance = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    config = Config()

    print("Enabled sources:")
    for source in config.get_enabled_sources():
        print(f"- {source.value}")

    print(f"\\nStorage path: {config.storage.base_path}")
    print(f"AI default style: {config.ai.default_style}")

    print("\\nPrompt templates:")
    for template in config.prompt_templates:
        print(f"- {template['name']}: {template['prompt'][:50]}...")

    config.save_config()