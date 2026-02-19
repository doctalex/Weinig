"""
Конфигурация приложения
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AppConfig:
    """Конфигурация приложения"""
    
    # Значения по умолчанию
    DEFAULT_CONFIG = {
        "security": {
            "mode": "read_only",  # ДОБАВЛЕНО: режим безопасности
            "full_access_key": "ctrl+shift+f"  # ДОБАВЛЕНО: горячая клавиша
        },
        "database": {
            "path": "tools_database.db",
            "auto_backup": True,
            "backup_count": 5
        },
        "ui": {
            "theme": "clam",
            "font_family": "Arial",
            "font_size": 10,
            "window_width": 1400,
            "window_height": 800
        },
        "tools": {
            "default_feed_rate": 2.5,
            "default_knives_count": 6,
            "default_set_number": 1,
            "code_format": "XXXXXX"
        },
        "heads": {
            "mapping": {
                1: "Bottom",
                2: "Top", 
                3: "Right",
                4: "Left",
                5: "Right",
                6: "Left",
                7: "Top",
                8: "Bottom",
                9: "Top",
                10: "Bottom"
            },
            "names": {
                1: "1 Bottom",
                2: "1 Top",
                3: "1 Right", 
                4: "1 Left",
                5: "2 Right",
                6: "2 Left",
                7: "2 Top",
                8: "2 Bottom",
                9: "3 Top",
                10: "3 Bottom"
            }
        },
        "export": {
            "default_format": "json",
            "auto_open_export": True
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_file and os.path.exists(config_file):
            self.load(config_file)
        else:
            self.save_default()
    
    def load(self, config_file: Optional[str] = None) -> bool:
        """Загружает конфигурацию из файла"""
        if config_file:
            self.config_file = config_file
        
        if not self.config_file or not os.path.exists(self.config_file):
            logger.warning(f"Config file not found: {self.config_file}")
            return False
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                self._deep_update(self.config, loaded_config)
            logger.info(f"Configuration loaded from {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
    
    def save(self, config_file: Optional[str] = None) -> bool:
        """Сохраняет конфигурацию в файл"""
        if config_file:
            self.config_file = config_file
        
        if not self.config_file:
            # Используем путь по умолчанию
            self.config_file = self.get_default_config_path()
        
        try:
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def save_default(self) -> bool:
        """Сохраняет конфигурацию по умолчанию"""
        return self.save(self.get_default_config_path())
    
    def get_default_config_path(self) -> str:
        """Возвращает путь к файлу конфигурации по умолчанию"""
        # Используем домашнюю директорию пользователя
        home_dir = Path.home()
        config_dir = home_dir / ".weinig_tool_manager"
        return str(config_dir / "config.json")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получает значение по ключу (с поддержкой вложенных ключей)"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> bool:
        """Устанавливает значение по ключу"""
        keys = key.split('.')
        config = self.config
        
        # Проходим по всем ключам кроме последнего
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        # Устанавливаем значение
        config[keys[-1]] = value
        return True
    
    def get_database_path(self) -> str:
        """Возвращает путь к базе данных"""
        db_path = self.get("database.path")
        if db_path and not os.path.isabs(db_path):
            # Если путь относительный, делаем его абсолютным относительно домашней директории
            home_dir = Path.home()
            config_dir = home_dir / ".weinig_tool_manager"
            return str(config_dir / db_path)
        return db_path or "tools_database.db"
    
    def get_head_mapping(self) -> Dict[int, str]:
        """Возвращает карту соответствия голов"""
        return self.get("heads.mapping", self.DEFAULT_CONFIG["heads"]["mapping"])
    
    def get_head_names(self) -> Dict[int, str]:
        """Возвращает имена голов"""
        return self.get("heads.names", self.DEFAULT_CONFIG["heads"]["names"])
    
    def get_security_mode(self) -> str:
        """Возвращает текущий режим безопасности"""
        return self.get("security.mode", "read_only")
    
    def set_security_mode(self, mode: str) -> bool:
        """Устанавливает режим безопасности"""
        return self.set("security.mode", mode)
    
    def _deep_update(self, target: Dict, source: Dict) -> Dict:
        """Рекурсивно обновляет словарь"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
        return target
    
    def to_dict(self) -> Dict[str, Any]:
        """Возвращает конфигурацию как словарь"""
        return self.config.copy()

# Глобальный экземпляр конфигурации
_config_instance: Optional[AppConfig] = None

def get_config() -> AppConfig:
    """Возвращает глобальный экземпляр конфигурации"""
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance

def init_config(config_file: Optional[str] = None) -> AppConfig:
    """Инициализирует глобальную конфигурацию"""
    global _config_instance
    _config_instance = AppConfig(config_file)
    return _config_instance