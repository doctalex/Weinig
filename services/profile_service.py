"""
Profile management service with PDF support
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict
from core.database import DatabaseManager
from core.models import Profile
from core.observable import Observable

# ДОБАВЛЯЕМ ИМПОРТ МЕНЕДЖЕРА БЕЗОПАСНОСТИ
from config.security import SecurityManager
# ДОБАВЛЯЕМ ИМПОРТ PDF МЕНЕДЖЕРА
from utils.pdf_manager import PDFManager

logger = logging.getLogger(__name__)


class ProfileService(Observable):
    """Profile management service with PDF support"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.current_profile_id: Optional[int] = None
        
        # ДОБАВЛЯЕМ ИНИЦИАЛИЗАЦИЮ МЕНЕДЖЕРА БЕЗОПАСНОСТИ
        self.security = SecurityManager()
        
        # ДОБАВЛЯЕМ ИНИЦИАЛИЗАЦИЮ PDF МЕНЕДЖЕРА
        self.pdf_manager = PDFManager()
    
    # === ВСПОМОГАТЕЛЬНЫЙ МЕТОД ДЛЯ ПРОВЕРКИ ДОСТУПА ===
    def _check_edit_permission(self) -> bool:
        """Check if editing is allowed in current security mode"""
        return not self.security.is_read_only()
    
    def _raise_if_read_only(self):
        """Raise error if in read-only mode"""
        if self.security.is_read_only():
            raise PermissionError(
                "This operation is not available in Read Only mode.\n\n"
                "Please switch to Full Access mode by pressing Ctrl+Shift+F."
            )
    
    # === СУЩЕСТВУЮЩИЕ МЕТОДЫ ЧТЕНИЯ (без изменений) ===
    
    def get_all_profiles(self) -> List[Profile]:
        """Gets all profiles"""
        rows = self.db.get_all_profiles()
        return [Profile.from_db_row(row) for row in rows]
    
    def get_profile(self, profile_id: int) -> Optional[Profile]:
        """Gets a profile by ID"""
        row = self.db.get_profile(profile_id)
        if row:
            return Profile.from_db_row(row)
        return None
    
    # Псевдоним для совместимости с GUI
    get_profile_by_id = get_profile
    
    def get_current_profile(self) -> Optional[Profile]:
        """Получает текущий выбранный профиль"""
        if not self.current_profile_id:
            return None

        return self.get_profile(self.current_profile_id)

    def update_profile_product_size(self, profile_id: int, product_size: str) -> bool:
        """Обновляет поле product_size у профиля"""
        try:
            return self.db.update_profile(
                profile_id=profile_id,
                product_size=product_size
            )
        except Exception as e:
            logger.error(f"Error updating profile product_size: {e}")
            return False

    
    def count_tools(self, profile_id: int) -> int:
        """Counts tools in the profile"""
        tools = self.db.get_tools_by_profile(profile_id)
        return len(tools) if tools else 0
    
    def get_profile_statistics(self, profile_id: int) -> Dict[str, Any]:
        """Gets profile statistics"""
        tools = self.db.get_tools_by_profile(profile_id)
        
        stats = {
            'total_tools': len(tools),
            'by_position': {'Bottom': 0, 'Top': 0, 'Right': 0, 'Left': 0},
            'by_type': {'Straight': 0, 'Profile': 0},
            'total_knives': 0
        }
        
        for tool in tools:
            position = tool['Position'] if len(tool) > 2 else None
            tool_type = tool['Tool_Type'] if len(tool) > 3 else None
            knives = tool['Knives_Count'] if len(tool) > 6 else 0
            
            if position in stats['by_position']:
                stats['by_position'][position] += 1
            
            if tool_type in stats['by_type']:
                stats['by_type'][tool_type] += 1
            
            stats['total_knives'] += knives
        
        return stats
    
    def set_current_profile(self, profile_id: int):
        """Sets the current profile"""
        self.current_profile_id = profile_id
        self.notify_observers('current_profile_changed', profile_id)
    
    def create_profile(self, name: str, description: str = '', 
                      feed_rate: float = 30.0, material_size: str = '',
                      product_size: str = '', pdf_data: bytes = None, 
                      pdf_filename: str = None) -> Optional[int]:
        """Creates a new profile with PDF support (Clean version)"""
        self._raise_if_read_only()
        
        try:
            logger.info(f"=== CREATE PROFILE START: {name} ===")
            
            # Шаг 1: Подготовка данных PDF
            pdf_path = None
            
            if pdf_data:
                logger.info(f"PDF provided: {len(pdf_data)} bytes, filename: {pdf_filename}")
                
                # Временное сохранение PDF
                success, temp_pdf_path = self.pdf_manager.save_profile_pdf(
                    0,  # Временный ID
                    pdf_data, 
                    pdf_filename
                )
                
                if not success:
                    logger.error("Failed to save PDF file")
                    return None
                
                pdf_path = temp_pdf_path
                logger.info(f"PDF temporarily saved: {pdf_path}")
                
                # ПРИМЕЧАНИЕ: Мы больше не извлекаем превью здесь, 
                # так как не сохраняем его в базу данных Profiles.
            
            # Шаг 2: Создаем профиль В БАЗЕ (Без image_data)
            logger.info("Creating profile in database...")
            profile_id = self.db.add_profile(
                name=name,
                description=description,
                feed_rate=feed_rate,
                material_size=material_size,
                product_size=product_size,
                pdf_path=pdf_path
            )
            
            if not profile_id:
                logger.error("Database returned no profile ID")
                if pdf_path:
                    import os
                    os.remove(pdf_path)
                return None

            logger.info(f"Profile created with ID: {profile_id}")
            
            # Шаг 3: Переименование PDF файла (строго ID.pdf)
            if pdf_path:
                import os
                from pathlib import Path
                
                old_path = Path(pdf_path)
                # Генерируем простое имя: 001.pdf
                new_filename = f"{profile_id:03d}.pdf"
                new_path = old_path.parent / new_filename
                
                try:
                    # Удаляем старый файл, если он есть (Windows fix)
                    if new_path.exists():
                        os.remove(new_path)
                    
                    old_path.rename(new_path)
                    logger.info(f"PDF finalized as: {new_filename}")
                    
                    self.db.update_profile(
                        profile_id=profile_id,
                        pdf_path=str(new_path)
                    )
                except Exception as rename_error:
                    logger.error(f"Error finalizing PDF name: {rename_error}")

            logger.info(f"=== CREATE PROFILE SUCCESS ===")
            self.notify_observers('profile_created', profile_id)
            return profile_id
            
        except Exception as e:
            logger.error(f"Error creating profile: {e}", exc_info=True)
            return None

    def get_profile_preview(self, profile_id: int) -> Optional[bytes]:
        """Получает превью из PDF файла профиля для отображения в GUI"""
        profile = self.get_profile(profile_id)
        if profile and profile.pdf_path:
            import os
            if os.path.exists(profile.pdf_path):
                try:
                    with open(profile.pdf_path, 'rb') as f:
                        pdf_data = f.read()
                    return self.pdf_manager.extract_pdf_preview(pdf_data)
                except Exception as e:
                    logger.error(f"Error reading PDF for preview: {e}")
        return None
    
    def _make_filename_safe(self, filename: str) -> str:
        """
        Делает имя файла безопасным для файловой системы
        """
        import os
        
        # Убираем путь если он есть
        filename = os.path.basename(filename)
        
        # Заменяем недопустимые символы
        unsafe_chars = '<>:"/\\|?*\'"'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # Убираем начальные/конечные пробелы и точки
        filename = filename.strip('. ')
        
        # Ограничиваем длину
        max_length = 180
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        
        return filename
    
    def update_profile(self, profile_id: int, name: str = None, description: str = None, 
                       feed_rate: float = None, material_size: str = None,
                       product_size: str = None, pdf_data: bytes = None,
                       pdf_filename: str = None, keep_existing_pdf: bool = False) -> bool:
        
        self._raise_if_read_only()
        
        try:
            current_profile = self.get_profile(profile_id)
            if not current_profile:
                return False
            
            update_data = {}
            if name is not None: update_data['name'] = name
            if description is not None: update_data['description'] = description
            if feed_rate is not None: update_data['feed_rate'] = feed_rate
            if material_size is not None: update_data['material_size'] = material_size
            if product_size is not None: update_data['product_size'] = product_size
            
            if not keep_existing_pdf:
                # Если пришли НОВЫЕ данные PDF
                if pdf_data is not None:
                    if current_profile.pdf_path:
                        self.pdf_manager.delete_profile_pdf(profile_id, current_profile.pdf_path)
                    
                    success, pdf_path = self.pdf_manager.save_profile_pdf(
                        profile_id, pdf_data, pdf_filename, overwrite_existing=True
                    )
                    if success:
                        update_data['pdf_path'] = pdf_path
                
                elif pdf_data is None and pdf_filename is None:
                    if current_profile.pdf_path:
                        self.pdf_manager.delete_profile_pdf(profile_id, current_profile.pdf_path)
                        update_data['pdf_path'] = None
                        # !!! И ЗДЕСЬ ТОЖЕ УДАЛИЛИ 'image_data' !!!
            
            # Отправляем в базу только те поля, которые в ней есть
            success = self.db.update_profile(profile_id, **update_data)
            
            if success:
                self.notify_observers('profile_updated', profile_id)
            return success
            
        except Exception as e:
            logger.error(f"Error updating profile {profile_id}: {e}")
            return False
            
    def delete_profile(self, profile_id: int) -> bool:
        """Deletes a profile and its associated PDF file"""
        # ПРОВЕРКА ДОСТУПА
        self._raise_if_read_only()
        
        try:
            # Получаем профиль чтобы знать путь к PDF
            profile = self.get_profile(profile_id)
            
            # Удаляем профиль из базы данных
            success = self.db.delete_profile(profile_id)
            
            if not success:
                logger.error(f"Failed to delete profile from database: {profile_id}")
                return False
            
            # Удаляем связанный PDF файл если он существует
            if profile and profile.pdf_path:
                pdf_deleted = self.pdf_manager.delete_profile_pdf(profile_id, profile.pdf_path)
                if pdf_deleted:
                    logger.info(f"PDF file deleted for profile {profile_id}")
                else:
                    logger.warning(f"PDF file not found for profile {profile_id}")
            
            # Обновляем текущий профиль если нужно
            if self.current_profile_id == profile_id:
                self.current_profile_id = None
            
            # Уведомляем наблюдателей
            self.notify_observers('profile_deleted', profile_id)
            logger.info(f"Profile deleted successfully: {profile_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting profile {profile_id}: {e}")
            return False
    
    # === НОВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С PDF ===
    
    def get_profile_pdf(self, profile_id: int) -> Optional[bytes]:
        """Gets PDF file data for a profile"""
        try:
            profile = self.get_profile(profile_id)
            if not profile or not profile.pdf_path:
                return None
            
            return self.pdf_manager.load_profile_pdf(profile_id, profile.pdf_path)
            
        except Exception as e:
            logger.error(f"Error getting PDF for profile {profile_id}: {e}")
            return None
    
    def open_profile_pdf(self, profile_id: int) -> bool:
        """Opens profile PDF in external viewer"""
        try:
            profile = self.get_profile(profile_id)
            if not profile or not profile.pdf_path:
                logger.warning(f"No PDF found for profile {profile_id}")
                return False
            
            return self.pdf_manager.open_pdf_external(profile.pdf_path)
            
        except Exception as e:
            logger.error(f"Error opening PDF for profile {profile_id}: {e}")
            return False
    
    def get_pdf_info(self, profile_id: int) -> Dict[str, Any]:
        """Gets information about profile's PDF file"""
        try:
            profile = self.get_profile(profile_id)
            if not profile:
                return {'has_pdf': False, 'error': 'Profile not found'}
            
            return self.pdf_manager.get_profile_pdf_info(profile_id)
            
        except Exception as e:
            logger.error(f"Error getting PDF info for profile {profile_id}: {e}")
            return {'has_pdf': False, 'error': str(e)}
    
    def has_pdf_document(self, profile_id: int) -> bool:
        """Checks if profile has a PDF document"""
        try:
            profile = self.get_profile(profile_id)
            return profile is not None and profile.has_pdf
            
        except Exception as e:
            logger.error(f"Error checking PDF for profile {profile_id}: {e}")
            return False
    
    # === МЕТОД ДЛЯ МИГРАЦИИ СТАРЫХ ДАННЫХ (опционально) ===
    
    def migrate_profile_to_pdf(self, profile_id: int, pdf_data: bytes, 
                              pdf_filename: str = None) -> bool:
        """Migrates existing profile to use PDF (for old profiles with images)"""
        try:
            profile = self.get_profile(profile_id)
            if not profile:
                logger.error(f"Cannot migrate: Profile {profile_id} not found")
                return False
            
            # Удаляем старое изображение если есть
            if profile.pdf_path:
                logger.warning(f"Profile {profile_id} already has PDF")
                return False
            
            # Сохраняем новый PDF
            success, pdf_path = self.pdf_manager.save_profile_pdf(
                profile_id, pdf_data, pdf_filename
            )
            
            if not success:
                logger.error(f"Failed to save PDF for migration: {profile_id}")
                return False
            
            # Извлекаем превью
            preview = self.pdf_manager.extract_pdf_preview(pdf_data)
            
            # Обновляем профиль
            update_success = self.db.update_profile(
                profile_id=profile_id,
                image_data=preview,
                pdf_path=pdf_path
            )
            
            if update_success:
                logger.info(f"Profile migrated to PDF: {profile_id}")
                self.notify_observers('profile_updated', profile_id)
            
            return update_success
            
        except Exception as e:
            logger.error(f"Error migrating profile {profile_id} to PDF: {e}")
            return False


# Make sure this export is at the end of the file
__all__ = ['ProfileService']