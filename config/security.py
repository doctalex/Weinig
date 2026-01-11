"""
Security modes management for Weinig application
"""
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)

# Импортируем AppConfig
try:
    from .app_config import AppConfig
except ImportError:
    # Альтернативный импорт для случаев когда запускаем из другого места
    from config.app_config import AppConfig


@dataclass
class SecurityConfig:
    """Security configuration"""
    mode: str = "read_only"  # "read_only" or "full_access"
    full_access_key: str = "ctrl+shift+f"


class SecurityManager:
    def __init__(self):
        self.app_config = AppConfig()  # Переименовываем для ясности
        
        # Загружаем текущий режим из конфигурации
        current_mode = self.app_config.get('security_mode', 'read_only')
        self._read_only = (current_mode == 'read_only')
        
        logger.info(f"Security mode initialized as: {'Read Only' if self._read_only else 'Full Access'}")
        
    def toggle_security_mode(self):
        """Переключает режим безопасности"""
        self._read_only = not self._read_only
        
        # Сохраняем в конфигурацию
        mode = 'read_only' if self._read_only else 'full_access'
        self.app_config.set('security_mode', mode)
        self.app_config.save()
        
        # Логируем
        mode_text = 'Read Only' if self._read_only else 'Full Access'
        logger.info(f"Switched to {mode_text} mode")
        return self._read_only
    
    def is_read_only(self) -> bool:
        """Check if in read-only mode"""
        return self._read_only
    
    def is_full_access(self) -> bool:
        """Check if in full access mode"""
        return not self._read_only
    
    def set_full_access(self):
        """Switch to full access mode"""
        self._read_only = False
        self.app_config.set('security_mode', 'full_access')
        self.app_config.save()
        logger.info("Switched to Full Access mode")
    
    def set_read_only(self):
        """Switch to read-only mode"""
        self._read_only = True
        self.app_config.set('security_mode', 'read_only')
        self.app_config.save()
        logger.info("Switched to Read Only mode")
    
    def toggle_mode(self):
        """Toggle between read-only and full access"""
        if self.is_read_only():
            self.set_full_access()
        else:
            self.set_read_only()
        return self.is_full_access()
    
    def get_current_mode(self) -> str:
        """Get current mode as string"""
        return 'read_only' if self._read_only else 'full_access'
