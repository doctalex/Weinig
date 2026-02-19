"""
Entry point for the Weinig Hydromat Tool Manager application
Optimized for Windows 7 compatibility
"""
import os
import sys
import platform
import ctypes
import logging
from pathlib import Path

# Проверка tkinter в самом начале
try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError as e:
    print(f"Error importing tkinter: {e}")
    # Пытаемся показать сообщение об ошибке разными способами
    if platform.system() == 'Windows':
        try:
            ctypes.windll.user32.MessageBoxW(0, f"Tkinter не найден: {e}\nУстановите Python с Tkinter.", "Ошибка импорта", 0x10)
        except:
            print("Не удалось показать диалог ошибки")
    sys.exit(1)

# Windows compatibility settings
if platform.system() == 'Windows':
    try:
        # Пытаемся установить режим 2 (Per Monitor DPI Aware) для Win 10+
        ctypes.windll.shcore.SetProcessDpiAwareness(2) 
    except (AttributeError, OSError):
        try:
            # Fallback для Win 8.1 / 7
            if hasattr(ctypes.windll.shcore, 'SetProcessDpiAwareness'):
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            elif hasattr(ctypes.windll.user32, 'SetProcessDPIAware'):
                ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

# Add the project root directory to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Check Python version
if sys.version_info < (3, 8):
    error_msg = "This application requires Python 3.8 or higher"
    print(error_msg)
    if platform.system() == 'Windows':
        try:
            ctypes.windll.user32.MessageBoxW(0, error_msg, "Python Version Error", 0x10)
        except:
            pass
    sys.exit(1)


def get_app_root() -> Path:
    """Получает корневую директорию приложения"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


APP_ROOT = get_app_root()
sys.path.insert(0, str(APP_ROOT))


def setup_logging():
    """Configure logging to console only"""
    # Clear any existing handlers
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # Reduce log level for some libraries
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    logger.info("Logging initialized (console only)")
    return logger


def check_dependencies():
    """Checks for required dependencies"""
    missing_deps = []
    
    # Check for PIL/Pillow
    try:
        import PIL
    except ImportError:
        missing_deps.append("Pillow (for image processing)")
    
    # Check for openpyxl (optional)
    try:
        import openpyxl
    except ImportError:
        # openpyxl is optional, just a warning
        logging.getLogger(__name__).warning(
            "openpyxl is not installed. Excel export will be unavailable."
        )
    
    if missing_deps:
        error_msg = "Missing required dependencies:\n\n"
        error_msg += "\n".join(f"• {dep}" for dep in missing_deps)
        error_msg += "\n\nInstall them using pip:"
        error_msg += "\npip install pillow openpyxl"
        
        # Show error dialog
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        messagebox.showerror("Dependency Error", error_msg)
        root.destroy()
        
        return False
    
    return True


def main():
    """Main application function"""
    # Configure logging
    logger = setup_logging()
    logger.info("Starting Weinig Hydromat Tool Manager")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Missing dependencies, exiting")
        sys.exit(1)
    
    # Initialize configuration
    try:
        from config.app_config import init_config
        config = init_config()
        logger.info(f"Configuration loaded from: {config.config_file}")
    except ImportError as e:
        logger.error(f"Error importing configuration module: {e}")
        messagebox.showerror("Import Error", f"Cannot load configuration: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        # Create default configuration
        try:
            config = init_config()
            logger.info("Created default configuration")
        except Exception as e2:
            logger.error(f"Cannot create default configuration: {e2}")
            messagebox.showerror("Configuration Error", f"Cannot create configuration: {e2}")
            sys.exit(1)
    
    # Create main window
    root = tk.Tk()
    
    # Устанавливаем заголовок окна
    root.title("Weinig Hydromat Tool Manager")
    
    # Configure theme and styles
    try:
        style = ttk.Style()
        
        # Try different themes
        available_themes = style.theme_names()
        logger.info(f"Available themes: {list(available_themes)}")
        
        preferred_themes = ['clam', 'alt', 'default', 'classic']
        
        for theme in preferred_themes:
            if theme in available_themes:
                try:
                    style.theme_use(theme)
                    logger.info(f"Using theme: {theme}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to apply theme {theme}: {e}")
                    continue
        else:
            if available_themes:
                try:
                    style.theme_use(available_themes[0])
                    logger.info(f"Using theme: {available_themes[0]}")
                except Exception as e:
                    logger.warning(f"Failed to apply theme {available_themes[0]}: {e}")
    except Exception as e:
        logger.warning(f"Could not set theme: {e}")
    
    # Create and run the application
    try:
        from gui.main_window import WeinigHydromatManager
        from core.database import DatabaseManager

        db_manager = DatabaseManager()
        app = WeinigHydromatManager(root, db_manager)

        logger.info("Application started successfully")
        
        # Handle window closing
        def on_closing():
            logger.info("Application closing")
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Start the main loop
        root.mainloop()
        
        logger.info("Application closed")
        
    except ImportError as e:
        logger.error(f"Cannot import application module: {e}", exc_info=True)
        messagebox.showerror("Import Error", f"Cannot load application: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error in application: {e}", exc_info=True)
        
        # Show error message
        error_msg = f"A critical error occurred:\n\n{str(e)}\n\n"
        error_msg += "Details are in the log."
        
        messagebox.showerror("Critical Error", error_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
