"""
Image processing utilities for file-based storage
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("Pillow library not installed. Image functionality will be limited.")

# Папка для хранения изображений
IMG_DIR = Path("IMG")
THUMBS_DIR = IMG_DIR / "thumbs"
PDF_ICON_PATH = IMG_DIR / "pdf_icon.png"  # здесь должна быть иконка PDF

# Создаем папки, если не существуют
IMG_DIR.mkdir(parents=True, exist_ok=True)
THUMBS_DIR.mkdir(parents=True, exist_ok=True)


class ImageUtils:
    """Image processing utilities for file-based storage"""
    
    @staticmethod
    def save_image(file_path: Path, target_name: str) -> Optional[Path]:
        """Сохраняет изображение или PDF в IMG/"""
        try:
            file_path = Path(file_path)
            ext = file_path.suffix.lower()
            
            if ext == ".pdf":
                target_path = IMG_DIR / f"{target_name}.pdf"
                target_path.write_bytes(file_path.read_bytes())
                return target_path
            
            elif ext in (".jpg", ".jpeg", ".png", ".gif"):
                if not HAS_PIL:
                    logger.warning("Pillow not installed, copying file as is.")
                    target_path = IMG_DIR / f"{target_name}{ext}"
                    target_path.write_bytes(file_path.read_bytes())
                    return target_path
                
                img = Image.open(file_path)
                # Сжимаем до ширины 800 и высоты 600
                img.thumbnail((800, 600), Image.LANCZOS)
                target_path = IMG_DIR / f"{target_name}.jpg"
                img = img.convert("RGB")  # всегда сохраняем в RGB JPEG
                img.save(target_path, format="JPEG", quality=85)
                return target_path
            
            else:
                logger.error(f"Unsupported file type: {ext}")
                return None
        
        except Exception as e:
            logger.error(f"Error saving image {file_path}: {e}")
            return None
    
    @staticmethod
    def create_thumbnail(file_path: Path, target_name: str, size: Tuple[int, int] = (200, 200)) -> Optional[Path]:
        """Создает миниатюру и сохраняет в IMG/thumbs"""
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        if ext == ".pdf":
            return PDF_ICON_PATH  # для PDF используем иконку
        
        if not HAS_PIL:
            logger.warning("Pillow not installed, thumbnail cannot be created.")
            return None
        
        try:
            img = Image.open(file_path)
            img.thumbnail(size, Image.LANCZOS)
            thumb_path = THUMBS_DIR / f"{target_name}.jpg"
            img = img.convert("RGB")
            img.save(thumb_path, format="JPEG", quality=85)
            return thumb_path
        except Exception as e:
            logger.error(f"Error creating thumbnail for {file_path}: {e}")
            return None

    @staticmethod
    def is_pdf(file_path: Path) -> bool:
        """Проверяет, является ли файл PDF"""
        return Path(file_path).suffix.lower() == ".pdf"

    @staticmethod
    def get_pdf_icon_path() -> Path:
        """Возвращает путь к иконке PDF"""
        return PDF_ICON_PATH

    @staticmethod
    def validate_image(file_path: Path, max_size_mb: int = 10) -> Tuple[bool, str]:
        """Проверяет размер и корректность изображения или PDF"""
        file_path = Path(file_path)
        if not file_path.exists():
            return False, "File does not exist"
        
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            return False, f"File too large ({size_mb:.1f}MB > {max_size_mb}MB)"
        
        if file_path.suffix.lower() == ".pdf":
            return True, "PDF file"
        
        if HAS_PIL:
            try:
                img = Image.open(file_path)
                img.verify()
                return True, f"Valid {img.format} image, {img.width}x{img.height}"
            except Exception as e:
                return False, f"Invalid image file: {e}"
        
        return True, "File exists (PIL not available for validation)"
