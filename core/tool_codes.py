"""
Генерация и декодирование кодов инструментов
"""
from typing import Dict, Optional

class ToolCodeGenerator:
    """Генератор и декодер кодов инструментов"""
    
    # Маппинги для кодирования
    POSITION_MAP = {
        'Bottom': '1', 'Top': '2', 'Right': '3', 'Left': '4',
        '1': 'Bottom', '2': 'Top', '3': 'Right', '4': 'Left'
    }
    
    TYPE_MAP = {
        'Straight': '0', 'Profile': '1',
        '0': 'Straight', '1': 'Profile'
    }
    
    @classmethod
    def generate(cls, profile_id: int, position: str, 
                tool_type: str, set_number: int = 1) -> str:
        """
        Генерирует код инструмента по правилам:
        XXXXXX (6 цифр):
        - 1: позиция (1-4)
        - 2: тип (0-1)
        - 3-5: ID профиля (001-999)
        - 6: номер комплекта (1-9)
        """
        # Проверка входных данных
        if not 1 <= profile_id <= 999:
            raise ValueError(f"Profile ID must be 1-999, got {profile_id}")
        
        if position not in cls.POSITION_MAP:
            raise ValueError(f"Invalid position: {position}")
        
        if tool_type not in cls.TYPE_MAP:
            raise ValueError(f"Invalid tool type: {tool_type}")
        
        if not 1 <= set_number <= 9:
            raise ValueError(f"Set number must be 1-9, got {set_number}")
        
        # Генерация кода
        pos_code = cls.POSITION_MAP[position]
        type_code = cls.TYPE_MAP[tool_type]
        profile_code = f"{profile_id:03d}"
        set_code = str(set_number)
        
        return f"{pos_code}{type_code}{profile_code}{set_code}"
    
    @classmethod
    def decode(cls, code: str) -> Optional[Dict[str, any]]:
        """
        Декодирует код инструмента
        """
        if not code or len(code) != 6:
            return None
        
        try:
            return {
                'position': cls.POSITION_MAP.get(code[0], 'Bottom'),
                'tool_type': cls.TYPE_MAP.get(code[1], 'Profile'),
                'profile_id': int(code[2:5]),
                'set_number': int(code[5])
            }
        except (ValueError, IndexError):
            return None
    
    @classmethod
    def validate_code(cls, code: str) -> bool:
        """Проверяет валидность кода"""
        return cls.decode(code) is not None