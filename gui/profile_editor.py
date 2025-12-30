"""
Редактор профилей - полная исправленная версия
"""
import os
import json
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional
from pathlib import Path
from datetime import datetime

from core.models import Profile
from services.profile_service import ProfileService
from gui.base.dialogs import show_error, show_info, ask_yesno
from gui.base.widgets import ImagePreview
from utils.logger import log_profile_change

logger = logging.getLogger(__name__)


class ProfileEditor:
    """Окно редактирования профиля - полная версия"""
    
    def __init__(self, parent, profile_service: ProfileService, 
                profile: Optional[Profile] = None, callback=None):
        print("ProfileEditor initialized")  # Debug print
        self.parent = parent
        self.profile_service = profile_service
        self.profile = profile
        self.callback = callback
        self.image_data = None
        self.is_editing = profile is not None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        # Создание окна
        self.window = tk.Toplevel(self.parent)
        title = "Edit Profile" if self.is_editing else "Add Profile"
        self.window.title(title)
        self.window.geometry("500x700")  # Увеличиваем высоту окна
        self.window.minsize(500, 700)   # Минимальный размер
        self.window.resizable(True, True)
        
        # Делаем модальным
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.focus_set()
        
        # Основной фрейм
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Создаем фрейм с возможностью прокрутки только при необходимости
        container = ttk.Frame(main_frame)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas для прокрутки
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Привязываем конфигурацию скроллбара
        def _on_frame_configure(event):
            # Обновляем область прокрутки при изменении содержимого
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Отключаем скроллбар, если содержимое помещается на экране
            if scrollable_frame.winfo_reqheight() <= canvas.winfo_height():
                scrollbar.pack_forget()
                canvas.configure(yscrollcommand=None)
            else:
                scrollbar.pack(side="right", fill="y")
                canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        # Привязываем колесо мыши для прокрутки
        def _on_mouse_wheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                # Игнорируем ошибки, возникающие при уничтожении окна
                pass
        
        # Сохраняем ID привязки для последующего удаления
        self._mouse_wheel_binding = canvas.bind_all("<MouseWheel>", _on_mouse_wheel)
        
        # Создаем окно с содержимым
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Упаковываем canvas и скроллбар
        canvas.pack(side="left", fill="both", expand=True)
        
        # Обновляем геометрию после загрузки всех виджетов
        def _update_scroll_region():
            canvas.update_idletasks()
            _on_frame_configure(None)
        
        self.window.after(100, _update_scroll_region)
        
        # Основной контейнер с отступами
        main_container = scrollable_frame
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Фрейм для формы
        form_frame = ttk.Frame(main_container)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Форма ввода
        self._setup_form(form_frame)
        
        # Фрейм для кнопок внизу
        button_frame = ttk.Frame(main_container)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        # Кнопки
        self._setup_buttons(button_frame)
        
        # Загружаем данные профиля если редактируем
        if self.is_editing and self.profile:
            self._load_profile_data()
        
        # Привязка клавиш
        self.window.bind('<Return>', lambda e: self.save())
        self.window.bind('<Escape>', lambda e: self.window.destroy())
        
        # Центрируем
        self.center_window()
        
        # Обработчик закрытия окна
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """Обработчик закрытия окна"""
        try:
            # Удаляем привязку колеса мыши
            if hasattr(self, '_mouse_wheel_binding'):
                self.window.unbind_all("<MouseWheel>")
        except Exception as e:
            logger.warning(f"Ошибка при закрытии окна: {e}")
        
        # Закрываем окно
        self.window.destroy()

    def _setup_form(self, parent):
        """Настройка формы ввода"""
        # Имя профиля
        name_frame = ttk.Frame(parent)
        name_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(name_frame, text="Profile Name:*", 
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=self.name_var, 
                            font=("Arial", 11))
        name_entry.pack(fill=tk.X, pady=(5, 0))
        
        # Описание
        desc_frame = ttk.LabelFrame(parent, text="Description", padding="10")
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.desc_text = tk.Text(desc_frame, height=4, font=("Arial", 10))
        self.desc_text.pack(fill=tk.BOTH, expand=True)
        
        # Параметры обработки
        params_frame = ttk.LabelFrame(parent, text="Processing Parameters", padding="10")
        params_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Скорость подачи
        feed_frame = ttk.Frame(params_frame)
        feed_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(feed_frame, text="Feed Rate:", width=12).pack(side=tk.LEFT)
        self.feed_var = tk.StringVar(value="30")
        feed_entry = ttk.Entry(feed_frame, textvariable=self.feed_var, width=10)
        feed_entry.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(feed_frame, text="m/min").pack(side=tk.LEFT, padx=(5, 0))
        
        # Размеры
        size_frame = ttk.Frame(params_frame)
        size_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(size_frame, text="Material Size:", width=12).pack(side=tk.LEFT)
        self.material_var = tk.StringVar(value="")
        material_entry = ttk.Entry(size_frame, textvariable=self.material_var, width=15)
        material_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(size_frame, text="Product Size:", width=12).pack(side=tk.LEFT, padx=(10, 0))
        self.product_var = tk.StringVar(value="")
        product_entry = ttk.Entry(size_frame, textvariable=self.product_var, width=15)
        product_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Изображение (уменьшенная и зафиксированная область)
        image_frame = ttk.LabelFrame(parent, text="Profile Image", padding="10")
        image_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Кнопки управления изображением
        image_btn_frame = ttk.Frame(image_frame)
        image_btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(image_btn_frame, text="Browse Image", 
                command=self.browse_image).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(image_btn_frame, text="Remove Image", 
                command=self.remove_image).pack(side=tk.LEFT)
        
        # Image preview with fixed size container
        preview_container = ttk.Frame(image_frame, width=200, height=150)
        preview_container.pack_propagate(False)  # Prevent container from resizing
        preview_container.pack(pady=5)
        # Create ImagePreview with smaller dimensions
        self.image_preview = ImagePreview(preview_container, width=180, height=120)
        self.image_preview.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)
    
    def _setup_buttons(self, parent):
        """Настройка кнопок - размещаем по центру внизу"""
        # Контейнер для кнопок с фиксированной высотой
        container = ttk.Frame(parent)
        container.pack(fill=tk.X, pady=20)
        
        # Фрейм для центрирования кнопок
        button_frame = ttk.Frame(container)
        button_frame.pack(expand=True)
        
        # Кнопка удаления (только при редактировании)
        if self.is_editing:
            delete_btn = ttk.Button(
                button_frame, 
                text="Delete", 
                command=self.delete,
                width=15
            )
            delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Кнопка отмены
        cancel_btn = ttk.Button(
            button_frame, 
            text="Cancel", 
            command=self.window.destroy,
            width=15
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Кнопка сохранения
        save_btn = ttk.Button(
            button_frame, 
            text="Save", 
            command=self.save,
            width=15
        )
        save_btn.pack(side=tk.LEFT, padx=5)
    
    def center_window(self):
        """Центрирует окно относительно родительского"""
        self.window.update_idletasks()
        
        try:
            if self.parent and self.parent.winfo_exists():
                parent_x = self.parent.winfo_rootx()
                parent_y = self.parent.winfo_rooty()
                parent_width = self.parent.winfo_width()
                parent_height = self.parent.winfo_height()
                
                window_width = self.window.winfo_width()
                window_height = self.window.winfo_height()
                
                x = parent_x + (parent_width - window_width) // 2
                y = parent_y + (parent_height - window_height) // 2
                
                self.window.geometry(f"+{x}+{y}")
                return
        except Exception:
            pass
        
        # Fallback: центрирование по экрану
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        window_width = self.window.winfo_width()
        window_height = self.window.winfo_height()
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.window.geometry(f"+{x}+{y}")
    
    def _load_profile_data(self):
        """Загружает данные профиля в форму"""
        if not self.profile:
            return
        
        self.name_var.set(self.profile.name)
        self.desc_text.insert("1.0", self.profile.description)
        self.feed_var.set(str(self.profile.feed_rate))
        self.material_var.set(self.profile.material_size)
        self.product_var.set(self.profile.product_size)
        
        # Загружаем изображение
        if self.profile.image_data:
            self.image_data = self.profile.image_data
            self.image_preview.set_image(self.image_data)
    
    def browse_image(self):
        """Выбирает изображение профиля"""
        filename = filedialog.askopenfilename(
            title="Select Profile Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp"),
                ("All files", "*.*")
            ],
            parent=self.window
        )
        
        if filename:
            try:
                with open(filename, "rb") as f:
                    self.image_data = f.read()
                
                self.image_preview.set_image(self.image_data)
                
            except Exception as e:
                show_error(self.window, "Error", f"Could not load image: {e}")
    
    def remove_image(self):
        """Удаляет изображение профиля"""
        self.image_data = None
        self.image_preview.clear()
    
    def save(self):
        """Сохраняет профиль"""
        print("Save method called - Start")  # Debug print
        try:
            print("Getting name...")  # Debug print
            name = self.name_var.get().strip()
            print(f"Name: {name}")  # Debug print
            
            if not name:
                messagebox.showerror("Error", "Profile name is required")
                return

            description = self.desc_text.get("1.0", tk.END).strip()
            feed_rate = float(self.feed_var.get())
            material_size = self.material_var.get().strip()
            product_size = self.product_var.get().strip()

            # Prepare profile data for logging
            profile_data = {
                "action": "update" if self.is_editing else "create",
                "description": description,
                "feed_rate": feed_rate,
                "material_size": material_size,
                "product_size": product_size,
                "has_image": bool(self.image_data),
                "tool_assignments": {}  # Add empty tool assignments as they're not available here
            }

            # Ensure logs directory exists
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_dir = os.path.join(base_dir, "logs")
            print(f"Base directory: {base_dir}")
            print(f"Log directory: {log_dir}")
            os.makedirs(log_dir, exist_ok=True)
            print(f"Ensured log directory exists at: {log_dir}")

            # Log the profile change
            from utils.logger import log_profile_change
            log_profile_change({
                'name': name,
                'feed_rate': profile_data.get('feed_rate', 0),
                'material_size': profile_data.get('material_size', ''),
                'product_size': profile_data.get('product_size', ''),
                'tools': []  # Add tools if available in profile_data
            })
            print("Profile change logged successfully")

            if self.is_editing and self.profile:
                # Update existing profile
                success = self.profile_service.update_profile(
                    self.profile.id,
                    name=name,
                    description=description,
                    feed_rate=feed_rate,
                    material_size=material_size,
                    product_size=product_size,
                    image_data=self.image_data
                )
                action = "updated"
            else:
                # Create new profile
                profile_id = self.profile_service.create_profile(
                    name=name,
                    description=description,
                    feed_rate=feed_rate,
                    material_size=material_size,
                    product_size=product_size,
                    image_data=self.image_data
                )
                success = profile_id is not None
                action = "created"

            if success:
                messagebox.showinfo("Success", f"Profile {action} successfully")
                if self.on_save:
                    self.on_save()
                self.window.destroy()
            else:
                messagebox.showerror("Error", f"Failed to {action} profile")

        except ValueError as ve:
            messagebox.showerror("Input Error", f"Invalid input: {str(ve)}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_save(self):
        """Callback called after successful save"""
        if hasattr(self, 'callback') and self.callback:
            self.callback()
        
    def delete(self):
        """Удаляет профиль"""
        if not self.profile:
            return
        
        # Подсчитываем инструменты
        try:
            tools_count = self.profile_service.count_tools(self.profile.id)
        except:
            tools_count = 0
        
        # Формируем сообщение
        message = f"Delete profile '{self.profile.name}'?"
        if tools_count > 0:
            message += f"\n\n⚠️ WARNING: {tools_count} tool(s) will also be deleted!"
            message += "\n\nAll tools assigned to this profile will be permanently deleted."
        
        if ask_yesno(self.window, "Confirm Delete", message):
            try:
                success = self.profile_service.delete_profile(self.profile.id)
                
                if success:
                    show_info(self.window, "Success", "Profile deleted successfully")
                    self.window.destroy()
                    if self.callback:
                        self.callback()
                else:
                    show_error(self.window, "Error", "Failed to delete profile")
                    
            except Exception as e:
                show_error(self.window, "Error", f"Delete failed: {e}")


# Экспорт класса
__all__ = ['ProfileEditor']