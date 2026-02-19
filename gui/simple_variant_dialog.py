# gui/simple_variant_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox


class SimpleVariantDialog:
    """Простой диалог для ввода размеров продукта"""
    
    def __init__(self, parent, title: str = "Product Size", 
                 initial_values: list = None):
        self.parent = parent
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("300x150")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        self._setup_ui(initial_values)
        self.center_window()
        
        self.window.bind('<Return>', lambda e: self._save())
        self.window.bind('<Escape>', lambda e: self.window.destroy())
        
        self.window.wait_window()
    
    def _setup_ui(self, initial_values: list = None):
        """Настройка интерфейса"""
        main_frame = ttk.Frame(self.window, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Ширина
        width_frame = ttk.Frame(main_frame)
        width_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(width_frame, text="Width (mm):*", width=12).pack(side=tk.LEFT)
        self.width_var = tk.StringVar(value=initial_values[0] if initial_values else "")
        ttk.Entry(width_frame, textvariable=self.width_var, width=10).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(width_frame, text="mm").pack(side=tk.LEFT, padx=(5, 0))
        
        # Толщина (опционально)
        thickness_frame = ttk.Frame(main_frame)
        thickness_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(thickness_frame, text="Thickness (mm):", width=12).pack(side=tk.LEFT)
        self.thickness_var = tk.StringVar(value=initial_values[1] if initial_values and len(initial_values) > 1 else "")
        ttk.Entry(thickness_frame, textvariable=self.thickness_var, width=10).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(thickness_frame, text="mm").pack(side=tk.LEFT, padx=(5, 0))
        
        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.window.destroy,
            width=10
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            button_frame,
            text="OK",
            command=self._save,
            width=10
        ).pack(side=tk.RIGHT)
    
    def _save(self):
        """Сохранить введенные данные"""
        width = self.width_var.get().strip()
        
        if not width:
            messagebox.showerror("Input Error", "Width is required")
            return
        
        try:
            float(width)  # Проверка что это число
            thickness = self.thickness_var.get().strip()
            if thickness:  # Проверка толщины если введена
                float(thickness)
            
            self.result = (width, thickness)
            self.window.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values")
    
    def center_window(self):
        """Центрирует окно"""
        self.window.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        window_width = self.window.winfo_width()
        window_height = self.window.winfo_height()
        
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2
        
        self.window.geometry(f"+{x}+{y}")