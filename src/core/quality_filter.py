"""
Image quality filtering and validation system.

Provides advanced filtering capabilities for wallpapers including
resolution checks, aspect ratio validation, content analysis,
and duplicate detection with perceptual hashing.
"""

import logging
import hashlib
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
from PIL import Image, ImageStat, ImageFilter
import imagehash
import numpy as np


logger = logging.getLogger(__name__)


class QualityFilter:
    """Advanced image quality filtering and validation."""

    def __init__(self):
        """Initialize the quality filter."""
        # Minimum resolution requirements
        self.min_width = 1280
        self.min_height = 720

        # Aspect ratio constraints (width/height)
        self.min_aspect_ratio = 0.5   # Very tall images
        self.max_aspect_ratio = 3.5   # Very wide images

        # Quality thresholds
        self.min_file_size = 50 * 1024        # 50KB minimum
        self.max_file_size = 50 * 1024 * 1024 # 50MB maximum

        # Perceptual hash storage for duplicate detection
        self.known_hashes: Set[str] = set()
        self.known_phashes: Set[str] = set()

    def validate_wallpaper(self, image_path: Path,
                          strict_mode: bool = False) -> Dict[str, any]:
        """
        Comprehensively validate an image for wallpaper suitability.

        Args:
            image_path: Path to the image file
            strict_mode: Enable stricter validation criteria

        Returns:
            Dictionary with validation results and metrics
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'metrics': {},
            'recommendations': []
        }

        try:
            # Basic file checks
            if not image_path.exists():
                result['errors'].append("File does not exist")
                return result

            file_size = image_path.stat().st_size
            result['metrics']['file_size'] = file_size

            if file_size < self.min_file_size:
                result['errors'].append(f"File too small: {file_size} bytes")
                return result

            if file_size > self.max_file_size:
                result['warnings'].append(f"Large file size: {file_size // (1024*1024)}MB")

            # Load and validate image
            with Image.open(image_path) as img:
                # Basic image properties
                width, height = img.size
                mode = img.mode
                format_name = img.format

                result['metrics'].update({
                    'width': width,
                    'height': height,
                    'aspect_ratio': width / height,
                    'mode': mode,
                    'format': format_name,
                    'channels': len(img.getbands())
                })

                # Resolution validation
                if width < self.min_width or height < self.min_height:
                    result['errors'].append(
                        f"Resolution too low: {width}x{height} (minimum: {self.min_width}x{self.min_height})"
                    )

                # Aspect ratio validation
                aspect_ratio = width / height
                if aspect_ratio < self.min_aspect_ratio or aspect_ratio > self.max_aspect_ratio:
                    result['errors'].append(
                        f"Invalid aspect ratio: {aspect_ratio:.2f} (range: {self.min_aspect_ratio}-{self.max_aspect_ratio})"
                    )

                # Format validation
                if format_name not in ['JPEG', 'PNG', 'WEBP', 'BMP']:
                    result['warnings'].append(f"Unusual format: {format_name}")

                # Color mode validation
                if mode not in ['RGB', 'RGBA']:
                    if mode in ['L', 'LA']:  # Grayscale
                        result['warnings'].append("Grayscale image")
                    else:
                        result['warnings'].append(f"Unusual color mode: {mode}")

                # Advanced quality checks
                if not result['errors']:  # Only if basic validation passed
                    quality_metrics = self._analyze_image_quality(img, strict_mode)
                    result['metrics'].update(quality_metrics)

                    # Check for quality issues
                    if quality_metrics.get('is_blurry', False):
                        result['warnings'].append("Image appears blurry")

                    if quality_metrics.get('is_too_dark', False):
                        result['warnings'].append("Image is very dark")

                    if quality_metrics.get('is_too_bright', False):
                        result['warnings'].append("Image is very bright")

                    if quality_metrics.get('low_contrast', False):
                        result['warnings'].append("Low contrast image")

                    # Duplicate detection
                    if self._is_duplicate(img, image_path):
                        result['errors'].append("Duplicate image detected")

                # Generate recommendations
                result['recommendations'] = self._generate_recommendations(result['metrics'])

                # Determine overall validity
                result['valid'] = len(result['errors']) == 0

                return result

        except Exception as e:
            result['errors'].append(f"Failed to process image: {e}")
            logger.error(f"Image validation failed for {image_path}: {e}")
            return result

    def _analyze_image_quality(self, img: Image.Image, strict_mode: bool) -> Dict[str, any]:
        """
        Analyze image quality metrics.

        Args:
            img: PIL Image object
            strict_mode: Enable stricter analysis

        Returns:
            Dictionary with quality metrics
        """
        metrics = {}

        try:
            # Convert to RGB if necessary for analysis
            if img.mode != 'RGB':
                analysis_img = img.convert('RGB')
            else:
                analysis_img = img

            # Basic statistics
            stat = ImageStat.Stat(analysis_img)
            metrics['mean_brightness'] = sum(stat.mean) / len(stat.mean)
            metrics['stddev_brightness'] = sum(stat.stddev) / len(stat.stddev)

            # Brightness analysis
            brightness = metrics['mean_brightness']
            metrics['is_too_dark'] = brightness < 30
            metrics['is_too_bright'] = brightness > 220

            # Contrast analysis
            contrast = metrics['stddev_brightness']
            metrics['contrast'] = contrast
            metrics['low_contrast'] = contrast < 20

            # Blur detection (using Laplacian variance)
            if strict_mode:
                metrics.update(self._detect_blur(analysis_img))

            # Color diversity
            metrics['color_diversity'] = self._calculate_color_diversity(analysis_img)

            # Dominant colors
            if strict_mode:
                metrics['dominant_colors'] = self._get_dominant_colors(analysis_img)

        except Exception as e:
            logger.warning(f"Quality analysis failed: {e}")

        return metrics

    def _detect_blur(self, img: Image.Image) -> Dict[str, any]:
        """
        Detect if image is blurry using Laplacian variance.

        Args:
            img: PIL Image in RGB mode

        Returns:
            Dictionary with blur detection metrics
        """
        try:
            # Convert to grayscale for blur detection
            gray = img.convert('L')

            # Resize for faster processing if image is very large
            if gray.size[0] > 1920 or gray.size[1] > 1080:
                gray = gray.resize((1920, 1080), Image.Resampling.LANCZOS)

            # Convert to numpy array
            gray_array = np.array(gray)

            # Calculate Laplacian variance
            # Using a simple approximation of Laplacian
            kernel = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]])

            # Apply convolution manually (simplified)
            height, width = gray_array.shape
            laplacian = np.zeros_like(gray_array, dtype=np.float32)

            for i in range(1, height - 1):
                for j in range(1, width - 1):
                    laplacian[i, j] = (
                        4 * gray_array[i, j] -
                        gray_array[i-1, j] - gray_array[i+1, j] -
                        gray_array[i, j-1] - gray_array[i, j+1]
                    )

            variance = np.var(laplacian)

            # Threshold for blur detection (tuned for wallpapers)
            blur_threshold = 100  # Lower values indicate more blur

            return {
                'laplacian_variance': float(variance),
                'is_blurry': variance < blur_threshold
            }

        except Exception as e:
            logger.warning(f"Blur detection failed: {e}")
            return {'laplacian_variance': 0, 'is_blurry': False}

    def _calculate_color_diversity(self, img: Image.Image) -> float:
        """
        Calculate color diversity score.

        Args:
            img: PIL Image in RGB mode

        Returns:
            Color diversity score (0-1, higher is more diverse)
        """
        try:
            # Resize for faster processing
            small_img = img.resize((100, 100), Image.Resampling.LANCZOS)

            # Get colors and count unique ones
            colors = small_img.getdata()
            unique_colors = set(colors)

            # Calculate diversity as ratio of unique colors to total pixels
            diversity = len(unique_colors) / (100 * 100)

            return min(diversity, 1.0)  # Cap at 1.0

        except Exception as e:
            logger.warning(f"Color diversity calculation failed: {e}")
            return 0.5  # Default moderate diversity

    def _get_dominant_colors(self, img: Image.Image, num_colors: int = 5) -> List[Tuple[int, int, int]]:
        """
        Get dominant colors in the image.

        Args:
            img: PIL Image in RGB mode
            num_colors: Number of dominant colors to extract

        Returns:
            List of RGB tuples for dominant colors
        """
        try:
            # Resize for faster processing
            small_img = img.resize((150, 150), Image.Resampling.LANCZOS)

            # Simple color quantization
            quantized = small_img.quantize(colors=num_colors)
            palette = quantized.getpalette()

            # Extract RGB values
            dominant_colors = []
            for i in range(num_colors):
                r = palette[i * 3]
                g = palette[i * 3 + 1]
                b = palette[i * 3 + 2]
                dominant_colors.append((r, g, b))

            return dominant_colors

        except Exception as e:
            logger.warning(f"Dominant color extraction failed: {e}")
            return [(128, 128, 128)]  # Default gray

    def _is_duplicate(self, img: Image.Image, image_path: Path) -> bool:
        """
        Check if image is a duplicate using perceptual hashing.

        Args:
            img: PIL Image object
            image_path: Path to the image file

        Returns:
            True if image is a duplicate
        """
        try:
            # File hash for exact duplicates
            file_hash = self._calculate_file_hash(image_path)
            if file_hash in self.known_hashes:
                return True

            # Perceptual hash for near duplicates
            phash = str(imagehash.phash(img))
            if phash in self.known_phashes:
                return True

            # Check for similar hashes (Hamming distance <= 5)
            for known_phash in self.known_phashes:
                try:
                    current_hash = imagehash.hex_to_hash(phash)
                    known_hash = imagehash.hex_to_hash(known_phash)
                    if current_hash - known_hash <= 5:  # Hamming distance
                        return True
                except ValueError:
                    continue

            # Store hashes for future comparisons
            self.known_hashes.add(file_hash)
            self.known_phashes.add(phash)

            return False

        except Exception as e:
            logger.warning(f"Duplicate detection failed: {e}")
            return False

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for exact duplicate detection."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"File hash calculation failed: {e}")
            return ""

    def _generate_recommendations(self, metrics: Dict[str, any]) -> List[str]:
        """
        Generate recommendations based on image metrics.

        Args:
            metrics: Image quality metrics

        Returns:
            List of recommendation strings
        """
        recommendations = []

        width = metrics.get('width', 0)
        height = metrics.get('height', 0)

        # Resolution recommendations
        if width >= 3840 and height >= 2160:
            recommendations.append("Excellent for 4K displays")
        elif width >= 2560 and height >= 1440:
            recommendations.append("Great for QHD displays")
        elif width >= 1920 and height >= 1080:
            recommendations.append("Good for Full HD displays")

        # Aspect ratio recommendations
        aspect_ratio = metrics.get('aspect_ratio', 1.0)
        if 2.3 <= aspect_ratio <= 2.4:
            recommendations.append("Perfect for ultrawide monitors")
        elif 1.7 <= aspect_ratio <= 1.8:
            recommendations.append("Suitable for standard widescreen")
        elif 0.55 <= aspect_ratio <= 0.65:
            recommendations.append("Good for mobile wallpapers")

        # Quality recommendations
        contrast = metrics.get('contrast', 0)
        if contrast > 50:
            recommendations.append("High contrast - great visual impact")

        color_diversity = metrics.get('color_diversity', 0)
        if color_diversity > 0.3:
            recommendations.append("Rich color palette")

        return recommendations

    def batch_validate(self, image_paths: List[Path],
                      strict_mode: bool = False) -> Dict[Path, Dict[str, any]]:
        """
        Validate multiple images in batch.

        Args:
            image_paths: List of image file paths
            strict_mode: Enable stricter validation

        Returns:
            Dictionary mapping paths to validation results
        """
        results = {}

        for image_path in image_paths:
            logger.info(f"Validating: {image_path}")
            results[image_path] = self.validate_wallpaper(image_path, strict_mode)

        return results

    def get_validation_summary(self, results: Dict[Path, Dict[str, any]]) -> Dict[str, any]:
        """
        Generate summary statistics from validation results.

        Args:
            results: Validation results from batch_validate

        Returns:
            Summary statistics dictionary
        """
        total_images = len(results)
        valid_images = sum(1 for result in results.values() if result['valid'])
        invalid_images = total_images - valid_images

        error_counts = {}
        warning_counts = {}

        for result in results.values():
            for error in result['errors']:
                error_counts[error] = error_counts.get(error, 0) + 1
            for warning in result['warnings']:
                warning_counts[warning] = warning_counts.get(warning, 0) + 1

        return {
            'total_images': total_images,
            'valid_images': valid_images,
            'invalid_images': invalid_images,
            'validation_rate': valid_images / total_images if total_images > 0 else 0,
            'common_errors': sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'common_warnings': sorted(warning_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    quality_filter = QualityFilter()

    # Example validation
    test_images = [
        Path("test_image_1.jpg"),
        Path("test_image_2.png"),
    ]

    # Note: These files don't exist, this is just for demonstration
    for test_image in test_images:
        if test_image.exists():
            result = quality_filter.validate_wallpaper(test_image)
            print(f"\\nValidation for {test_image}:")
            print(f"Valid: {result['valid']}")
            print(f"Errors: {result['errors']}")
            print(f"Warnings: {result['warnings']}")
            print(f"Recommendations: {result['recommendations']}")
        else:
            print(f"Test image {test_image} not found - skipping")