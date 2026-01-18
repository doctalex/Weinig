"""
Виджет для предпросмотра изображений инструментов
Поддерживает PNG, JPG, BMP и PDF (иконка)
"""

import tkinter as tk
from PIL import Image, ImageTk
import os

class ImagePreview(tk.Frame):
    def __init__(self, parent, width=400, height=200, bg="white"):
        super().__init__(parent, width=width, height=height, bg=bg)
        self.width = width
        self.height = height
        self.bg = bg
        self.image_label = tk.Label(self, bg=bg)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        self.current_image = None

    def set_image(self, path):
        """Показывает изображение (масштабирует по размеру виджета)"""
        if not os.path.exists(path):
            self.clear()
            return
        try:
            img = Image.open(path)
            img.thumbnail((self.width, self.height), Image.ANTIALIAS)
            self.current_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.current_image)
        except Exception as e:
            self.clear()
            print(f"Failed to load image {path}: {e}")

    def set_pdf_icon(self, icon_path):
        """Показывает иконку PDF вместо изображения"""
        if not os.path.exists(icon_path):
            self.clear()
            return
        try:
            img = Image.open(icon_path)
            img.thumbnail((self.width, self.height), Image.ANTIALIAS)
            self.current_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.current_image)
        except Exception as e:
            self.clear()
            print(f"Failed to load PDF icon {icon_path}: {e}")

    def clear(self):
        """Очищает предпросмотр"""
        self.current_image = None
        self.image_label.config(image="", text="", bg=self.bg)
