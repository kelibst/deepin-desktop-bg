"""
Craiyon (formerly DALL-E Mini) client for unlimited free AI wallpaper generation.

Provides access to Craiyon's free AI image generation service through
the Apify API wrapper with commercial use rights and attribution.
"""

import logging
import requests
import time
import base64
from typing import List, Dict, Optional, Any
from pathlib import Path
import tempfile
from apify_client import ApifyClient


logger = logging.getLogger(__name__)


class CraiyonClient:
    """Client for Craiyon AI image generation service."""

    CRAIYON_URL = "https://www.craiyon.com"
    APIFY_ACTOR_ID = "muhammetakkurtt/craiyon-ai-image-creator"

    def __init__(self, apify_token: Optional[str] = None):
        """
        Initialize the Craiyon client.

        Args:
            apify_token: Optional Apify API token for higher rate limits.
                        Can use without token but with limitations.
        """
        self.apify_token = apify_token
        self.apify_client = ApifyClient(apify_token) if apify_token else None

        # Rate limiting for free tier
        self.last_request_time = 0
        self.min_request_interval = 5.0  # Conservative rate limiting
        self.max_generations_per_hour = 10  # Conservative limit

        # Generation tracking
        self.generations_this_hour = 0
        self.hour_start_time = time.time()

    def _rate_limit(self) -> None:
        """Apply rate limiting to respect free tier limits."""
        current_time = time.time()

        # Reset hourly counter
        if current_time - self.hour_start_time > 3600:
            self.generations_this_hour = 0
            self.hour_start_time = current_time

        # Check hourly limit
        if self.generations_this_hour >= self.max_generations_per_hour:
            logger.warning("Hourly generation limit reached for Craiyon")
            return False

        # Apply minimum interval
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()
        return True

    def generate_wallpaper(self,
                          prompt: str,
                          style: str = "art",
                          count: int = 1,
                          save_path: Optional[Path] = None) -> List[Path]:
        """
        Generate wallpapers using Craiyon AI.

        Args:
            prompt: Text description of the desired wallpaper
            style: Generation style ('art', 'drawing', 'photo')
            count: Number of variations to generate (1-9)
            save_path: Directory to save generated wallpapers

        Returns:
            List of paths to generated wallpaper files
        """
        if not self._rate_limit():
            return []

        try:
            # Enhance prompt for wallpaper generation
            enhanced_prompt = self._enhance_wallpaper_prompt(prompt, style)

            logger.info(f"Generating {count} wallpaper(s) with Craiyon: {enhanced_prompt}")

            if self.apify_client:
                generated_images = self._generate_via_apify(enhanced_prompt, style, count)
            else:
                generated_images = self._generate_via_direct_api(enhanced_prompt, style, count)

            if not generated_images:
                return []

            # Save generated images
            saved_paths = []
            if save_path is None:
                save_path = Path.home() / "Pictures" / "Wallpapers" / "ai_generated"

            save_path.mkdir(parents=True, exist_ok=True)

            for i, image_data in enumerate(generated_images):
                # Create filename
                safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = f"craiyon_{safe_prompt}_{style}_{i+1}.png"
                file_path = save_path / filename

                # Handle filename conflicts
                counter = 1
                original_path = file_path
                while file_path.exists():
                    stem = original_path.stem
                    suffix = original_path.suffix
                    file_path = original_path.parent / f"{stem}_v{counter}{suffix}"
                    counter += 1

                # Save the image
                try:
                    if isinstance(image_data, str):
                        # Base64 encoded image
                        image_bytes = base64.b64decode(image_data)
                    else:
                        # Raw bytes
                        image_bytes = image_data

                    with open(file_path, 'wb') as f:
                        f.write(image_bytes)

                    saved_paths.append(file_path)
                    logger.info(f"Saved Craiyon wallpaper: {file_path}")

                except Exception as e:
                    logger.error(f"Failed to save image {i+1}: {e}")

            self.generations_this_hour += len(saved_paths)
            return saved_paths

        except Exception as e:
            logger.error(f"Failed to generate wallpapers with Craiyon: {e}")
            return []

    def _enhance_wallpaper_prompt(self, prompt: str, style: str) -> str:
        """
        Enhance a user prompt for better wallpaper generation.

        Args:
            prompt: Original user prompt
            style: Generation style

        Returns:
            Enhanced prompt optimized for wallpaper generation
        """
        style_enhancements = {
            "art": "digital art, wallpaper, desktop background, high quality",
            "drawing": "artistic drawing, wallpaper, desktop background, detailed",
            "photo": "photographic style, wallpaper, desktop background, high resolution"
        }

        # Add wallpaper-specific terms
        wallpaper_terms = "desktop wallpaper, background image, wide format, landscape orientation"

        base_enhancement = style_enhancements.get(style, style_enhancements["art"])

        return f"{prompt}, {base_enhancement}, {wallpaper_terms}"

    def _generate_via_apify(self, prompt: str, style: str, count: int) -> List[bytes]:
        """
        Generate images using the Apify API wrapper.

        Args:
            prompt: Enhanced prompt for generation
            style: Generation style
            count: Number of images to generate

        Returns:
            List of image data as bytes
        """
        try:
            run_input = {
                "prompt": prompt,
                "type": style.capitalize(),  # Art, Drawing, Photo
                "aspectRatio": "Landscape",  # Better for wallpapers
                "excludeWords": "nsfw, inappropriate, explicit"
            }

            logger.debug(f"Starting Apify actor run with input: {run_input}")

            # Start the actor
            run = self.apify_client.actor(self.APIFY_ACTOR_ID).call(run_input=run_input)

            # Get results
            images = []
            for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                if "imageUrls" in item:
                    for image_url in item["imageUrls"][:count]:
                        try:
                            response = requests.get(image_url, timeout=30)
                            response.raise_for_status()
                            images.append(response.content)
                        except requests.RequestException as e:
                            logger.error(f"Failed to download generated image: {e}")

            return images

        except Exception as e:
            logger.error(f"Apify generation failed: {e}")
            return []

    def _generate_via_direct_api(self, prompt: str, style: str, count: int) -> List[bytes]:
        """
        Generate images using direct API calls (fallback method).

        This is a placeholder for direct integration with Craiyon's API.
        In practice, you would need to reverse engineer their API or
        use a web scraping approach.

        Args:
            prompt: Enhanced prompt for generation
            style: Generation style
            count: Number of images to generate

        Returns:
            List of image data as bytes
        """
        logger.warning("Direct Craiyon API not implemented - using placeholder")

        # Placeholder implementation
        # In a real implementation, this would:
        # 1. Make POST request to Craiyon's generation endpoint
        # 2. Poll for completion
        # 3. Download the generated images

        return []

    def get_wallpaper_templates(self) -> List[Dict[str, str]]:
        """
        Get pre-made prompt templates optimized for Craiyon generation.

        Returns:
            List of template dictionaries with 'name', 'prompt', and 'style'
        """
        return [
            {
                'name': 'Mountain Vista',
                'prompt': 'majestic mountain landscape with snow peaks and alpine lake',
                'style': 'photo'
            },
            {
                'name': 'Space Art',
                'prompt': 'cosmic nebula with bright stars and galaxies',
                'style': 'art'
            },
            {
                'name': 'Abstract Waves',
                'prompt': 'flowing abstract waves in vibrant colors',
                'style': 'art'
            },
            {
                'name': 'Forest Scene',
                'prompt': 'peaceful forest with sunlight through trees',
                'style': 'photo'
            },
            {
                'name': 'Geometric Art',
                'prompt': 'colorful geometric patterns and shapes',
                'style': 'art'
            },
            {
                'name': 'Ocean Sunset',
                'prompt': 'beautiful ocean sunset with golden sky',
                'style': 'photo'
            },
            {
                'name': 'Digital Landscape',
                'prompt': 'futuristic digital landscape with neon colors',
                'style': 'art'
            },
            {
                'name': 'Minimalist Design',
                'prompt': 'clean minimalist design with simple shapes',
                'style': 'drawing'
            }
        ]

    def get_styles(self) -> List[str]:
        """Get available generation styles."""
        return ['art', 'drawing', 'photo']

    def test_connection(self) -> bool:
        """
        Test connection to Craiyon service.

        Returns:
            True if service is accessible, False otherwise
        """
        try:
            response = requests.get(self.CRAIYON_URL, timeout=10)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Failed to connect to Craiyon: {e}")
            return False

    def get_generation_stats(self) -> Dict[str, Any]:
        """
        Get current generation statistics and limits.

        Returns:
            Dictionary with generation stats and remaining limits
        """
        current_time = time.time()

        # Reset hourly counter if needed
        if current_time - self.hour_start_time > 3600:
            self.generations_this_hour = 0
            self.hour_start_time = current_time

        remaining_this_hour = max(0, self.max_generations_per_hour - self.generations_this_hour)

        return {
            'generations_this_hour': self.generations_this_hour,
            'remaining_this_hour': remaining_this_hour,
            'max_per_hour': self.max_generations_per_hour,
            'has_apify_token': self.apify_token is not None,
            'time_until_reset': max(0, 3600 - (current_time - self.hour_start_time))
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    client = CraiyonClient()

    # Test connection
    if client.test_connection():
        print("Craiyon service is accessible")
    else:
        print("Craiyon service is not accessible")

    # Show generation stats
    stats = client.get_generation_stats()
    print(f"Generation stats: {stats}")

    # Show available templates
    print("\\nAvailable wallpaper templates:")
    for template in client.get_wallpaper_templates():
        print(f"- {template['name']}: {template['prompt']} ({template['style']})")

    # Generate a wallpaper (requires Apify token for actual generation)
    # wallpapers = client.generate_wallpaper(
    #     prompt="beautiful mountain landscape at sunset",
    #     style="photo",
    #     count=2
    # )
    # print(f"Generated {len(wallpapers)} wallpapers")