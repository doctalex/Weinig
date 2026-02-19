"""
Стандартные диалоги
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from .window import BaseDialog
from typing import Optional, Callable

class ConfirmDialog(BaseDialog):
    """Диалог подтверждения"""
    
    def __init__(self, parent, title: str, message: str, 
                 ok_text: str = "OK", cancel_text: str = "Cancel"):
        self.message = message
        self.ok_text = ok_text
        self.cancel_text = cancel_text
        super().__init__(parent, title, 300, 150)
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text=self.message, wraplength=250).pack(pady=(0, 20))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text=self.ok_text, 
                  command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=self.cancel_text,
                  command=self.on_cancel).pack(side=tk.RIGHT, padx=5)

class InputDialog(BaseDialog):
    """Диалог ввода текста"""
    
    def __init__(self, parent, title: str, label: str, 
                 default: str = "", width: int = 30):
        self.label = label
        self.default = default
        self.width = width
        super().__init__(parent, title, 350, 150)
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text=self.label).pack(anchor=tk.W, pady=(0, 10))
        
        self.var = tk.StringVar(value=self.default)
        entry = ttk.Entry(main_frame, textvariable=self.var, width=self.width)
        entry.pack(fill=tk.X, pady=(0, 20))
        entry.focus_set()
        entry.select_range(0, tk.END)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="OK", 
                  command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel",
                  command=self.on_cancel).pack(side=tk.RIGHT, padx=5)
    
    def get_value(self) -> str:
        return self.var.get().strip()

class ProgressDialog(BaseDialog):
    """Диалог прогресса"""
    
    def __init__(self, parent, title: str, message: str = "Processing..."):
        self.message = message
        super().__init__(parent, title, 300, 120)
        self.window.resizable(False, False)
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text=self.message).pack(pady=(0, 10))
        
        self.progress = ttk.Progressbar(
            main_frame, mode='indeterminate', length=200
        )
        self.progress.pack(pady=(0, 10))
        self.progress.start(10)
    
    def close(self):
        """Закрывает диалог"""
        self.progress.stop()
        self.destroy()

def show_error(parent, title: str, message: str):
    """Показывает диалог ошибки"""
    messagebox.showerror(title, message, parent=parent)

def show_warning(parent, title: str, message: str):
    """Показывает диалог предупреждения"""
    messagebox.showwarning(title, message, parent=parent)

def show_info(parent, title: str, message: str):
    """Показывает информационный диалог"""
    messagebox.showinfo(title, message, parent=parent)

def ask_yesno(parent, title: str, message: str) -> bool:
    """Спрашивает Да/Нет"""
    return messagebox.askyesno(title, message, parent=parent)

def ask_yesnocancel(parent, title: str, message: str) -> Optional[bool]:
    """Спрашивает Да/Нет/Отмена"""
    return messagebox.askyesnocancel(title, message, parent=parent)

def open_file_dialog(parent, title: str = "Open File", 
                    filetypes: list = None) -> Optional[str]:
    """Открывает диалог выбора файла"""
    if filetypes is None:
        filetypes = [("All files", "*.*")]
    
    return filedialog.askopenfilename(
        title=title, filetypes=filetypes, parent=parent
    )

def save_file_dialog(parent, title: str = "Save File",
                    defaultextension: str = "",
                    filetypes: list = None) -> Optional[str]:
    """Открывает диалог сохранения файла"""
    if filetypes is None:
        filetypes = [("All files", "*.*")]
    
    return filedialog.asksaveasfilename(
        title=title, defaultextension=defaultextension,
        filetypes=filetypes, parent=parent
    )