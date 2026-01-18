"""
Non-invasive security checks for existing functions
"""
from config.security import SecurityManager
from functools import wraps
import logging

logger = logging.getLogger(__name__)
security = SecurityManager()


def check_edit_permission(func):
    """Decorator to check edit permission before function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if in read-only mode
        if security.is_read_only():
            # Log the attempt
            logger.warning(f"Edit attempt blocked in read-only mode: {func.__name__}")
            
            # Try to show message box if possible
            try:
                import tkinter.messagebox as mb
                mb.showerror(
                    "Access Denied",
                    "This action is not available in Read Only mode.\n\n"
                    "Press Ctrl+Shift+F to switch to Full Access mode."
                )
            except:
                pass
            
            return None  # Or raise PermissionError if preferred
        return func(*args, **kwargs)
    return wrapper


def check_delete_permission(func):
    """Decorator to check delete permission"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if security.is_read_only():
            logger.warning(f"Delete attempt blocked: {func.__name__}")
            try:
                import tkinter.messagebox as mb
                mb.showerror(
                    "Access Denied",
                    "Cannot delete in Read Only mode.\n"
                    "Switch to Full Access with Ctrl+Shift+F."
                )
            except:
                pass
            return None
        return func(*args, **kwargs)
    return wrapper
