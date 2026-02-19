"""
Паттерн Observer для уведомлений между компонентами
"""
from typing import Callable, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Observable:
    """Базовый класс для наблюдаемых объектов"""
    
    def __init__(self):
        self._observers: Dict[str, List[Callable]] = {}
    
    def add_observer(self, event_type: str, observer: Callable):
        """Добавляет наблюдателя для определенного события"""
        if event_type not in self._observers:
            self._observers[event_type] = []
        self._observers[event_type].append(observer)
        logger.debug(f"Added observer for event '{event_type}': {observer}")
    
    def remove_observer(self, event_type: str, observer: Callable):
        """Удаляет наблюдателя"""
        if event_type in self._observers and observer in self._observers[event_type]:
            self._observers[event_type].remove(observer)
            logger.debug(f"Removed observer for event '{event_type}': {observer}")
    
    def notify_observers(self, event_type: str, *args, **kwargs):
        """Уведомляет всех наблюдателей о событии"""
        if event_type in self._observers:
            for observer in self._observers[event_type]:
                try:
                    observer(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in observer for event '{event_type}': {e}")
    
    def clear_observers(self, event_type: str = None):
        """Очищает всех наблюдателей"""
        if event_type:
            if event_type in self._observers:
                self._observers[event_type].clear()
        else:
            self._observers.clear()