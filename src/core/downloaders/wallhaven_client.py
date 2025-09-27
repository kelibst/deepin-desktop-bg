"""
Wallhaven.cc client for downloading wallpapers.

Provides access to high-quality wallpapers with multiple resolutions
and categories. All images are freely available for wallpaper use.
"""

import logging
import requests
import time
from typing import List, Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class WallhavenClient:
    """Client for accessing Wallhaven.cc's wallpaper collection."""

    BASE_URL = "https://wallhaven.cc/api/v1"
    FULL_IMAGE_URL = "https://w.wallhaven.cc/full"
    THUMBNAIL_URL = "https://th.wallhaven.cc/lg"

    # Rate limiting: 45 requests per minute
    REQUESTS_PER_MINUTE = 45
    MIN_REQUEST_INTERVAL = 60.0 / REQUESTS_PER_MINUTE

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Wallhaven client."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Deepin-Wallpaper-Source-Manager/0.1.0'
        })

        if api_key:
            self.session.headers.update({
                'X-API-Key': api_key
            })

        self.last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting."""
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.MIN_REQUEST_INTERVAL:
            sleep_time = self.MIN_REQUEST_INTERVAL - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def search_wallpapers(self,
                         query: Optional[str] = None,
                         categories: str = "111",  # general/anime/people
                         purity: str = "100",      # SFW only
                         sorting: str = "relevance",
                         order: str = "desc",
                         topRange: str = "1M",
                         atleast: Optional[str] = "1920x1080",
                         ratios: Optional[str] = None,
                         colors: Optional[str] = None,
                         page: int = 1,
                         limit: int = 24) -> List[Dict[str, Any]]:
        """
        Search for wallpapers on Wallhaven.

        Args:
            query: Search query string
            categories: Category filter (111 = all, 100 = general only, etc.)
            purity: Purity filter (100 = SFW only, 110 = SFW + sketchy, etc.)
            sorting: Sort method (date_added, relevance, random, views, favorites, toplist)
            order: Sort order (desc, asc)
            topRange: Time range for toplist sorting (1d, 3d, 1w, 1M, 3M, 6M, 1y)
            atleast: Minimum resolution (e.g., "1920x1080")
            ratios: Aspect ratios (e.g., "16x9,16x10")
            colors: Color filter (hex color without #)
            page: Page number
            limit: Number of results per page (max 24)

        Returns:
            List of wallpaper metadata dictionaries
        """
        try:
            self._rate_limit()

            params = {
                'categories': categories,
                'purity': purity,
                'sorting': sorting,
                'order': order,
                'topRange': topRange,
                'page': page
            }

            if query:
                params['q'] = query
            if atleast:
                params['atleast'] = atleast
            if ratios:
                params['ratios'] = ratios
            if colors:
                params['colors'] = colors

            response = self.session.get(f"{self.BASE_URL}/search", params=params)
            response.raise_for_status()

            data = response.json()
            wallpapers = []

            for item in data.get('data', []):
                wallpaper = {
                    'id': item['id'],
                    'title': f"Wallhaven {item['id']}",
                    'description': f"Category: {item.get('category', 'N/A')}, Views: {item.get('views', 0)}",
                    'tags': [tag['name'] for tag in item.get('tags', [])],
                    'resolution': f"{item['dimension_x']}x{item['dimension_y']}",
                    'file_size': item.get('file_size', 0),
                    'file_type': item.get('file_type', 'jpg'),
                    'colors': item.get('colors', []),
                    'views': item.get('views', 0),
                    'favorites': item.get('favorites', 0),
                    'category': item.get('category', 'general'),
                    'purity': item.get('purity', 'sfw'),
                    'url': item.get('url', ''),
                    'short_url': item.get('short_url', ''),
                    'thumbs': item.get('thumbs', {}),
                    'path': item.get('path', ''),
                    'created_at': item.get('created_at', '')
                }
                wallpapers.append(wallpaper)

            return wallpapers[:limit]

        except requests.RequestException as e:
            logger.error(f"Failed to search wallpapers on Wallhaven: {e}")
            return []

    def get_wallpaper_info(self, wallpaper_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific wallpaper.

        Args:
            wallpaper_id: The wallpaper ID

        Returns:
            Wallpaper metadata dictionary or None if failed
        """
        try:
            self._rate_limit()

            response = self.session.get(f"{self.BASE_URL}/w/{wallpaper_id}")
            response.raise_for_status()

            data = response.json()
            item = data.get('data', {})

            return {
                'id': item['id'],
                'title': f"Wallhaven {item['id']}",
                'description': f"Category: {item.get('category', 'N/A')}, Views: {item.get('views', 0)}",
                'tags': [tag['name'] for tag in item.get('tags', [])],
                'resolution': f"{item['dimension_x']}x{item['dimension_y']}",
                'file_size': item.get('file_size', 0),
                'file_type': item.get('file_type', 'jpg'),
                'colors': item.get('colors', []),
                'views': item.get('views', 0),
                'favorites': item.get('favorites', 0),
                'category': item.get('category', 'general'),
                'purity': item.get('purity', 'sfw'),
                'url': item.get('url', ''),
                'short_url': item.get('short_url', ''),
                'thumbs': item.get('thumbs', {}),
                'path': item.get('path', ''),
                'created_at': item.get('created_at', '')
            }

        except requests.RequestException as e:
            logger.error(f"Failed to get wallpaper info for {wallpaper_id}: {e}")
            return None

    def download_wallpaper(self, wallpaper: Dict[str, Any],
                          save_path: Optional[Path] = None,
                          check_duplicates: bool = True) -> Optional[Path]:
        """
        Download a specific wallpaper.

        Args:
            wallpaper: Wallpaper metadata dictionary
            save_path: Directory to save the wallpaper
            check_duplicates: Whether to check for duplicates before downloading

        Returns:
            Path to the downloaded file, or None if failed
        """
        try:
            wallpaper_id = wallpaper['id']

            # Use the path provided by the API
            download_url = wallpaper.get('path')
            if not download_url:
                # Fallback: construct URL manually
                file_type = wallpaper.get('file_type', 'image/jpeg')
                ext = file_type.split('/')[-1] if '/' in file_type else file_type
                download_url = f"{self.FULL_IMAGE_URL}/{wallpaper_id[:2]}/wallhaven-{wallpaper_id}.{ext}"

            # Create filename
            resolution = wallpaper.get('resolution', 'unknown')
            safe_title = f"wallhaven_{wallpaper_id}_{resolution}"

            # Get file extension from download URL or file_type
            if download_url:
                ext = download_url.split('.')[-1]
            else:
                file_type = wallpaper.get('file_type', 'image/jpeg')
                ext = file_type.split('/')[-1] if '/' in file_type else file_type

            filename = f"{safe_title}.{ext}"

            if save_path:
                file_path = save_path / filename
            else:
                file_path = Path.home() / "Pictures" / "Wallpapers" / "wallhaven" / filename

            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file already exists
            if file_path.exists():
                logger.info(f"Wallpaper already exists: {file_path}")
                return file_path

            # Check for duplicates if enabled
            if check_duplicates:
                from core.image_manager import ImageManager
                try:
                    image_manager = ImageManager()

                    # Check if we already have this wallpaper by ID or hash
                    existing_wallpapers = image_manager.list_wallpapers('wallhaven')
                    for existing in existing_wallpapers:
                        existing_metadata = existing.get('metadata', {})
                        if existing_metadata.get('wallpaper_id') == wallpaper_id:
                            logger.info(f"Wallpaper {wallpaper_id} already exists in collection: {existing['path']}")
                            return Path(existing['path'])

                except Exception as e:
                    logger.warning(f"Failed to check for duplicates: {e}")
                    # Continue with download if duplicate check fails

            self._rate_limit()

            # Download the image
            response = self.session.get(download_url, stream=True)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded wallpaper: {file_path}")
            return file_path

        except requests.RequestException as e:
            logger.error(f"Failed to download wallpaper {wallpaper['id']}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading wallpaper: {e}")
            return None

    def download_thumbnail(self, wallpaper: Dict[str, Any],
                          size: str = 'large',
                          save_path: Optional[Path] = None) -> Optional[Path]:
        """
        Download a thumbnail for a specific wallpaper.

        Args:
            wallpaper: Wallpaper metadata dictionary
            size: Thumbnail size ('large', 'original', 'small')
            save_path: Directory to save the thumbnail

        Returns:
            Path to the downloaded thumbnail, or None if failed
        """
        try:
            wallpaper_id = wallpaper['id']
            thumbs = wallpaper.get('thumbs', {})

            if size not in thumbs:
                logger.error(f"Thumbnail size '{size}' not available for wallpaper {wallpaper_id}")
                return None

            thumbnail_url = thumbs[size]

            # Create filename
            safe_title = f"thumb_{wallpaper_id}_{size}"
            filename = f"{safe_title}.jpg"  # Thumbnails are typically JPEG

            if save_path:
                file_path = save_path / filename
            else:
                # Store thumbnails in a separate cache directory
                cache_dir = Path.home() / ".cache" / "deepin-wallpaper-manager" / "thumbnails"
                cache_dir.mkdir(parents=True, exist_ok=True)
                file_path = cache_dir / filename

            # Check if thumbnail already exists
            if file_path.exists():
                logger.debug(f"Thumbnail already exists: {file_path}")
                return file_path

            self._rate_limit()

            # Download the thumbnail
            response = self.session.get(thumbnail_url, stream=True)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.debug(f"Downloaded thumbnail: {file_path}")
            return file_path

        except requests.RequestException as e:
            logger.error(f"Failed to download thumbnail for {wallpaper['id']}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading thumbnail: {e}")
            return None

    def get_thumbnail_url(self, wallpaper: Dict[str, Any], size: str = 'large') -> Optional[str]:
        """
        Get thumbnail URL for a wallpaper.

        Args:
            wallpaper: Wallpaper metadata dictionary
            size: Thumbnail size ('large', 'original', 'small')

        Returns:
            Thumbnail URL or None if not available
        """
        thumbs = wallpaper.get('thumbs', {})
        return thumbs.get(size)

    def get_categories(self) -> List[str]:
        """Get available wallpaper categories."""
        return [
            'general',
            'anime',
            'people'
        ]

    def get_purities(self) -> List[str]:
        """Get available purity levels."""
        return [
            'sfw',
            'sketchy',
            'nsfw'
        ]

    def get_sorting_options(self) -> List[str]:
        """Get available sorting options."""
        return [
            'date_added',
            'relevance',
            'random',
            'views',
            'favorites',
            'toplist'
        ]


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    client = WallhavenClient()

    # Search for nature wallpapers
    wallpapers = client.search_wallpapers(
        query="nature",
        atleast="1920x1080",
        sorting="favorites",
        limit=5
    )

    for wallpaper in wallpapers:
        print(f"ID: {wallpaper['id']}")
        print(f"Resolution: {wallpaper['resolution']}")
        print(f"Tags: {', '.join(wallpaper['tags'])}")
        print(f"Views: {wallpaper['views']}")
        print("---")

        # Download the first wallpaper as example
        if wallpaper == wallpapers[0]:
            downloaded_path = client.download_wallpaper(wallpaper)
            if downloaded_path:
                print(f"Downloaded to: {downloaded_path}")