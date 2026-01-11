"""
Security modes management for Weinig application
"""
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """Security configuration"""
    mode: str = "read_only"  # "read_only" or "full_access"
    full_access_key: str = "ctrl+shift+f"


class SecurityManager:
    """Singleton security manager"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.config_file = Path.home() / ".weinig_security.json"
            self.config = SecurityConfig()
            self._load_config()
            self.initialized = True
    
    def _load_config(self):
        """Load security configuration"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.config.mode = data.get('mode', 'read_only')
        except Exception as e:
            logger.warning(f"Could not load security config: {e}")
    
    def _save_config(self):
        """Save security configuration"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(asdict(self.config), f, indent=2)
        except Exception as e:
            logger.error(f"Could not save security config: {e}")
    
    def is_read_only(self) -> bool:
        """Check if in read-only mode"""
        return self.config.mode == "read_only"
    
    def is_full_access(self) -> bool:
        """Check if in full access mode"""
        return self.config.mode == "full_access"
    
    def set_full_access(self):
        """Switch to full access mode"""
        self.config.mode = "full_access"
        self._save_config()
        logger.info("Switched to Full Access mode")
    
    def set_read_only(self):
        """Switch to read-only mode"""
        self.config.mode = "read_only"
        self._save_config()
        logger.info("Switched to Read Only mode")
    
    def toggle_mode(self):
        """Toggle between read-only and full access"""
        if self.is_read_only():
            self.set_full_access()
        else:
            self.set_read_only()
        return self.is_full_access()
