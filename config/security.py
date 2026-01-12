"""
Security modes management for Weinig application
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Импортируем AppConfig
try:
    from .app_config import AppConfig
except ImportError:
    from config.app_config import AppConfig


class SecurityManager:
    def __init__(self):
        self.app_config = AppConfig()  # Переименовываем для ясности
        
        # Загружаем текущий режим из конфигурации
        current_mode = self.app_config.get('security.mode', 'read_only')
        self._read_only = (current_mode == 'read_only')
        
        logger.info(f"Security mode initialized as: {'Read Only' if self._read_only else 'Full Access'}")
        logger.info(f"Loaded from config: security.mode = {current_mode}")
        
    def toggle_security_mode(self):
        """Переключает режим безопасности"""
        self._read_only = not self._read_only
        
        # Сохраняем в конфигурацию с правильным ключом
        mode = 'read_only' if self._read_only else 'full_access'
        success = self.app_config.set('security.mode', mode)
        
        if success:
            save_success = self.app_config.save()
            if save_success:
                logger.info(f"Configuration saved successfully")
            else:
                logger.error(f"Failed to save configuration!")
        
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
        self.app_config.set('security.mode', 'full_access')
        save_success = self.app_config.save()
        logger.info(f"Switched to Full Access mode (save: {'success' if save_success else 'failed'})")
    
    def set_read_only(self):
        """Switch to read-only mode"""
        self._read_only = True
        self.app_config.set('security.mode', 'read_only')
        save_success = self.app_config.save()
        logger.info(f"Switched to Read Only mode (save: {'success' if save_success else 'failed'})")
    
    def get_current_mode(self) -> str:
        """Get current mode as string"""
        return 'read_only' if self._read_only else 'full_access'
    
    def get_mode_text(self) -> str:
        """Get current mode as display text"""
        return 'Read Only' if self._read_only else 'Full Access'