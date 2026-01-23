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
from services.size_service import SizeService

logger = logging.getLogger(__name__)


class ProfileEditor:
    """Окно редактирования профиля с поддержкой PDF"""
    
    def __init__(self, parent, profile_service: ProfileService, 
                profile: Optional[Profile] = None, callback=None, size_service: Optional[SizeService] = None):
        print("ProfileEditor initialized")
        self.parent = parent
        self.profile_service = profile_service
        self.profile = profile
        self.callback = callback
        
        # Инициализация сервиса размеров - используем переданный или создаём новый
        if size_service:
            self.size_service = size_service
        else:
            self.size_service = SizeService()
        
        # ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННЫХ ДЛЯ ВИДЖЕТОВ
        self.save_btn = None
        self.cancel_btn = None
        self.delete_btn = None
        self.upload_btn = None
        self.remove_btn = None
        self.pdf_status_label = None
        self.pdf_preview = None
        self.name_entry = None
        self.desc_text = None
        self.feed_entry = None
        self.material_combo = None
        self.product_tree = None
        self.material_info_label = None

        
        # Списки для хранения вариантов
        self.product_variants = []  # список объектов ProductSizeVariant
        self.edited_variants = []   # варианты, добавленные/измененные в этой сессии
        self.deleted_variant_ids = []  # ID удаленных вариантов

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
        """Настройка интерфейса с оптимизированным расположением"""
        # Создание окна - оптимальный размер
        self.window = tk.Toplevel(self.parent)
        title = "Edit Profile" if self.is_editing else "Add Profile"
        self.window.title(title)
        self.window.geometry("800x850")  # Увеличили на 50px для комфорта
        self.window.minsize(800, 700)
        
        # Делаем модальным
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.focus_set()
        
        # Основной контейнер с отступами
        main_container = ttk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 1. Имя профиля - как есть
        name_frame = ttk.Frame(main_container)
        name_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(name_frame, text="Profile Name:*", 
                  font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var, 
                                  font=("Arial", 11))
        self.name_entry.pack(fill=tk.X, pady=(5, 0))
        
        # 2. Описание - уменьшаем высоту
        desc_frame = ttk.LabelFrame(main_container, text="Description", padding="6")
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.desc_text = tk.Text(desc_frame, height=2, font=("Arial", 10))  # height=2 вместо 3
        self.desc_text.pack(fill=tk.BOTH, expand=True)
        
        # 3. ОПТИМИЗИРУЕМ: Feed Rate и Material в одной строке!
        params_frame = ttk.LabelFrame(main_container, text="Processing Parameters", padding="10")
        params_frame.pack(fill=tk.X, pady=(0, 10))
        
        # ГРИД для размещения в одной строке
        params_grid = ttk.Frame(params_frame)
        params_grid.pack(fill=tk.X)
        
        # Feed Rate слева
        feed_group = ttk.Frame(params_grid)
        feed_group.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 20))
        
        ttk.Label(feed_group, text="Feed Rate:").pack(anchor=tk.W)
        feed_input_frame = ttk.Frame(feed_group)
        feed_input_frame.pack(fill=tk.X, pady=(2, 0))
        
        self.feed_var = tk.StringVar(value="30")
        self.feed_entry = ttk.Entry(feed_input_frame, textvariable=self.feed_var, width=8)
        self.feed_entry.pack(side=tk.LEFT)
        ttk.Label(feed_input_frame, text=" m/min").pack(side=tk.LEFT, padx=(2, 0))
        
        # Material справа - ИСПРАВЛЕННАЯ ВЕРСИЯ
        material_group = ttk.Frame(params_grid)
        material_group.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        ttk.Label(material_group, text="Suitable Blank:").pack(anchor=tk.W)
        
        # Загружаем ВСЕ размеры заготовок для начального заполнения
        material_sizes = self.size_service.get_all_material_sizes()
        size_names = [s.display_name() for s in material_sizes]
        size_names.insert(0, "")
        
        self.material_size_var = tk.StringVar()
        material_input_frame = ttk.Frame(material_group)
        material_input_frame.pack(fill=tk.X, pady=(2, 0))
        
        self.material_combo = ttk.Combobox(
            material_input_frame,
            textvariable=self.material_size_var,
            values=size_names,  # ← ТЕПЕРЬ ПЕРЕДАЁМ ЗНАЧЕНИЯ
            state="readonly",   # ← Изменено на readonly для фильтрации
            width=25
        )
        self.material_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Информационная метка
        self.material_info_label = ttk.Label(
            material_group, 
            text="Select a product size first",
            foreground="gray",
            font=("Arial", 8)
        )
        self.material_info_label.pack(anchor=tk.W, pady=(2, 0))
        
        # 4. Размеры продукта - можно немного уменьшить высоту таблицы
        product_frame = ttk.LabelFrame(main_container, text="Product Sizes", padding="8")
        product_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Таблица вариантов - height=4 вместо 5
        columns = ("Width", "Thickness", "Default")
        self.product_tree = ttk.Treeview(
            product_frame,
            columns=columns,
            show="headings",
            height=4  # Уменьшили высоту
        )
        self.product_tree.bind("<Double-1>", self._on_variant_double_click)
        self.product_tree.bind('<<TreeviewSelect>>', self._on_product_selected)  # ← НОВОЕ: привязка события выбора
        
        self.product_tree.heading("Width", text="Width (mm)")
        self.product_tree.heading("Thickness", text="Thickness (mm)")
        self.product_tree.heading("Default", text="Active")
        
        self.product_tree.column("Width", width=80, anchor="center")
        self.product_tree.column("Thickness", width=100, anchor="center")
        self.product_tree.column("Default", width=60, anchor="center")
        
        scrollbar = ttk.Scrollbar(product_frame, orient="vertical",
                                 command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=scrollbar.set)
        
        self.product_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопки управления вариантами (вертикально)
        variant_btn_frame = ttk.Frame(product_frame)
        variant_btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # Делаем кнопки меньше
        button_config = {'width': 7, 'padding': (2, 2)}
        ttk.Button(variant_btn_frame, text="Add", command=self._add_product_variant, **button_config).pack(pady=(0, 2))
        ttk.Button(variant_btn_frame, text="Edit", command=self._edit_product_variant, **button_config).pack(pady=2)
        ttk.Button(variant_btn_frame, text="Delete", command=self._delete_product_variant, **button_config).pack(pady=2)
        ttk.Button(variant_btn_frame, text="Up", command=lambda: self._move_variant(-1), **button_config).pack(pady=2)
        ttk.Button(variant_btn_frame, text="Down", command=lambda: self._move_variant(1), **button_config).pack(pady=2)
        
        # 5. PDF документ - упрощаем
        pdf_frame = ttk.LabelFrame(main_container, text="Profile Document (PDF)", padding="8")
        pdf_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Статус и кнопки в одной строке
        pdf_top_frame = ttk.Frame(pdf_frame)
        pdf_top_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.pdf_status_label = ttk.Label(
            pdf_top_frame,
            text="No PDF loaded",
            foreground="gray",
            font=("Arial", 9)
        )
        self.pdf_status_label.pack(side=tk.LEFT, anchor=tk.W, fill=tk.X, expand=True)
        
        # Кнопки управления PDF
        pdf_btn_frame = ttk.Frame(pdf_top_frame)
        pdf_btn_frame.pack(side=tk.RIGHT)
        
        self.upload_btn = ttk.Button(pdf_btn_frame, text="Upload", 
                                    command=self.upload_pdf, width=8)
        self.upload_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.remove_btn = ttk.Button(pdf_btn_frame, text="Remove", 
                                    command=self.remove_pdf, width=8)
        self.remove_btn.pack(side=tk.LEFT)
        
        # Предпросмотр PDF - уменьшаем
        preview_frame = ttk.Frame(pdf_frame)
        preview_frame.pack(fill=tk.X)
        
        preview_inner = ttk.Frame(preview_frame, width=200, height=100)  # Уменьшили высоту
        preview_inner.pack_propagate(False)
        preview_inner.pack(pady=2)
        
        self.pdf_preview = ImagePreview(preview_inner, width=180, height=80)  # Уменьшили
        self.pdf_preview.pack(expand=True, fill=tk.BOTH)
        
        # 6. КНОПКИ УПРАВЛЕНИЯ - ВИДИМЫЕ!
        # Добавляем разделитель перед кнопками
        ttk.Separator(main_container, orient='horizontal').pack(fill=tk.X, pady=(15, 10))

        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill=tk.X, pady=(0, 0))

        # Распределяем кнопки равномерно
        if self.is_editing:
            # Для редактирования: Delete | [Cancel] [Save]
            # СОХРАНЯЕМ ССЫЛКУ В self.delete_btn
            self.delete_btn = ttk.Button(button_frame, text="Delete Profile", 
                          command=self.delete, width=15)
            self.delete_btn.pack(side=tk.LEFT)
            
            spacer = ttk.Frame(button_frame)
            spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # СОХРАНЯЕМ ССЫЛКУ В self.cancel_btn
            self.cancel_btn = ttk.Button(button_frame, text="Cancel", 
                          command=self.window.destroy, width=12)
            self.cancel_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            # СОХРАНЯЕМ ССЫЛКУ В self.save_btn
            self.save_btn = ttk.Button(button_frame, text="Save", 
                          command=self._safe_save, width=12)
            self.save_btn.pack(side=tk.LEFT)
        else:
            # Для добавления: [Cancel] [Save]
            spacer = ttk.Frame(button_frame)
            spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # СОХРАНЯЕМ ССЫЛКУ В self.cancel_btn
            self.cancel_btn = ttk.Button(button_frame, text="Cancel", 
                          command=self.window.destroy, width=12)
            self.cancel_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            # СОХРАНЯЕМ ССЫЛКУ В self.save_btn
            self.save_btn = ttk.Button(button_frame, text="Save", 
                          command=self._safe_save, width=12)
            self.save_btn.pack(side=tk.LEFT)
            
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
        
        # Сразу применяем режим доступа после создания всех виджетов
        self.window.after(150, self._apply_access_mode)

    def _on_close(self):
        """Обработчик закрытия окна"""
        try:
            if hasattr(self, 'security_manager') and self.security_manager:
                try:
                    self.security_manager.remove_callback(self._on_security_mode_changed)
                except:
                    pass
        except:
            pass
        
        try:
            self.window.destroy()
        except:
            pass

    def _on_product_selected(self, event):
        """Обработчик выбора строки в таблице размеров продукта"""
        self._update_material_for_selected_product()

    def _update_material_for_selected_product(self):
        """Обновляет список заготовок для выбранного размера продукта"""
        # Получаем выбранную строку в таблице продукта
        selection = self.product_tree.selection()
        
        if not selection:
            # Если ничего не выбрано - показываем все заготовки
            material_sizes = self.size_service.get_all_material_sizes()
            size_names = [s.display_name() for s in material_sizes]
            size_names.insert(0, "")
            self.material_combo['values'] = size_names
            self.material_info_label.config(
                text="Select a product size first",
                foreground="gray"
            )
            return
        
        # Получаем данные выбранного продукта
        item = self.product_tree.item(selection[0])
        values = item['values']
        
        try:
            width = float(values[0])  # Ширина продукта
            thickness = float(values[1]) if values[1] else 0  # Толщина продукта (может быть пустой)
            
            if width <= 0:
                # Если некорректная ширина - показываем все
                material_sizes = self.size_service.get_all_material_sizes()
                size_names = [s.display_name() for s in material_sizes]
                size_names.insert(0, "")
                self.material_combo['values'] = size_names
                self.material_info_label.config(
                    text="Enter valid product dimensions",
                    foreground="orange"
                )
                return
            
            # Получаем подходящие заготовки
            suitable_blanks = self.size_service.get_suitable_material_sizes(width, thickness)
            
            if not suitable_blanks:
                self.material_combo['values'] = []
                self.material_info_label.config(
                    text=f"No suitable blanks for {width}×{thickness if thickness else '?'}mm",
                    foreground="red"
                )
                return
            
            # Формируем список
            blank_list = [blank.display_name() for blank in suitable_blanks]
            blank_list.insert(0, "")
            self.material_combo['values'] = blank_list
            
            # Обновляем информационную метку
            if thickness > 0:
                self.material_info_label.config(
                    text=f"Found {len(suitable_blanks)} suitable blanks for {width}×{thickness}mm",
                    foreground="green"
                )
            else:
                self.material_info_label.config(
                    text=f"Found {len(suitable_blanks)} suitable blanks for width {width}mm",
                    foreground="green"
                )
            
        except (ValueError, IndexError, TypeError) as e:
            # Если ошибка - показываем все заготовки
            print(f"DEBUG: Error filtering blanks: {e}")
            material_sizes = self.size_service.get_all_material_sizes()
            size_names = [s.display_name() for s in material_sizes]
            size_names.insert(0, "")
            self.material_combo['values'] = size_names
            self.material_info_label.config(
                text="Error processing product dimensions",
                foreground="orange"
            )

    # Все остальные методы остаются без изменений
    def center_window(self):
        """Центрирует окно"""
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

    def _open_material_sizes_dialog(self):
        """Временная заглушка для диалога размеров материала"""
        messagebox.showinfo("Info", "Material sizes dialog will be implemented soon")

    def _on_security_mode_changed(self, mode):
        """Обработчик изменения режима безопасности"""
        self._apply_access_mode()

    def _apply_access_mode(self):
        """Применяет режим доступа ко всем элементам интерфейса"""
        if not hasattr(self, 'security_manager') or not self.security_manager:
            return
        
        is_read_only = self.security_manager.is_read_only()
        
        # Применяем ко всем виджетам
        widgets_to_disable = [
            self.name_entry, self.desc_text, self.feed_entry,
            self.material_combo, self.upload_btn, self.remove_btn,
            self.save_btn
        ]
        
        for widget in widgets_to_disable:
            if widget:
                try:
                    widget.configure(state='disabled' if is_read_only else 'normal')
                except Exception as e:
                    print(f"DEBUG: Error setting state for {widget}: {e}")
        
        # Особые случаи
        if self.delete_btn:
            self.delete_btn.configure(state='disabled' if is_read_only else 'normal')

    def _load_profile_data(self):
        """Загружает данные профиля в форму"""
        if not self.profile:
            return
        
        try:
            # Имя
            self.name_var.set(self.profile.name or "")
            
            # Описание
            self.desc_text.delete(1.0, tk.END)
            self.desc_text.insert(1.0, self.profile.description or "")
            
            # Feed Rate
            if self.profile.feed_rate:
                self.feed_var.set(str(self.profile.feed_rate))
            
            # Material Size - если есть в профиле
            if hasattr(self.profile, 'material_size') and self.profile.material_size:
                self.material_size_var.set(self.profile.material_size)
            
            # Загружаем варианты размеров продукта
            self._load_product_variants()
            
            # Загружаем PDF если есть
            if hasattr(self.profile, 'pdf_filename') and self.profile.pdf_filename:
                self._load_existing_pdf()
                
        except Exception as e:
            logger.error(f"Error loading profile data: {e}")
            show_error(self.window, "Error", f"Failed to load profile data: {str(e)}")

    def _load_product_variants(self):
        """Загружает варианты размеров продукта"""
        if not self.profile or not hasattr(self.profile, 'id'):
            return
        
        try:
            variants = self.size_service.get_product_variants_for_profile(self.profile.id)
            self.product_variants = variants
            
            # Очищаем таблицу
            for item in self.product_tree.get_children():
                self.product_tree.delete(item)
            
            # Заполняем таблицу
            for variant in variants:
                values = (
                    variant.get('width', ''),
                    variant.get('thickness', ''),
                    "✓" if variant.get('is_default') else ""
                )
                self.product_tree.insert("", "end", values=values)
                
        except Exception as e:
            logger.error(f"Error loading product variants: {e}")

    def _load_existing_pdf(self):
        """Загружает существующий PDF файл"""
        try:
            if not self.profile or not hasattr(self.profile, 'pdf_filename'):
                return
            
            pdf_filename = self.profile.pdf_filename
            if not pdf_filename or not os.path.exists(pdf_filename):
                return
            
            # Загружаем данные PDF
            with open(pdf_filename, 'rb') as f:
                self.pdf_data = f.read()
            
            self.pdf_filename = pdf_filename
            self.original_pdf_data = self.pdf_data
            self.original_pdf_filename = self.pdf_filename
            
            # Обновляем статус
            self.pdf_status_label.config(
                text=os.path.basename(pdf_filename),
                foreground="black"
            )
            
            # Показываем превью
            self._show_pdf_preview()
            
        except Exception as e:
            logger.error(f"Error loading existing PDF: {e}")

    def _show_pdf_preview(self):
        """Показывает превью PDF"""
        if not self.pdf_data or not self.pdf_preview:
            return
        
        try:
            # Просто очищаем превью, если нет метода show_placeholder
            self.pdf_preview.clear()  # Используем существующий метод clear()
            # Или добавляем простую надпись
            if hasattr(self.pdf_preview, 'set_text'):
                self.pdf_preview.set_text("PDF loaded")
        except Exception as e:
            logger.error(f"Error showing PDF preview: {e}")

    def upload_pdf(self):
        """Загружает PDF файл"""
        try:
            filename = filedialog.askopenfilename(
                title="Select PDF file",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
            )
            
            if not filename:
                return
            
            # Читаем файл
            with open(filename, 'rb') as f:
                self.pdf_data = f.read()
            
            self.pdf_filename = filename
            self.pdf_was_uploaded = True
            
            # Обновляем статус
            self.pdf_status_label.config(
                text=os.path.basename(filename),
                foreground="black"
            )
            
            # Показываем превью
            self._show_pdf_preview()
            
        except Exception as e:
            logger.error(f"Error uploading PDF: {e}")
            show_error(self.window, "Error", f"Failed to upload PDF: {str(e)}")

    def remove_pdf(self):
        """Удаляет загруженный PDF"""
        if not self.pdf_data and not self.original_pdf_data:
            show_info(self.window, "Info", "No PDF to remove")
            return
        
        self.pdf_data = None
        self.pdf_filename = None
        self.pdf_was_removed = True
        
        # Обновляем статус
        self.pdf_status_label.config(
            text="No PDF loaded",
            foreground="gray"
        )
        
        # Очищаем превью
        if self.pdf_preview:
            self.pdf_preview.clear()

    def _add_product_variant(self):
        """Добавляет новый вариант размера продукта"""
        # Здесь должна быть логика диалога добавления варианта
        # Временно добавляем тестовый вариант
        self.product_tree.insert("", "end", values=("100", "25", ""))
        
    def _edit_product_variant(self):
        """Редактирует выбранный вариант размера продукта"""
        selection = self.product_tree.selection()
        if not selection:
            show_info(self.window, "Info", "Please select a product size to edit")
            return
        
        # Здесь должна быть логика диалога редактирования
        show_info(self.window, "Info", "Edit dialog will be implemented soon")

    def _delete_product_variant(self):
        """Удаляет выбранный вариант размера продукта"""
        selection = self.product_tree.selection()
        if not selection:
            show_info(self.window, "Info", "Please select a product size to delete")
            return
        
        for item in selection:
            self.product_tree.delete(item)

    def _move_variant(self, direction):
        """Перемещает вариант вверх или вниз"""
        selection = self.product_tree.selection()
        if not selection:
            return
        
        # Здесь должна быть логика перемещения
        show_info(self.window, "Info", "Move functionality will be implemented soon")

    def _on_variant_double_click(self, event):
        """Обработчик двойного клика по варианту"""
        self._edit_product_variant()

    def _safe_save(self):
        """Безопасное сохранение с защитой от двойного нажатия"""
        if self._saving:
            return
        
        self._saving = True
        try:
            self.save()
        finally:
            self._saving = False

    def save(self):
        """Сохраняет профиль"""
        try:
            # Проверяем обязательные поля
            name = self.name_var.get().strip()
            if not name:
                show_error(self.window, "Error", "Profile name is required")
                return
            
            # Собираем данные
            profile_data = {
                'name': name,
                'description': self.desc_text.get(1.0, tk.END).strip(),
                'feed_rate': float(self.feed_var.get()) if self.feed_var.get() else None,
                'material_size': self.material_size_var.get() if self.material_size_var.get() else None
            }
            
            # Обрабатываем PDF
            if self.pdf_was_uploaded and self.pdf_data:
                profile_data['pdf_data'] = self.pdf_data
                profile_data['pdf_filename'] = self.pdf_filename
            elif self.pdf_was_removed:
                profile_data['pdf_data'] = None
                profile_data['pdf_filename'] = None
            
            # Сохраняем или обновляем профиль
            if self.is_editing and self.profile:
                profile_data['id'] = self.profile.id
                self.profile_service.update_profile(profile_data)
                show_info(self.window, "Success", "Profile updated successfully")
            else:
                new_profile_id = self.profile_service.create_profile(profile_data)
                self.profile = self.profile_service.get_profile_by_id(new_profile_id)
                self.is_editing = True
                show_info(self.window, "Success", "Profile created successfully")
            
            # Сохраняем варианты размеров продукта
            self._save_product_variants()
            
            # Вызываем колбэк если есть
            if self.callback:
                self.callback()
            
            # Закрываем окно
            self.window.destroy()
            
        except ValueError as e:
            show_error(self.window, "Validation Error", f"Please check your input values: {str(e)}")
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            show_error(self.window, "Error", f"Failed to save profile: {str(e)}")

    def _save_product_variants(self):
        """Сохраняет варианты размеров продукта"""
        if not self.profile or not hasattr(self.profile, 'id'):
            return
        
        try:
            # Здесь должна быть логика сохранения вариантов в БД
            # Пока просто логируем
            variants = []
            for item in self.product_tree.get_children():
                values = self.product_tree.item(item)['values']
                variants.append({
                    'width': values[0],
                    'thickness': values[1] if values[1] else None,
                    'is_default': values[2] == "✓"
                })
            
            logger.info(f"Would save {len(variants)} product variants for profile {self.profile.id}")
            
        except Exception as e:
            logger.error(f"Error saving product variants: {e}")

    def delete(self):
        """Удаляет профиль"""
        if not self.is_editing or not self.profile:
            return
        
        if not ask_yesno(self.window, "Confirm Delete", 
                        f"Are you sure you want to delete profile '{self.profile.name}'?"):
            return
        
        try:
            self.profile_service.delete_profile(self.profile.id)
            
            if self.callback:
                self.callback()
            
            show_info(self.window, "Success", "Profile deleted successfully")
            self.window.destroy()
            
        except Exception as e:
            logger.error(f"Error deleting profile: {e}")
            show_error(self.window, "Error", f"Failed to delete profile: {str(e)}")