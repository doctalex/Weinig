"""
Простой менеджер для работы с PDF файлами профилей
"""
import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple
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
                         original_filename: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Сохраняет PDF файл профиля
        
        Args:
            profile_id: ID профиля
            pdf_data: Данные PDF файла
            original_filename: Оригинальное имя файла (для информации)
            
        Returns:
            Tuple[bool, Optional[str]]: (успех, путь к файлу)
        """
        try:
            # Генерируем имя файла
            if original_filename:
                # Безопасное имя файла
                safe_name = self._make_filename_safe(original_filename)
                filename = f"profile_{profile_id:04d}_{safe_name}"
            else:
                filename = f"profile_{profile_id:04d}"
            
            # Добавляем расширение если его нет
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            filepath = self.pdf_folder / filename
            
            # Сохраняем файл
            with open(filepath, 'wb') as f:
                f.write(pdf_data)
            
            logger.info(f"PDF сохранен: {filepath.name} (размер: {len(pdf_data)} байт)")
            return True, str(filepath)
            
        except Exception as e:
            logger.error(f"Ошибка сохранения PDF для профиля {profile_id}: {e}")
            return False, None
    
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
            pdf_path: Конкретный путь к файлу
            
        Returns:
            bool: True если успешно удалено
        """
        try:
            deleted = False
            
            # Удаляем по конкретному пути
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
                logger.info(f"PDF удален: {pdf_path}")
                deleted = True
            
            # Удаляем все PDF для этого профиля (на всякий случай)
            for pdf_file in self.pdf_folder.glob(f"profile_{profile_id:04d}*"):
                if pdf_file.suffix.lower() == '.pdf':
                    os.remove(pdf_file)
                    logger.info(f"PDF удален: {pdf_file.name}")
                    deleted = True
            
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