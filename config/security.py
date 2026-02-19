"""
Security modes management for Weinig application
"""
import json
import logging
from pathlib import Path
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)

# Импортируем AppConfig
try:
    from .app_config import AppConfig
except ImportError:
    from config.app_config import AppConfig


class SecurityManager:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Гарантируем, что инициализация выполняется только один раз
        if not self._initialized:
            self.app_config = AppConfig()
            
            # Загружаем текущий режим из конфигурации
            current_mode = self.app_config.get('security.mode', 'read_only')
            self._read_only = (current_mode == 'read_only')
            
            self._callbacks = []  # Для уведомлений об изменениях
            self._initialized = True
            
            logger.info(f"Security mode initialized as: {'Read Only' if self._read_only else 'Full Access'}")
            logger.info(f"Loaded from config: security.mode = {current_mode}")
    
    def add_callback(self, callback: Callable[[bool], None]):
        """Добавить callback для уведомления об изменениях режима"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[bool], None]):
        """Удалить callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """Уведомить все зарегистрированные callback-функции"""
        for callback in self._callbacks:
            try:
                callback(self._read_only)
            except Exception as e:
                logger.error(f"Error in security callback: {e}")
    
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
        
        # Уведомляем всех подписчиков
        self._notify_callbacks()
        
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
        self._notify_callbacks()
    
    def set_read_only(self):
        """Switch to read-only mode"""
        self._read_only = True
        self.app_config.set('security.mode', 'read_only')
        save_success = self.app_config.save()
        logger.info(f"Switched to Read Only mode (save: {'success' if save_success else 'failed'})")
        self._notify_callbacks()
    
    def get_current_mode(self) -> str:
        """Get current mode as string"""
        return 'read_only' if self._read_only else 'full_access'
    
    def get_mode_text(self) -> str:
        """Get current mode as display text"""
        return 'Read Only' if self._read_only else 'Full Access'


# Глобальные функции доступа
def get_security_manager() -> SecurityManager:
    """Получить глобальный экземпляр SecurityManager"""
    return SecurityManager()

def get_security_mode() -> str:
    """Получить текущий режим безопасности"""
    return get_security_manager().get_current_mode()

def is_read_only() -> bool:
    """Проверить, находится ли приложение в режиме только для чтения"""
    return get_security_manager().is_read_only()