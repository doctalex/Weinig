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

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError as e:
    print(f"Error importing tkinter: {e}")
    sys.exit(1)

# Windows 7 compatibility settings
if platform.system() == 'Windows':
    # Set process DPI awareness for better display scaling
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # System DPI aware
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # Fallback for older Windows
        except (AttributeError, OSError):
            pass

# Add the project root directory to the path
project_root = Path(__file__).parent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Check Python version
if sys.version_info < (3, 8):
    error_msg = "This application requires Python 3.8 or higher"
    print(error_msg)
    if platform.system() == 'Windows':
        ctypes.windll.user32.MessageBoxW(0, error_msg, "Python Version Error", 0x10)
    sys.exit(1)

try:
    from config.app_config import init_config, get_config
    from gui.main_window import WeinigHydromatManager
except ImportError as e:
    error_msg = f"Failed to import required modules: {e}"
    print(error_msg)
    if platform.system() == 'Windows':
        ctypes.windll.user32.MessageBoxW(0, error_msg, "Import Error", 0x10)
    sys.exit(1)

def get_app_root() -> Path:
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
        
        from tkinter import messagebox
        messagebox.showerror("Dependency Error", error_msg)
        
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
        config = init_config()
        logger.info(f"Configuration loaded from: {config.config_file}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        # Create default configuration
        config = init_config()
    
    # Create main window
    root = tk.Tk()
    
    # Configure theme and styles
    try:
        from tkinter import ttk
        style = ttk.Style()
        
        # Try different themes
        available_themes = style.theme_names()
        preferred_themes = ['clam', 'alt', 'default', 'classic']
        
        for theme in preferred_themes:
            if theme in available_themes:
                style.theme_use(theme)
                logger.info(f"Using theme: {theme}")
                break
        else:
            if available_themes:
                style.theme_use(available_themes[0])
                logger.info(f"Using theme: {available_themes[0]}")
    except Exception as e:
        logger.warning(f"Could not set theme: {e}")
    
    # Create and run the application
    try:
        app = WeinigHydromatManager(root)
        logger.info("Application started successfully")
        
        # Handle window closing
        def on_closing():
            logger.info("Application closing")
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Start the main loop
        root.mainloop()
        
        logger.info("Application closed")
        
    except Exception as e:
        logger.error(f"Fatal error in application: {e}", exc_info=True)
        
        # Show error message
        error_msg = f"A critical error occurred:\n\n{str(e)}\n\n"
        error_msg += "Details are in the log file."
        
        from tkinter import messagebox
        messagebox.showerror("Critical Error", error_msg)
        
        sys.exit(1)

if __name__ == "__main__":
    main()