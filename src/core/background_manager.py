"""
Background Manager for setting wallpapers on Deepin and other desktop environments.

Provides unified interface for setting desktop backgrounds across different
desktop environments with primary support for Deepin via gsettings.
"""

import logging
import subprocess
import os
from typing import Optional, Dict, Any
from pathlib import Path
from urllib.parse import quote


logger = logging.getLogger(__name__)


class BackgroundManager:
    """Manages desktop background/wallpaper setting across desktop environments."""

    # Deepin/GNOME desktop background schema
    DEEPIN_SCHEMA = "com.deepin.wrap.gnome.desktop.background"
    GNOME_SCHEMA = "org.gnome.desktop.background"

    def __init__(self):
        """Initialize the background manager."""
        self.desktop_environment = self._detect_desktop_environment()
        logger.info(f"Detected desktop environment: {self.desktop_environment}")

    def _detect_desktop_environment(self) -> str:
        """
        Detect the current desktop environment.

        Returns:
            String identifier for the desktop environment
        """
        # Check environment variables
        desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()

        if 'deepin' in desktop_env or 'dde' in desktop_env:
            return 'deepin'
        elif 'gnome' in desktop_env:
            return 'gnome'
        elif 'kde' in desktop_env or 'plasma' in desktop_env:
            return 'kde'
        elif 'xfce' in desktop_env:
            return 'xfce'
        elif 'mate' in desktop_env:
            return 'mate'
        elif 'cinnamon' in desktop_env:
            return 'cinnamon'

        # Fallback detection methods
        if os.environ.get('DESKTOP_SESSION'):
            session = os.environ.get('DESKTOP_SESSION', '').lower()
            if 'deepin' in session or 'dde' in session:
                return 'deepin'
            elif 'gnome' in session:
                return 'gnome'
            elif 'kde' in session:
                return 'kde'

        # Default fallback
        return 'unknown'

    def _validate_image_file(self, image_path: Path) -> bool:
        """
        Validate that the image file exists and is accessible.

        Args:
            image_path: Path to the image file

        Returns:
            True if file is valid, False otherwise
        """
        if not image_path.exists():
            logger.error(f"Image file does not exist: {image_path}")
            return False

        if not image_path.is_file():
            logger.error(f"Path is not a file: {image_path}")
            return False

        if not os.access(image_path, os.R_OK):
            logger.error(f"Image file is not readable: {image_path}")
            return False

        # Check file size (avoid empty files)
        if image_path.stat().st_size == 0:
            logger.error(f"Image file is empty: {image_path}")
            return False

        return True

    def _format_file_uri(self, image_path: Path) -> str:
        """
        Format file path as proper file:// URI.

        Args:
            image_path: Path to the image file

        Returns:
            Properly formatted file URI
        """
        # Convert to absolute path
        abs_path = image_path.resolve()

        # URL encode the path to handle special characters
        encoded_path = quote(str(abs_path))

        return f"file://{encoded_path}"

    def _run_gsettings_command(self, schema: str, key: str, value: str) -> bool:
        """
        Run gsettings command safely.

        Args:
            schema: GSettings schema name
            key: Setting key name
            value: Value to set

        Returns:
            True if command succeeded, False otherwise
        """
        try:
            cmd = ['gsettings', 'set', schema, key, value]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"Successfully set {schema}.{key} = {value}")
                return True
            else:
                logger.error(f"gsettings command failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("gsettings command timed out")
            return False
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to run gsettings command: {e}")
            return False

    def set_background_deepin(self, image_path: Path) -> bool:
        """
        Set background using Deepin's gsettings schema.

        Args:
            image_path: Path to the image file

        Returns:
            True if successful, False otherwise
        """
        if not self._validate_image_file(image_path):
            return False

        file_uri = self._format_file_uri(image_path)

        # Try Deepin schema first
        if self._run_gsettings_command(self.DEEPIN_SCHEMA, 'picture-uri', file_uri):
            return True

        # Fallback to GNOME schema
        logger.info("Deepin schema failed, trying GNOME schema...")
        return self._run_gsettings_command(self.GNOME_SCHEMA, 'picture-uri', file_uri)

    def set_background_gnome(self, image_path: Path) -> bool:
        """
        Set background using GNOME's gsettings schema.

        Args:
            image_path: Path to the image file

        Returns:
            True if successful, False otherwise
        """
        if not self._validate_image_file(image_path):
            return False

        file_uri = self._format_file_uri(image_path)
        return self._run_gsettings_command(self.GNOME_SCHEMA, 'picture-uri', file_uri)

    def set_background_kde(self, image_path: Path) -> bool:
        """
        Set background for KDE Plasma desktop.

        Args:
            image_path: Path to the image file

        Returns:
            True if successful, False otherwise
        """
        if not self._validate_image_file(image_path):
            return False

        try:
            # KDE Plasma uses qdbus or kwriteconfig
            abs_path = str(image_path.resolve())

            # Try using qdbus first
            cmd = [
                'qdbus', 'org.kde.plasmashell', '/PlasmaShell',
                'org.kde.PlasmaShell.evaluateScript',
                f'''
                var allDesktops = desktops();
                for (i = 0; i < allDesktops.length; i++) {{
                    d = allDesktops[i];
                    d.wallpaperPlugin = "org.kde.image";
                    d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
                    d.writeConfig("Image", "{abs_path}");
                }}
                '''
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logger.info(f"Successfully set KDE background to: {abs_path}")
                return True
            else:
                logger.error(f"KDE qdbus command failed: {result.stderr}")
                return False

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Failed to set KDE background: {e}")
            return False

    def set_background_xfce(self, image_path: Path) -> bool:
        """
        Set background for XFCE desktop.

        Args:
            image_path: Path to the image file

        Returns:
            True if successful, False otherwise
        """
        if not self._validate_image_file(image_path):
            return False

        try:
            abs_path = str(image_path.resolve())

            # XFCE uses xfconf-query
            cmd = [
                'xfconf-query', '--channel', 'xfce4-desktop',
                '--property', '/backdrop/screen0/monitor0/workspace0/last-image',
                '--set', abs_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logger.info(f"Successfully set XFCE background to: {abs_path}")
                return True
            else:
                logger.error(f"XFCE xfconf-query command failed: {result.stderr}")
                return False

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Failed to set XFCE background: {e}")
            return False

    def set_background(self, image_path: Path, force_method: Optional[str] = None) -> bool:
        """
        Set desktop background using the appropriate method for the current environment.

        Args:
            image_path: Path to the image file
            force_method: Force a specific method ('deepin', 'gnome', 'kde', 'xfce')

        Returns:
            True if successful, False otherwise
        """
        image_path = Path(image_path)

        logger.info(f"Setting background to: {image_path}")

        # Use forced method if specified
        if force_method:
            method_map = {
                'deepin': self.set_background_deepin,
                'gnome': self.set_background_gnome,
                'kde': self.set_background_kde,
                'xfce': self.set_background_xfce,
            }

            if force_method in method_map:
                return method_map[force_method](image_path)
            else:
                logger.error(f"Unknown forced method: {force_method}")
                return False

        # Auto-detect and use appropriate method
        if self.desktop_environment in ['deepin', 'dde']:
            return self.set_background_deepin(image_path)
        elif self.desktop_environment == 'gnome':
            return self.set_background_gnome(image_path)
        elif self.desktop_environment == 'kde':
            return self.set_background_kde(image_path)
        elif self.desktop_environment == 'xfce':
            return self.set_background_xfce(image_path)
        else:
            # Try multiple methods as fallback
            logger.info(f"Unknown desktop environment: {self.desktop_environment}, trying fallback methods...")

            # Try Deepin/GNOME first (most common)
            if self.set_background_deepin(image_path):
                return True

            # Try other methods
            for method in [self.set_background_kde, self.set_background_xfce]:
                try:
                    if method(image_path):
                        return True
                except Exception as e:
                    logger.debug(f"Fallback method failed: {e}")
                    continue

            logger.error("All background setting methods failed")
            return False

    def get_current_background(self) -> Optional[str]:
        """
        Get the current desktop background image path.

        Returns:
            Path to current background image, or None if unable to determine
        """
        try:
            # Try Deepin schema first
            result = subprocess.run(
                ['gsettings', 'get', self.DEEPIN_SCHEMA, 'picture-uri'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                uri = result.stdout.strip().strip("'\"")
                if uri.startswith('file://'):
                    return uri[7:]  # Remove 'file://' prefix
                return uri

            # Fallback to GNOME schema
            result = subprocess.run(
                ['gsettings', 'get', self.GNOME_SCHEMA, 'picture-uri'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                uri = result.stdout.strip().strip("'\"")
                if uri.startswith('file://'):
                    return uri[7:]  # Remove 'file://' prefix
                return uri

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.error(f"Failed to get current background: {e}")

        return None

    def test_background_setting(self) -> Dict[str, Any]:
        """
        Test background setting capability and return system information.

        Returns:
            Dictionary with test results and system information
        """
        info = {
            'desktop_environment': self.desktop_environment,
            'gsettings_available': False,
            'deepin_schema_available': False,
            'gnome_schema_available': False,
            'current_background': None,
            'test_passed': False
        }

        # Check if gsettings is available
        try:
            subprocess.run(['gsettings', '--version'],
                         capture_output=True, timeout=5)
            info['gsettings_available'] = True
        except (subprocess.SubprocessError, FileNotFoundError):
            info['gsettings_available'] = False

        if info['gsettings_available']:
            # Check schema availability
            try:
                result = subprocess.run(
                    ['gsettings', 'list-schemas'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                schemas = result.stdout
                info['deepin_schema_available'] = self.DEEPIN_SCHEMA in schemas
                info['gnome_schema_available'] = self.GNOME_SCHEMA in schemas
            except subprocess.SubprocessError:
                pass

            # Get current background
            info['current_background'] = self.get_current_background()

        info['test_passed'] = (
            info['gsettings_available'] and
            (info['deepin_schema_available'] or info['gnome_schema_available'])
        )

        return info


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = BackgroundManager()

    # Test system capabilities
    test_info = manager.test_background_setting()
    print("Background Manager Test Results:")
    for key, value in test_info.items():
        print(f"  {key}: {value}")

    # Example: Set background (uncomment to test)
    # test_image = Path.home() / "Pictures" / "test_wallpaper.jpg"
    # if test_image.exists():
    #     success = manager.set_background(test_image)
    #     print(f"Background setting: {'Success' if success else 'Failed'}")