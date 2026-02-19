"""
Простой менеджер для работы с PDF файлами профилей
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
    
    # Поддерживаемые MIME типы для PDF
    PDF_MIME_TYPES = ['application/pdf']
    PDF_EXTENSIONS = ['.pdf']
    
    def __init__(self, base_folder: Optional[str] = None):
        """
        Инициализация менеджера PDF
        
        Args:
            base_folder: Базовая папка для хранения PDF
        """
        if base_folder is None:
            # Определяем папку проекта
            project_root = Path(__file__).parent.parent
            self.pdf_folder = project_root / 'img' / 'profile_pdfs'
        else:
            self.pdf_folder = Path(base_folder)
        
        # Создаем папку если ее нет
        self.pdf_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"PDF manager initialized. Folder: {self.pdf_folder}")
    
    def save_profile_pdf(self, profile_id: int, pdf_data: bytes, 
                         original_filename: Optional[str] = None,
                         overwrite_existing: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Сохраняет PDF файл профиля
        
        Args:
            profile_id: ID профиля
            pdf_data: Данные PDF файла
            original_filename: Оригинальное имя файла
            overwrite_existing: Если True, перезаписывает существующий файл вместо создания нового
            
        Returns:
            Tuple[bool, Optional[str]]: (успех, путь к файлу)
        """
        try:
            logger.info(f"=== SAVE PDF START ===")
            logger.info(f"Profile ID: {profile_id}")
            logger.info(f"PDF data size: {len(pdf_data) if pdf_data else 'None'} bytes")
            logger.info(f"Original filename: {original_filename}")
            logger.info(f"Overwrite existing: {overwrite_existing}")
            
            # Проверка PDF данных
            if not pdf_data:
                logger.error("PDF data is empty or None!")
                return False, None
            
            if len(pdf_data) < 100:
                logger.warning(f"PDF data very small ({len(pdf_data)} bytes). Might be corrupted.")
            
            # Создаем папку если ее нет
            self.pdf_folder.mkdir(parents=True, exist_ok=True)
            
            # ПОИСК СУЩЕСТВУЮЩИХ PDF ФАЙЛОВ
            existing_files = self._find_profile_pdfs(profile_id)
            logger.info(f"Found {len(existing_files)} existing PDF files for profile {profile_id}")
            
            # Определяем имя файла
            if original_filename:
                safe_name = self._make_filename_safe(original_filename)
                target_filename = f"profile_{profile_id:04d}_{safe_name}"
            else:
                # Если имя файла не указано, используем первое существующее имя или генерируем новое
                if existing_files and overwrite_existing:
                    # Используем имя первого существующего файла
                    target_filename = existing_files[0].name
                    logger.info(f"Reusing existing filename: {target_filename}")
                else:
                    target_filename = f"profile_{profile_id:04d}.pdf"
            
            # Добавляем расширение если его нет
            if not target_filename.lower().endswith('.pdf'):
                target_filename += '.pdf'
            
            filepath = self.pdf_folder / target_filename
            
            # ПРОВЕРКА, НУЖНО ЛИ СОХРАНЯТЬ ФАЙЛ
            if existing_files and overwrite_existing:
                # Проверяем, существует ли уже файл с таким именем
                if filepath.exists():
                    # Сравниваем хэши
                    existing_hash = self._get_file_hash(filepath)
                    new_hash = hashlib.md5(pdf_data).hexdigest()[:8]
                    
                    if existing_hash == new_hash:
                        logger.info(f"PDF unchanged (hash: {new_hash}), skipping file write")
                        logger.info(f"=== SAVE PDF SKIPPED (unchanged) ===")
                        return True, str(filepath)
                    else:
                        logger.info(f"PDF changed (existing hash: {existing_hash}, new hash: {new_hash}), overwriting")
                
                # УДАЛЯЕМ ВСЕ СТАРЫЕ PDF ФАЙЛЫ ДЛЯ ЭТОГО ПРОФИЛЯ
                self._delete_old_profile_pdfs(profile_id, keep_file=str(filepath))
            
            # Сохраняем файл
            logger.info(f"Writing {len(pdf_data)} bytes to {filepath}")
            
            try:
                with open(filepath, 'wb') as f:
                    f.write(pdf_data)
                    f.flush()
                    os.fsync(f.fileno())
                
                # Проверяем сохранение
                if filepath.exists():
                    file_size = filepath.stat().st_size
                    if file_size == len(pdf_data):
                        logger.info(f"✓ PDF успешно сохранен: {filepath.name} ({file_size} bytes)")
                        logger.info(f"=== SAVE PDF SUCCESS ===")
                        return True, str(filepath)
                    else:
                        logger.error(f"✗ File size mismatch: expected {len(pdf_data)}, got {file_size}")
                        return False, None
                else:
                    logger.error("✗ File was not created")
                    return False, None
                    
            except Exception as e:
                logger.error(f"Error writing file: {e}")
                return False, None
                
        except Exception as e:
            logger.error(f"Ошибка сохранения PDF для профиля {profile_id}: {e}", exc_info=True)
            logger.info(f"=== SAVE PDF ERROR ===")
            return False, None
    
    def _find_profile_pdfs(self, profile_id: int) -> List[Path]:
        """Находит все PDF файлы для профиля"""
        try:
            pattern = f"profile_{profile_id:04d}*"
            pdf_files = []
            
            for file_path in self.pdf_folder.glob(pattern):
                if file_path.suffix.lower() == '.pdf' and file_path.is_file():
                    pdf_files.append(file_path)
            
            return sorted(pdf_files)  # Сортируем для консистентности
            
        except Exception as e:
            logger.error(f"Error finding PDFs for profile {profile_id}: {e}")
            return []
    
    def _get_file_hash(self, filepath: Path) -> str:
        """Вычисляет хэш файла"""
        try:
            with open(filepath, 'rb') as f:
                file_data = f.read()
            return hashlib.md5(file_data).hexdigest()[:8]  # Первые 8 символов для краткости
        except:
            return ""
    
    def _delete_old_profile_pdfs(self, profile_id: int, keep_file: str = None) -> None:
        """Удаляет старые PDF файлы профиля, оставляя только указанный"""
        try:
            existing_files = self._find_profile_pdfs(profile_id)
            
            for file_path in existing_files:
                if keep_file and str(file_path) == keep_file:
                    continue  # Пропускаем файл, который нужно сохранить
                
                try:
                    file_path.unlink()
                    logger.info(f"Deleted old PDF: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Could not delete old PDF {file_path.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error deleting old PDFs: {e}")
    
    def load_profile_pdf(self, profile_id: int, pdf_path: Optional[str] = None) -> Optional[bytes]:
        """
        Загружает PDF файл профиля
        
        Args:
            profile_id: ID профиля
            pdf_path: Конкретный путь к файлу (если известен)
            
        Returns:
            Optional[bytes]: Данные PDF или None
        """
        try:
            # Если указан конкретный путь
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    return f.read()
            
            # Ищем PDF по ID профиля
            for pdf_file in self.pdf_folder.glob(f"profile_{profile_id:04d}*"):
                if pdf_file.suffix.lower() == '.pdf':
                    with open(pdf_file, 'rb') as f:
                        return f.read()
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка загрузки PDF для профиля {profile_id}: {e}")
            return None
    
    def delete_profile_pdf(self, profile_id: int, pdf_path: Optional[str] = None) -> bool:
        """
        Удаляет PDF файл профиля
        
        Args:
            profile_id: ID профиля
            pdf_path: Конкретный путь к файлу (если None, удаляет все PDF профиля)
            
        Returns:
            bool: True если успешно удалено
        """
        try:
            deleted = False
            
            # Если указан конкретный путь, удаляем только его
            if pdf_path and os.path.exists(pdf_path):
                filename = os.path.basename(pdf_path)
                # Проверяем, что файл действительно принадлежит этому профилю
                if filename.startswith(f"profile_{profile_id:04d}"):
                    os.remove(pdf_path)
                    logger.info(f"PDF удален: {pdf_path}")
                    deleted = True
                else:
                    logger.warning(f"Файл {filename} не принадлежит профилю {profile_id}")
            
            # Если путь не указан, удаляем все PDF для этого профиля
            elif pdf_path is None:
                for pdf_file in self.pdf_folder.glob(f"profile_{profile_id:04d}*.pdf"):
                    try:
                        os.remove(pdf_file)
                        logger.info(f"PDF удален: {pdf_file.name}")
                        deleted = True
                    except Exception as e:
                        logger.error(f"Ошибка удаления {pdf_file}: {e}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Ошибка удаления PDF для профиля {profile_id}: {e}")
            return False
    
    def extract_pdf_preview(self, pdf_data: bytes) -> Optional[bytes]:
        """
        Извлекает первую страницу PDF как изображение для превью
        
        Args:
            pdf_data: Данные PDF файла
            
        Returns:
            Optional[bytes]: Изображение первой страницы в формате PNG
        """
        try:
            # Пробуем использовать PyMuPDF если установлен
            try:
                import fitz  # PyMuPDF
                
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(pdf_data)
                    tmp_path = tmp.name
                
                try:
                    # Открываем PDF
                    pdf_document = fitz.open(tmp_path)
                    
                    if len(pdf_document) == 0:
                        return None
                    
                    # Получаем первую страницу
                    page = pdf_document[0]
                    
                    # Рендерим как изображение
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    
                    # Конвертируем в PNG
                    image_data = pix.tobytes("png")
                    
                    pdf_document.close()
                    return image_data
                    
                finally:
                    # Удаляем временный файл
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                        
            except ImportError:
                # PyMuPDF не установлен - используем Pillow для создания заглушки
                logger.warning("PyMuPDF not installed. Creating placeholder preview.")
                return self._create_placeholder_preview()
                
        except Exception as e:
            logger.error(f"Ошибка извлечения превью из PDF: {e}")
            return None
    
    def open_pdf_external(self, pdf_path: str) -> bool:
        """
        Открывает PDF файл во внешнем просмотрщике
        
        Args:
            pdf_path: Путь к PDF файлу
            
        Returns:
            bool: True если успешно открыто
        """
        try:
            if not os.path.exists(pdf_path):
                logger.error(f"PDF файл не найден: {pdf_path}")
                return False
            
            # Открываем в системном просмотрщике
            if os.name == 'nt':  # Windows
                os.startfile(pdf_path)
            elif os.name == 'posix':  # Linux/Mac
                import subprocess
                try:
                    subprocess.run(['xdg-open', pdf_path], check=False)
                except:
                    subprocess.run(['open', pdf_path], check=False)
            else:
                logger.error(f"Неподдерживаемая ОС: {os.name}")
                return False
            
            logger.info(f"PDF открыт во внешнем просмотрщике: {pdf_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка открытия PDF: {e}")
            return False
    
    def get_profile_pdf_info(self, profile_id: int) -> dict:
        """
        Получает информацию о PDF файлах профиля
        
        Args:
            profile_id: ID профиля
            
        Returns:
            dict: Информация о PDF файлах
        """
        info = {
            'has_pdf': False,
            'files': [],
            'total_size': 0
        }
        
        try:
            pdf_files = list(self.pdf_folder.glob(f"profile_{profile_id:04d}*"))
            
            for pdf_file in pdf_files:
                if pdf_file.suffix.lower() == '.pdf':
                    info['has_pdf'] = True
                    file_info = {
                        'name': pdf_file.name,
                        'path': str(pdf_file),
                        'size': pdf_file.stat().st_size,
                        'modified': pdf_file.stat().st_mtime
                    }
                    info['files'].append(file_info)
                    info['total_size'] += file_info['size']
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о PDF: {e}")
        
        return info
    
    def _make_filename_safe(self, filename: str) -> str:
        """
        Создает безопасное имя файла
        
        Args:
            filename: Оригинальное имя файла
            
        Returns:
            str: Безопасное имя файла
        """
        # Убираем расширение
        name = os.path.splitext(filename)[0]
        
        # Заменяем небезопасные символы
        safe_chars = " -_."
        result = ''.join(c if c.isalnum() or c in safe_chars else '_' for c in name)
        
        # Убираем множественные подчеркивания
        while '__' in result:
            result = result.replace('__', '_')
        
        # Обрезаем до разумной длины
        if len(result) > 50:
            result = result[:50]
        
        return result.strip(' _-.')
    
    def _create_placeholder_preview(self) -> bytes:
        """
        Создает заглушку для превью если PyMuPDF не установлен
        
        Returns:
            bytes: Изображение заглушки в формате PNG
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Создаем изображение 200x200
            img = Image.new('RGB', (200, 200), color='white')
            draw = ImageDraw.Draw(img)
            
            # Рисуем значок PDF
            draw.rectangle([50, 50, 150, 150], outline='blue', width=3)
            
            # Добавляем текст
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            draw.text((75, 80), "PDF", fill='blue', font=font)
            draw.text((60, 120), "File", fill='blue', font=font)
            
            # Сохраняем в PNG
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Ошибка создания заглушки: {e}")
            return b''