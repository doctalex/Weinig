"""
Кастомные виджеты
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Callable
from PIL import Image
RESAMPLE = getattr(Image, 'Resampling', Image).LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS

class LabeledEntry(ttk.Frame):
    """Поле ввода с меткой"""
    
    def __init__(self, parent, label: str, width: int = 30, **kwargs):
        super().__init__(parent)
        ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0, 10))
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, width=width, **kwargs)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def get(self) -> str:
        return self.var.get().strip()
    
    def set(self, value: str):
        self.var.set(value)
    
    def clear(self):
        self.var.set("")

class LabeledSpinbox(ttk.Frame):
    """Спинбокс с меткой"""
    
    def __init__(self, parent, label: str, from_: int, to: int, 
                 default: int = 1, width: int = 10):
        super().__init__(parent)
        ttk.Label(self, text=label).pack(side=tk.LEFT, padx=(0, 10))
        self.var = tk.IntVar(value=default)
        self.spinbox = tk.Spinbox(
            self, from_=from_, to=to, 
            textvariable=self.var, width=width
        )
        self.spinbox.pack(side=tk.LEFT)
    
    def get(self) -> int:
        return self.var.get()
    
    def set(self, value: int):
        self.var.set(value)

class StatusLabel(ttk.Label):
    """Метка для отображения статуса"""
    
    STATUS_COLORS = {
        'ready': 'green',
        'worn': 'orange',
        'in_service': 'red',
        'info': 'blue',
        'warning': 'orange',
        'error': 'red'
    }
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
    
    def set_status(self, text: str, status_type: str = 'info'):
        """Устанавливает статус с цветом"""
        self.config(text=text)
        color = self.STATUS_COLORS.get(status_type, 'black')
        self.config(foreground=color)

class ImagePreview(tk.Label):
    """Превью изображения"""
    
    def __init__(self, parent, width: int = 200, height: int = 150, **kwargs):
        super().__init__(parent, **kwargs)
        self.width = width
        self.height = height
        self.config(
            width=width, 
            height=height,
            relief='sunken', 
            borderwidth=1,
            bg='white', 
            text="No Image",
            anchor='center'  # Центрируем содержимое
        )
        self.pack_propagate(False)  # Предотвращаем изменение размера
    
    def set_image(self, image_data: Optional[bytes]):
        """Устанавливает изображение"""
        if image_data:
            try:
                from PIL import Image, ImageTk
                import io
                
                img = Image.open(io.BytesIO(image_data))
                
                # Рассчитываем соотношение сторон
                img_ratio = img.width / img.height
                preview_ratio = self.width / self.height
                
                # Масштабируем с сохранением пропорций
                if img_ratio > preview_ratio:
                    # Широкое изображение
                    new_width = self.width
                    new_height = int(self.width / img_ratio)
                else:
                    # Высокое изображение
                    new_height = self.height
                    new_width = int(self.height * img_ratio)
                
                img = img.resize((new_width, new_height), RESAMPLE)
                photo = ImageTk.PhotoImage(img)
                
                # Обновляем метку
                self.config(image=photo, text="")
                self.image = photo  # сохраняем ссылку
                
            except ImportError:
                self.config(text="PIL not installed")
            except Exception as e:
                self.config(text=f"Error: {str(e)[:30]}")
        else:
            self.clear()
    
    def clear(self):
        """Очищает изображение"""
        self.config(image='', text="No Image")
        if hasattr(self, 'image'):
            self.image = None