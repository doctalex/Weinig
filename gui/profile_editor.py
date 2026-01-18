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

from services.size_service import MaterialSize
from core.models import Profile
from services.profile_service import ProfileService
from gui.base.dialogs import show_error, show_info, ask_yesno
from gui.base.widgets import ImagePreview
from utils.logger import log_profile_change
from services.size_service import SizeService

logger = logging.getLogger(__name__)


class ProfileEditor:
    """Окно редактирования профиля с поддержкой PDF"""
    
    def __init__(self, parent, profile_service, size_service, profile=None, callback=None):
        self.parent = parent
        self.profile_service = profile_service
        self.size_service = size_service
        self.profile = profile
        self.callback = callback
        self._saving = False

        print("ProfileEditor initialized")
        
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
        
        # Material справа
        material_group = ttk.Frame(params_grid)
        material_group.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        ttk.Label(material_group, text="Material Size:").pack(anchor=tk.W)
        
        # Загружаем размеры из справочника
        material_sizes = self.size_service.get_all_material_sizes()
        size_names = [s.display_name() for s in material_sizes]
        size_names.insert(0, "")
        
        self.material_size_var = tk.StringVar()
        material_input_frame = ttk.Frame(material_group)
        material_input_frame.pack(fill=tk.X, pady=(2, 0))
        
        self.material_combo = ttk.Combobox(
            material_input_frame,
            textvariable=self.material_size_var,
            values=size_names,
            state="normal",
            width=25
        )
        self.material_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
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
    
    def _add_product_variant(self):
        """Упрощенный диалог добавления варианта"""
        from gui.simple_variant_dialog import SimpleVariantDialog
        
        dialog = SimpleVariantDialog(
            self.window,
            title="Add Product Size"
        )
        
        if dialog.result:
            width, thickness = dialog.result
            try:
                width_val = float(width)
                thickness_val = float(thickness) if thickness.strip() else None
                
                variant_data = {
                    'temp_id': len(self.edited_variants) + 1000,
                    'width': width_val,
                    'thickness': thickness_val,
                    'is_default': False  # Первый добавленный будет по умолчанию
                }
                
                # Если это первый вариант, делаем его default
                if not self.product_variants:
                    variant_data['is_default'] = True
                
                # Добавляем в ОБА списка
                self.edited_variants.append(variant_data)
                self.product_variants.append(variant_data)  # ЭТОЙ СТРОКИ НЕ БЫЛО!
                
                self._update_product_variants_table()
                
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numeric values")
    
    def _edit_product_variant(self):
        """Редактировать выбранный вариант"""
        selection = self.product_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a variant to edit")
            return
        
        item = selection[0]
        item_data = self.product_tree.item(item)
        values = item_data['values']
        
        from gui.simple_variant_dialog import SimpleVariantDialog
        
        dialog = SimpleVariantDialog(
            self.window,
            title="Edit Product Size",
            initial_values=values[:2]  # Только width и thickness
        )
        
        if dialog.result:
            width, thickness = dialog.result
            try:
                width_val = float(width)
                thickness_val = float(thickness) if thickness.strip() else None
                
                # Находим и обновляем вариант
                variant_id = int(item.split('_')[-1])
                for variant in self.product_variants:
                    if variant.get('id') == variant_id or variant.get('temp_id') == variant_id:
                        variant['width'] = width_val
                        variant['thickness'] = thickness_val
                        break
                
                self._update_product_variants_table()
                
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numeric values")
    
    def _delete_product_variant(self):
        """Удалить выбранный вариант"""
        selection = self.product_tree.selection()
        if not selection:
            return
        
        for item in selection:
            variant_id = int(item.split('_')[-1])
            
            # Если это существующий вариант (ID > 0), добавляем в список удаленных
            if variant_id > 0 and variant_id < 1000:
                self.deleted_variant_ids.append(variant_id)
            
            # Удаляем из отображаемых списков
            self.product_variants = [v for v in self.product_variants 
                                   if v.get('id') != variant_id and v.get('temp_id') != variant_id]
            self.edited_variants = [v for v in self.edited_variants 
                                  if v.get('id') != variant_id and v.get('temp_id') != variant_id]
        
        self._update_product_variants_table()
    
    def _move_variant(self, direction):
        """Переместить вариант вверх/вниз"""
        selection = self.product_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        item_id = int(item.split('_')[-1])
        
        # Находим индекс в списке
        for i, variant in enumerate(self.product_variants):
            if variant.get('id') == item_id or variant.get('temp_id') == item_id:
                new_index = i + direction
                if 0 <= new_index < len(self.product_variants):
                    # Меняем местами
                    self.product_variants[i], self.product_variants[new_index] = \
                        self.product_variants[new_index], self.product_variants[i]
                    break
        
        self._update_product_variants_table()
    
    def _update_product_variants_table(self):
        """Обновить таблицу вариантов"""
        # Очищаем таблицу
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
        
        # Добавляем все варианты ИЗ self.product_variants
        for i, variant in enumerate(self.product_variants):
            thickness = variant.get('thickness', '')
            if thickness:
                thickness = f"{thickness}"
            
            values = (
                variant.get('width', ''),
                thickness,
                '✓' if variant.get('is_default') else ''
            )
            
            item_id = f"variant_{variant.get('id', variant.get('temp_id', i))}"
            self.product_tree.insert('', 'end', iid=item_id, values=values)
    
    def _on_variant_double_click(self, event):
        item_id = self.product_tree.focus()
        if not item_id:
            return

        variant_id = int(item_id.split('_')[-1])

        # 1. Снимаем Active со всех
        for v in self.product_variants:
            v['is_default'] = False

        # 2. Активируем выбранный
        for v in self.product_variants:
            if v.get('id') == variant_id or v.get('temp_id') == variant_id:
                v['is_default'] = True
                break

        # 3. Обновляем таблицу
        self._update_product_variants_table()
            
    def _load_profile_data(self):
        """Загружает данные профиля в форму"""
        if not self.profile:
            return
        
        self.name_var.set(self.profile.name)
        self.desc_text.insert("1.0", self.profile.description)
        self.feed_var.set(str(self.profile.feed_rate))
        
        # Размер материала
        if self.profile.material_size:
            self.material_size_var.set(self.profile.material_size)
        
        # Варианты размеров продукта
        if hasattr(self.profile, 'id') and self.profile.id:
            self.product_variants = self.size_service.get_product_variants_for_profile(self.profile.id)
        else:
            self.product_variants = []
        
        self._update_product_variants_table()
        
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
        if not self._check_security('upload_documents'):
            return
        
        filename = filedialog.askopenfilename(
            title="Select PDF Document",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            parent=self.window
        )
        
        if filename:
            try:
                if not filename.lower().endswith('.pdf'):
                    show_error(self.window, "Error", "Please select a PDF file (.pdf)")
                    return
                
                file_size = os.path.getsize(filename)
                if file_size > 50 * 1024 * 1024:
                    show_error(self.window, "Error", "PDF file is too large. Maximum size is 50MB.")
                    return
                
                with open(filename, "rb") as f:
                    self.pdf_data = f.read()
                
                self.pdf_filename = os.path.basename(filename)
                self.pdf_was_uploaded = True
                self.pdf_was_removed = False
                
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
                    else:
                        show_error(self.window, "Warning", 
                                 "Could not extract preview from PDF.")
                        self.pdf_data = None
                        self.pdf_filename = None
                        self.pdf_was_uploaded = False
                        
                except ImportError:
                    show_error(self.window, "Error", 
                             "PyMuPDF library is not installed.")
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
        if not self._check_security('modify_profile'):
            return
        
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
            self.pdf_was_removed = True
            self.pdf_was_uploaded = False
    
    def save(self):
        """Сохраняет профиль с PDF и выбранным размером материала"""
        if self._saving:
            return
        self._saving = True

        try:
            # Проверка режима доступа
            if hasattr(self, 'access_mode') and self.access_mode == "READ_ONLY":
                messagebox.showerror(
                    "Access Denied",
                    "This profile is in READ ONLY mode.\nYou cannot modify it."
                )
                self._saving = False
                self.save_btn.config(state='normal')
                return

            # Валидация имени профиля
            name = self.name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Profile name is required")
                self._saving = False
                self.save_btn.config(state='normal')
                return

            # Описание и скорость подачи
            description = self.desc_text.get("1.0", tk.END).strip()
            try:
                feed_rate = float(self.feed_var.get())
            except ValueError:
                feed_rate = 30.0

            # 🔹 Получаем выбранный размер материала
            selected_material = self._get_selected_material()
            material_size_id = selected_material.id if selected_material else None
            material_size_str = selected_material.display_name() if selected_material else ""

            # 🔹 Определяем PDF данные для сохранения
            if not self.is_editing:
                pdf_data_to_save = self.pdf_data
                pdf_filename_to_save = self.pdf_filename
            else:
                if self.pdf_was_uploaded:
                    pdf_data_to_save = self.pdf_data
                    pdf_filename_to_save = self.pdf_filename
                elif self.pdf_was_removed:
                    pdf_data_to_save = None
                    pdf_filename_to_save = None
                else:
                    pdf_data_to_save = self.original_pdf_data
                    pdf_filename_to_save = None

            # 🔹 Сохраняем профиль
            success = False
            action = ""
            profile_id = None

            if self.is_editing and self.profile:
                # Обновление существующего профиля
                profile_id = self.profile.id
                success = self.profile_service.update_profile(
                    profile_id,
                    name=name,
                    description=description,
                    feed_rate=feed_rate,
                    material_size=material_size_str,    # только строка
                    pdf_data=pdf_data_to_save,
                    pdf_filename=pdf_filename_to_save
                )
                action = "updated"
            else:
                # Создание нового профиля
                profile_id = self.profile_service.create_profile(
                    name=name,
                    description=description,
                    feed_rate=feed_rate,
                    material_size_id=material_size_id,
                    material_size=material_size_str,
                    pdf_data=pdf_data_to_save,
                    pdf_filename=pdf_filename_to_save
                )
                success = profile_id is not None
                action = "created"

            if success:
                # 🔹 Сохраняем варианты размеров продукта (если есть)
                if profile_id and hasattr(self, 'product_variants'):
                    self._save_product_variants(profile_id)
                    product_size_str = self._get_product_size_string()
                    self.profile_service.update_profile_product_size(profile_id, product_size_str)

                messagebox.showinfo("Success", f"Profile {action} successfully")

                # 🔹 Обновляем главное окно
                try:
                    if hasattr(self.parent, 'show_profile_details'):
                        self.parent.show_profile_details()
                    if hasattr(self.parent, 'load_profiles'):
                        self.parent.load_profiles()
                    if hasattr(self.parent, 'load_profile_tools'):
                        self.parent.load_profile_tools()
                except Exception as e:
                    print(f"DEBUG: Error updating parent directly: {e}")

                if hasattr(self, 'callback') and self.callback:
                    try:
                        self.callback()
                    except Exception as e:
                        print(f"DEBUG: Callback error: {e}")

                # Сброс флагов PDF
                self.pdf_was_uploaded = False
                self.pdf_was_removed = False

                # Закрываем окно
                self.window.destroy()

            else:
                messagebox.showerror("Error", f"Failed to {action} profile")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            self._saving = False
            if hasattr(self, 'save_btn'):
                self.save_btn.config(state='normal')
    
    def _get_product_size_string(self):
        """Формирует строку product_size для отображения в главном окне"""
        if not self.product_variants:
            return "Not specified"
        
        # Находим default вариант
        default_variant = None
        for variant in self.product_variants:
            if variant.get('is_default'):
                default_variant = variant
                break
        
        # Если нет default, берем первый
        if not default_variant and self.product_variants:
            default_variant = self.product_variants[0]
            # Отмечаем его как default для будущих операций
            default_variant['is_default'] = True
        
        if not default_variant:
            return "Not specified"
        
        # Форматируем строку
        thickness = default_variant.get('thickness')
        if thickness:
            return f"{default_variant['width']} x {thickness}"
        else:
            return f"{default_variant['width']}"


    def _save_product_variants(self, profile_id):
        """Сохраняет все варианты размеров продукта в базу данных"""
        try:
            print(f"DEBUG: Saving {len(self.product_variants)} product variants")
            
            # Для редактирования: обрабатываем удаленные варианты
            if self.is_editing:
                # Удаляем помеченные варианты
                for variant_id in self.deleted_variant_ids:
                    print(f"DEBUG: Deleting variant ID {variant_id}")
                    self.size_service.delete_product_variant(variant_id)
                
                # Сначала проверяем существующие варианты
                existing_variants = self.size_service.get_product_variants_for_profile(profile_id)
                existing_ids = [v['id'] for v in existing_variants if 'id' in v]
                
                # Обновляем/добавляем варианты
                for variant in self.product_variants:
                    variant_id = variant.get('id')
                    
                    if variant_id and variant_id in existing_ids:
                        # Это существующий вариант - обновляем
                        print(f"DEBUG: Updating existing variant ID {variant_id}")
                        self.size_service.update_product_variant(
                            variant_id=variant_id,
                            width=variant['width'],
                            thickness=variant.get('thickness'),
                            is_default=variant.get('is_default', False)
                        )
                    else:
                        # Это новый вариант
                        print(f"DEBUG: Creating new variant for profile {profile_id}")
                        self.size_service.create_product_variant(
                            profile_id=profile_id,
                            width=variant['width'],
                            thickness=variant.get('thickness'),
                            is_default=variant.get('is_default', False)
                        )
            else:
                # Для нового профиля просто добавляем все варианты
                for i, variant in enumerate(self.product_variants):
                    print(f"DEBUG: Creating variant {i+1}/{len(self.product_variants)}")
                    try:
                        self.size_service.create_product_variant(
                            profile_id=profile_id,
                            width=variant['width'],
                            thickness=variant.get('thickness'),
                            is_default=variant.get('is_default', False)
                        )
                    except Exception as e:
                        print(f"DEBUG: Error creating product variant: {e}")
            
            print(f"DEBUG: Product variants saved successfully")
            
        except Exception as e:
            print(f"DEBUG: Error saving product variants: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_active_product_size(self):
        variants = self.size_service.get_product_variants_for_profile(self.current_profile_id)

        active = next((v for v in variants if v["is_default"]), None)
        if not active:
            return

        if active["thickness"] is not None:
            size_str = f'{active["width"]} x {active["thickness"]}'
        else:
            size_str = f'{active["width"]}'

        # обновляем поле в главном окне
        self.product_size_entry.delete(0, "end")
        self.product_size_entry.insert(0, size_str)

        # и сразу сохраняем в профиль
        self.profile_service.update_profile_product_size(
            self.current_profile_id,
            size_str
        )
    
    def delete(self):
        """Удаляет профиль"""
        if not self._check_security('delete_profile'):
            return
        
        if not self.profile:
            return
        
        # Подсчитываем инструменты
        try:
            tools_count = self.profile_service.count_tools(self.profile.id)
        except:
            tools_count = 0
        
        message = f"Delete profile '{self.profile.name}'?"
        if tools_count > 0:
            message += f"\n\n⚠️ WARNING: {tools_count} tool(s) will also be deleted!"
        
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
        except:
            pass
        
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        window_width = self.window.winfo_width()
        window_height = self.window.winfo_height()
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.window.geometry(f"+{x}+{y}")
    
    def _apply_access_mode(self):
        """Применяет режим доступа (READ ONLY или FULL ACCESS) к виджетам"""
        try:
            from config.security import is_read_only
            current_read_only = is_read_only()
        except Exception as e:
            print(f"DEBUG: Error getting security mode: {e}")
            current_read_only = False
        
        if current_read_only:
            access_mode = "READ_ONLY"
        else:
            access_mode = "FULL_ACCESS"
        
        if self.profile and hasattr(self.profile, 'locked') and self.profile.locked:
            access_mode = "READ_ONLY"
        
        print(f"DEBUG: Applying access mode: {access_mode}")
        
        if access_mode == "READ_ONLY":
            state = "disabled"
            bg_color = "#f0f0f0"
            readonly_text = " (READ ONLY)"
            
            if hasattr(self, 'window') and self.window.winfo_exists():
                current_title = self.window.title()
                if "(READ ONLY)" not in current_title:
                    self.window.title(f"{current_title} {readonly_text}")
        else:
            state = "normal"
            bg_color = "white"
        
        # Применяем состояние ко всем редактируемым виджетам
        # Проверяем каждый виджет перед доступом к нему
        widgets_to_update = []
        
        # Собираем только существующие виджеты
        if hasattr(self, 'name_entry') and self.name_entry:
            widgets_to_update.append(self.name_entry)
        if hasattr(self, 'desc_text') and self.desc_text:
            widgets_to_update.append(self.desc_text)
        if hasattr(self, 'feed_entry') and self.feed_entry:
            widgets_to_update.append(self.feed_entry)
        if hasattr(self, 'upload_btn') and self.upload_btn:
            widgets_to_update.append(self.upload_btn)
        if hasattr(self, 'remove_btn') and self.remove_btn:
            widgets_to_update.append(self.remove_btn)
        if hasattr(self, 'material_combo') and self.material_combo:
            widgets_to_update.append(self.material_combo)
        if hasattr(self, 'save_btn') and self.save_btn:
            widgets_to_update.append(self.save_btn)
        if hasattr(self, 'delete_btn') and self.delete_btn:
            widgets_to_update.append(self.delete_btn)
        if hasattr(self, 'cancel_btn') and self.cancel_btn:
            widgets_to_update.append(self.cancel_btn)
        
        for widget in widgets_to_update:
            try:
                widget.configure(state=state)
            except Exception as e:
                print(f"DEBUG: Error configuring widget {widget}: {e}")
        
        if hasattr(self, 'desc_text') and self.desc_text:
            try:
                self.desc_text.configure(state=state)
                if state == "normal":
                    self.desc_text.configure(bg="white")
                else:
                    self.desc_text.configure(bg="#f0f0f0")
            except:
                pass
        
        self.access_mode = access_mode
        logger.info(f"Access mode applied: {access_mode}")
    
    def _check_security(self, action: str) -> bool:
        """Проверка прав доступа"""
        try:
            from config.security import is_read_only
            if is_read_only():
                messagebox.showwarning(
                    "Read Only Mode",
                    f"Action '{action}' is not available in Read Only mode."
                )
                return False
        except:
            pass
        
        return True
    
    def _on_security_mode_changed(self, is_read_only: bool):
        """Callback при изменении режима безопасности"""
        if hasattr(self, 'window') and self.window.winfo_exists():
            self.window.after(100, self._apply_access_mode)
    
    def _safe_save(self):
        """Защищенный вызов save"""
        if self._saving:
            return
        self.save_btn.config(state='disabled')
        try:
            self.save()
        except Exception as e:
            print(f"Error in save: {e}")
            self.save_btn.config(state='normal')
            self._saving = False
            
    def _init_material_dropdown(self):
        """Инициализация выпадающего списка материалов"""
        self.material_size_var = tk.StringVar()
        self.material_combo = ttk.Combobox(self, textvariable=self.material_size_var, state="readonly")
        self.material_combo.grid(row=..., column=..., sticky="w")  # вставьте правильные координаты

        # Загружаем варианты из SizeService
        self._load_material_sizes()

    def _load_material_sizes(self):
        """Загрузить доступные размеры материала в Combobox"""
        material_sizes = self.size_service.get_all_material_sizes()
        size_names = [s.display_name() for s in material_sizes]
        self.material_combo['values'] = size_names

        # Если у профиля уже есть материал, выставляем его
        if hasattr(self, 'profile') and self.profile.material_size_id:
            current_material = self.size_service.get_material_size_by_id(self.profile.material_size_id)
            if current_material:
                self.material_size_var.set(current_material.display_name())

    def _get_selected_material(self) -> Optional[MaterialSize]:
        """Возвращает объект MaterialSize выбранного значения или None"""
        selected_name = self.material_size_var.get()
        if not selected_name:
            return None

        # Проходим по всем материалам из сервиса
        for size in self.size_service.get_all_material_sizes():
            if size.display_name() == selected_name:
                return size

        return None
       
# Экспорт класса
__all__ = ['ProfileEditor']