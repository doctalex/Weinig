import tkinter as tk
from tkinter import ttk

class ScrollableContainer(ttk.Frame):
    """
    Универсальный контейнер с вертикальной прокруткой.
    Автоматически адаптирует внутреннюю ширину под размер окна.
    """
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # Создаем холст и полосу прокрутки
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        # Фрейм внутри холста, в котором будут все ваши виджеты
        self.scrollable_content = ttk.Frame(self.canvas)

        # При изменении размера содержимого обновляем область прокрутки
        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Размещаем фрейм на холсте
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        
        # Растягиваем внутренний контент по ширине холста
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Упаковка компонентов
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Поддержка прокрутки колесиком мыши
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_canvas_configure(self, event):
        # Гарантируем, что ширина контента совпадает с шириной видимой области
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        # Прокрутка для Windows
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")