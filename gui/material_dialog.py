import tkinter as tk
from tkinter import ttk
import logging
from gui.base.dialogs import show_error, show_info

logger = logging.getLogger(__name__)

class MaterialAddDialog:
    """Диалоговое окно для добавления нового типоразмера заготовки"""
    
    def __init__(self, parent, db_manager, callback: callable = None):
        """
        Args:
            parent: Родительское окно
            db_manager: Экземпляр DatabaseManager для работы с БД
            callback: Функция, вызываемая после успешного сохранения
        """
        self.window = tk.Toplevel(parent)
        self.window.title("New Material Size")
        self.window.geometry("320x400")
        self.window.resizable(False, False)
        
        self.db = db_manager
        self.callback = callback
        
        # Делаем окно модальным
        self.window.transient(parent)
        self.window.grab_set()
        self.window.focus_set()

        self._setup_ui()
        self._center_window(parent)

    def _setup_ui(self):
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Поля ввода
        # Ширина
        ttk.Label(main_frame, text="Width (mm):*").pack(anchor=tk.W)
        self.width_var = tk.StringVar()
        self.width_entry = ttk.Entry(main_frame, textvariable=self.width_var)
        self.width_entry.pack(fill=tk.X, pady=(0, 15))
        self.width_entry.focus_set()

        # Толщина
        ttk.Label(main_frame, text="Thickness (mm):*").pack(anchor=tk.W)
        self.thickness_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.thickness_var).pack(fill=tk.X, pady=(0, 15))

        # Категория (Name в твоей БД)
        ttk.Label(main_frame, text="Material Name/Category:").pack(anchor=tk.W)
        self.name_var = tk.StringVar(value="Thermowood")
        ttk.Entry(main_frame, textvariable=self.name_var).pack(fill=tk.X, pady=(0, 15))

        # Описание (Description в твоей БД)
        ttk.Label(main_frame, text="Description/Code:").pack(anchor=tk.W)
        self.desc_var = tk.StringVar(value="WT")
        ttk.Entry(main_frame, textvariable=self.desc_var).pack(fill=tk.X, pady=(0, 20))

        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_frame, text="Save", command=self._save, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.window.destroy, width=15).pack(side=tk.RIGHT, padx=5)

        # Привязка Enter для сохранения
        self.window.bind('<Return>', lambda e: self._save())
        self.window.bind('<Escape>', lambda e: self.window.destroy())

    def _save(self):
        try:
            # Считываем и базово чистим ввод
            width_raw = self.width_var.get().replace(',', '.')
            thick_raw = self.thickness_var.get().replace(',', '.')
            
            if not width_raw or not thick_raw:
                show_error(self.window, "Error", "Width and Thickness are required!")
                return

            width = float(width_raw)
            thickness = float(thick_raw)
            name = self.name_var.get().strip() or "General"
            description = self.desc_var.get().strip()

            # Сохраняем напрямую в базу через метод, который мы добавим в DatabaseManager
            new_id = self.db.add_material_size(width, thickness, name, description)
            
            if new_id:
                logger.info(f"Material {width}x{thickness} added with ID: {new_id}")
                if self.callback:
                    self.callback(new_id) # Передаем ID нового материала обратно
                self.window.destroy()
            
        except ValueError:
            show_error(self.window, "Input Error", "Please enter valid numbers for dimensions.")
        except Exception as e:
            logger.error(f"Error saving material: {e}")
            show_error(self.window, "DB Error", f"Could not save to database: {e}")

    def _center_window(self, parent):
        self.window.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (self.window.winfo_width() // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")