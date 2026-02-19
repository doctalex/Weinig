"""
Image processing utilities
"""
import io
import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("Pillow library not installed. Image functionality will be limited.")

class ImageUtils:
    """Image processing utilities"""
    
    @staticmethod
    def load_image(filepath: str) -> Optional[bytes]:
        """Loads an image from a file"""
        try:
            with open(filepath, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading image from {filepath}: {e}")
            return None
    
    @staticmethod
    def resize_image(image_data: bytes, max_width: int = 800, 
                    max_height: int = 600) -> Optional[bytes]:
        """Resizes an image"""
        if not HAS_PIL or not image_data:
            return image_data
        
        try:
            img = Image.open(io.BytesIO(image_data))
            
            # Maintain aspect ratio
            width, height = img.size
            
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                if img.mode == 'P' and 'transparency' in img.info:
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
            
            # Save to bytes
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            return image_data
    
    @staticmethod
    def create_thumbnail(image_data: bytes, size: Tuple[int, int] = (200, 200)) -> Optional[bytes]:
        """Creates a thumbnail of the image"""
        if not HAS_PIL or not image_data:
            return None
        
        try:
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail(size, Image.LANCZOS)
            
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                if img.mode == 'P' and 'transparency' in img.info:
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
            
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            return None
    
    @staticmethod
    def get_image_info(image_data: bytes) -> Optional[dict]:
        """Gets information about the image"""
        if not HAS_PIL or not image_data:
            return None
        
        try:
            img = Image.open(io.BytesIO(image_data))
            return {
                'format': img.format,
                'size': img.size,
                'mode': img.mode,
                'width': img.width,
                'height': img.height
            }
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return None
    
    @staticmethod
    def validate_image(image_data: bytes, max_size_mb: int = 10) -> Tuple[bool, str]:
        """Validates the image"""
        if not image_data:
            return True, "No image"
        
        # Check size
        size_mb = len(image_data) / (1024 * 1024)
        if size_mb > max_size_mb:
            return False, f"Image too large ({size_mb:.1f}MB > {max_size_mb}MB)"
        
        if HAS_PIL:
            try:
                img = Image.open(io.BytesIO(image_data))
                img.verify()  # Verify file integrity
                return True, f"Valid {img.format} image, {img.width}x{img.height}"
            except Exception as e:
                return False, f"Invalid image file: {str(e)}"
        
        return True, "Image loaded (PIL not available for validation)"