"""
Reddit client for downloading community wallpapers.

Provides access to wallpaper-focused subreddits like r/wallpapers
and r/EarthPorn for community-sourced high-quality images.
"""

import logging
import requests
import praw
from typing import List, Dict, Optional, Any
from pathlib import Path
import time
from urllib.parse import urlparse
import re


logger = logging.getLogger(__name__)


class RedditClient:
    """Client for downloading wallpapers from Reddit communities."""

    # Popular wallpaper subreddits
    WALLPAPER_SUBREDDITS = [
        'wallpapers',       # General wallpapers
        'EarthPorn',        # Nature photography
        'SpacePorn',        # Space images
        'CityPorn',         # Urban photography
        'wallpaper',        # Alternative wallpaper community
        'WidescreenWallpaper',  # Ultrawide wallpapers
        'MinimalWallpaper', # Minimalist wallpapers
        'AbstractArt',      # Abstract wallpapers
    ]

    def __init__(self, client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 user_agent: Optional[str] = None):
        """
        Initialize the Reddit client.

        Args:
            client_id: Reddit API client ID (optional for read-only access)
            client_secret: Reddit API client secret (optional for read-only access)
            user_agent: Custom user agent string
        """
        self.client_id = client_id
        self.client_secret = client_secret

        if user_agent is None:
            user_agent = "Deepin-Wallpaper-Source-Manager/0.1.0"

        # Initialize PRAW for Reddit API access
        if client_id and client_secret:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
        else:
            # Read-only mode without authentication
            self.reddit = None
            logger.warning("Reddit client initialized without credentials - using fallback method")

        # HTTP session for direct requests
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # Conservative rate limiting

    def _rate_limit(self) -> None:
        """Apply rate limiting to respect Reddit's API limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def get_wallpapers(self,
                      subreddit: str = 'wallpapers',
                      sort_by: str = 'hot',
                      time_filter: str = 'week',
                      limit: int = 25) -> List[Dict[str, Any]]:
        """
        Get wallpapers from a Reddit community.

        Args:
            subreddit: Subreddit name (without r/ prefix)
            sort_by: Sort method ('hot', 'top', 'new')
            time_filter: Time filter for 'top' sort ('day', 'week', 'month', 'year', 'all')
            limit: Maximum number of posts to fetch

        Returns:
            List of wallpaper post dictionaries
        """
        try:
            self._rate_limit()

            if self.reddit:
                return self._get_wallpapers_via_praw(subreddit, sort_by, time_filter, limit)
            else:
                return self._get_wallpapers_via_json(subreddit, sort_by, time_filter, limit)

        except Exception as e:
            logger.error(f"Failed to fetch wallpapers from r/{subreddit}: {e}")
            return []

    def _get_wallpapers_via_praw(self, subreddit: str, sort_by: str,
                                time_filter: str, limit: int) -> List[Dict[str, Any]]:
        """Get wallpapers using PRAW (authenticated API access)."""
        sub = self.reddit.subreddit(subreddit)

        if sort_by == 'hot':
            submissions = sub.hot(limit=limit)
        elif sort_by == 'new':
            submissions = sub.new(limit=limit)
        elif sort_by == 'top':
            submissions = sub.top(time_filter=time_filter, limit=limit)
        else:
            submissions = sub.hot(limit=limit)

        wallpapers = []
        for submission in submissions:
            wallpaper_data = self._process_submission(submission)
            if wallpaper_data:
                wallpapers.append(wallpaper_data)

        return wallpapers

    def _get_wallpapers_via_json(self, subreddit: str, sort_by: str,
                                time_filter: str, limit: int) -> List[Dict[str, Any]]:
        """Get wallpapers using JSON API (no authentication required)."""
        # Construct Reddit JSON API URL
        if sort_by == 'top':
            url = f"https://www.reddit.com/r/{subreddit}/top.json"
            params = {'t': time_filter, 'limit': limit}
        else:
            url = f"https://www.reddit.com/r/{subreddit}/{sort_by}.json"
            params = {'limit': limit}

        response = self.session.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        wallpapers = []

        for post in data.get('data', {}).get('children', []):
            submission_data = post.get('data', {})
            wallpaper_data = self._process_submission_dict(submission_data)
            if wallpaper_data:
                wallpapers.append(wallpaper_data)

        return wallpapers

    def _process_submission(self, submission) -> Optional[Dict[str, Any]]:
        """Process a PRAW submission object."""
        return self._process_submission_dict({
            'title': submission.title,
            'url': submission.url,
            'id': submission.id,
            'score': submission.score,
            'num_comments': submission.num_comments,
            'created_utc': submission.created_utc,
            'author': str(submission.author) if submission.author else '[deleted]',
            'subreddit': str(submission.subreddit),
            'permalink': f"https://reddit.com{submission.permalink}",
            'is_video': submission.is_video,
            'is_self': submission.is_self
        })

    def _process_submission_dict(self, submission_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process submission data from JSON API or PRAW."""
        # Skip self posts, videos, and deleted posts
        if (submission_data.get('is_self') or
            submission_data.get('is_video') or
            not submission_data.get('url')):
            return None

        url = submission_data.get('url', '')

        # Check if URL points to an image
        if not self._is_image_url(url):
            # Try to extract image from Reddit gallery or imgur
            image_url = self._extract_image_url(url)
            if not image_url:
                return None
            url = image_url

        # Filter by title keywords to ensure it's wallpaper-related
        title = submission_data.get('title', '').lower()
        if not self._is_wallpaper_related(title):
            return None

        return {
            'title': submission_data.get('title', ''),
            'url': url,
            'id': submission_data.get('id', ''),
            'score': submission_data.get('score', 0),
            'num_comments': submission_data.get('num_comments', 0),
            'created_utc': submission_data.get('created_utc', 0),
            'author': submission_data.get('author', '[deleted]'),
            'subreddit': submission_data.get('subreddit', ''),
            'permalink': submission_data.get('permalink', ''),
            'source': 'reddit'
        }

    def _is_image_url(self, url: str) -> bool:
        """Check if URL points directly to an image."""
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
        parsed_url = urlparse(url.lower())
        return any(parsed_url.path.endswith(ext) for ext in image_extensions)

    def _extract_image_url(self, url: str) -> Optional[str]:
        """Try to extract direct image URL from Reddit/Imgur links."""
        # Handle common Reddit and Imgur patterns

        # Reddit image/gallery URLs
        if 'reddit.com/gallery/' in url or 'redd.it/' in url:
            # These would need additional API calls to resolve
            return None

        # Imgur direct links
        if 'imgur.com' in url and not url.endswith(('.jpg', '.png', '.gif')):
            # Convert imgur page URL to direct image URL
            imgur_id = re.search(r'imgur\.com/(\w+)', url)
            if imgur_id:
                return f"https://i.imgur.com/{imgur_id.group(1)}.jpg"

        return None

    def _is_wallpaper_related(self, title: str) -> bool:
        """Check if post title suggests it's wallpaper content."""
        wallpaper_keywords = [
            'wallpaper', 'background', 'desktop', 'screen',
            'resolution', '1920x1080', '4k', '2560x1440',
            'nature', 'landscape', 'space', 'abstract',
            'minimal', 'city', 'mountain', 'ocean'
        ]

        # Always include if it's from wallpaper-specific subreddits
        wallpaper_subreddits = ['wallpapers', 'wallpaper', 'widescreenwallpaper', 'minimalwallpaper']

        return (any(keyword in title for keyword in wallpaper_keywords) or
                any(sub in title.lower() for sub in wallpaper_subreddits))

    def download_wallpaper(self, wallpaper: Dict[str, Any],
                          save_path: Optional[Path] = None) -> Optional[Path]:
        """
        Download a wallpaper from Reddit.

        Args:
            wallpaper: Wallpaper metadata dictionary
            save_path: Directory to save the wallpaper

        Returns:
            Path to the downloaded file, or None if failed
        """
        try:
            self._rate_limit()

            url = wallpaper['url']

            # Create save path
            if save_path is None:
                save_path = Path.home() / "Pictures" / "Wallpapers" / "community"

            save_path.mkdir(parents=True, exist_ok=True)

            # Generate filename
            title = wallpaper.get('title', wallpaper['id'])
            safe_title = "".join(c for c in title[:50] if c.isalnum() or c in (' ', '-', '_')).rstrip()

            # Get file extension from URL
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.split('.')
            extension = f".{path_parts[-1]}" if len(path_parts) > 1 else ".jpg"

            filename = f"reddit_{safe_title}_{wallpaper['id']}{extension}"
            file_path = save_path / filename

            # Handle filename conflicts
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                suffix = original_path.suffix
                file_path = original_path.parent / f"{stem}_{counter}{suffix}"
                counter += 1

            # Download the image
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"URL does not point to an image: {url}")
                return None

            # Save the file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded Reddit wallpaper: {file_path}")
            return file_path

        except requests.RequestException as e:
            logger.error(f"Failed to download wallpaper {wallpaper['id']}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading wallpaper: {e}")
            return None

    def get_popular_subreddits(self) -> List[str]:
        """Get list of popular wallpaper subreddits."""
        return self.WALLPAPER_SUBREDDITS.copy()

    def search_wallpapers(self, query: str, subreddit: str = 'wallpapers',
                         limit: int = 25) -> List[Dict[str, Any]]:
        """
        Search for wallpapers with specific keywords.

        Args:
            query: Search query
            subreddit: Subreddit to search in
            limit: Maximum number of results

        Returns:
            List of matching wallpaper posts
        """
        try:
            self._rate_limit()

            if self.reddit:
                sub = self.reddit.subreddit(subreddit)
                submissions = sub.search(query, limit=limit, sort='top', time_filter='all')

                wallpapers = []
                for submission in submissions:
                    wallpaper_data = self._process_submission(submission)
                    if wallpaper_data:
                        wallpapers.append(wallpaper_data)

                return wallpapers
            else:
                # Use JSON API for search
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {
                    'q': query,
                    'restrict_sr': 'on',
                    'sort': 'top',
                    'limit': limit
                }

                response = self.session.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                wallpapers = []

                for post in data.get('data', {}).get('children', []):
                    submission_data = post.get('data', {})
                    wallpaper_data = self._process_submission_dict(submission_data)
                    if wallpaper_data:
                        wallpapers.append(wallpaper_data)

                return wallpapers

        except Exception as e:
            logger.error(f"Failed to search wallpapers: {e}")
            return []

    def test_connection(self) -> bool:
        """
        Test connection to Reddit.

        Returns:
            True if Reddit is accessible, False otherwise
        """
        try:
            response = self.session.get("https://www.reddit.com/r/wallpapers.json?limit=1")
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Failed to connect to Reddit: {e}")
            return False


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    client = RedditClient()

    # Test connection
    if client.test_connection():
        print("Reddit is accessible")
    else:
        print("Reddit is not accessible")

    # Get popular wallpapers
    print("\\nFetching popular wallpapers from r/wallpapers...")
    wallpapers = client.get_wallpapers(subreddit='wallpapers', limit=5)

    for wallpaper in wallpapers:
        print(f"Title: {wallpaper['title'][:60]}...")
        print(f"Score: {wallpaper['score']}, Comments: {wallpaper['num_comments']}")
        print(f"URL: {wallpaper['url']}")
        print("---")

    # Show available subreddits
    print(f"\\nAvailable wallpaper subreddits: {', '.join(client.get_popular_subreddits())}")