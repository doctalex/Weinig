"""
Profile management service
"""
import logging
from typing import List, Optional, Dict, Any
from core.database import DatabaseManager
from core.models import Profile
from core.observable import Observable

# ДОБАВЛЯЕМ ИМПОРТ МЕНЕДЖЕРА БЕЗОПАСНОСТИ
from config.security import SecurityManager

logger = logging.getLogger(__name__)


class ProfileService(Observable):
    """Profile management service"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.current_profile_id: Optional[int] = None
        # ДОБАВЛЯЕМ ИНИЦИАЛИЗАЦИЮ МЕНЕДЖЕРА БЕЗОПАСНОСТИ
        self.security = SecurityManager()
    
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
    
    def get_current_profile(self) -> Optional[Profile]:
        """Gets the current profile"""
        if self.current_profile_id:
            return self.get_profile(self.current_profile_id)
        return None
    
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
    
    # === МЕТОДЫ РЕДАКТИРОВАНИЯ (добавляем проверки) ===
    
    def create_profile(self, name: str, description: str = '', 
                      feed_rate: float = 2.5, material_size: str = '100x100',
                      product_size: str = '90x90', image_data: bytes = None) -> Optional[int]:
        """Creates a new profile"""
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        self._raise_if_read_only()
        
        try:
            profile_id = self.db.add_profile(
                name, description, feed_rate, material_size, product_size, image_data
            )
            self.notify_observers('profile_created', profile_id)
            return profile_id
        except Exception as e:
            logger.error(f"Error creating profile: {e}")
            return None
    
    def update_profile(self, profile_id: int, **kwargs) -> bool:
        """Updates a profile"""
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        self._raise_if_read_only()
        
        success = self.db.update_profile(profile_id, **kwargs)
        if success:
            self.notify_observers('profile_updated', profile_id)
        return success
    
    def delete_profile(self, profile_id: int) -> bool:
        """Deletes a profile"""
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        self._raise_if_read_only()
        
        success = self.db.delete_profile(profile_id)
        if success:
            self.notify_observers('profile_deleted', profile_id)
            if self.current_profile_id == profile_id:
                self.current_profile_id = None
        return success


# Make sure this export is at the end of the file
__all__ = ['ProfileService']
