"""
Редактор инструментов
"""
import tkinter as tk
from tkinter import ttk, filedialog
import os
import logging
from typing import Optional, Callable
import io

from core.models import Tool
from services.profile_service import ProfileService
from services.tool_service import ToolService
from gui.base.dialogs import show_error, show_info, ask_yesno
from gui.base.widgets import ImagePreview, LabeledEntry, LabeledSpinbox

logger = logging.getLogger(__name__)

class ToolEditor:
    """Окно редактирования инструмента"""
    
    def __init__(self, parent, profile_service: ProfileService, 
                 tool_service: ToolService, profile_id: Optional[int] = None,
                 tool: Optional[Tool] = None, callback: Optional[Callable] = None,
                 on_profile_created: Optional[Callable] = None):
        self.parent = parent
        self.profile_service = profile_service
        self.tool_service = tool_service
        self.profile_id = profile_id
        self.tool = tool
        self.callback = callback
        self.on_profile_created = on_profile_created
        self.image_data = None
        
        self.is_editing = tool is not None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        # Создание окна
        self.window = tk.Toplevel(self.parent)
        title = "Edit Tool" if self.is_editing else "Add Tool"
        self.window.title(title)
        self.window.geometry("625x700")  # Match profile editor size
        self.window.minsize(625, 700)    # Set minimum size
        
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
        
        # Форма ввода
        self._setup_form(scrollable_frame)
        
        # Кнопки
        self._setup_buttons(scrollable_frame)
        
        # Обновляем геометрию после загрузки всех виджетов
        def _update_scroll_region():
            canvas.update_idletasks()
            _on_frame_configure(None)
        
        self.window.after(100, _update_scroll_region)
        
        # Загружаем данные если редактируем
        if self.is_editing and self.tool:
            self._load_tool_data()
        elif self.profile_id:
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
    
    def _setup_form(self, parent):
        """Настройка формы ввода"""
        # Создаем стиль для комбобокса
        style = ttk.Style()
        style.configure('TCombobox', postoffset=(0, 0, 25, 0))  # Устанавливаем фиксированную ширину выпадающего списка

        # Секция: Профиль
        profile_frame = ttk.LabelFrame(parent, text="Profile", padding="10")
        profile_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(profile_frame, text="Select Profile:*").pack(anchor=tk.W, pady=(0, 5))
        
        # Загружаем профили
        self.profiles = self.profile_service.get_all_profiles()
        self.profile_names = [p.name for p in self.profiles]
        self.profile_ids = [p.id for p in self.profiles]
        self.profile_var = tk.StringVar()
        
        # Создаем комбобокс
        self.profile_combo = ttk.Combobox(
            profile_frame,
            textvariable=self.profile_var,
            values=self.profile_names,
            state="readonly",
            width=15
        )
        self.profile_combo.pack(fill=tk.X, pady=(0, 5))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)
        
        # Если передан profile_id, выбираем его
        if self.profile_id:
            for i, pid in enumerate(self.profile_ids):
                if pid == self.profile_id:
                    self.profile_var.set(self.profile_names[i])
                    break
        
        # Кнопка создания профиля
        #ttk.Button(profile_frame, text="New Profile", 
        #        command=self._create_new_profile).pack(anchor=tk.W)
        
        # Секция: Позиционирование и тип
        pos_frame = ttk.LabelFrame(parent, text="Positioning & Type", padding="10")
        pos_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Позиция
        pos_row = ttk.Frame(pos_frame)
        pos_row.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(pos_row, text="Position:", width=10).pack(side=tk.LEFT)
        self.position_var = tk.StringVar(value="Bottom")
        if self.is_editing and self.tool:
            # При редактировании блокируем изменение позиции
            self.position_combo = ttk.Combobox(
                pos_row,
                textvariable=self.position_var,
                values=["Bottom", "Top", "Right", "Left"],
                state="readonly",
                width=15
            )
        else:
            self.position_combo = ttk.Combobox(
                pos_row,
                textvariable=self.position_var,
                values=["Bottom", "Top", "Right", "Left"],
                state="readonly",
                width=15
            )
        self.position_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        # Тип инструмента
        ttk.Label(pos_row, text="Tool Type:").pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value="Profile")
        type_combo = ttk.Combobox(
            pos_row,
            textvariable=self.type_var,
            values=["Straight", "Profile"],
            state="readonly",
            width=15
        )
        type_combo.pack(side=tk.LEFT, padx=5)
        
        # Номер комплекта и количество ножей
        count_row = ttk.Frame(pos_frame)
        count_row.pack(fill=tk.X)
        
        ttk.Label(count_row, text="Set Number:", width=11).pack(side=tk.LEFT)
        self.set_var = tk.IntVar(value=1)
        set_spinbox = tk.Spinbox(
            count_row,
            from_=1, to=9,
            textvariable=self.set_var,
            width=10
        )
        set_spinbox.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(count_row, text="Knives Count:").pack(side=tk.LEFT)
        self.knives_var = tk.IntVar(value=6)
        knives_spinbox = tk.Spinbox(
            count_row,
            from_=1, to=200,
            textvariable=self.knives_var,
            width=10
        )
        knives_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Секция: Код инструмента
        code_frame = ttk.LabelFrame(parent, text="Tool Code", padding="10")
        code_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Информация о формате кода
        code_info = """Format: XXXXXX (6 digits)
1st digit: Position (1=Bottom, 2=Top, 3=Right, 4=Left)
2nd digit: Type (0=Straight, 1=Profile)
3rd-5th digits: Profile ID (001-999)
6th digit: Set number (1-9)"""
        
        ttk.Label(code_frame, text=code_info, justify=tk.LEFT).pack(anchor=tk.W)
        
        # Сгенерированный код
        ttk.Label(code_frame, text="Generated Code:", 
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        
        self.code_var = tk.StringVar(value="Select profile first")
        code_label = ttk.Label(
            code_frame,
            textvariable=self.code_var,
            font=("Arial", 12, "bold"),
            background="white",
            relief="sunken",
            width=15,
            anchor="center"
        )
        code_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Декодированная информация
        self.decoded_var = tk.StringVar()
        ttk.Label(code_frame, textvariable=self.decoded_var, 
                 foreground="blue").pack(anchor=tk.W)
        
        # Секция: Идентификация и статус
        id_frame = ttk.LabelFrame(parent, text="Identification & Status", padding="10")
        id_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Создаем фрейм для строки с Template ID и Status
        id_status_row = ttk.Frame(id_frame)
        id_status_row.pack(fill=tk.X, pady=(0, 10))
        
        # Левая колонка: Template ID
        id_column = ttk.Frame(id_status_row)
        id_column.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        
        ttk.Label(id_column, text="Template ID:").pack(anchor=tk.W)
        self.template_var = tk.StringVar()
        template_entry = ttk.Entry(id_column, textvariable=self.template_var, width=20)
        template_entry.pack(anchor=tk.W, pady=(5, 0))
        
        # Правая колонка: Status
        status_column = ttk.Frame(id_status_row)
        status_column.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(status_column, text="Status:").pack(anchor=tk.W)
        
        status_frame = ttk.Frame(status_column)
        status_frame.pack(anchor=tk.W, pady=(5, 0))
        
        self.status_var = tk.StringVar(value="ready")
        
        ttk.Radiobutton(
            status_frame,
            text="✅ Ready",
            variable=self.status_var,
            value="ready"
        ).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Radiobutton(
            status_frame,
            text="⚠️ Worn",
            variable=self.status_var,
            value="worn"
        ).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Radiobutton(
            status_frame,
            text="🔧 In Service",
            variable=self.status_var,
            value="in_service"
        ).pack(side=tk.LEFT)
        
        # Заметки по сервису (только для статуса in_service)
        self.service_frame = ttk.Frame(id_frame)
        
        ttk.Label(self.service_frame, text="Service Notes:").pack(side=tk.LEFT, padx=(0, 10))
        self.service_var = tk.StringVar()
        service_entry = ttk.Entry(self.service_frame, textvariable=self.service_var, width=40)
        service_entry.pack(side=tk.LEFT)
        
        # Привязываем изменение статуса
        self.status_var.trace('w', self._on_status_changed)
        
        # Секция: Изображение инструмента
        image_frame = ttk.LabelFrame(parent, text="Tool Image", padding="10")
        image_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Кнопки управления изображением
        image_btn_frame = ttk.Frame(image_frame)
        image_btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(image_btn_frame, text="Browse Image", 
                  command=self.browse_image).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(image_btn_frame, text="Remove Image", 
                  command=self.remove_image).pack(side=tk.LEFT)
        
        # Image preview with fixed size container
        preview_container = ttk.Frame(image_frame, height=150)  # Fixed height
        preview_container.pack(fill=tk.X, pady=5)
        preview_container.pack_propagate(False)  # Prevent the frame from resizing to fit content
        # Create ImagePreview with dynamic width but fixed height
        self.image_preview = ImagePreview(
            preview_container,
            width=600,  # Default width
            height=150,  # Fixed height
            bg='white'
        )
        self.image_preview.pack(fill=tk.X, expand=True)
        # Add a border to make the preview area more visible
        preview_container.config(style='Preview.TFrame')
        style = ttk.Style()
        style.configure('Preview.TFrame', borderwidth=1, relief='sunken')
        
        # Секция: Заметки
        notes_frame = ttk.LabelFrame(parent, text="Notes", padding="10")
        notes_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.notes_text = tk.Text(notes_frame, height=4, font=("Arial", 10))
        self.notes_text.pack(fill=tk.BOTH, expand=True)
        
        # Привязываем события для обновления кода
        self.profile_var.trace('w', self._update_code)
        self.position_var.trace('w', self._update_code)
        self.type_var.trace('w', self._update_code)
        self.set_var.trace('w', self._update_code)
    
    def _setup_buttons(self, parent):
        """Настройка кнопок"""
        # Контейнер для кнопок с фиксированной высотой
        container = ttk.Frame(parent)
        container.pack(fill=tk.X, pady=20)
        
        # Фрейм для центрирования кнопок
        button_frame = ttk.Frame(container)
        button_frame.pack(expand=True)
        
        # Кнопка сохранения
        save_btn = ttk.Button(button_frame, text="Save", 
                             command=self.save, width=15)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Кнопка отмены
        cancel_btn = ttk.Button(button_frame, text="Cancel", 
                               command=self.window.destroy, width=15)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Кнопка удаления (только при редактировании)
        if self.is_editing:
            delete_btn = ttk.Button(button_frame, text="Delete", 
                                   command=self.delete, width=15)
            delete_btn.pack(side=tk.RIGHT, padx=5)
    
    def _load_profile_data(self):
        """Загружает данные профиля"""
        if not self.profile_id:
            return
        
        # Находим имя профиля по ID
        for i, pid in enumerate(self.profile_ids):
            if pid == self.profile_id:
                self.profile_var.set(self.profile_names[i])
                break
        
        self._update_code()
    
    def _load_tool_data(self):
        """Load tool data into form"""
        if not self.tool:
            return
        
        # Load profile data
        self.profile_id = self.tool.profile_id
        self._load_profile_data()
        
        # Set other fields
        self.position_var.set(self.tool.position)
        self.type_var.set(self.tool.tool_type)
        self.set_var.set(self.tool.set_number)
        self.knives_var.set(self.tool.knives_count)
        self.template_var.set(self.tool.template_id or "")
        self.status_var.set(self.tool.status)
        
        # Load notes
        if hasattr(self, 'notes_text') and self.notes_text.winfo_exists():
            self.notes_text.delete('1.0', tk.END)
            self.notes_text.insert('1.0', self.tool.notes or "")
        
        # Load image if exists
        if self.tool.photo:
            self.image_data = self.tool.photo
            if hasattr(self, 'image_preview'):
                self.image_preview.set_image(self.image_data)
        
        self._update_code()
        
        # Загружаем изображение если есть
        if self.tool.photo:
            self.image_data = self.tool.photo
            self.image_preview.set_image(self.image_data)
    
    def _on_profile_selected(self, event):
        """Обработка выбора профиля"""
        selected_name = self.profile_var.get()
        if selected_name in self.profile_names:
            index = self.profile_names.index(selected_name)
            self.profile_id = self.profile_ids[index]
            self._update_code()
    
    def _create_new_profile(self):
        """Создает новый профиль"""
        from .profile_editor import ProfileEditor
        
        editor = ProfileEditor(
            self.window,
            self.profile_service,
            callback=self._on_profile_created
        )
        
        # Ждем закрытия окна
        self.window.wait_window(editor.window)
        
        # Обновляем список профилей
        self._refresh_profiles()
        
        # Вызываем callback если передан
        if self.on_profile_created:
            self.on_profile_created()
    
    def _on_profile_created(self):
        """Обработка создания профиля"""
        self._refresh_profiles()
    
    def _refresh_profiles(self):
        """Обновляет список профилей"""
        self.profiles = self.profile_service.get_all_profiles()
        self.profile_names = [p.name for p in self.profiles]
        self.profile_ids = [p.id for p in self.profiles]
        
        self.profile_combo['values'] = self.profile_names
        
        # Если есть профили, выбираем первый
        if self.profile_names:
            self.profile_var.set(self.profile_names[0])
            self.profile_id = self.profile_ids[0]
            self._update_code()
    
    def _update_code(self, *args):
        """Обновляет сгенерированный код"""
        if not self.profile_id:
            self.code_var.set("Select profile first")
            self.decoded_var.set("")
            return
        
        try:
            # Получаем значения
            position = self.position_var.get()
            tool_type = self.type_var.get()
            set_number = self.set_var.get()
            
            # Генерируем код
            code = self.tool_service.code_generator.generate(
                self.profile_id, position, tool_type, set_number
            )
            
            self.code_var.set(code)
            
            # Декодируем код для отображения
            decoded = self.tool_service.code_generator.decode(code)
            if decoded:
                decoded_text = (
                    f"Position: {decoded['position']} | "
                    f"Type: {decoded['tool_type']} | "
                    f"Profile ID: {decoded['profile_id']} | "
                    f"Set: {decoded['set_number']}"
                )
                self.decoded_var.set(decoded_text)
            else:
                self.decoded_var.set("")
                
        except ValueError as e:
            self.code_var.set(f"Error: {str(e)}")
            self.decoded_var.set("")
        except Exception as e:
            logger.error(f"Error updating code: {e}")
            self.code_var.set("Error generating code")
            self.decoded_var.set("")
    
    def _on_status_changed(self, *args):
        """Обработка изменения статуса"""
        status = self.status_var.get()
        if status == "in_service":
            self.service_frame.pack(fill=tk.X, pady=(10, 0))
        else:
            self.service_frame.pack_forget()
            
        # Обновляем код при изменении статуса
        self._update_code_from_fields()

    def browse_image(self):
        """Open a file dialog to select an image file"""
        filetypes = [
            ("Image files", "*.png *.jpg *.jpeg *.bmp"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Tool Image",
            filetypes=filetypes,
            parent=self.window
        )
        
        if filename:
            try:
                with open(filename, "rb") as f:
                    self.image_data = f.read()
                # Update the image preview if available
                if hasattr(self, 'image_preview'):
                    self.image_preview.set_image(self.image_data)
            except Exception as e:
                logger.error(f"Error loading image: {e}")
                show_error(self.window, "Error", f"Could not load image: {e}")
    
    def remove_image(self):
        """Remove the current image"""
        self.image_data = None
        if hasattr(self, 'image_preview'):
            self.image_preview.clear()

    def _update_code_from_fields(self):
        """Обновляет сгенерированный код"""
        if not self.profile_id:
            self.code_var.set("Select profile first")
            self.decoded_var.set("")
            return
        
        try:
            # Получаем значения
            position = self.position_var.get()
            tool_type = self.type_var.get()
            set_number = self.set_var.get()
            
            # Генерируем код
            code = self.tool_service.code_generator.generate(
                self.profile_id, position, tool_type, set_number
            )
            
            self.code_var.set(code)
            
            # Декодируем код для отображения
            decoded = self.tool_service.code_generator.decode(code)
            if decoded:
                decoded_text = (
                    f"Position: {decoded['position']} | "
                    f"Type: {decoded['tool_type']} | "
                    f"Profile ID: {decoded['profile_id']} | "
                    f"Set: {decoded['set_number']}"
                )
                self.decoded_var.set(decoded_text)
            else:
                self.decoded_var.set("")
                
        except ValueError as e:
            self.code_var.set(f"Error: {str(e)}")
            self.decoded_var.set("")
        except Exception as e:
            logger.error(f"Error updating code: {e}")
            self.code_var.set("Error generating code")
            self.decoded_var.set("")

    def save(self):
        """Сохраняет инструмент"""
        # Валидация
        if not self.profile_var.get():
            show_error(self.window, "Error", "Please select a profile first")
            return
            
        # Get the selected profile ID
        try:
            profile_idx = self.profile_names.index(self.profile_var.get())
            profile_id = self.profile_ids[profile_idx]
        except (ValueError, IndexError):
            show_error(self.window, "Error", "Invalid profile selected")
            return
            
        try:
            # Get form values
            position = self.position_var.get()
            tool_type = self.type_var.get()  # Keep the original case from the combobox
            set_number = int(self.set_var.get())
            knives_count = int(self.knives_var.get())
            template_id = self.template_var.get() or None
            status = self.status_var.get()
            notes = self.notes_text.get("1.0", tk.END).strip() or None
            
            if self.is_editing and self.tool:
                # Update existing tool
                self.tool.profile_id = profile_id
                self.tool.position = position
                self.tool.tool_type = tool_type
                self.tool.set_number = set_number
                self.tool.knives_count = knives_count
                self.tool.template_id = template_id
                self.tool.status = status
                self.tool.notes = notes
                self.tool.photo = self.image_data
                
                success = self.tool_service.update_tool(self.tool.id, self.tool)
                if success:
                    show_info(self.window, "Success", "Tool updated successfully!")
                else:
                    show_error(self.window, "Error", "Failed to update tool")
            else:
                # Create new tool
                from core.models import Tool
                tool = Tool(
                    profile_id=profile_id,
                    position=position,
                    tool_type=tool_type,
                    set_number=set_number,
                    knives_count=knives_count,
                    template_id=template_id,
                    status=status,
                    notes=notes,
                    photo=self.image_data
                )
                tool_id, tool_code = self.tool_service.create_tool(tool)
                if tool_id:
                    show_info(self.window, "Success", 
                             f"Tool created successfully!\nCode: {tool_code}")
                else:
                    show_error(self.window, "Error", "Failed to create tool")
            
            # Close window and call callback
            self.window.destroy()
            if self.callback:
                self.callback()
                
        except Exception as e:
            logger.error(f"Error saving tool: {e}")
            show_error(self.window, "Error", f"Save failed: {str(e)}")

    def delete(self):
        """Удаляет инструмент"""
        if not self.tool:
            return
            
        if ask_yesno(self.window, "Confirm Delete", 
                    f"Delete tool {self.tool.code}?\nThis action cannot be undone."):
            try:
                success = self.tool_service.delete_tool(self.tool_id)
                if success:
                    show_info(self.window, "Success", "Tool deleted successfully")
                    self.window.destroy()
                    if self.callback:
                        self.callback()
                else:
                    show_error(self.window, "Error", "Failed to delete tool")
            except ValueError as ve:
                show_error(self.window, "Deletion Error", str(ve))
            except Exception as e:
                show_error(self.window, "Error", f"Delete failed: {e}")
            # In _update_image_editing_state
            if not is_first_tool and tools_in_set_sorted:
                self.image_button.tooltip = "Image can only be modified for the first tool in the set"
                self.remove_image_button.tooltip = "Image can only be removed from the first tool in the set"
            else:
                self.image_button.tooltip = "Upload image"
                self.remove_image_button.tooltip = "Remove image"

    def _update_image_editing_state(self):
        """Enable/disable image editing based on whether this is the first tool in the set"""
        if not self.tool_id:  # New tool
            return
            
        # Get all tools in the same set
        tools_in_set = self.tool_service.get_tools_by_code_prefix(
            self.tool_data['Auto_Generated_Code'][:5]
        )
        
        # Sort by ID to find the first tool
        tools_in_set_sorted = sorted(tools_in_set, key=lambda x: x.id)
        
        # Enable image editing only for the first tool in the set
        is_first_tool = tools_in_set_sorted and tools_in_set_sorted[0].id == self.tool_id
        self.image_button.config(state='normal' if is_first_tool else 'disabled')
        self.remove_image_button.config(state='normal' if is_first_tool else 'disabled')
        
        # Show a tooltip explaining why it's disabled
        if not is_first_tool and tools_in_set_sorted:
            self.image_button.tooltip = "Изображение можно изменить только у первого инструмента в наборе"
            self.remove_image_button.tooltip = "Изображение можно удалить только у первого инструмента в наборе"
        else:
            self.image_button.tooltip = "Загрузить изображение"
            self.remove_image_button.tooltip = "Удалить изображение"