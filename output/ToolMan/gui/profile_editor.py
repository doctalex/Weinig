# gui/profile_editor.py
"""
Редактор профилей с поддержкой PDF
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
    """Окно редактирования профиля с поддержкой PDF"""
    
    def __init__(self, parent, profile_service: ProfileService, 
                profile: Optional[Profile] = None, callback=None):
        print("ProfileEditor initialized")
        self.parent = parent
        self.profile_service = profile_service
        self.profile = profile
        self.callback = callback
        
        # PDF данные вместо изображения
        self.pdf_data = None
        self.pdf_filename = None
        self.original_pdf_data = None  # Сохраняем оригинальный PDF
        self.original_pdf_filename = None  # Сохраняем оригинальное имя файла
        
        # Флаги для отслеживания изменений PDF
        self.pdf_was_removed = False
        self.pdf_was_uploaded = False
        
        self.is_editing = profile is not None
        
        # Флаг для защиты от двойного нажатия Save
        self._saving = False
        
        # Получаем глобальный SecurityManager
        try:
            from config.security import get_security_manager, is_read_only
            self.security_manager = get_security_manager()
            self.security_manager.add_callback(self._on_security_mode_changed)
            print(f"DEBUG: SecurityManager initialized, read_only: {is_read_only()}")
        except Exception as e:
            print(f"DEBUG: SecurityManager error: {e}")
            self.security_manager = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса с фиксированными кнопками управления"""
        # Создание окна
        self.window = tk.Toplevel(self.parent)
        title = "Edit Profile" if self.is_editing else "Add Profile"
        self.window.title(title)
        self.window.geometry("650x750")  # Увеличиваем размеры
        self.window.minsize(600, 700)
        self.window.resizable(True, True)
        
        # Делаем модальным
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.focus_set()
        
        # Основная структура: 1) Скроллируемая форма, 2) Фиксированные кнопки
        main_container = ttk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Фрейм для скроллируемого контента (занимает всё пространство кроме кнопок)
        scrollable_frame_container = ttk.Frame(main_container)
        scrollable_frame_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas для прокрутки
        canvas = tk.Canvas(scrollable_frame_container)
        scrollbar = ttk.Scrollbar(scrollable_frame_container, orient="vertical", command=canvas.yview)
        
        # Сохраняем ссылку на canvas в self
        self.canvas = canvas
        
        # Фрейм внутри Canvas для размещения виджетов
        scrollable_content = ttk.Frame(canvas)
        
        # Настройка прокрутки
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Показываем скроллбар только при необходимости
            if scrollable_content.winfo_reqheight() > canvas.winfo_height():
                scrollbar.pack(side="right", fill="y")
                canvas.configure(yscrollcommand=scrollbar.set)
            else:
                scrollbar.pack_forget()
                canvas.configure(yscrollcommand=None)
        
        scrollable_content.bind("<Configure>", _on_frame_configure)
        
        # Создаем окно в Canvas
        canvas.create_window((0, 0), window=scrollable_content, anchor="nw", width=canvas.winfo_width())
        
        def _configure_canvas(event):
            canvas.itemconfig(1, width=event.width)  # Обновляем ширину окна в Canvas
        
        canvas.bind('<Configure>', _configure_canvas)
        
        # Упаковка Canvas
        canvas.pack(side="left", fill="both", expand=True)
        
        # Привязка колеса мыши - ИСПРАВЛЕННАЯ ВЕРСИЯ
        def _on_mouse_wheel(event):
            try:
                # Используем self.canvas вместо локальной переменной
                if hasattr(self, 'canvas') and self.canvas.winfo_exists():
                    self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except (tk.TclError, AttributeError):
                # Игнорируем ошибки, возникающие при уничтожении окна
                pass
        
        # Привязываем с использованием self.canvas
        self._mouse_wheel_binding = self.canvas.bind_all("<MouseWheel>", _on_mouse_wheel)
        
        # Настройка формы внутри скроллируемого контента
        self._setup_form(scrollable_content)
        
        # Фрейм для кнопок управления (ВСЕГДА ВИДИМЫЙ)
        button_frame = ttk.Frame(main_container, height=70)  # Фиксированная высота
        button_frame.pack_propagate(False)  # Не менять высоту
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(10, 10))
        
        # Настройка кнопок
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
        
        # Обновляем прокрутку после загрузки
        self.window.after(100, lambda: _on_frame_configure(None))
        
        # Сразу применяем режим доступа после создания всех виджетов
        self.window.after(150, self._apply_access_mode)

    def _on_close(self):
        """Обработчик закрытия окна"""
        try:
            # Отписываемся от SecurityManager
            if hasattr(self, 'security_manager') and self.security_manager:
                try:
                    self.security_manager.remove_callback(self._on_security_mode_changed)
                    print("DEBUG: Unsubscribed from security changes")
                except Exception as e:
                    print(f"DEBUG: Error unsubscribing from security: {e}")
            
            # Удаляем привязку колеса мыши - ВАЖНО: ДО уничтожения окна!
            try:
                if hasattr(self, '_mouse_wheel_binding'):
                    # Очищаем все привязки MouseWheel
                    self.window.unbind_all("<MouseWheel>")
                    # Также отключаем конкретную привязку если она была сохранена
                    if hasattr(self, 'canvas'):
                        try:
                            self.canvas.unbind_all("<MouseWheel>")
                        except:
                            pass
            except Exception as e:
                print(f"DEBUG: Error removing mouse wheel binding: {e}")
                
        except Exception as e:
            logger.warning(f"Ошибка при закрытии окна: {e}")
        
        # Закрываем окно
        try:
            self.window.destroy()
        except:
            pass

    def _setup_form(self, parent):
        """Настройка формы ввода с управлением состоянием READ ONLY"""
        # Имя профиля
        name_frame = ttk.Frame(parent)
        name_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(name_frame, text="Profile Name:*", 
                  font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var, 
                                  font=("Arial", 11))
        self.name_entry.pack(fill=tk.X, pady=(5, 0))
        
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
        self.feed_entry = ttk.Entry(feed_frame, textvariable=self.feed_var, width=10)
        self.feed_entry.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(feed_frame, text="m/min").pack(side=tk.LEFT, padx=(5, 0))
        
        # Размеры
        size_frame = ttk.Frame(params_frame)
        size_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(size_frame, text="Material Size:", width=12).pack(side=tk.LEFT)
        self.material_var = tk.StringVar(value="")
        self.material_entry = ttk.Entry(size_frame, textvariable=self.material_var, width=15)
        self.material_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(size_frame, text="Product Size:", width=12).pack(side=tk.LEFT, padx=(10, 0))
        self.product_var = tk.StringVar(value="")
        self.product_entry = ttk.Entry(size_frame, textvariable=self.product_var, width=15)
        self.product_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # PDF документ вместо изображения
        pdf_frame = ttk.LabelFrame(parent, text="Profile Document (PDF)", padding="10")
        pdf_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Кнопки управления PDF
        pdf_btn_frame = ttk.Frame(pdf_frame)
        pdf_btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.upload_btn = ttk.Button(pdf_btn_frame, text="Upload PDF Document", 
                                    command=self.upload_pdf)
        self.upload_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.remove_btn = ttk.Button(pdf_btn_frame, text="Remove PDF", 
                                    command=self.remove_pdf)
        self.remove_btn.pack(side=tk.LEFT)
        
        # Статус PDF
        self.pdf_status_label = ttk.Label(
            pdf_frame,
            text="No PDF document loaded",
            foreground="gray",
            font=("Arial", 9)
        )
        self.pdf_status_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Предпросмотр первой страницы PDF
        preview_container = ttk.LabelFrame(pdf_frame, text="PDF Preview (First Page)", padding="10")
        preview_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        preview_inner = ttk.Frame(preview_container, width=200, height=150)
        preview_inner.pack_propagate(False)
        preview_inner.pack(pady=5)
        
        # Image preview для показа первой страницы PDF
        self.pdf_preview = ImagePreview(preview_inner, width=180, height=120)
        self.pdf_preview.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)
        
        # Подсказка
        info_label = ttk.Label(
            pdf_frame,
            text="Double-click preview to open PDF in viewer",
            foreground="blue",
            font=("Arial", 8, "italic")
        )
        info_label.pack(anchor=tk.W, pady=(5, 0))
    
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
            self.delete_btn = ttk.Button(
                button_frame, 
                text="Delete", 
                command=self.delete,
                width=15
            )
            self.delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Кнопка отмены
        self.cancel_btn = ttk.Button(
            button_frame, 
            text="Cancel", 
            command=self.window.destroy,
            width=15
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Кнопка сохранения
        self.save_btn = ttk.Button(
            button_frame, 
            text="Save", 
            command=self._safe_save,  # Используем обертку для защиты от двойного нажатия
            width=15
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)
    
    def _safe_save(self):
        """Защищенный вызов save с защитой от двойного нажатия"""
        if self._saving:
            return
        self.save_btn.config(state='disabled')
        try:
            self.save()
        except Exception as e:
            print(f"Error in save: {e}")
            self.save_btn.config(state='normal')
            self._saving = False
    
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
        
        # Загружаем статус PDF
        if self.profile.has_pdf:
            self.pdf_status_label.config(
                text=f"PDF: {os.path.basename(self.profile.pdf_path)}",
                foreground="green"
            )
            
            # Загружаем существующий PDF в память
            try:
                self.original_pdf_data = self.profile_service.get_profile_pdf(self.profile.id)
                self.original_pdf_filename = os.path.basename(self.profile.pdf_path)
                
                # Устанавливаем текущие данные PDF равными оригинальным
                self.pdf_data = self.original_pdf_data
                self.pdf_filename = self.original_pdf_filename
                
                print(f"DEBUG: Loaded existing PDF: {self.pdf_filename}, size: {len(self.pdf_data) if self.pdf_data else 0} bytes")
            except Exception as e:
                print(f"DEBUG: Error loading existing PDF: {e}")
                self.original_pdf_data = None
                self.original_pdf_filename = None
                self.pdf_data = None
                self.pdf_filename = None
        else:
            self.pdf_status_label.config(
                text="No PDF document loaded",
                foreground="gray"
            )
            self.original_pdf_data = None
            self.original_pdf_filename = None
        
        # Загружаем превью PDF если есть
        if self.profile.image_data:
            self.pdf_preview.set_image(self.profile.image_data)
    
    def upload_pdf(self):
        """Выбирает PDF файл профиля"""
        # Безопасность: проверяем права загрузки PDF
        if not self._check_security('upload_documents'):
            return
        
        filename = filedialog.askopenfilename(
            title="Select PDF Document",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("All files", "*.*")
            ],
            parent=self.window
        )
        
        if filename:
            try:
                # Проверяем расширение файла
                if not filename.lower().endswith('.pdf'):
                    show_error(self.window, "Error", "Please select a PDF file (.pdf)")
                    return
                
                # Проверяем размер файла (максимум 50MB)
                file_size = os.path.getsize(filename)
                if file_size > 50 * 1024 * 1024:  # 50MB
                    show_error(self.window, "Error", "PDF file is too large. Maximum size is 50MB.")
                    return
                
                # Загружаем PDF
                with open(filename, "rb") as f:
                    self.pdf_data = f.read()
                
                self.pdf_filename = os.path.basename(filename)
                self.pdf_was_uploaded = True  # Флаг что PDF был загружен
                self.pdf_was_removed = False   # Сбрасываем флаг удаления
                
                # Извлекаем превью из PDF
                try:
                    from utils.pdf_manager import PDFManager
                    pdf_manager = PDFManager()
                    preview = pdf_manager.extract_pdf_preview(self.pdf_data)
                    
                    if preview:
                        self.pdf_preview.set_image(preview)
                        self.pdf_status_label.config(
                            text=f"PDF: {self.pdf_filename}",
                            foreground="green"
                        )
                        
                        # Показываем информацию о файле
                        show_info(self.window, "PDF Loaded", 
                                 f"PDF document loaded successfully:\n"
                                 f"File: {self.pdf_filename}\n"
                                 f"Size: {file_size:,} bytes")
                    else:
                        show_error(self.window, "Warning", 
                                 "Could not extract preview from PDF.\n"
                                 "The file may be corrupted or protected.")
                        self.pdf_data = None
                        self.pdf_filename = None
                        self.pdf_was_uploaded = False
                        
                except ImportError:
                    show_error(self.window, "Error", 
                             "PyMuPDF library is not installed.\n"
                             "Please install it: pip install PyMuPDF")
                    self.pdf_data = None
                    self.pdf_filename = None
                    self.pdf_was_uploaded = False
                
            except Exception as e:
                show_error(self.window, "Error", f"Could not load PDF: {e}")
                self.pdf_data = None
                self.pdf_filename = None
                self.pdf_was_uploaded = False
                self.pdf_status_label.config(text="No PDF loaded", foreground="gray")
    
    def remove_pdf(self):
        """Удаляет PDF документ профиля"""
        # Безопасность: проверяем права
        if not self._check_security('modify_profile'):
            return
        
        # Проверяем, есть ли что удалять
        current_status = self.pdf_status_label.cget("text")
        if "No PDF document loaded" in current_status:
            show_info(self.window, "Info", "No PDF document to remove")
            return
        
        response = ask_yesno(
            self.window, 
            "Confirm Remove", 
            "Are you sure you want to remove the PDF document from this profile?"
        )
        
        if response:
            self.pdf_data = None
            self.pdf_filename = None
            self.pdf_preview.clear()
            self.pdf_status_label.config(
                text="No PDF document loaded",
                foreground="gray"
            )
            self.pdf_was_removed = True     # Флаг что PDF был удален
            self.pdf_was_uploaded = False    # Сбрасываем флаг загрузки
    
    def save(self):
        """Сохраняет профиль с PDF"""
        # Защита от двойного нажатия
        if self._saving:
            return
        self._saving = True
        
        try:
            # ПРОВЕРКА РЕЖИМА ДОСТУПА
            if hasattr(self, 'access_mode') and self.access_mode == "READ_ONLY":
                messagebox.showerror(
                    "Access Denied", 
                    "This profile is in READ ONLY mode.\n"
                    "You cannot modify it. Contact an administrator."
                )
                self._saving = False
                self.save_btn.config(state='normal')
                return
            
            # Безопасность: проверяем права сохранения
            if not self._check_security('create_profile' if not self.is_editing else 'edit_profile'):
                self._saving = False
                self.save_btn.config(state='normal')
                return
            
            print("Save method called - Start")  # Debug print
            try:
                print("Getting name...")  # Debug print
                name = self.name_var.get().strip()
                print(f"Name: {name}")  # Debug print
                
                if not name:
                    messagebox.showerror("Error", "Profile name is required")
                    self._saving = False
                    self.save_btn.config(state='normal')
                    return

                description = self.desc_text.get("1.0", tk.END).strip()
                
                try:
                    feed_rate = float(self.feed_var.get())
                except ValueError:
                    feed_rate = 30.0  # Значение по умолчанию
                
                material_size = self.material_var.get().strip()
                product_size = self.product_var.get().strip()

                # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ:
                # Определяем какие PDF данные передавать
                pdf_data_to_save = None
                pdf_filename_to_save = None
                
                if not self.is_editing:
                    # Для нового профиля просто передаем то, что есть
                    pdf_data_to_save = self.pdf_data
                    pdf_filename_to_save = self.pdf_filename
                    print(f"DEBUG: New profile - PDF data: {'yes' if pdf_data_to_save else 'no'}")
                else:
                    # Для редактируемого профиля
                    if self.pdf_was_uploaded:
                        # Пользователь загрузил новый PDF - передаем его
                        pdf_data_to_save = self.pdf_data
                        pdf_filename_to_save = self.pdf_filename
                        print(f"DEBUG: PDF was uploaded - will update with new PDF")
                    elif self.pdf_was_removed:
                        # Пользователь нажал "Remove PDF" - передаем None чтобы удалить
                        pdf_data_to_save = None
                        pdf_filename_to_save = None
                        print(f"DEBUG: PDF was removed - will delete PDF")
                    else:
                        # PDF не менялся
                        if self.original_pdf_data:
                            pdf_data_to_save = self.original_pdf_data
                            pdf_filename_to_save = None  # КЛЮЧЕВОЕ: НЕ ПЕРЕДАВАЙТЕ ИМЯ ФАЙЛА
                            print(f"DEBUG: PDF unchanged - sending data WITHOUT filename")
                        else:
                            pdf_data_to_save = None
                            pdf_filename_to_save = None

                # Логирование перед сохранением
                profile_data = {
                    "action": "update" if self.is_editing else "create",
                    "description": description,
                    "feed_rate": feed_rate,
                    "material_size": material_size,
                    "product_size": product_size,
                    "has_pdf": bool(pdf_data_to_save),
                    "tool_assignments": {}
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
                    'tools': []
                })
                print("Profile change logged successfully")

                if self.is_editing and self.profile:
                    # Update existing profile
                    print(f"DEBUG: Updating profile {self.profile.id}")
                    print(f"DEBUG: PDF data to save: {'yes' if pdf_data_to_save else 'no'}")
                    
                    success = self.profile_service.update_profile(
                        self.profile.id,
                        name=name,
                        description=description,
                        feed_rate=feed_rate,
                        material_size=material_size,
                        product_size=product_size,
                        pdf_data=pdf_data_to_save,
                        pdf_filename=pdf_filename_to_save
                    )
                    action = "updated"
                else:
                    # Create new profile
                    print(f"DEBUG: Creating new profile")
                    profile_id = self.profile_service.create_profile(
                        name=name,
                        description=description,
                        feed_rate=feed_rate,
                        material_size=material_size,
                        product_size=product_size,
                        pdf_data=pdf_data_to_save,
                        pdf_filename=pdf_filename_to_save
                    )
                    success = profile_id is not None
                    action = "created"

                if success:
                    messagebox.showinfo("Success", f"Profile {action} successfully")
                    
                    # Вызываем коллбэк если он есть
                    if hasattr(self, 'callback') and self.callback:
                        self.callback()
                    
                    # Сбрасываем флаги после успешного сохранения
                    self.pdf_was_uploaded = False
                    self.pdf_was_removed = False
                    
                    self.window.destroy()
                else:
                    messagebox.showerror("Error", f"Failed to {action} profile")
                    self._saving = False
                    self.save_btn.config(state='normal')

            except ValueError as ve:
                messagebox.showerror("Input Error", f"Invalid input: {str(ve)}")
                self._saving = False
                self.save_btn.config(state='normal')
            except PermissionError as pe:
                # Ошибка режима безопасности
                messagebox.showerror("Access Denied", str(pe))
                self._saving = False
                self.save_btn.config(state='normal')
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
                import traceback
                traceback.print_exc()
                self._saving = False
                self.save_btn.config(state='normal')
                
        except Exception as e:
            self._saving = False
            self.save_btn.config(state='normal')
            raise e
    
    def delete(self):
        """Удаляет профиль"""
        # Безопасность: проверяем права удаления
        if not self._check_security('delete_profile'):
            return
        
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
    
    def _apply_access_mode(self):
        """Применяет режим доступа (READ ONLY или FULL ACCESS) к виджетам"""
        # Всегда проверяем актуальное состояние
        try:
            from config.security import is_read_only
            current_read_only = is_read_only()
            print(f"DEBUG: Current security mode: {'read_only' if current_read_only else 'full_access'}")
        except Exception as e:
            print(f"DEBUG: Error getting security mode: {e}")
            current_read_only = False  # По умолчанию FULL ACCESS
        
        # Определяем режим доступа
        if current_read_only:
            access_mode = "READ_ONLY"
        else:
            access_mode = "FULL_ACCESS"
        
        # Дополнительная проверка: если профиль заблокирован
        if self.profile and hasattr(self.profile, 'locked') and self.profile.locked:
            access_mode = "READ_ONLY"
        
        print(f"DEBUG: Applying access mode: {access_mode}")
        
        # Применяем режим
        if access_mode == "READ_ONLY":
            state = "disabled"
            bg_color = "#f0f0f0"
            readonly_text = " (READ ONLY)"
            
            # Обновляем заголовок окна
            if hasattr(self, 'window') and self.window.winfo_exists():
                current_title = self.window.title()
                if "(READ ONLY)" not in current_title:
                    self.window.title(f"{current_title} {readonly_text}")
        else:
            state = "normal"
            bg_color = "white"
        
        # Применяем состояние ко всем редактируемым виджетам
        widgets = [
            self.name_entry,
            self.desc_text,
            self.feed_entry,
            self.material_entry,
            self.product_entry,
            self.upload_btn,
            self.remove_btn
        ]
        
        # Добавляем кнопки если они есть
        if hasattr(self, 'save_btn'):
            widgets.append(self.save_btn)
        if hasattr(self, 'delete_btn'):
            widgets.append(self.delete_btn)
        if hasattr(self, 'cancel_btn'):
            widgets.append(self.cancel_btn)
        
        for widget in widgets:
            if widget:
                try:
                    widget.configure(state=state)
                    # Для виджетов с background
                    if hasattr(widget, 'configure') and 'background' in widget.configure():
                        widget.configure(background=bg_color)
                except Exception as e:
                    print(f"DEBUG: Error setting widget state: {e}")  # Debug print
        
        # Для Text виджета устанавливаем состояние отдельно
        if self.desc_text:
            try:
                self.desc_text.configure(state=state)
                if state == "normal":
                    self.desc_text.configure(bg="white")
                else:
                    self.desc_text.configure(bg="#f0f0f0")
            except Exception as e:
                print(f"DEBUG: Error setting desc_text: {e}")
        
        # Сохраняем режим доступа
        self.access_mode = access_mode
        logger.info(f"Access mode applied: {access_mode}")
    
    # ========== МЕТОДЫ БЕЗОПАСНОСТИ ==========
    
    def _check_security(self, action: str) -> bool:
        """
        Проверка прав доступа с динамической проверкой режима
        """
        # ВСЕГДА проверяем актуальный режим
        try:
            from config.security import is_read_only
            if is_read_only():
                logger.warning(f"Action denied in READ ONLY mode: {action}")
                
                # Показываем информативное сообщение
                messagebox.showwarning(
                    "Read Only Mode",
                    f"Action '{action}' is not available in Read Only mode.\n\n"
                    f"Please switch to Full Access mode:\n"
                    f"1. Press Ctrl+Shift+F in main window\n"
                    f"2. Then retry this operation"
                )
                return False
        except Exception as e:
            print(f"DEBUG: Error checking security: {e}")
            # В случае ошибки разрешаем операцию
        
        return True
    
    def _on_security_mode_changed(self, is_read_only: bool):
        """Callback при изменении режима безопасности"""
        print(f"DEBUG: Security mode changed to: {'READ_ONLY' if is_read_only else 'FULL_ACCESS'}")
        # Обновляем UI с небольшой задержкой
        if hasattr(self, 'window') and self.window.winfo_exists():
            self.window.after(100, self._apply_access_mode)
    
    def _confirm_critical_operation(self, title: str, message: str) -> bool:
        """
        Подтверждение критических операций
        
        Args:
            title: Заголовок окна подтверждения
            message: Сообщение для подтверждения
        
        Returns:
            bool: True если подтверждено, False если отменено
        """
        # TODO: Использовать SecurityManager.confirm_critical_operation()
        # Пример:
        # try:
        #     from config.security import SecurityManager
        #     security_manager = SecurityManager()
        #     return security_manager.confirm_critical_operation(title, message)
        # except ImportError:
        #     pass
        
        # Fallback на стандартное подтверждение
        return ask_yesno(self.window, title, message)
    
    def _log_security_action(self, action: str, details: str, severity: str = 'LOW'):
        """
        Логирование действий безопасности
        
        Args:
            action: Тип действия
            details: Подробности действия
            severity: Уровень серьезности ('LOW', 'MEDIUM', 'HIGH')
        """
        # TODO: Реализовать через SecurityManager.log_activity()
        # Пример:
        # try:
        #     from config.security import SecurityManager
        #     security_manager = SecurityManager()
        #     if hasattr(self, 'current_user'):
        #         security_manager.log_activity(
        #             user=self.current_user,
        #             action=action,
        #             details=details,
        #             severity=severity
        #         )
        # except ImportError:
        #     pass
        
        # Временное логирование в консоль
        logger.info(f"Security action: {action} - {details} [{severity}]")
    
    def _scan_file_for_security(self, filepath: str) -> bool:
        """
        Проверка файла на безопасность
        
        Args:
            filepath: Путь к файлу
        
        Returns:
            bool: True если файл безопасен, False если содержит угрозы
        """
        # TODO: Реализовать через SecurityManager.scan_file()
        # Пример:
        # try:
        #     from config.security import SecurityManager
        #     security_manager = SecurityManager()
        #     return security_manager.scan_file(filepath)
        # except ImportError:
        #     pass
        
        # По умолчанию считаем файл безопасным
        return True


# Экспорт класса
__all__ = ['ProfileEditor']