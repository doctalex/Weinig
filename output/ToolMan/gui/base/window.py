"""
Базовые классы окон
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

class BaseWindow:
    """Базовый класс для окон"""
    
    def __init__(self, parent, title: str, width: int = 400, height: int = 300,
                 resizable: bool = False, modal: bool = False):
        self.parent = parent
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title(title)
        self.window.geometry(f"{width}x{height}")
        self.window.resizable(resizable, resizable)
        
        if modal and parent:
            self.window.transient(parent)
            self.window.grab_set()
            self.window.focus_set()
    
    def center_window(self):
        """Центрирует окно"""
        self.window.update_idletasks()
        
        if self.parent and self.parent.winfo_exists():
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            window_width = self.window.winfo_width()
            window_height = self.window.winfo_height()
            
            x = parent_x + (parent_width - window_width) // 2
            y = parent_y + (parent_height - window_height) // 2
        else:
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            x = (screen_width - self.window.winfo_width()) // 2
            y = (screen_height - self.window.winfo_height()) // 2
        
        self.window.geometry(f"+{x}+{y}")
    
    def run(self):
        """Запускает главный цикл"""
        self.center_window()
        self.window.mainloop()
    
    def destroy(self):
        """Закрывает окно"""
        if self.window:
            self.window.destroy()

class BaseDialog(BaseWindow):
    """Базовый класс для диалогов"""
    
    def __init__(self, parent, title: str, width: int = 300, height: int = 200):
        super().__init__(parent, title, width, height, modal=True)
        self.result = None
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса (должен быть переопределен)"""
        pass
    
    def on_ok(self):
        """Обработка нажатия OK"""
        self.result = True
        self.destroy()
    
    def on_cancel(self):
        """Обработка нажатия Cancel"""
        self.result = False
        self.destroy()