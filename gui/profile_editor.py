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
from gui.base.scroll_container import ScrollableContainer

from core.models import Profile
from services.profile_service import ProfileService
from gui.base.dialogs import show_error, show_info, ask_yesno
from gui.base.widgets import ImagePreview
from utils.logger import log_profile_change
from services.size_service import SizeService

logger = logging.getLogger(__name__)


class ProfileEditor:
    """Окно редактирования профиля с поддержкой PDF"""
    
    def __init__(self, parent, profile_id=None, security_mode="FULL ACCESS", db_manager=None):
        print("ProfileEditor initialized")

        self.parent = parent
        self.db_manager = db_manager
        self.security_mode = security_mode

        # --- ProfileService ---
        self.profile_service = parent.profile_service

        # Загружаем профиль по ID
        self.profile = self.profile_service.get_profile_by_id(profile_id)

        # Колбэк пока не используется
        self.callback = None

        # --- SizeService ---
        self.size_service = SizeService(db_path=self.db_manager.db_path)

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
        self.product_variants = []
        self.edited_variants = []
        self.deleted_variant_ids = []

        # PDF данные
        self.pdf_data = None
        self.pdf_filename = None
        self.original_pdf_data = None
        self.original_pdf_filename = None
        self.pdf_was_removed = False
        self.pdf_was_uploaded = False

        self.is_editing = self.profile is not None
        self._saving = False

        # SecurityManager
        try:
            from config.security import get_security_manager, is_read_only
            self.security_manager = get_security_manager()
            self.security_manager.add_callback(self._on_security_mode_changed)
            print(f"DEBUG: SecurityManager initialized, read_only: {is_read_only()}")
        except Exception as e:
            print(f"DEBUG: SecurityManager error: {e}")
            self.security_manager = None

        # Запуск UI
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса с поддержкой прокрутки и адаптивным размером"""
        from gui.base.scroll_container import ScrollableContainer

        self.window = tk.Toplevel(self.parent.root)
        title = "Edit Profile" if self.is_editing else "Add Profile"
        self.window.title(title)

        # --- АДАПТИВНЫЙ РАЗМЕР ОКНА ---
        screen_h = self.window.winfo_screenheight()
        # Если экран маленький (например, ноутбук с 150% DPI), ограничиваем высоту окна
        actual_h = min(750, screen_h - 120) 
        self.window.geometry(f"820x{actual_h}") # 820 для запаса под полосу прокрутки
        self.window.minsize(800, 500)

        self.window.transient(self.parent.root)
        self.window.grab_set()
        self.window.focus_set()

        # --- ВНЕДРЕНИЕ ПРОКРУТКИ ---
        # Создаем прокручиваемый контейнер
        scroll_wrapper = ScrollableContainer(self.window)
        scroll_wrapper.pack(fill=tk.BOTH, expand=True)

        # Теперь main_container размещается внутри прокручиваемой области
        main_container = ttk.Frame(scroll_wrapper.scrollable_content)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # --- Profile Name ---
        name_frame = ttk.Frame(main_container)
        name_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(name_frame, text="Profile Name:*",
                  font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var,
                                    font=("Arial", 11))
        self.name_entry.pack(fill=tk.X, pady=(5, 0))

        # --- Description ---
        desc_frame = ttk.LabelFrame(main_container, text="Description", padding="6")
        desc_frame.pack(fill=tk.X, pady=(0, 10))

        self.desc_text = tk.Text(desc_frame, height=2, font=("Arial", 10))
        self.desc_text.pack(fill=tk.BOTH, expand=True)

        # --- Feed Rate + Material ---
        params_frame = ttk.LabelFrame(main_container, text="Processing Parameters", padding="10")
        params_frame.pack(fill=tk.X, pady=(0, 10))

        params_grid = ttk.Frame(params_frame)
        params_grid.pack(fill=tk.X)

        # Feed Rate
        feed_group = ttk.Frame(params_grid)
        feed_group.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 20))

        ttk.Label(feed_group, text="Feed Rate:").pack(anchor=tk.W)
        feed_input_frame = ttk.Frame(feed_group)
        feed_input_frame.pack(fill=tk.X, pady=(2, 0))

        self.feed_var = tk.StringVar(value="30")
        self.feed_entry = ttk.Entry(feed_input_frame, textvariable=self.feed_var, width=8)
        self.feed_entry.pack(side=tk.LEFT)
        ttk.Label(feed_input_frame, text=" m/min").pack(side=tk.LEFT, padx=(2, 0))

        # Material
        material_group = ttk.Frame(params_grid)
        material_group.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        ttk.Label(material_group, text="Material Size:").pack(anchor=tk.W)

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
        self.material_combo.bind("<<ComboboxSelected>>", self._on_material_changed)

        # --- Product Sizes ---
        product_frame = ttk.LabelFrame(main_container, text="Product Sizes", padding="8")
        product_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ("Width", "Thickness", "Default", "Material")
        self.product_tree = ttk.Treeview(
            product_frame,
            columns=columns,
            show="headings",
            height=4
        )
        self.product_tree.bind("<Double-1>", self._on_variant_double_click)
        self.product_tree.bind("<<TreeviewSelect>>", self._on_product_variant_selected)
        
        self.product_tree.heading("Width", text="Width (mm)")
        self.product_tree.heading("Thickness", text="Thickness (mm)")
        self.product_tree.heading("Default", text="Active")
        self.product_tree.heading("Material", text="Material")

        self.product_tree.column("Width", width=80, anchor="center")
        self.product_tree.column("Thickness", width=100, anchor="center")
        self.product_tree.column("Default", width=60, anchor="center")
        self.product_tree.column("Material", width=120, anchor="center")

        scrollbar = ttk.Scrollbar(product_frame, orient="vertical",
                                  command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=scrollbar.set)

        self.product_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Variant buttons
        variant_btn_frame = ttk.Frame(product_frame)
        variant_btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

        button_config = {'width': 7, 'padding': (2, 2)}
        ttk.Button(variant_btn_frame, text="Add", command=self._add_product_variant,
                   **button_config).pack(pady=(0, 2))
        ttk.Button(variant_btn_frame, text="Edit", command=self._edit_product_variant,
                   **button_config).pack(pady=2)
        ttk.Button(variant_btn_frame, text="Delete", command=self._delete_product_variant,
                   **button_config).pack(pady=2)
        ttk.Button(variant_btn_frame, text="Up", command=lambda: self._move_variant(-1),
                   **button_config).pack(pady=2)
        ttk.Button(variant_btn_frame, text="Down", command=lambda: self._move_variant(1),
                   **button_config).pack(pady=2)

        # --- PDF Section ---
        pdf_frame = ttk.LabelFrame(main_container, text="Profile Document (PDF)", padding="8")
        pdf_frame.pack(fill=tk.X, pady=(0, 15))

        pdf_top_frame = ttk.Frame(pdf_frame)
        pdf_top_frame.pack(fill=tk.X, pady=(0, 8))

        self.pdf_status_label = ttk.Label(
            pdf_top_frame,
            text="No PDF loaded",
            foreground="gray",
            font=("Arial", 9)
        )
        self.pdf_status_label.pack(side=tk.LEFT, anchor=tk.W, fill=tk.X, expand=True)

        pdf_btn_frame = ttk.Frame(pdf_top_frame)
        pdf_btn_frame.pack(side=tk.RIGHT)

        self.upload_btn = ttk.Button(pdf_btn_frame, text="Upload",
                                     command=self.upload_pdf, width=8)
        self.upload_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.remove_btn = ttk.Button(pdf_btn_frame, text="Remove",
                                     command=self.remove_pdf, width=8)
        self.remove_btn.pack(side=tk.LEFT)

        preview_frame = ttk.Frame(pdf_frame)
        preview_frame.pack(fill=tk.X)

        preview_inner = ttk.Frame(preview_frame, width=200, height=100)
        preview_inner.pack_propagate(False)
        preview_inner.pack(pady=2)

        self.pdf_preview = ImagePreview(preview_inner, width=180, height=80)
        self.pdf_preview.pack(expand=True, fill=tk.BOTH)

        # --- Buttons ---
        ttk.Separator(main_container, orient='horizontal').pack(fill=tk.X, pady=(15, 10))

        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill=tk.X)

        if self.is_editing:
            self.delete_btn = ttk.Button(button_frame, text="Delete Profile",
                                         command=self.delete, width=15)
            self.delete_btn.pack(side=tk.LEFT)

            spacer = ttk.Frame(button_frame)
            spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)

            self.cancel_btn = ttk.Button(button_frame, text="Cancel",
                                         command=self.window.destroy, width=12)
            self.cancel_btn.pack(side=tk.LEFT, padx=(0, 10))

            self.save_btn = ttk.Button(button_frame, text="Save",
                                       command=self._safe_save, width=12)
            self.save_btn.pack(side=tk.LEFT)
        else:
            spacer = ttk.Frame(button_frame)
            spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)

            self.cancel_btn = ttk.Button(button_frame, text="Cancel",
                                         command=self.window.destroy, width=12)
            self.cancel_btn.pack(side=tk.LEFT, padx=(0, 10))

            self.save_btn = ttk.Button(button_frame, text="Save",
                                       command=self._safe_save, width=12)
            self.save_btn.pack(side=tk.LEFT)

        # Применяем данные и центрируем
        self._load_profile_data()
        self._apply_access_mode()
        self.center_window()
        
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

    def _on_variant_selected(self, event=None):
        """Фильтрует список материалов в зависимости от выбранного варианта профиля."""
        selection = self.product_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        values = self.product_tree.item(item_id, "values")

        if not values:
            return

        width = float(values[0])
        thickness = float(values[1])

        # Фильтруем материалы
        all_sizes = self.size_service.get_all_material_sizes()
        filtered = [
            s for s in all_sizes
            if s.width >= width and s.thickness >= thickness
        ]

        size_names = [s.display_name() for s in filtered]
        size_names.insert(0, "")

        # Обновляем комбобокс
        self.material_combo["values"] = size_names

        # Сбрасываем выбранное значение, если оно не подходит
        current = self.material_size_var.get()
        if current not in size_names:
            self.material_size_var.set("")
   
    def _filter_material_sizes(self, min_width, min_thickness):
        """Фильтрует список размеров материала по минимальным размерам профиля."""
        all_sizes = self.size_service.get_all_material_sizes()

        filtered = []
        for s in all_sizes:
            if s.width >= min_width and s.thickness >= min_thickness:
                filtered.append(s)

        return filtered

    def _refresh_material_sizes(self):
        """Обновить список размеров материала в комбобоксе"""
        material_sizes = self.size_service.get_all_material_sizes()
        size_names = [s.display_name() for s in material_sizes]
        size_names.insert(0, "")

        current_value = self.material_size_var.get()
        self.material_combo['values'] = size_names

        if current_value in size_names:
            self.material_size_var.set(current_value)

    def _parse_material_size(self, text: str):
        """Парсит строку '140 x 27'"""
        try:
            parts = text.lower().replace("×", "x").split("x")
            if len(parts) != 2:
                return None

            width = float(parts[0].strip())
            thickness = float(parts[1].strip())

            if width <= 0 or thickness <= 0:
                return None

            return width, thickness
        except:
            return None

    def _add_product_variant(self):
        """Добавление варианта без автоматического назначения материала"""
        from gui.simple_variant_dialog import SimpleVariantDialog

        dialog = SimpleVariantDialog(self.window, title="Add Product Size")

        if dialog.result:
            width, thickness = dialog.result
            try:
                width_val = float(width)
                thickness_val = float(thickness) if thickness.strip() else None

                variant_data = {
                    'temp_id': len(self.edited_variants) + 1000,
                    'width': width_val,
                    'thickness': thickness_val,
                    'is_default': False,
                    'material_id': None  # ⭐ Всегда создаем без материала
                }

                if not self.product_variants:
                    variant_data['is_default'] = True

                # Добавляем в списки
                self.edited_variants.append(variant_data)
                self.product_variants.append(variant_data)

                # ⭐ Сбрасываем комбобокс и фильтр, так как новый вариант чист
                self.material_size_var.set("")
                # Обновляем комбобокс полным списком материалов (так как фильтровать пока нечего)
                all_m = self.size_service.get_all_material_sizes()
                self.material_combo['values'] = [""] + [m.display_name() for m in all_m]

                self._update_product_variants_table()
                
                # Опционально: выделяем новую строку в таблице
                item_id = f"variant_{variant_data['temp_id']}"
                self.product_tree.selection_set(item_id)
                self.product_tree.focus(item_id)

            except ValueError:
                messagebox.showerror("Error", "Please enter valid numeric values")
    def _on_material_changed(self, event=None):
        """Обновляет материал ТОЛЬКО для выбранного в данный момент варианта"""
        # 1. Получаем выбранную строку в таблице
        item_id = self.product_tree.focus()
        if not item_id:
            # Если ничего не выбрано, просто выходим (или сбрасываем комбобокс)
            return

        # 2. Получаем объект выбранного материала из комбобокса
        selected_material = self._get_selected_material_size()
        m_id = selected_material.id if selected_material else None
        
        # 3. Находим соответствующий вариант в нашем списке и обновляем только его
        idx_str = item_id.split('_')[-1]
        for variant in self.product_variants:
            if str(variant.get('id', variant.get('temp_id'))) == idx_str:
                variant['material_id'] = m_id
                print(f"DEBUG: Updated material_id to {m_id} for variant {idx_str}")
                break
        
        # 4. Перерисовываем таблицу, чтобы увидеть изменения в колонке Material
        self._update_product_variants_table()
    
    def _get_selected_variant(self):
        """Возвращает данные варианта, выбранного в таблице"""
        item_id = self.product_tree.focus()
        if not item_id:
            return None

        try:
            # Извлекаем ID из iid строки (например, из "variant_105" получаем "105")
            idx_str = item_id.split('_')[-1]
            
            # Ищем этот ID в нашем списке вариантов
            for v in self.product_variants:
                if str(v.get('id', v.get('temp_id'))) == idx_str:
                    return v
            return None
        except Exception as e:
            print(f"DEBUG: Error in _get_selected_variant: {e}")
            return None
    
    def _edit_product_variant(self):
        """Редактирование варианта"""
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
            initial_values=values[:2]
        )

        if dialog.result:
            width, thickness = dialog.result
            try:
                width_val = float(width)
                thickness_val = float(thickness) if thickness.strip() else None

                variant_id = int(item.split('_')[-1])
                for variant in self.product_variants:
                    if variant.get('id') == variant_id or variant.get('temp_id') == variant_id:
                        variant['width'] = width_val
                        variant['thickness'] = thickness_val

                        # материал
                        selected_name = self.material_size_var.get()
                        material_sizes = self.size_service.get_all_material_sizes()
                        material_obj = next((m for m in material_sizes if m.display_name() == selected_name), None)
                        variant['material_id'] = material_obj.id if material_obj else None

                        break

                self._update_product_variants_table()

            except ValueError:
                messagebox.showerror("Error", "Please enter valid numeric values")

    def _delete_product_variant(self):
        """Удаление варианта"""
        selection = self.product_tree.selection()
        if not selection:
            return

        for item in selection:
            variant_id = int(item.split('_')[-1])

            if 0 < variant_id < 1000:
                self.deleted_variant_ids.append(variant_id)

            self.product_variants = [
                v for v in self.product_variants
                if v.get('id') != variant_id and v.get('temp_id') != variant_id
            ]
            self.edited_variants = [
                v for v in self.edited_variants
                if v.get('id') != variant_id and v.get('temp_id') != variant_id
            ]

        self._update_product_variants_table()
        if not self.product_variants:
            print("DEBUG: No variants left, clearing material selection")
            self.material_size_var.set("") # Устанавливаем пустую строку (первая строка комбобокса)

    def _move_variant(self, direction):
        """Перемещение варианта"""
        selection = self.product_tree.selection()
        if not selection:
            return

        item = selection[0]
        item_id = int(item.split('_')[-1])

        for i, variant in enumerate(self.product_variants):
            if variant.get('id') == item_id or variant.get('temp_id') == item_id:
                new_index = i + direction
                if 0 <= new_index < len(self.product_variants):
                    self.product_variants[i], self.product_variants[new_index] = \
                        self.product_variants[new_index], self.product_variants[i]
                break

        self._update_product_variants_table()

    def _on_product_variant_selected(self, event=None):
        variant = self._get_selected_variant()
        if not variant:
            return

        width = variant["width"]
        thickness = variant["thickness"]

        # Фильтруем материалы
        filtered = self._filter_material_sizes(width, thickness)

        # Обновляем комбобокс
        size_names = [s.display_name() for s in filtered]
        size_names.insert(0, "")

        self.material_combo['values'] = size_names

        # Если текущий выбранный материал меньше профиля — сбрасываем
        current = self.material_size_var.get()
        if current not in size_names:
            self.material_size_var.set("")
    
    def _update_product_variants_table(self):
        """Обновление таблицы вариантов"""
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)

        for i, variant in enumerate(self.product_variants):
            thickness = variant.get('thickness') or ""
            thickness = f"{thickness}" if thickness else ""

            material_id = variant.get('material_id')
            material_obj = None
            if material_id:
                material_obj = self.size_service.get_material_size_by_id(material_id)

            material_name = material_obj.display_name() if material_obj else ""

            values = (
                variant.get('width', ''),
                thickness,
                '✓' if variant.get('is_default') else '',
                material_name
            )

            item_id = f"variant_{variant.get('id', variant.get('temp_id', i))}"
            self.product_tree.insert('', 'end', iid=item_id, values=values)

    def _on_variant_double_click(self, event):
        item_id = self.product_tree.focus()
        if not item_id:
            return

        variant_id = int(item_id.split('_')[-1])

        for v in self.product_variants:
            v['is_default'] = False

        for v in self.product_variants:
            if v.get('id') == variant_id or v.get('temp_id') == variant_id:
                v['is_default'] = True

                material_id = v.get('material_id')
                if material_id:
                    material = self.size_service.get_material_size_by_id(material_id)
                    if material:
                        self.material_size_var.set(material.display_name())
                else:
                    self.material_size_var.set("")

                break

        self._update_product_variants_table()
    def _get_selected_material_size(self):
        """Получить выбранный объект MaterialSize"""
        selected_name = self.material_size_var.get()
        if not selected_name:
            return None

        material_sizes = self.size_service.get_all_material_sizes()
        for size in material_sizes:
            if size.display_name() == selected_name:
                return size
        return None

    def _load_profile_data(self):
        """Загружает данные профиля в форму"""
        if not self.profile:
            return

        self.name_var.set(self.profile.name)
        self.desc_text.insert("1.0", self.profile.description)
        self.feed_var.set(str(self.profile.feed_rate))

        # Материал
        if self.profile.material_size:
            self.material_size_var.set(self.profile.material_size)

        # Варианты продукта
        if hasattr(self.profile, 'id') and self.profile.id:
            self.product_variants = self.size_service.get_product_variants_for_profile(self.profile.id)
        else:
            self.product_variants = []

        self._update_product_variants_table()

        # PDF
        if self.profile.has_pdf:
            self.pdf_status_label.config(
                text=f"PDF: {os.path.basename(self.profile.pdf_path)}",
                foreground="green"
            )

            try:
                self.original_pdf_data = self.profile_service.get_profile_pdf(self.profile.id)
                self.original_pdf_filename = os.path.basename(self.profile.pdf_path)

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

                # Превью PDF
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
        """Сохраняет профиль с PDF и синхронизирует материал активного варианта"""
        if self._saving:
            return
        self._saving = True

        try:
            if hasattr(self, 'access_mode') and self.access_mode == "READ_ONLY":
                messagebox.showerror(
                    "Access Denied",
                    "This profile is in READ ONLY mode.\n"
                    "You cannot modify it. Contact an administrator."
                )
                self._saving = False
                self.save_btn.config(state='normal')
                return

            if not self._check_security('create_profile' if not self.is_editing else 'edit_profile'):
                self._saving = False
                self.save_btn.config(state='normal')
                return

            name = self.name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Profile name is required")
                self._saving = False
                self.save_btn.config(state='normal')
                return

            description = self.desc_text.get("1.0", tk.END).strip()

            try:
                feed_rate = float(self.feed_var.get())
            except ValueError:
                feed_rate = 30.0

            # --- ЛОГИКА ОПРЕДЕЛЕНИЯ МАТЕРИАЛА ДЛЯ ГЛАВНОГО ОКНА ---
            # Ищем вариант с галочкой (is_default)
            default_variant = next((v for v in self.product_variants if v.get('is_default')), None)
            
            # Если вариантов несколько, но галочка не стоит, берем первый как основной
            if not default_variant and self.product_variants:
                default_variant = self.product_variants[0]

            material_size_str = ""
            if default_variant and default_variant.get('material_id'):
                # Если у активного варианта есть материал, подтягиваем его имя из БД
                mat_obj = self.size_service.get_material_size_by_id(default_variant['material_id'])
                if mat_obj:
                    material_size_str = mat_obj.display_name()
            
            # Если активный вариант не найден или у него нет материала, 
            # используем текущее значение из комбобокса как запасное
            if not material_size_str:
                selected_material_size = self._get_selected_material_size()
                material_size_str = selected_material_size.display_name() if selected_material_size else ""

            # --- Обработка PDF ---
            pdf_data_to_save = None
            pdf_filename_to_save = None

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
                    pdf_data_to_save = self.original_pdf_data if self.original_pdf_data else None

            log_profile_change({
                'name': name,
                'feed_rate': feed_rate,
                'material_size': material_size_str,
                'product_size': "",
                'tools': []
            })

            profile_id = None
            action = ""
            success = False

            if self.is_editing and self.profile:
                profile_id = self.profile.id
                success = self.profile_service.update_profile(
                    self.profile.id,
                    name=name,
                    description=description,
                    feed_rate=feed_rate,
                    material_size=material_size_str,
                    product_size="",
                    pdf_data=pdf_data_to_save,
                    pdf_filename=pdf_filename_to_save
                )
                action = "updated"
            else:
                profile_id = self.profile_service.create_profile(
                    name=name,
                    description=description,
                    feed_rate=feed_rate,
                    material_size=material_size_str,
                    product_size="",
                    pdf_data=pdf_data_to_save,
                    pdf_filename=pdf_filename_to_save
                )
                success = profile_id is not None
                action = "created"
                
                if success:
                    self.profile = self.profile_service.get_profile_by_id(profile_id)
                    self.is_editing = True

            if success and profile_id:
                print(f"DEBUG: Saving {len(self.product_variants)} product variants for profile {profile_id}")

                self._save_product_variants(profile_id)
                self.product_variants = self.size_service.get_product_variants_for_profile(profile_id)
                self._update_product_variants_table()

                product_size_str = self._get_product_size_string()
                update_success = self.profile_service.update_profile_product_size(
                    profile_id, product_size_str
                )
                
                # Дополнительно обновляем material_size в БД на случай, если он изменился в процессе сохранения вариантов
                self.profile_service.update_profile(
                    profile_id, 
                    material_size=material_size_str,
                    keep_existing_pdf=True  # Сохраняем PDF!
                )

            if success:
                messagebox.showinfo("Success", f"Profile {action} successfully")
                
                if hasattr(self.parent, "profile_service"):
                    try:
                        self.parent.profile_service.set_current_profile(profile_id)
                    except Exception as e:
                        print(f"DEBUG: Error setting current profile: {e}")

                try:
                    if hasattr(self.parent, 'show_profile_details'):
                        self.parent.show_profile_details()
                    if hasattr(self.parent, 'load_profiles'):
                        self.parent.load_profiles()
                except Exception as e:
                    print(f"DEBUG: Error updating parent UI: {e}")

                if hasattr(self, 'callback') and self.callback:
                    try: self.callback()
                    except: pass

                self.pdf_was_uploaded = False
                self.pdf_was_removed = False
                self.window.destroy()
            else:
                messagebox.showerror("Error", f"Failed to {action} profile")
                self._saving = False
                self.save_btn.config(state='normal')

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self._saving = False
            if hasattr(self, 'save_btn'): self.save_btn.config(state='normal')

    def _get_product_size_string(self):
        """Формирует строку product_size для отображения в главном окне"""
        if not self.product_variants:
            return "Not specified"

        default_variant = next((v for v in self.product_variants if v.get('is_default')), None)

        if not default_variant and self.product_variants:
            default_variant = self.product_variants[0]
            default_variant['is_default'] = True

        if not default_variant:
            return "Not specified"

        thickness = default_variant.get('thickness')
        if thickness:
            return f"{default_variant['width']} x {thickness}"
        else:
            return f"{default_variant['width']}"

    def _save_product_variants(self, profile_id):
        """Сохраняет варианты размеров продукта, используя правильные методы SizeService"""
        try:
            print(f"DEBUG: Saving {len(self.product_variants)} product variants for profile {profile_id}")

            # 1. Удаление помеченных на удаление
            if hasattr(self, 'deleted_variant_ids') and self.deleted_variant_ids:
                for v_id in self.deleted_variant_ids:
                    self.size_service.delete_product_variant(v_id)
                self.deleted_variant_ids = []

            # 2. Получаем текущие ID из базы для проверки
            existing_variants = self.size_service.get_product_variants_for_profile(profile_id)
            existing_ids = [v['id'] for v in existing_variants] if existing_variants else []

            # 3. Сохранение/Обновление
            for variant in self.product_variants:
                v_id = variant.get('id')
                
                # Подготовка данных (защита от отсутствующих ключей)
                width = variant.get('width', 0)
                thickness = variant.get('thickness')
                is_default = variant.get('is_default', False)
                material_id = variant.get('material_id')

                if v_id and v_id in existing_ids:
                    # ОБНОВЛЕНИЕ существующего
                    print(f"DEBUG: Updating variant ID {v_id}")
                    self.size_service.update_product_variant(
                        variant_id=v_id,
                        width=width,
                        thickness=thickness,
                        is_default=is_default,
                        material_id=material_id
                    )
                else:
                    # СОЗДАНИЕ НОВОГО (Используем точное имя метода из вашего сервиса)
                    print(f"DEBUG: Inserting new variant for profile {profile_id}")
                    new_id = self.size_service.insert_product_variant(
                        profile_id=profile_id,
                        width=width,
                        thickness=thickness,
                        is_default=is_default,
                        material_id=material_id
                    )
                    if new_id:
                        variant['id'] = new_id

            print("DEBUG: Product variants saved successfully")
        except Exception as e:
            print(f"DEBUG: Error in _save_product_variants: {e}")
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

        self.product_size_entry.delete(0, "end")
        self.product_size_entry.insert(0, size_str)

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
        """Центрирует окно с защитой от вылета за границы экрана"""
        self.window.update_idletasks()
        
        # Размеры этого окна
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        
        # Размеры экрана
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        # По умолчанию считаем центр экрана
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        # Если есть родитель, пытаемся центрироваться относительно него
        try:
            if self.parent and self.parent.winfo_exists():
                p_x = self.parent.winfo_rootx()
                p_y = self.parent.winfo_rooty()
                p_w = self.parent.winfo_width()
                p_h = self.parent.winfo_height()
                
                x = p_x + (p_w - width) // 2
                y = p_y + (p_h - height) // 2
        except:
            pass

        # ⭐ ЗАЩИТА ОТ "СПОЛЗАНИЯ"
        padding = 30  # Отступ от краев экрана
        
        # Не даем уйти за левый и верхний край
        x = max(padding, x)
        y = max(padding, y)
        
        # Не даем уйти за правый и нижний край
        if x + width > screen_width - padding:
            x = screen_width - width - padding
        if y + height > screen_height - padding:
            y = screen_height - height - padding

        # Применяем координаты
        self.window.geometry(f"+{int(x)}+{int(y)}")

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
            if hasattr(self, 'window') and self.window.winfo_exists():
                current_title = self.window.title()
                if "(READ ONLY)" not in current_title:
                    self.window.title(f"{current_title} (READ ONLY)")
        else:
            state = "normal"

        widgets_to_update = []

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


__all__ = ['ProfileEditor']
