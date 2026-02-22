"""
Улучшенный менеджер для работы с PDF файлами профилей (строгое именование ID.pdf)
"""
import os
import shutil
import logging
import hashlib
from pathlib import Path
from typing import Optional, Tuple, List
import tempfile

logger = logging.getLogger(__name__)

class PDFManager:
    """Менеджер для работы с PDF файлами профилей"""
    
    def __init__(self, base_folder: Optional[str] = None):
        if base_folder is None:
            project_root = Path(__file__).parent.parent
            self.pdf_folder = project_root / 'img' / 'profile_pdfs'
        else:
            self.pdf_folder = Path(base_folder)
        
        self.pdf_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"PDF manager initialized. Folder: {self.pdf_folder}")
    
    def save_profile_pdf(self, profile_id: int, pdf_data: bytes, 
                         original_filename: Optional[str] = None,
                         overwrite_existing: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Сохраняет PDF файл профиля строго в формате ID.pdf (например, 001.pdf)
        """
        try:
            logger.info(f"=== SAVE PDF START ===")
            if not pdf_data:
                logger.error("PDF data is empty!")
                return False, None
            
            # Строгое имя файла
            target_filename = f"{profile_id:03d}.pdf"
            filepath = self.pdf_folder / target_filename
            
            # Проверка на изменения через хэш
            if filepath.exists() and overwrite_existing:
                new_hash = hashlib.md5(pdf_data).hexdigest()[:8]
                if self._get_file_hash(filepath) == new_hash:
                    logger.info(f"PDF unchanged, skipping write.")
                    return True, str(filepath)

            # Удаляем старые файлы этого профиля (и 001.pdf и profile_0001_xxx.pdf)
            self._delete_old_profile_pdfs(profile_id, keep_file=str(filepath))

            # Windows fix: принудительное удаление перед записью
            if filepath.exists():
                try: os.remove(filepath)
                except: pass

            with open(filepath, 'wb') as f:
                f.write(pdf_data)
                f.flush()
                os.fsync(f.fileno())
            
            logger.info(f"✓ PDF успешно сохранен: {target_filename}")
            return True, str(filepath)
                
        except Exception as e:
            logger.error(f"Ошибка сохранения PDF: {e}", exc_info=True)
            return False, None

    def _find_profile_pdfs(self, profile_id: int) -> List[Path]:
        """Находит все PDF файлы, относящиеся к ID (новый и старый форматы)"""
        found = []
        short_name = f"{profile_id:03d}.pdf"
        old_prefix = f"profile_{profile_id:04d}"
        
        for file_path in self.pdf_folder.glob("*.pdf"):
            if file_path.name == short_name or file_path.name.startswith(old_prefix):
                found.append(file_path)
        return sorted(found)

    def _delete_old_profile_pdfs(self, profile_id: int, keep_file: Optional[str] = None) -> None:
        """Вычищает все вариации файлов для конкретного профиля"""
        for file_path in self._find_profile_pdfs(profile_id):
            if keep_file and str(file_path.absolute()) == str(Path(keep_file).absolute()):
                continue
            try:
                file_path.unlink()
                logger.info(f"Deleted old PDF: {file_path.name}")
            except Exception as e:
                logger.warning(f"Could not delete {file_path.name}: {e}")

    def load_profile_pdf(self, profile_id: int, pdf_path: Optional[str] = None) -> Optional[bytes]:
        """Загружает данные PDF, пробуя сначала переданный путь, затем поиск по ID"""
        try:
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f: return f.read()
            
            # Поиск по папке, если путь из базы не сработал
            files = self._find_profile_pdfs(profile_id)
            if files:
                with open(files[0], 'rb') as f: return f.read()
            return None
        except Exception as e:
            logger.error(f"Ошибка загрузки PDF {profile_id}: {e}")
            return None

    def delete_profile_pdf(self, profile_id: int, pdf_path: Optional[str] = None) -> bool:
        """Удаляет файлы профиля. Если путь не указан - удаляет все найденные для ID"""
        if pdf_path and os.path.exists(pdf_path):
            if self._is_file_belongs_to_profile(os.path.basename(pdf_path), profile_id):
                try:
                    os.remove(pdf_path)
                    return True
                except: return False
        
        self._delete_old_profile_pdfs(profile_id)
        return True

    def _is_file_belongs_to_profile(self, filename: str, profile_id: int) -> bool:
        """Проверка принадлежности файла профилю"""
        short_name = f"{profile_id:03d}.pdf"
        old_prefix = f"profile_{profile_id:04d}"
        return filename == short_name or filename.startswith(old_prefix)

    def _get_file_hash(self, filepath: Path) -> str:
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()[:8]
        except: return ""

    def extract_pdf_preview(self, pdf_data: bytes) -> Optional[bytes]:
        """Извлечение первой страницы через PyMuPDF (fitz)"""
        try:
            import fitz
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_data)
                tmp_path = tmp.name
            
            try:
                doc = fitz.open(tmp_path)
                if len(doc) > 0:
                    page = doc[0]
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    return pix.tobytes("png")
                return None
            finally:
                doc.close()
                if os.path.exists(tmp_path): os.unlink(tmp_path)
        except ImportError:
            logger.warning("PyMuPDF not installed.")
            return self._create_placeholder_preview()
        except Exception as e:
            logger.error(f"Preview extraction error: {e}")
            return None

    def open_pdf_external(self, pdf_path: str) -> bool:
        """Открытие в системном просмотрщике"""
        if not os.path.exists(pdf_path): return False
        try:
            if os.name == 'nt': os.startfile(pdf_path)
            else:
                import subprocess
                cmd = 'xdg-open' if os.name == 'posix' else 'open'
                subprocess.run([cmd, pdf_path], check=False)
            return True
        except Exception as e:
            logger.error(f"Error opening PDF: {e}")
            return False

    def _create_placeholder_preview(self) -> bytes:
        from PIL import Image, ImageDraw
        import io
        img = Image.new('RGB', (200, 200), color='white')
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 150, 150], outline='red', width=3)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()