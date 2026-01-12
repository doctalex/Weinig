"""
Главное окно приложения с поддержкой PDF для профилей
"""
import os
import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, Dict
from utils.logger import ToolLogEntry
from PIL import Image
RESAMPLE = getattr(Image, 'Resampling', Image).LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS
from core.database import DatabaseManager
from core.models import Profile, Tool
from services.profile_service import ProfileService
from services.tool_service import ToolService
from gui.base.dialogs import show_error, show_warning, show_info, ask_yesno
from gui.profile_editor import ProfileEditor
from gui.tool_manager import ToolManager
from gui.tool_assigner import ToolAssigner

# ДОБАВЛЯЕМ ИМПОРТ МЕНЕДЖЕРА БЕЗОПАСНОСТИ
from config.security import SecurityManager

logger = logging.getLogger(__name__)


class WeinigHydromatManager:
    """Главное окно управления инструментами"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Weinig Hydromat 2000 - Advanced Tool Management")
        
        try:
            self.root.state("zoomed")
        except Exception:
            self.root.geometry("1400x800")
        
        # Инициализация сервисов
        self.db = DatabaseManager()
        self.profile_service = ProfileService(self.db)
        self.tool_service = ToolService(self.db)
        
        # ИНИЦИАЛИЗАЦИЯ МЕНЕДЖЕРА БЕЗОПАСНОСТИ (НОВОЕ)
        self.security = SecurityManager()
        
        # Настройка горячих клавиш (НОВОЕ)
        self._setup_hotkeys()
        
        # Подписка на события
        self._setup_observers()
        
        # Текущее состояние
        self.current_profile_id: Optional[int] = None
        self.image_windows = {}
        self.modal_windows = {}
        
        # Настройка интерфейса
        self.setup_ui()
        
        # Загружаем профили с сортировкой по ID по умолчанию
        self._sort_column = 'id'
        self._sort_reverse = False
        self.load_profiles()
        
        # Карта голов
        self.head_position_map = self.tool_service.get_head_position_mapping()
        self.head_names = {
            1: "1 BOTTOM", 2: "1 TOP", 3: "1 RIGHT", 4: "1 LEFT",
            5: "2 RIGHT", 6: "2 LEFT", 7: "2 TOP", 8: "2 BOTTOM",
            9: "3 TOP", 10: "3 BOTTOM"
        }
        
        # ОБНОВЛЯЕМ ИНТЕРФЕЙС С УЧЕТОМ ТЕКУЩЕГО РЕЖИМА (НОВОЕ)
        self.update_ui_for_security_mode()
    
    def _setup_hotkeys(self):
        """Настройка горячих клавиш для переключения режима безопасности"""
        # Горячие клавиши для переключения режима безопасности
        self.root.bind('<Control-Shift-F>', self.toggle_security_mode)
        self.root.bind('<Control-Shift-f>', self.toggle_security_mode)
    
    def _setup_observers(self):
        """Настройка подписок на события"""
        self.profile_service.add_observer('profile_created', self._on_profile_created)
        self.profile_service.add_observer('profile_updated', self._on_profile_updated)
        self.profile_service.add_observer('profile_deleted', self._on_profile_deleted)
        self.profile_service.add_observer('current_profile_changed', self._on_current_profile_changed)
        
        self.tool_service.add_observer('tool_created', self._on_tool_created)
        self.tool_service.add_observer('tool_updated', self._on_tool_updated)
        self.tool_service.add_observer('tool_deleted', self._on_tool_deleted)
        self.tool_service.add_observer('tool_assigned', self._on_tool_assigned)
        self.tool_service.add_observer('assignment_cleared', self._on_assignment_cleared)
    
    # СОБЫТИЯ БЕЗ ИЗМЕНЕНИЙ
    def _on_profile_created(self, profile_id: int):
        """Обработка создания профиля"""
        self.load_profiles()
        logger.info(f"Profile created: {profile_id}")
    
    def _on_profile_updated(self, profile_id: int):
        """Обработка обновления профиля"""
        self.load_profiles()
        if self.current_profile_id == profile_id:
            self.show_profile_details()
        logger.info(f"Profile updated: {profile_id}")
    
    def _on_profile_deleted(self, profile_id: int):
        """Обработка удаления профиля"""
        self.load_profiles()
        if self.current_profile_id == profile_id:
            self.current_profile_id = None
            self.clear_display()
        logger.info(f"Profile deleted: {profile_id}")
    
    def _on_current_profile_changed(self, profile_id: int):
        """Обработка смены текущего профиля"""
        self.current_profile_id = profile_id
        self.show_profile_details()
    
    def show_profile_details(self):
        """Показывает детали текущего профиля"""
        if not self.current_profile_id:
            self.clear_display()
            return
        
        # Получаем текущий профиль
        profile = self.profile_service.get_current_profile()
        if not profile:
            self.clear_display()
            return
        
        # Обновляем переменные
        self.current_profile_var.set(f"Current: {profile.name}")
        self.profile_name_var.set(profile.name)
        self.profile_desc_var.set(profile.description or "No description")
        self.feed_rate_var.set(f"{profile.feed_rate} m/min" if profile.feed_rate else "")
        self.material_size_var.set(profile.material_size or "Not specified")
        self.product_size_var.set(profile.product_size or "Not specified")
        
        # Загружаем превью PDF (первая страница)
        self._load_profile_preview(profile.get_preview())
        
        # Загружаем инструменты
        self.load_profile_tools()
    
    def _on_tool_created(self, tool_id: int, tool_code: str):
        """Обработка создания инструмента"""
        logger.info(f"Tool created: {tool_id} ({tool_code})")
    
    def _on_tool_updated(self, tool_id: int):
        """Обработка обновления инструмента"""
        logger.info(f"Tool updated: {tool_id}")
        self.load_profile_tools()
    
    def _on_tool_deleted(self, tool_id: int):
        """Обработка удаления инструмента"""
        logger.info(f"Tool deleted: {tool_id}")
        self.load_profile_tools()
    
    def _on_tool_assigned(self, profile_id: int, head_number: int, tool_id: int):
        """Обработка назначения инструмента"""
        logger.info(f"Tool {tool_id} assigned to head {head_number} in profile {profile_id}")
        if profile_id == self.current_profile_id:
            self.load_profile_tools()
    
    def _on_assignment_cleared(self, profile_id: int, head_number: int):
        """Обработка очистки назначения"""
        logger.info(f"Assignment cleared from head {head_number} in profile {profile_id}")
        if profile_id == self.current_profile_id:
            self.load_profile_tools()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        # Стили
        style = ttk.Style()
        style.theme_use('clam')
        
        # Шрифты
        self.large_font = ("Arial", 14)
        self.medium_font = ("Arial", 13)
        self.small_font = ("Arial", 12)
        self.title_font = ("Arial", 16, "bold")
        self.header_font = ("Arial", 14, "bold")
        
        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Настройка растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Левая панель - профили
        self._setup_left_panel(main_frame)
        
        # Правая панель - детали
        self._setup_right_panel(main_frame)
        
        # Настройка весов колонок
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
    
    def _sort_profiles(self, col, reverse):
        """Сортировка профилей по выбранной колонке"""
        # Получаем все элементы
        items = [(self.profiles_tree.set(child, col), child) 
                for child in self.profiles_tree.get_children('')]
        
        # Определяем тип сортировки
        if col == 'id':
            # Для ID сортируем как числа
            items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=reverse)
        else:
            # Для остальных колонок как строки
            items.sort(key=lambda x: x[0].lower(), reverse=reverse)
        
        # Перемещаем элементы в отсортированном порядке
        for index, (val, child) in enumerate(items):
            self.profiles_tree.move(child, '', index)
        
        # Устанавливаем стрелку сортировки в заголовке
        self.profiles_tree.heading(col, 
            command=lambda: self._sort_profiles(col, not reverse))
        
        # Обновляем стрелку направления сортировки
        for c in self.profiles_tree['columns']:
            if c != col:
                self.profiles_tree.heading(c, 
                    command=lambda _c=c: self._sort_profiles(_c, False))
                
        # Устанавливаем стрелку вверх/вниз в зависимости от направления
        sort_symbol = ' ↓' if reverse else ' ↑'
        for c in self.profiles_tree['columns']:
            heading_text = self.profiles_tree.heading(c)['text'].replace(' ↓', '').replace(' ↑', '')
            if c == col:
                self.profiles_tree.heading(c, text=heading_text + sort_symbol)
            else:
                self.profiles_tree.heading(c, text=heading_text)
    
    def _setup_left_panel(self, parent):
        """Настройка левой панели с профилями"""
        style = ttk.Style()
        style.configure("Treeview", 
            font=('Arial', 12),
            rowheight=25)
        style.configure("Treeview.Heading", 
            font=('Arial', 12, 'bold'))  # bold font for headers
            
        left_panel = ttk.LabelFrame(parent, padding="15")
        left_panel.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W), padx=(0, 15))
        
        # Create a frame for the header with icon and title
        header_frame = ttk.Frame(left_panel)
        header_frame.pack(pady=(0, 15), fill=tk.X)
        
        # Add the icon
        try:
            from PIL import Image, ImageTk
            # Load the icon using PIL
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'img', 'nordicb.ico')
            icon_img = Image.open(icon_path)
            # Resize to 128x128
            icon_img = icon_img.resize((128, 128), Image.LANCZOS)
            icon = ImageTk.PhotoImage(icon_img)
            
            icon_label = ttk.Label(header_frame, image=icon)
            icon_label.image = icon  # Keep a reference
            icon_label.pack(side=tk.LEFT, padx=(0, 10))
            icon_label.bind("<Double-1>", self._show_about)
        except Exception as e:
            logger.warning(f"Could not load icon: {e}")
            # Fallback to text if icon fails to load
            ttk.Label(header_frame, text="[ICON]", font=('Arial', 8)).pack(side=tk.LEFT, padx=(0, 10))
        
        # Add the title
        ttk.Label(
            header_frame, 
            text="PROFILES", 
            font=self.header_font
        ).pack(side=tk.LEFT)
        
        # Search
        search_frame = ttk.LabelFrame(left_panel)
        search_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(search_frame, text="Search:", font=self.small_font).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, 
                            width=20, font=self.small_font)
        search_entry.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", self._on_search)
        
        # Frame for profiles list with scrollbar
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create Treeview with two columns
        self.profiles_tree = ttk.Treeview(
            list_frame,
            columns=('id', 'name'),
            show='headings',
            yscrollcommand=scrollbar.set,
            selectmode='browse'
        )
        
        # Configure columns with sorting
        self.profiles_tree.heading('id', text='PROFILE ID', 
                                 command=lambda: self._sort_profiles('id', False))
        self.profiles_tree.heading('name', text='PROFILE NAME',
                                 command=lambda: self._sort_profiles('name', False))
        
        # Set column widths
        self.profiles_tree.column('id', width=55, anchor='center')  # Slightly wider for larger text
        self.profiles_tree.column('name', width=210, anchor='w')    # Slightly wider for larger text
        
        # Pack Treeview
        self.profiles_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=self.profiles_tree.yview)
        
        # Привязываем событие выбора
        self.profiles_tree.bind('<<TreeviewSelect>>', self._on_profile_select)
        
        # Кнопки профилей
        button_frame = tk.Frame(left_panel, bg='#e8f5e9', relief=tk.RAISED, bd=2)
        button_frame.pack(fill=tk.X, pady=(15, 0), padx=5)
        
        profile_button_style = {
            'font': ('Arial', 10, 'bold'),
            'bg': '#1976D2',
            'fg': 'white',
            'activebackground': '#1565C0',
            'activeforeground': 'white',
            'bd': 2,
            'relief': 'raised',
            'cursor': 'hand2',
            'padx': 15,
            'pady': 10,
            'width': 10,
            'height': 1
        }
        
        # СОХРАНЯЕМ ССЫЛКИ НА КНОПКИ ДЛЯ ОБНОВЛЕНИЯ СОСТОЯНИЯ (НОВОЕ)
        self.add_profile_btn = tk.Button(button_frame, text="ADD PROFILE",
                        command=self.add_new_profile, **profile_button_style)
        self.add_profile_btn.grid(row=0, column=0, padx=5, pady=8, sticky='ew')
        
        self.edit_profile_btn = tk.Button(button_frame, text="EDIT PROFILE",
                            command=self.edit_profile, **profile_button_style)
        self.edit_profile_btn.grid(row=0, column=1, padx=5, pady=8, sticky='ew')
        
        self.delete_profile_btn = tk.Button(button_frame, text="DELETE PROFILE",
                            command=self.delete_profile, **profile_button_style)
        self.delete_profile_btn.grid(row=0, column=2, padx=5, pady=8, sticky='ew')
        
        for i in range(3):
            button_frame.columnconfigure(i, weight=1)
    
    def _setup_right_panel(self, parent):
        """Настройка правой панели с деталями"""
        right_panel = ttk.Frame(parent)
        right_panel.grid(row=0, column=1, sticky=(tk.N, tk.E, tk.S, tk.W))
        
        # Заголовок
        header_frame = ttk.Frame(right_panel)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(
            header_frame,
            text="WEINIG HYDROMAT 2000 - ADVANCED TOOL MANAGEMENT",
            font=self.title_font,
        ).pack(side=tk.LEFT)
        
        self.current_profile_var = tk.StringVar(value="No profile selected")
        ttk.Label(
            header_frame,
            textvariable=self.current_profile_var,
            font=self.large_font,
            foreground="blue",
        ).pack(side=tk.RIGHT)
        
        # ДОБАВЛЯЕМ ИНДИКАТОР РЕЖИМА БЕЗОПАСНОСТИ (НОВОЕ)
        style = ttk.Style()
        bg_color = style.lookup('TLabel', 'background') or 'SystemButtonFace'
        
        self.security_mode_label = tk.Label(
            header_frame,
            text="[READ ONLY]" if self.security.is_read_only() else "[FULL ACCESS]",
            font=('Arial', 10, 'bold'),
            fg='green' if self.security.is_read_only() else 'red',
            bg=bg_color
        )
        self.security_mode_label.pack(side=tk.RIGHT, padx=(0, 20))
        
        # Детали профиля
        details_frame = ttk.LabelFrame(right_panel, text="PROFILE DETAILS", padding="15")
        details_frame.pack(fill=tk.X, pady=(0, 15))
        
        self._setup_profile_details(details_frame)
        
        # Таблица голов
        tools_frame = ttk.LabelFrame(right_panel, text="MILLING HEADS CONFIGURATION", padding="15")
        tools_frame.pack(fill=tk.X, pady=(0, 15))
        
        self._setup_heads_table(tools_frame)
        
        # Панель управления
        controls_frame = tk.Frame(right_panel, bg='#fff3e0', relief=tk.RAISED, bd=3)
        controls_frame.pack(fill=tk.X, pady=20, padx=10)
        
        self._setup_controls(controls_frame)
    
    def _load_profile_preview(self, image_data: Optional[bytes]):
        """Загружает превью профиля (первая страница PDF или изображение)"""
        # Очищаем текущее изображение
        if hasattr(self, 'profile_image_label'):
            self.profile_image_label.config(image='', text='')
        
        # Если нет данных для превью
        if not image_data:
            if hasattr(self, 'profile_image_label'):
                profile = self.profile_service.get_current_profile()
                if profile and profile.has_pdf:
                    # Есть PDF, но не удалось извлечь превью
                    self.profile_image_label.config(
                        text='PDF Document\n(Double-click to open)',
                        bg="white",
                        font=("Arial", 10)
                    )
                else:
                    # Нет PDF документа
                    self.profile_image_label.config(
                        text='No Document',
                        bg="white",
                        font=("Arial", 10)
                    )
            return
        
        try:
            from PIL import Image, ImageTk
            import io
            
            # Открываем изображение превью
            img = Image.open(io.BytesIO(image_data))
            
            # Ресайз для UI
            max_size = (200, 200)
            img.thumbnail(max_size, Image.LANCZOS)
            
            # Конвертируем в Tkinter формат
            photo = ImageTk.PhotoImage(img)
            
            # Создаем или обновляем лейбл
            if not hasattr(self, 'profile_image_label'):
                self.profile_image_label = ttk.Label(self.profile_image_frame, image=photo)
                self.profile_image_label.image = photo  # Keep a reference
                self.profile_image_label.pack(expand=True, fill='both')
            else:
                self.profile_image_label.config(image=photo)
                self.profile_image_label.image = photo
            
            # Настраиваем курсор и текст
            profile = self.profile_service.get_current_profile()
            if profile and profile.has_pdf:
                # PDF документ - двойной клик открывает PDF
                self.profile_image_label.config(
                    cursor="hand2",
                    text=""
                )
            else:
                # Простое изображение - обычный курсор
                self.profile_image_label.config(
                    cursor="arrow",
                    text=""
                )
                
        except Exception as e:
            logger.error(f"Error loading profile preview: {e}")
            if hasattr(self, 'profile_image_label'):
                self.profile_image_label.config(
                    text='Preview Error',
                    bg="white",
                    font=("Arial", 10)
                )
    
    def _show_about(self, event=None):
        """Show the About dialog"""
        about_text = """Weinig Hydromat 2000
    Advanced Tool Management System v2.0
                    
    Courtesy of Dr. Alex for Nordic B
            doctalex@gmail.com"""
        
        # Create a top level window
        about_window = tk.Toplevel(self.root)
        about_window.title("About")
        about_window.resizable(False, False)
        
        # Center the window
        window_width = 400
        window_height = 250
        screen_width = about_window.winfo_screenwidth()
        screen_height = about_window.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        about_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Add content with centered text
        text_frame = ttk.Frame(about_window)
        text_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # Split text into lines and center each line
        for line in about_text.split('\n'):
            ttk.Label(
                text_frame,
                text=line.strip(),
                font=('Arial', 10),
                anchor='center'
            ).pack(expand=True, fill=tk.X, pady=2)
        
        # Add close button
        button_frame = ttk.Frame(about_window)
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Button(
            button_frame,
            text="Close",
            command=about_window.destroy
        ).pack(side=tk.TOP, pady=10)
        
        # Make window modal
        about_window.grab_set()
    
    def _setup_profile_details(self, parent):
        """Настройка деталей профиля"""
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X)
        
        # Текстовая информация
        text_frame = ttk.Frame(info_frame)
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Фрейм для превью документа
        self.profile_image_frame = ttk.LabelFrame(parent, text="Document Preview", padding=10)
        self.profile_image_frame.pack(side=tk.RIGHT, padx=10, pady=5, fill='both')
        
        # Название
        ttk.Label(text_frame, text="Name:", font=("Arial", 12, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=4
        )
        self.profile_name_var = tk.StringVar(value="")
        ttk.Label(text_frame, textvariable=self.profile_name_var, 
                 font=self.small_font).grid(
                     row=0, column=1, sticky=tk.W, pady=4, padx=(8, 0)
                 )
        
        # Описание
        ttk.Label(text_frame, text="Description:", font=("Arial", 12, "bold")).grid(
            row=1, column=0, sticky=tk.W, pady=4
        )
        self.profile_desc_var = tk.StringVar(value="")
        ttk.Label(text_frame, textvariable=self.profile_desc_var, 
                 wraplength=500, font=self.small_font).grid(
                     row=1, column=1, sticky=tk.W, pady=4, padx=(8, 0)
                 )
        
        # Скорость подачи
        ttk.Label(text_frame, text="Feed Rate:", font=("Arial", 12, "bold")).grid(
            row=2, column=0, sticky=tk.W, pady=4
        )
        self.feed_rate_var = tk.StringVar(value="")
        ttk.Label(text_frame, textvariable=self.feed_rate_var, 
                 font=self.small_font).grid(
                     row=2, column=1, sticky=tk.W, pady=4, padx=(8, 0)
                 )
        
        # Размер материала
        ttk.Label(text_frame, text="Material Size:", font=("Arial", 12, "bold")).grid(
            row=3, column=0, sticky=tk.W, pady=4
        )
        self.material_size_var = tk.StringVar(value="")
        ttk.Label(text_frame, textvariable=self.material_size_var, 
                 font=self.small_font).grid(
                     row=3, column=1, sticky=tk.W, pady=4, padx=(8, 0)
                 )
        
        # Размер изделия
        ttk.Label(text_frame, text="Product Size:", font=("Arial", 12, "bold")).grid(
            row=4, column=0, sticky=tk.W, pady=4
        )
        self.product_size_var = tk.StringVar(value="")
        ttk.Label(text_frame, textvariable=self.product_size_var, 
                 font=self.small_font).grid(
                     row=4, column=1, sticky=tk.W, pady=4, padx=(8, 0)
                 )
        
        # Контейнер для превью документа (PDF или изображения)
        self.profile_image_frame = ttk.Frame(info_frame, width=200, height=150)
        self.profile_image_frame.pack_propagate(False)  # Prevent resizing
        self.profile_image_frame.pack(side=tk.RIGHT, padx=(20, 0), pady=10)
        
        # Лейбл для превью
        self.profile_image_label = tk.Label(
            self.profile_image_frame,
            text="No Document",
            bg="white",
            font=self.small_font,
            anchor="center",
            bd=1,
            relief="sunken"
        )
        self.profile_image_label.pack(expand=True, fill=tk.BOTH)
        
        # Двойной клик открывает PDF или показывает увеличенное изображение
        self.profile_image_label.bind("<Double-Button-1>", self.show_profile_document)
    
    def show_profile_document(self, event):
        """Показывает PDF документ профиля или увеличенное изображение"""
        if not self.current_profile_id:
            return

        profile = self.profile_service.get_current_profile()
        if not profile:
            return
        
        # Если есть PDF - открываем его во внешнем просмотрщике
        if profile.has_pdf:
            success = self.profile_service.open_profile_pdf(profile.id)
            if not success:
                show_error(self.root, "Error", 
                          "Could not open PDF document.\n"
                          "Make sure you have a PDF viewer installed.")
        elif profile.get_preview():
            # Нет PDF, но есть превью (изображение) - показываем увеличенное
            self._show_preview_large(profile)
        else:
            # Нет ни PDF, ни превью
            show_info(self.root, "Info", "No document available for this profile")
    
    def _show_preview_large(self, profile: Profile):
        """Показывает увеличенное превью профиля"""
        try:
            from PIL import Image, ImageTk
            import io

            # Create a new window
            preview_window = tk.Toplevel(self.root)
            preview_window.title(f"Profile Preview - {profile.name}")

            # Load and resize the image
            img = Image.open(io.BytesIO(profile.get_preview()))

            # Limit the maximum display size
            max_size = (800, 600)
            img.thumbnail(max_size, RESAMPLE)

            # Convert to Tkinter format
            photo = ImageTk.PhotoImage(img)

            # Create and pack the image label
            img_label = ttk.Label(preview_window, image=photo)
            img_label.image = photo  # Keep a reference
            img_label.pack(padx=10, pady=10)

            # Add a close button
            close_btn = ttk.Button(preview_window, text="Close", command=preview_window.destroy)
            close_btn.pack(pady=(0, 10))

            # Center the window on screen
            preview_window.update_idletasks()
            width = img.width + 40
            height = img.height + 70
            x = (preview_window.winfo_screenwidth() - width) // 2
            y = (preview_window.winfo_screenheight() - height) // 2
            preview_window.geometry(f"{width}x{height}+{x}+{y}")

            # Make the window modal
            preview_window.transient(self.root)
            preview_window.grab_set()

        except ImportError:
            show_error(self.root, "Error", "Pillow library is required to display images")
        except Exception as e:
            logger.error(f"Error displaying profile preview: {e}")
            show_error(self.root, "Error", f"Could not display preview: {e}")

    def _setup_heads_table(self, parent):
        """Настройка таблицы голов"""
        # Настройка стиля для Treeview
        style = ttk.Style()
        
        # Увеличиваем высоту строки
        style.configure("Treeview", rowheight=35)  # Увеличиваем высоту строки
        style.configure("Custom.Treeview", font=self.large_font, rowheight=35)
        style.configure("Custom.Treeview.Heading", font=self.header_font)
        
        # Создание Treeview
        self.tools_tree = ttk.Treeview(
            parent,
            columns=("HeadNumber", "Head", "Image", "Type", "Code", "RPM", "Pass"),
            show="headings",
            height=11,
            style="Custom.Treeview"
        )
      
        # Настройка заголовков
        self.tools_tree.heading("Head", text="HYDROMAT HEAD", anchor="center")
        self.tools_tree.heading("Image", text="TOOL IMAGE", anchor="center")
        self.tools_tree.heading("Type", text="TOOL TYPE", anchor="center")
        self.tools_tree.heading("Code", text="TOOL CODE", anchor="center")
        self.tools_tree.heading("RPM", text="RPM", anchor="center")
        self.tools_tree.heading("Pass", text="PASS DEPTH", anchor="center")
        
        # Настройка колонок
        self.tools_tree.column("HeadNumber", width=0, stretch=False)
        self.tools_tree.column("Head", width=150, anchor="w", minwidth=120)  # Увеличиваем ширину
        self.tools_tree.column("Image", width=150, anchor="center", minwidth=120)  # Увеличиваем ширину
        self.tools_tree.column("Type", width=200, anchor="center", minwidth=150)  # Увеличиваем ширину
        self.tools_tree.column("Code", width=180, anchor="center", minwidth=150)  # Увеличиваем ширину
        self.tools_tree.column("RPM", width=120, anchor="center", minwidth=100)  # Увеличиваем ширину
        self.tools_tree.column("Pass", width=150, anchor="center", minwidth=120)  # Увеличиваем ширину
        
        # Привязка событий
        self.tools_tree.bind("<Double-1>", self._on_head_double_click)
        self.tools_tree.bind("<Button-1>", self._on_head_click)
        
        self.tools_tree.pack(fill=tk.X)
        
        # Теги для разных статусов
        self.tools_tree.tag_configure('empty', foreground='gray')
        self.tools_tree.tag_configure('assigned', foreground='black')
        self.tools_tree.tag_configure('warning', foreground='orange', font=('Arial', 10, 'bold'))
    
    def _setup_controls(self, parent):
        """Настройка панели управления"""
        tools_buttons_frame = tk.Frame(parent, bg='#fff3e0')
        tools_buttons_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        tool_button_style = {
            'font': ('Arial', 10, 'bold'),
            'fg': 'white',
            'activeforeground': 'white',
            'bd': 3,
            'relief': 'raised',
            'cursor': 'hand2',
            'padx': 25,
            'pady': 15,
            'width': 10,
            'height': 1
        }
        
        # Кнопки - СОХРАНЯЕМ ССЫЛКИ ДЛЯ ОБНОВЛЕНИЯ СОСТОЯНИЯ
        self.assign_tool_btn = tk.Button(
            tools_buttons_frame,
            text="ASSIGN TOOL",
            command=self.assign_tool,
            bg='#4CAF50',
            activebackground='darkgreen',
            **tool_button_style
        )
        self.assign_tool_btn.grid(row=0, column=0, padx=10, pady=5, sticky='ew')
        
        self.manage_tools_btn = tk.Button(
            tools_buttons_frame,
            text="MANAGE TOOLS",
            command=self.manage_profile_tools,
            bg='#FF9800',
            activebackground='darkorange',
            **tool_button_style
        )
        self.manage_tools_btn.grid(row=0, column=1, padx=10, pady=5, sticky='ew')
        
        self.library_btn = tk.Button(
            tools_buttons_frame,
            text="TOOL LIBRARY",
            command=self.open_global_library,
            bg='#9C27B0',
            activebackground='darkviolet',
            **tool_button_style
        )
        self.library_btn.grid(row=0, column=2, padx=10, pady=5, sticky='ew')
        
        self.save_job_btn = tk.Button(
            tools_buttons_frame,
            text="SAVE JOB",
            command=self.save_all,
            bg='#00BCD4',
            activebackground='darkcyan',
            **tool_button_style
        )
        self.save_job_btn.grid(row=0, column=3, padx=10, pady=5, sticky='ew')
        
        for col in range(4):
            tools_buttons_frame.columnconfigure(col, weight=1)
    
    def _on_profile_select(self, event):
        """Обработка выбора профиля"""
        selected = self.profiles_tree.selection()
        if selected:
            item = self.profiles_tree.item(selected[0])
            profile_id = item['values'][0]  # Получаем ID из первой колонки
            self.profile_service.set_current_profile(profile_id)

    def _on_head_double_click(self, event):
        """Двойной клик на голове"""
        self._on_head_click(event)

    def _on_head_click(self, event):
        """Клик на голове"""
        item = self.tools_tree.identify_row(event.y)
        column = self.tools_tree.identify_column(event.x)

        if not item:
            return

        item_data = self.tools_tree.item(item)
        values = item_data["values"]

        if not values or len(values) < 1:
            return

        head_number = values[0]

        # Check if click was on the image column (column #3, 0-indexed as #0 is the hidden column)
        if column == "#3":  # Image column
            # Check if there's a tool assigned (values[2] is the tool code)
            if len(values) > 2 and values[2] == "🖼️":  # If there's an image icon
                self._show_tool_image(head_number)
                return 'break'  # Prevent further event processing
        # Handle click on Code column (column #5)
        elif column == "#5":  
            self._show_tool_selector(head_number, event.x_root, event.y_root)

    def _show_tool_selector(self, head_number: int, x: int, y: int):
        """Показывает селектор инструментов для головы"""
        if not self.current_profile_id:
            show_warning(self.root, "Warning", "Please select a profile first")
            return
        
        # ПРОВЕРКА ДОСТУПА (НОВОЕ) - только для редактирования
        if self.security.is_read_only():
            show_warning(self.root, "Access Denied", 
                        "Cannot assign tools in Read Only mode.\n\n"
                        "Press Ctrl+Shift+F to switch to Full Access mode.")
            return

        required_position = self.head_position_map.get(head_number)
        if not required_position:
            show_error(self.root, "Error", f"Invalid head number: {head_number}")
            return

        # Создаем диалог назначения
        ToolAssigner(
            self.root,
            self.profile_service,
            self.tool_service,
            self.current_profile_id,
            head_number,
            callback=self.load_profile_tools
        )

    # Then update the _show_tool_image method in the WeinigHydromatManager class:
    def _show_tool_image(self, head_number: int):
        """Показывает изображение инструмента в отдельном окне"""
        if not self.current_profile_id:
            return

        # Get the tool assignment for this head
        assignments = self.tool_service.get_tool_assignments(self.current_profile_id)
        if head_number not in assignments:
            return

        assignment = assignments[head_number]
        tool = self.tool_service.get_tool(assignment.tool_id)

        if not tool or not tool.photo:
            show_info(self.root, "Info", "No image available for this tool")
            return

        # Create and show the image viewer
        ToolImageViewer(self.root, tool)

    def load_profiles(self):
        """Загружает список профилей"""
        profiles = self.profile_service.get_all_profiles()
        
        # Очищаем Treeview
        for item in self.profiles_tree.get_children():
            self.profiles_tree.delete(item)
        
        # Добавляем профили в Treeview с форматированным ID
        for profile in profiles:
            formatted_id = f"{profile.id:03d}"  # Форматируем ID с ведущими нулями (001, 002, и т.д.)
            self.profiles_tree.insert('', 'end', values=(formatted_id, profile.name))
        
        # Применяем текущую сортировку
        if hasattr(self, '_sort_column'):
            self._sort_profiles(self._sort_column, self._sort_reverse)
        
        # Если есть текущий профиль, выделяем его
        if hasattr(self, 'current_profile_id') and self.current_profile_id:
            for item in self.profiles_tree.get_children():
                # Сравниваем с отформатированным ID
                if int(self.profiles_tree.item(item)['values'][0]) == self.current_profile_id:
                    self.profiles_tree.selection_set(item)
                    self.profiles_tree.see(item)
                    break
    
    def _on_search(self, event=None):
        """Обработка поиска"""
        search_term = self.search_var.get().strip().lower()
        profiles = self.profile_service.get_all_profiles()
        
        # Очищаем Treeview
        for item in self.profiles_tree.get_children():
            self.profiles_tree.delete(item)
        
        # Фильтруем и добавляем профили с форматированным ID
        for profile in profiles:
            if not search_term or search_term in profile.name.lower():
                formatted_id = f"{profile.id:03d}"  # Форматируем ID с ведущими нулями
                self.profiles_tree.insert('', 'end', values=(formatted_id, profile.name))
        
        # Если есть текущий профиль, выделяем его
        if hasattr(self, 'current_profile_id') and self.current_profile_id:
            for item in self.profiles_tree.get_children():
                # Сравниваем с отформатированным ID
                if int(self.profiles_tree.item(item)['values'][0]) == self.current_profile_id:
                    self.profiles_tree.selection_set(item)
                    self.profiles_tree.see(item)
                    break

    def load_profile_tools(self):
        """Загружает инструменты профиля в таблицу голов"""
        if not self.current_profile_id:
            for item in self.tools_tree.get_children():
                self.tools_tree.delete(item)
            return

        # Очищаем таблицу
        for item in self.tools_tree.get_children():
            self.tools_tree.delete(item)

        # Получаем назначения
        assignments = self.tool_service.get_tool_assignments(self.current_profile_id)

        # Заполняем все 10 голов
        for head_num in range(1, 11):
            head_name = self.head_names.get(head_num, f"Head {head_num}")

            if head_num in assignments:
                assignment = assignments[head_num]
                tool = self.tool_service.get_tool(assignment.tool_id)

                if tool:
                    # Use image icon if tool has a photo, otherwise use wrench emoji
                    image_icon = "🖼️" if tool.photo else "🔧"
                    tool_type = tool.tool_type or "[Unknown]"
                    tool_code = tool.code or "-"
                    rpm = assignment.rpm or "-"
                    pass_depth = assignment.pass_depth or "-"

                    # Проверяем, соответствует ли позиция
                    required_pos = self.head_position_map.get(head_num)
                    if tool.position != required_pos:
                        tags = ('warning',)
                    else:
                        tags = ('assigned',)
                else:
                    image_icon = "○"
                    tool_type = "[Empty]"
                    tool_code = "-"
                    rpm = "-"
                    pass_depth = "-"
                    tags = ('empty',)
            else:
                image_icon = "○"
                tool_type = "[Empty]"
                tool_code = "-"
                rpm = "-"
                pass_depth = "-"
                tags = ('empty',)
            
            # Добавляем строку
            self.tools_tree.insert(
                "", "end",
                values=(head_num, head_name, image_icon, 
                       tool_type, tool_code, rpm, pass_depth),
                tags=tags
            )
    
    def clear_display(self):
        """Очищает отображение"""
        self.current_profile_var.set("No profile selected")
        self.profile_name_var.set("")
        self.profile_desc_var.set("")
        self.feed_rate_var.set("")
        self.material_size_var.set("")
        self.product_size_var.set("")
        self.profile_image_label.config(image='', text='No Document')
        
        for item in self.tools_tree.get_children():
            self.tools_tree.delete(item)
    
    def add_new_profile(self):
        """Добавляет новый профиль"""
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        if self.security.is_read_only():
            show_warning(self.root, "Access Denied", 
                        "Cannot add profiles in Read Only mode.\n\n"
                        "Press Ctrl+Shift+F to switch to Full Access mode.")
            return
        
        ProfileEditor(
            self.root,
            self.profile_service,
            callback=self.load_profiles
        )
    
    def edit_profile(self):
        """Редактирует выбранный профиль"""
        if not self.current_profile_id:
            show_warning(self.root, "Warning", "Please select a profile to edit")
            return
        
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        if self.security.is_read_only():
            show_warning(self.root, "Access Denied", 
                        "Cannot edit profiles in Read Only mode.\n\n"
                        "Press Ctrl+Shift+F to switch to Full Access mode.")
            return
        
        profile = self.profile_service.get_current_profile()
        if profile:
            ProfileEditor(
                self.root,
                self.profile_service,
                profile=profile,
                callback=self.load_profiles
            )
    
    def delete_profile(self):
        """Удаляет выбранный профиль"""
        if not self.current_profile_id:
            show_warning(self.root, "Warning", "No profile selected")
            return
        
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        if self.security.is_read_only():
            show_warning(self.root, "Access Denied", 
                        "Cannot delete profiles in Read Only mode.\n\n"
                        "Press Ctrl+Shift+F to switch to Full Access mode.")
            return
        
        profile = self.profile_service.get_current_profile()
        if not profile:
            show_error(self.root, "Error", "Profile not found")
            return
        
        # Подсчитываем инструменты
        tools_count = self.profile_service.count_tools(profile.id)
        
        # Формируем сообщение
        message = f"Delete profile '{profile.name}'?"
        if tools_count > 0:
            message += f"\n\n⚠️ WARNING: {tools_count} tool(s) will also be deleted!"
            message += "\n\nAll tools assigned to this profile will be permanently deleted."
        
        if ask_yesno(self.root, "Confirm Delete", message):
            try:
                success = self.profile_service.delete_profile(profile.id)
                if success:
                    show_info(self.root, "Success", 
                             f"Profile '{profile.name}' deleted successfully")
            except Exception as e:
                show_error(self.root, "Error", f"Failed to delete profile: {e}")
    
    def assign_tool(self):
        """Открывает форму назначения инструмента"""
        if not self.current_profile_id:
            show_warning(self.root, "Warning", "No profile selected")
            return
        
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        if self.security.is_read_only():
            show_warning(self.root, "Access Denied", 
                        "Cannot assign tools in Read Only mode.\n\n"
                        "Press Ctrl+Shift+F to switch to Full Access mode.")
            return
        
        selection = self.tools_tree.selection()
        if not selection:
            show_warning(self.root, "Warning", "Please select a milling head")
            return
        
        item = self.tools_tree.item(selection[0])
        head_number = item["values"][0]
        
        self._show_tool_selector(head_number, 
                               self.root.winfo_pointerx(),
                               self.root.winfo_pointery())
   
    def manage_profile_tools(self):
        """Открывает управление инструментами профиля"""
        if not self.current_profile_id:
            show_warning(self.root, "Warning", "Please select a profile first")
            return
        
        # ИЗМЕНЯЕМ: В READ ONLY режиме разрешаем просмотр инструментов профиля
        read_only = self.security.is_read_only()
        
        ToolManager(
            self.root,
            self.profile_service,
            self.tool_service,
            self.current_profile_id,
            callback=self.load_profile_tools,
            read_only=read_only  # Передаем режим только для чтения
        )
    
    def open_global_library(self):
        """Открывает глобальную библиотеку инструментов"""
        # ИЗМЕНЯЕМ: В READ ONLY режиме разрешаем просмотр библиотеки инструментов
        read_only = self.security.is_read_only()
        
        # Если в режиме READ ONLY, показываем информационное сообщение
        if read_only:
            show_info(self.root, "Information", 
                     "Opening Global Tool Library in READ ONLY mode.\n"
                     "You can view all tools but cannot modify them.")
        
        ToolManager(
            self.root,
            self.profile_service,
            self.tool_service,
            callback=self.load_profile_tools,
            read_only=read_only  # Передаем режим только для чтения
        )
    
    def save_all(self):
        """Сохраняет текущую конфигурацию"""
        if not self.current_profile_id:
            show_warning(self.root, "Warning", "Please select a profile first")
            return
        
        # SAVE JOB должен быть доступен в любом режиме
        # (это операция чтения/экспорта, а не записи)
        profile = self.profile_service.get_current_profile()
        if not profile:
            return
        
        try:
            # Get all tool assignments
            assignments = self.tool_service.get_tool_assignments(self.current_profile_id)
            tools = []
            
            # Prepare tool log entries
            for head_num in range(1, 11):  # For all 10 heads
                head_name = self.head_names.get(head_num, f"Head {head_num}")
                
                if head_num in assignments:
                    assignment = assignments[head_num]
                    tool = self.tool_service.get_tool(assignment.tool_id)
                    
                    if tool:
                        tools.append(ToolLogEntry(
                            head_number=head_num,
                            head_name=head_name,
                            tool_type=tool.tool_type or "-",
                            tool_code=tool.code or "-",
                            rpm=assignment.rpm,
                            pass_depth=assignment.pass_depth
                        ))
                        continue
                
                # Add empty tool entry if no assignment or tool found
                tools.append(ToolLogEntry(
                    head_number=head_num,
                    head_name=head_name,
                    tool_type="[Empty]",
                    tool_code="-",
                    rpm=None,
                    pass_depth=None
                ))
            
            # Log the configuration
            from utils.logger import log_job_configuration
            
            if log_job_configuration(
                profile_name=profile.name,
                feed_rate=profile.feed_rate or 0,
                material_size=profile.material_size or "N/A",
                product_size=profile.product_size or "N/A",
                tools=tools,
                action_type="JOB"  # Set action type for SAVE JOB
            ):
                show_info(self.root, "Success", "Job configuration saved to log")
            else:
                show_warning(self.root, "Warning", "Failed to save job log")
                
        except Exception as e:
            show_error(self.root, "Error", f"Failed to save job configuration: {str(e)}")
    
    # НОВЫЙ МЕТОД ДЛЯ ОБНОВЛЕНИЯ ИНТЕРФЕЙСА ПРИ СМЕНЕ РЕЖИМА
    def on_security_mode_change(self):
        """Вызывается при изменении режима безопасности"""
        self.update_ui_for_security_mode()
        logger.info(f"Security mode changed to: {'READ ONLY' if self.security.is_read_only() else 'FULL ACCESS'}")
    
    def update_ui_for_security_mode(self):
        """Обновляет интерфейс в зависимости от текущего режима безопасности"""
        is_read_only = self.security.is_read_only()
        
        # Обновляем индикатор режима
        if self.security_mode_label:
            if is_read_only:
                self.security_mode_label.config(
                    text="[READ ONLY]",
                    fg='green'  # Зеленый для READ ONLY
                )
            else:
                self.security_mode_label.config(
                    text="[FULL ACCESS]",
                    fg='red'    # Красный для FULL ACCESS
                )
        
        # Обновляем состояние кнопок
        button_state = tk.NORMAL if not is_read_only else tk.DISABLED
        
        # Кнопки профилей (доступны только в FULL ACCESS)
        if hasattr(self, 'add_profile_btn'):
            self.add_profile_btn.config(state=button_state)
        if hasattr(self, 'edit_profile_btn'):
            self.edit_profile_btn.config(state=button_state)
        if hasattr(self, 'delete_profile_btn'):
            self.delete_profile_btn.config(state=button_state)
        
        # Кнопки инструментов (доступны только в FULL ACCESS)
        if hasattr(self, 'assign_tool_btn'):
            self.assign_tool_btn.config(state=button_state)
        if hasattr(self, 'manage_tools_btn'):
            # В READ ONLY режиме кнопка должна быть активна для просмотра
            self.manage_tools_btn.config(state=tk.NORMAL)
            if is_read_only:
                self.manage_tools_btn.config(
                    bg='#CCCCCC',  # Серый цвет для READ ONLY
                    activebackground='#999999'
                )
            else:
                self.manage_tools_btn.config(
                    bg='#FF9800',  # Оранжевый цвет для FULL ACCESS
                    activebackground='darkorange'
                )
        
        if hasattr(self, 'library_btn'):
            # В READ ONLY режиме кнопка должна быть активна для просмотра
            self.library_btn.config(state=tk.NORMAL)
            if is_read_only:
                self.library_btn.config(
                    bg='#CCCCCC',  # Серый цвет для READ ONLY
                    activebackground='#999999'
                )
            else:
                self.library_btn.config(
                    bg='#9C27B0',  # Фиолетовый цвет для FULL ACCESS
                    activebackground='darkviolet'
                )
        
        # Кнопка SAVE JOB всегда доступна (голубой цвет)
        if hasattr(self, 'save_job_btn'):
            self.save_job_btn.config(state=tk.NORMAL)
            self.save_job_btn.config(
                bg='#00BCD4',  # Голубый цвет
                activebackground='darkcyan'
            )
    
    # НОВЫЕ МЕТОДЫ ДЛЯ ПЕРЕКЛЮЧЕНИЯ РЕЖИМА БЕЗОПАСНОСТИ
    def toggle_security_mode(self, event=None):
        """Переключение режима безопасности"""
        print(f"DEBUG: toggle_security_mode called")
        print(f"DEBUG: Before - is_read_only: {self.security.is_read_only()}")
        
        # Переключаем режим
        self.security.toggle_security_mode()
        
        print(f"DEBUG: After - is_read_only: {self.security.is_read_only()}")
        print(f"DEBUG: Current mode: {self.security.get_current_mode()}")
        
        # Обновляем интерфейс
        self.on_security_mode_change()
        
        # Показываем сообщение пользователю
        mode_text = "Read Only" if self.security.is_read_only() else "Full Access"
        from tkinter import messagebox
        messagebox.showinfo("Security Mode", f"Switched to {mode_text} mode")
    
    def set_security_mode(self, mode: str):
        """Устанавливает конкретный режим безопасности"""
        if mode == 'full_access':
            self.security.set_full_access()
        elif mode == 'read_only':
            self.security.set_read_only()
        else:
            return
        
        # Обновляем интерфейс
        self.on_security_mode_change()
        
        # Показываем сообщение
        mode_text = "Full Access" if not self.security.is_read_only() else "Read Only"
        from tkinter import messagebox
        messagebox.showinfo("Security Mode", f"Switched to {mode_text} mode")


class ToolImageViewer(tk.Toplevel):
    def __init__(self, parent, tool, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.tool = tool
        self._setup_ui()
        
    def _setup_ui(self):
        self.title(f"Tool Image - {self.tool.code or 'Unnamed Tool'}")
        
        # Make the window modal
        self.transient(self.parent)
        self.grab_set()
        
        # Create a frame to hold the content
        content_frame = ttk.Frame(self)
        content_frame.pack(padx=10, pady=10)
        
        try:
            from PIL import Image, ImageTk
            import io
            
            # Load and resize the image
            img = Image.open(io.BytesIO(self.tool.photo))
            max_size = (800, 600)
            img.thumbnail(max_size, RESAMPLE)
            
            # Convert to Tkinter format
            self.photo = ImageTk.PhotoImage(img)
            
            # Create and pack the image label
            img_label = ttk.Label(content_frame, image=self.photo)
            img_label.pack(padx=10, pady=10)
                                    
            # Bind Escape key to close
            self.bind('<Escape>', lambda e: self.destroy())
            
            # Center the window on screen
            self.update_idletasks()
            width = img.width + 40
            height = img.height + 100
            x = (self.winfo_screenwidth() - width) // 2
            y = (self.winfo_screenheight() - height) // 2
            self.geometry(f"{width}x{height}+{x}+{y}")
            
            # Set focus to the window
            self.focus_force()
            
        except ImportError:
            show_error(self, "Error", "Pillow library is required to display images")
        except Exception as e:
            logger.error(f"Error displaying tool image: {e}")
            show_error(self, "Error", f"Could not display image: {e}")