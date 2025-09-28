"""
Background Setter utility for setting wallpapers as desktop background.

Supports multiple Linux desktop environments including Deepin, GNOME, KDE,
XFCE, and provides fallback options for other environments.
"""

import logging
import subprocess
import os
from typing import Optional, Tuple
from pathlib import Path
import shutil


logger = logging.getLogger(__name__)


class BackgroundSetter:
    """Utility class for setting desktop wallpapers across different Linux DEs."""

    def __init__(self):
        """Initialize the background setter."""
        self.desktop_environment = self.detect_desktop_environment()
        logger.info(f"Detected desktop environment: {self.desktop_environment}")

    def detect_desktop_environment(self) -> str:
        """
        Detect the current desktop environment.

        Returns:
            String identifier for the desktop environment
        """
        # Check environment variables
        desktop_session = os.environ.get('DESKTOP_SESSION', '').lower()
        xdg_current_desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()

        # Deepin detection
        if 'deepin' in desktop_session or 'deepin' in xdg_current_desktop:
            return 'deepin'

        # GNOME detection
        if 'gnome' in desktop_session or 'gnome' in xdg_current_desktop:
            return 'gnome'

        # KDE detection
        if 'kde' in desktop_session or 'kde' in xdg_current_desktop or 'plasma' in xdg_current_desktop:
            return 'kde'

        # XFCE detection
        if 'xfce' in desktop_session or 'xfce' in xdg_current_desktop:
            return 'xfce'

        # MATE detection
        if 'mate' in desktop_session or 'mate' in xdg_current_desktop:
            return 'mate'

        # Cinnamon detection
        if 'cinnamon' in desktop_session or 'cinnamon' in xdg_current_desktop:
            return 'cinnamon'

        # Check for specific tools available
        if shutil.which('dde-desktop'):
            return 'deepin'
        elif shutil.which('gnome-session'):
            return 'gnome'
        elif shutil.which('kwin'):
            return 'kde'
        elif shutil.which('xfce4-session'):
            return 'xfce'

        return 'unknown'

    def set_wallpaper(self, wallpaper_path: Path, mode: str = 'scaled') -> Tuple[bool, str]:
        """
        Set the desktop wallpaper.

        Args:
            wallpaper_path: Path to the wallpaper image file
            mode: Wallpaper display mode ('scaled', 'centered', 'stretched', 'tiled')

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not wallpaper_path.exists():
            return False, f"Wallpaper file does not exist: {wallpaper_path}"

        # Convert to absolute path
        absolute_path = wallpaper_path.resolve()

        try:
            if self.desktop_environment == 'deepin':
                return self._set_deepin_wallpaper(absolute_path, mode)
            elif self.desktop_environment == 'gnome':
                return self._set_gnome_wallpaper(absolute_path, mode)
            elif self.desktop_environment == 'kde':
                return self._set_kde_wallpaper(absolute_path, mode)
            elif self.desktop_environment == 'xfce':
                return self._set_xfce_wallpaper(absolute_path, mode)
            elif self.desktop_environment == 'mate':
                return self._set_mate_wallpaper(absolute_path, mode)
            elif self.desktop_environment == 'cinnamon':
                return self._set_cinnamon_wallpaper(absolute_path, mode)
            else:
                return self._set_fallback_wallpaper(absolute_path, mode)

        except Exception as e:
            logger.error(f"Failed to set wallpaper: {e}")
            return False, f"Failed to set wallpaper: {str(e)}"

    def _set_deepin_wallpaper(self, wallpaper_path: Path, mode: str) -> Tuple[bool, str]:
        """Set wallpaper for Deepin Desktop Environment."""
        try:
            # Map mode to Deepin's picture options
            deepin_modes = {
                'scaled': 'scaled',
                'centered': 'centered',
                'stretched': 'stretched',
                'tiled': 'tiled'
            }
            deepin_mode = deepin_modes.get(mode, 'scaled')

            # Use gsettings to set the wallpaper
            uri = f"file://{wallpaper_path}"

            # Set wallpaper URI
            result = subprocess.run([
                'gsettings', 'set', 'com.deepin.wrap.gnome.desktop.background',
                'picture-uri', uri
            ], capture_output=True, text=True, check=True)

            # Set wallpaper mode
            subprocess.run([
                'gsettings', 'set', 'com.deepin.wrap.gnome.desktop.background',
                'picture-options', deepin_mode
            ], capture_output=True, text=True, check=True)

            logger.info(f"Successfully set Deepin wallpaper: {wallpaper_path}")
            return True, f"Wallpaper set successfully on Deepin"

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set Deepin wallpaper: {e}")
            return False, f"Failed to set Deepin wallpaper: {e.stderr}"

    def _set_gnome_wallpaper(self, wallpaper_path: Path, mode: str) -> Tuple[bool, str]:
        """Set wallpaper for GNOME Desktop Environment."""
        try:
            # Map mode to GNOME's picture options
            gnome_modes = {
                'scaled': 'scaled',
                'centered': 'centered',
                'stretched': 'stretched',
                'tiled': 'wallpaper'
            }
            gnome_mode = gnome_modes.get(mode, 'scaled')

            uri = f"file://{wallpaper_path}"

            # Set wallpaper URI
            subprocess.run([
                'gsettings', 'set', 'org.gnome.desktop.background',
                'picture-uri', uri
            ], capture_output=True, text=True, check=True)

            # Set wallpaper mode
            subprocess.run([
                'gsettings', 'set', 'org.gnome.desktop.background',
                'picture-options', gnome_mode
            ], capture_output=True, text=True, check=True)

            logger.info(f"Successfully set GNOME wallpaper: {wallpaper_path}")
            return True, "Wallpaper set successfully on GNOME"

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set GNOME wallpaper: {e}")
            return False, f"Failed to set GNOME wallpaper: {e.stderr}"

    def _set_kde_wallpaper(self, wallpaper_path: Path, mode: str) -> Tuple[bool, str]:
        """Set wallpaper for KDE Plasma Desktop Environment."""
        try:
            # KDE uses different fill modes
            kde_modes = {
                'scaled': '6',  # Scaled, Keep Proportions
                'centered': '1',  # Centered
                'stretched': '0',  # Scaled and Cropped
                'tiled': '3'   # Tiled
            }
            kde_mode = kde_modes.get(mode, '6')

            # Use qdbus to set wallpaper
            script = f'''
            var allDesktops = desktops();
            for (i=0;i<allDesktops.length;i++) {{
                d = allDesktops[i];
                d.wallpaperPlugin = "org.kde.image";
                d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
                d.writeConfig("Image", "file://{wallpaper_path}");
                d.writeConfig("FillMode", {kde_mode});
            }}
            '''

            subprocess.run([
                'qdbus', 'org.kde.plasmashell', '/PlasmaShell',
                'org.kde.PlasmaShell.evaluateScript', script
            ], capture_output=True, text=True, check=True)

            logger.info(f"Successfully set KDE wallpaper: {wallpaper_path}")
            return True, "Wallpaper set successfully on KDE"

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set KDE wallpaper: {e}")
            # Fallback to kwriteconfig5
            try:
                subprocess.run([
                    'kwriteconfig5', '--file', 'plasma-org.kde.plasma.desktop-appletsrc',
                    '--group', 'Containments', '--group', '1', '--group', 'Wallpaper',
                    '--group', 'org.kde.image', '--group', 'General',
                    '--key', 'Image', f"file://{wallpaper_path}"
                ], check=True)
                return True, "Wallpaper set successfully on KDE (fallback method)"
            except subprocess.CalledProcessError as e2:
                return False, f"Failed to set KDE wallpaper: {e2.stderr}"

    def _set_xfce_wallpaper(self, wallpaper_path: Path, mode: str) -> Tuple[bool, str]:
        """Set wallpaper for XFCE Desktop Environment."""
        try:
            # XFCE uses different style values
            xfce_modes = {
                'scaled': '4',    # Scaled
                'centered': '1',  # Centered
                'stretched': '3', # Stretched
                'tiled': '2'      # Tiled
            }
            xfce_mode = xfce_modes.get(mode, '4')

            # Set wallpaper using xfconf-query
            subprocess.run([
                'xfconf-query', '--channel', 'xfce4-desktop',
                '--property', '/backdrop/screen0/monitor0/workspace0/last-image',
                '--set', str(wallpaper_path)
            ], capture_output=True, text=True, check=True)

            # Set wallpaper style
            subprocess.run([
                'xfconf-query', '--channel', 'xfce4-desktop',
                '--property', '/backdrop/screen0/monitor0/workspace0/image-style',
                '--set', xfce_mode
            ], capture_output=True, text=True, check=True)

            logger.info(f"Successfully set XFCE wallpaper: {wallpaper_path}")
            return True, "Wallpaper set successfully on XFCE"

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set XFCE wallpaper: {e}")
            return False, f"Failed to set XFCE wallpaper: {e.stderr}"

    def _set_mate_wallpaper(self, wallpaper_path: Path, mode: str) -> Tuple[bool, str]:
        """Set wallpaper for MATE Desktop Environment."""
        try:
            uri = f"file://{wallpaper_path}"

            # Set wallpaper URI
            subprocess.run([
                'gsettings', 'set', 'org.mate.background',
                'picture-filename', str(wallpaper_path)
            ], capture_output=True, text=True, check=True)

            # Map mode to MATE's picture options
            mate_modes = {
                'scaled': 'scaled',
                'centered': 'centered',
                'stretched': 'stretched',
                'tiled': 'wallpaper'
            }
            mate_mode = mate_modes.get(mode, 'scaled')

            subprocess.run([
                'gsettings', 'set', 'org.mate.background',
                'picture-options', mate_mode
            ], capture_output=True, text=True, check=True)

            logger.info(f"Successfully set MATE wallpaper: {wallpaper_path}")
            return True, "Wallpaper set successfully on MATE"

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set MATE wallpaper: {e}")
            return False, f"Failed to set MATE wallpaper: {e.stderr}"

    def _set_cinnamon_wallpaper(self, wallpaper_path: Path, mode: str) -> Tuple[bool, str]:
        """Set wallpaper for Cinnamon Desktop Environment."""
        try:
            uri = f"file://{wallpaper_path}"

            # Set wallpaper URI
            subprocess.run([
                'gsettings', 'set', 'org.cinnamon.desktop.background',
                'picture-uri', uri
            ], capture_output=True, text=True, check=True)

            # Map mode to Cinnamon's picture options
            cinnamon_modes = {
                'scaled': 'scaled',
                'centered': 'centered',
                'stretched': 'stretched',
                'tiled': 'mosaic'
            }
            cinnamon_mode = cinnamon_modes.get(mode, 'scaled')

            subprocess.run([
                'gsettings', 'set', 'org.cinnamon.desktop.background',
                'picture-options', cinnamon_mode
            ], capture_output=True, text=True, check=True)

            logger.info(f"Successfully set Cinnamon wallpaper: {wallpaper_path}")
            return True, "Wallpaper set successfully on Cinnamon"

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set Cinnamon wallpaper: {e}")
            return False, f"Failed to set Cinnamon wallpaper: {e.stderr}"

    def _set_fallback_wallpaper(self, wallpaper_path: Path, mode: str) -> Tuple[bool, str]:
        """Fallback wallpaper setting using external tools."""
        # Try common wallpaper setting tools
        tools = [
            (['feh', '--bg-scale', str(wallpaper_path)], 'feh'),
            (['nitrogen', '--set-scaled', str(wallpaper_path)], 'nitrogen'),
            (['hsetroot', '-fill', str(wallpaper_path)], 'hsetroot'),
            (['xwallpaper', '--maximize', str(wallpaper_path)], 'xwallpaper')
        ]

        for command, tool_name in tools:
            if shutil.which(command[0]):
                try:
                    subprocess.run(command, capture_output=True, text=True, check=True)
                    logger.info(f"Successfully set wallpaper using {tool_name}: {wallpaper_path}")
                    return True, f"Wallpaper set successfully using {tool_name}"
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to set wallpaper with {tool_name}: {e}")
                    continue

        return False, "No compatible wallpaper setting tool found"

    def get_supported_modes(self) -> list:
        """
        Get list of supported wallpaper modes for current desktop environment.

        Returns:
            List of supported mode strings
        """
        if self.desktop_environment in ['deepin', 'gnome', 'mate', 'cinnamon']:
            return ['scaled', 'centered', 'stretched', 'tiled']
        elif self.desktop_environment == 'kde':
            return ['scaled', 'centered', 'stretched', 'tiled']
        elif self.desktop_environment == 'xfce':
            return ['scaled', 'centered', 'stretched', 'tiled']
        else:
            return ['scaled']  # Fallback tools usually support scaling


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    setter = BackgroundSetter()
    print(f"Detected desktop environment: {setter.desktop_environment}")
    print(f"Supported modes: {setter.get_supported_modes()}")

    # Test wallpaper setting (uncomment to test)
    # test_image = Path("/path/to/test/wallpaper.jpg")
    # if test_image.exists():
    #     success, message = setter.set_wallpaper(test_image)
    #     print(f"Result: {success} - {message}")