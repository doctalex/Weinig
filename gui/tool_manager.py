"""
Менеджер инструментов (глобальный и профильный)
"""
import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, List
from PIL import Image
RESAMPLE = getattr(Image, 'Resampling', Image).LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS
from core.models import Tool
from services.profile_service import ProfileService
from services.tool_service import ToolService
from gui.base.dialogs import show_error, show_info, ask_yesno
from gui.tool_editor import ToolEditor

logger = logging.getLogger(__name__)

class ToolManager:
    """Окно управления инструментами"""
    
    def __init__(self, parent, profile_service: ProfileService,
                 tool_service: ToolService, profile_id: Optional[int] = None,
                 callback: Optional[callable] = None, read_only: bool = False):
        """
        Args:
            parent: Родительское окно
            profile_service: Сервис профилей
            tool_service: Сервис инструментов
            profile_id: ID профиля или None для глобального режима
            callback: Коллбек после сохранения
            read_only: Режим только для чтения
        """
        self.parent = parent
        self.profile_service = profile_service
        self.tool_service = tool_service
        self.profile_id = profile_id
        self.callback = callback
        self.read_only = read_only  # Режим только для чтения
        
        # Initialize filter variables
        self.filter_var = tk.StringVar(value="ALL")
        self.search_var = tk.StringVar()
        self.all_items = []  # Track all item IDs separately
        
        self.setup_ui()
        self.load_tools()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        # Создание окна
        self.window = tk.Toplevel(self.parent)
        
        # Set a custom style for this window's Treeview
        style = ttk.Style()
        style.configure("ToolManager.Treeview", 
                       font=('Arial', 10),
                       rowheight=25)
        style.configure("ToolManager.Treeview.Heading", 
                       font=('Arial', 10, 'bold'))
        
        # Заголовок
        title = "Tool Management"
        if self.profile_id:
            profile = self.profile_service.get_profile(self.profile_id)
            if profile:
                title = f"Tools for Profile: {profile.name}"
        else:
            title = "Global Tool Library"
        
        # Добавляем индикатор READ ONLY
        if self.read_only:
            title += " [READ ONLY]"
        
        self.window.title(title)
        self.window.geometry("1000x600")
        
        # Делаем модальным
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.focus_set()
        
        # Основной фрейм
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Панель фильтров и поиска
        self._setup_filters(main_frame)
        
        # Таблица инструментов
        self._setup_table(main_frame)
        
        # Статистика (только для профиля)
        if self.profile_id:
            self._setup_statistics(main_frame)
        
        # Центрируем
        self.center_window()
    
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
    
    def _setup_filters(self, parent):
        """Настройка панели фильтров"""
        filter_frame = ttk.LabelFrame(parent, text="Filters & Search", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Main filter frame
        filter_buttons_frame = ttk.Frame(filter_frame)
        filter_buttons_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Position filter frame
        pos_frame = ttk.LabelFrame(filter_buttons_frame, text="Position", padding=(5, 2))
        pos_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Position filter options
        pos_options = [
            ("All", "ALL"),
            ("Bottom", "Bottom"),
            ("Top", "Top"),
            ("Right", "Right"),
            ("Left", "Left")
        ]
        
        self.pos_var = tk.StringVar(value="ALL")
        for text, value in pos_options:
            btn = ttk.Radiobutton(
                pos_frame,
                text=text,
                variable=self.pos_var,
                value=value,
                command=self.apply_filters
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # Status filter frame
        status_frame = ttk.LabelFrame(filter_buttons_frame, text="Status", padding=(5, 2))
        status_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Status filter options
        status_options = [
            ("All", "ALL"),
            ("Ready", "ready"),
            ("Worn", "worn"),
            ("In Service", "in_service")
        ]
        
        self.status_var = tk.StringVar(value="ALL")
        for text, value in status_options:
            btn = ttk.Radiobutton(
                status_frame,
                text=text,
                variable=self.status_var,
                value=value,
                command=self.apply_filters
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # Search frame
        search_frame = ttk.Frame(filter_frame)
        search_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind("<KeyRelease>", self.on_search)
        
        # Add tool button (скрываем в READ ONLY режиме)
        if not self.read_only:
            ttk.Button(
                filter_frame, 
                text="+ Add New Tool",
                command=self.add_tool
            ).pack(side=tk.RIGHT, padx=(10, 0))
    
    def _setup_table(self, parent):
        """Настройка таблицы инструментов"""
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Создание Treeview с кастомным стилем
        self.tools_tree = ttk.Treeview(
            table_frame,
            columns=("image", "code", "profile", "position", "type", "set", "knives", "status"),
            show="headings",
            selectmode="browse",
            style="ToolManager.Treeview"
        )
        
        # Настройка колонок
        self.tools_tree.column("#0", width=0, stretch=tk.NO)  # Скрытая колонка для ID
        self.tools_tree.column("image", width=30, anchor=tk.CENTER, stretch=tk.NO)
        self.tools_tree.column("code", width=100, anchor=tk.CENTER)
        self.tools_tree.column("profile", width=100, anchor=tk.CENTER)
        self.tools_tree.column("position", width=80, anchor=tk.CENTER)
        self.tools_tree.column("type", width=100, anchor=tk.CENTER)
        self.tools_tree.column("set", width=60, anchor=tk.CENTER)
        self.tools_tree.column("knives", width=60, anchor=tk.CENTER)
        self.tools_tree.column("status", width=100, anchor=tk.CENTER)
        # Настройка заголовков
        self.tools_tree.heading("image", text="", anchor=tk.CENTER)
        self.tools_tree.heading("code", text="Tool Code", anchor=tk.CENTER)
        self.tools_tree.heading("profile", text="Profile", anchor=tk.CENTER)
        self.tools_tree.heading("position", text="Position", anchor=tk.CENTER)
        self.tools_tree.heading("type", text="Type", anchor=tk.CENTER)
        self.tools_tree.heading("set", text="Set", anchor=tk.CENTER)
        self.tools_tree.heading("knives", text="Knives", anchor=tk.CENTER)
        self.tools_tree.heading("status", text="Status", anchor=tk.CENTER)

        # Добавление прокрутки
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", 
                                   command=self.tools_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal",
                                   command=self.tools_tree.xview)
        
        self.tools_tree.configure(yscrollcommand=v_scrollbar.set, 
                                 xscrollcommand=h_scrollbar.set)
        
        # Размещение элементов
        self.tools_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew", columnspan=2)
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Настройка стилей
        style = ttk.Style()
        # Configure the specific style for this Treeview
        style.configure("ToolManager.Treeview", 
                       font=('Arial', 10),
                       rowheight=25)
        style.configure("ToolManager.Treeview.Heading", 
                       font=('Arial', 10, 'bold'),
                       background="#f0f0f0")
        
        # Explicitly set the font for the Treeview and its headings
        self.tools_tree.configure(style="ToolManager.Treeview")
        
        # Настройка тегов
        self.tools_tree.tag_configure("ready", foreground="#2e7d32")
        self.tools_tree.tag_configure("worn", foreground="#d32f2f")
        self.tools_tree.tag_configure("in_service", foreground="#f57c00")
        
        # Привязка событий
        self.tools_tree.bind("<Double-1>", self.on_double_click)
        self.tools_tree.bind("<Button-1>", self.on_single_click)
        
        # Контекстное меню (меняем в зависимости от режима)
        self.context_menu = tk.Menu(self.window, tearoff=0)
        
        if not self.read_only:
            self.context_menu.add_command(label="Edit Tool", 
                                         command=self.edit_selected_tool)
            self.context_menu.add_command(label="Delete Tool", 
                                         command=self.delete_selected_tool)
        
        self.context_menu.add_command(label="View Image",
                                    command=self.view_tool_image,
                                    state='disabled')
        self.context_menu.add_separator()
        self.context_menu.add_command(label="View Details",
                                    command=self.view_tool_details)
        
        self.tools_tree.bind("<Button-3>", self.show_context_menu)
        
        # Переменная для хранения выбранного инструмента
        self.selected_tool = None
    
    def _setup_statistics(self, parent):
        """Настройка панели статистики"""
        stats_frame = ttk.LabelFrame(parent, text="Tool Statistics", padding="5")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Здесь будет статистика
        self.stats_label = ttk.Label(stats_frame, text="")
        # Обновляем статистику
        self.update_statistics()
    
    def load_tools(self):
        """Загружает инструменты в таблицу - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        # Очищаем таблицу
        for item in self.tools_tree.get_children():
            self.tools_tree.delete(item)
        self.all_items = []  # Сбрасываем список всех элементов
        
        # Получаем инструменты
        if self.profile_id:
            # Режим профиля: получаем инструменты только этого профиля
            tools = self.tool_service.get_tools_by_profile(self.profile_id)
        else:
            # Глобальный режим: получаем ВСЕ инструменты из базы
            # Используем новый метод или исправляем существующий
            try:
                # Способ 1: Используем прямой доступ к базе через сервис
                tools = self.tool_service.get_all_tools()
            except AttributeError:
                # Способ 2: Если метода нет, используем обходной путь
                tools = self._get_all_tools_fallback()
        
        if not tools:
            logger.warning(f"No tools found. Profile ID: {self.profile_id}")
            # Можно показать информационное сообщение
            if len(self.tools_tree.get_children()) == 0:
                self.tools_tree.insert("", "end", values=("", "No tools found", "", "", "", "", "", ""))
            return
        
        # Добавляем инструменты в таблицу
        for tool in tools:
            # Получаем имя профиля
            profile_name = "Unassigned"
            if tool.profile_id:
                profile = self.profile_service.get_profile(tool.profile_id)
                if profile:
                    profile_name = profile.name
            
            # Форматируем статус
            status_map = {
                'ready': ' Ready',
                'worn': ' Worn',
                'in_service': ' In Service'
            }
            status_display = status_map.get(tool.status, tool.status)
            tags = (tool.status,)
            
            # Добавляем иконку изображения если есть фото
            image_icon = "🖼️" if tool.photo else ""
            
            # Добавляем в таблицу и сохраняем ID элемента
            item_id = self.tools_tree.insert(
                "", "end",
                values=(
                    image_icon,  # Иконка изображения
                    tool.code,
                    profile_name,
                    tool.position,
                    tool.tool_type,
                    tool.set_number,
                    tool.knives_count,
                    status_display
                ),
                tags=tags
            )
            
            # Сохраняем данные изображения для быстрого доступа
            if tool.photo:
                self.tools_tree.set(item_id, "image", "🖼️")
                self.tools_tree.item(item_id, tags=tags + ('has_image',))
            self.all_items.append(item_id)
        
        # Apply filters after loading tools
        self.apply_filters()
    
    def _get_all_tools_fallback(self):
        """Обходной способ получения всех инструментов, если метода нет"""
        tools = []
        try:
            # Получаем все профили
            profiles = self.profile_service.get_all_profiles()
            for profile in profiles:
                profile_tools = self.tool_service.get_tools_by_profile(profile.id)
                tools.extend(profile_tools)
            
            # Также получаем инструменты без профиля
            # Нужно проверить, есть ли такой метод в tool_service
            if hasattr(self.tool_service, 'get_unassigned_tools'):
                unassigned_tools = self.tool_service.get_unassigned_tools()
                tools.extend(unassigned_tools)
                
        except Exception as e:
            logger.error(f"Error loading all tools: {e}")
        
        return tools
    
    def apply_filters(self):
        """Applies filters to the tools table"""
        pos_filter = self.pos_var.get()
        status_filter = self.status_var.get()
        search_term = self.search_var.get().lower().strip()
        
        # First, make all items visible
        for item in self.all_items:
            self.tools_tree.reattach(item, '', 'end')
        
        # If no filtering needed, we're done
        if pos_filter == "ALL" and status_filter == "ALL" and not search_term:
            return
            
        # Now apply filters
        for item in self.all_items:
            values = self.tools_tree.item(item)["values"]
            item_tags = self.tools_tree.item(item, 'tags')
            
            if not values:
                continue
            
            # Check position filter
            pos_match = True
            if pos_filter != "ALL":
                pos_match = False
                if len(values) > 3 and values[3]:
                    pos_match = (str(values[3]).lower() == pos_filter.lower())
            
            # Check status filter
            status_match = True
            if status_filter != "ALL":
                status_match = status_filter in item_tags
                
            # Check search term in all string values
            search_match = True
            if search_term:
                search_match = any(
                    search_term in str(value).lower() 
                    for value in values 
                    if value is not None
                )

            # Hide row if it doesn't match all active filters and search
            if not (pos_match and status_match and search_match):
                self.tools_tree.detach(item)
    
    def on_search(self, event=None):
        """Handles search input"""
        # Apply filters immediately when search changes
        self.apply_filters()
    
    def update_statistics(self):
        """Обновляет статистику"""
        if not self.profile_id:
            return
        
        stats = self.profile_service.get_profile_statistics(self.profile_id)
        
        stats_text = (
            f"Total Tools: {stats['total_tools']} | "
            f"Knives: {stats['total_knives']} | "
            f"Bottom: {stats['by_position']['Bottom']} | "
            f"Top: {stats['by_position']['Top']} | "
            f"Right: {stats['by_position']['Right']} | "
            f"Left: {stats['by_position']['Left']}"
        )
        
        self.stats_label.config(text=stats_text)
    
    def add_tool(self):
        """Добавляет новый инструмент"""
        if self.read_only:
            show_error(self.window, "Read Only", "Cannot add tools in read-only mode")
            return
            
        ToolEditor(
            self.window,
            self.profile_service,
            self.tool_service,
            self.profile_id,
            callback=self._on_tool_saved
        )
    
    def edit_selected_tool(self, event=None):
        """Редактирует выбранный инструмент"""
        if self.read_only:
            show_error(self.window, "Read Only", "Cannot edit tools in read-only mode")
            return
            
        selection = self.tools_tree.selection()
        if not selection:
            show_error(self.window, "Warning", "Please select a tool to edit")
            return
        
        item = self.tools_tree.item(selection[0])
        values = item["values"]
        
        if not values:
            show_error(self.window, "Error", "No tool data in selected row")
            return
        
        # Находим инструмент по коду
        tool_code = values[1]
        tool = self.tool_service.get_tool_by_code(tool_code)
        
        if not tool:
            show_error(self.window, "Error", f"Tool with code '{tool_code}' not found")
            return
        
        # Открываем редактор
        ToolEditor(
            self.window,
            self.profile_service,
            self.tool_service,
            tool.profile_id,
            tool,
            callback=self._on_tool_saved
        )
    
    def delete_selected_tool(self):
        """Удаляет выбранный инструмент"""
        if self.read_only:
            show_error(self.window, "Read Only", "Cannot delete tools in read-only mode")
            return
            
        selection = self.tools_tree.selection()
        if not selection:
            return
        
        item = self.tools_tree.item(selection[0])
        values = item["values"]
        
        if not values:
            return
        
        tool_code = values[1]
        profile_name = values[2] if len(values) > 2 else "Unknown"
        
        if not ask_yesno(self.window, "Confirm Delete",
                        f"Delete tool '{tool_code}' from profile '{profile_name}'?\n"
                        f"This action cannot be undone."):
            return
        
        # Находим и удаляем инструмент
        tool = self.tool_service.get_tool_by_code(tool_code)
        if not tool:
            show_error(self.window, "Error", "Tool not found")
            return
        
        try:
            success = self.tool_service.delete_tool(tool.id)
            
            if success:
                show_info(self.window, "Success", "Tool deleted successfully")
                self.load_tools()
                self.update_statistics()
                if self.callback:
                    self.callback()
            else:
                show_error(self.window, "Error", "Failed to delete tool")
                
        except Exception as e:
            show_error(self.window, "Error", f"Failed to delete tool: {e}")
    
    def show_context_menu(self, event):
        """Показывает контекстное меню"""
        selection = self.tools_tree.identify_row(event.y)
        if selection:
            self.tools_tree.selection_set(selection)
            
            # Проверяем, есть ли у выбранного инструмента изображение
            item = self.tools_tree.item(selection)
            has_image = 'has_image' in item['tags']
            
            # Активируем/деактивируем пункт меню для просмотра изображения
            self.context_menu.entryconfig("View Image", state='normal' if has_image else 'disabled')
            
            # Показываем контекстное меню
            self.context_menu.tk_popup(event.x_root, event.y_root)
    
    def _on_tool_saved(self):
        """Обработка сохранения инструмента"""
        self.load_tools()
        self.update_statistics()
        if self.callback:
            self.callback()
            
    def on_single_click(self, event):
        """Обработка одиночного клика по строке"""
        region = self.tools_tree.identify_region(event.x, event.y)
        if region == 'cell':
            column = self.tools_tree.identify_column(event.x)
            item = self.tools_tree.identify_row(event.y)
            
            if column == '#1':  # Колонка с изображением
                self.view_tool_image()
                return 'break'  # Предотвращаем дальнейшую обработку события
    
    def on_double_click(self, event):
        """Обработка двойного клика по строке"""
        region = self.tools_tree.identify_region(event.x, event.y)
        if region == 'cell':
            column = self.tools_tree.identify_column(event.x)
            if column != '#1':  # Если клик не по колонке с изображением
                if self.read_only:
                    self.view_tool_details()
                else:
                    self.edit_selected_tool()
                
    def view_tool_image(self):
        """Отображает изображение инструмента в новом окне"""
        selection = self.tools_tree.selection()
        if not selection:
            return

        # Получаем код инструмента из выбранной строки
        item = self.tools_tree.item(selection[0])
        values = item['values']
        if not values or len(values) < 2:
            return

        tool_code = values[1]

        # Находим инструмент по коду
        tool = self.tool_service.get_tool_by_code(tool_code)
        if not tool or not tool.photo:
            show_info(self.window, "No Image", "No image available for this tool")
            return

        try:
            from PIL import Image, ImageTk
            import io

            # Загружаем изображение и обрабатываем его
            img = Image.open(io.BytesIO(tool.photo))
            max_size = (800, 600)
            img.thumbnail(max_size, RESAMPLE)

            # Создаем окно с обычным оформлением Windows
            img_window = tk.Toplevel(self.window)
            img_window.title(f"Tool Image - {tool_code}")
            img_window.transient(self.window)  # Связываем с родительским окном
            img_window.grab_set()  # Делаем окно модальным

            # Конвертируем изображение
            photo = ImageTk.PhotoImage(img)
            
            # Создаем фрейм для содержимого
            content_frame = ttk.Frame(img_window)
            content_frame.pack(padx=10, pady=10)

            # Создаем метку для изображения
            img_label = ttk.Label(content_frame, image=photo)
            img_label.image = photo  # Сохраняем ссылку
            img_label.pack()

            # Обработка нажатия Esc для закрытия
            img_window.bind('<Escape>', lambda e: img_window.destroy())

            # Вычисляем размеры и позицию окна
            img_window.update_idletasks()
            width = content_frame.winfo_reqwidth()
            height = content_frame.winfo_reqheight()
            x = (self.window.winfo_screenwidth() - width) // 2
            y = (self.window.winfo_screenheight() - height) // 2

            # Устанавливаем позицию и размеры
            img_window.geometry(f"{width}x{height}+{x}+{y}")

        except ImportError:
            show_error(self.window, "Ошибка", "Для отображения изображений требуется библиотека Pillow")
        except Exception as e:
            logger.error(f"Ошибка при отображении изображения: {e}")
            show_error(self.window, "Ошибка", f"Не удалось отобразить изображение: {e}")
    
    def view_tool_details(self):
        """Показывает детальную информацию об инструменте (только чтение)"""
        selection = self.tools_tree.selection()
        if not selection:
            show_error(self.window, "Warning", "Please select a tool to view details")
            return
        
        item = self.tools_tree.item(selection[0])
        values = item["values"]
        
        if not values:
            show_error(self.window, "Error", "No tool data in selected row")
            return
        
        # Находим инструмент по коду
        tool_code = values[1]
        tool = self.tool_service.get_tool_by_code(tool_code)
        
        if not tool:
            show_error(self.window, "Error", f"Tool with code '{tool_code}' not found")
            return
        
        # Создаем окно с деталями (только для чтения)
        self._show_tool_details_dialog(tool, values[2] if len(values) > 2 else "Unknown")
    
    def _show_tool_details_dialog(self, tool: Tool, profile_name: str):
        """Показывает диалог с деталями инструмента"""
        details_window = tk.Toplevel(self.window)
        details_window.title(f"Tool Details - {tool.code}")
        details_window.geometry("400x500")
        details_window.transient(self.window)
        details_window.resizable(False, False)
        
        # Основной фрейм
        main_frame = ttk.Frame(details_window, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        ttk.Label(
            main_frame, 
            text=f"Tool: {tool.code}",
            font=("Arial", 14, "bold")
        ).pack(pady=(0, 15))
        
        # Создаем фрейм для деталей
        details_frame = ttk.Frame(main_frame)
        details_frame.pack(fill=tk.BOTH, expand=True)
        
        # Отображаем детали
        details = [
            ("Profile:", profile_name),
            ("Position:", tool.position),
            ("Type:", tool.tool_type),
            ("Set Number:", tool.set_number),
            ("Knives Count:", tool.knives_count),
            ("Status:", tool.status),
            ("Notes:", tool.notes if tool.notes else "N/A"),  # ИСПРАВЛЕНО: используем notes
        ]
        
        for label, value in details:
            row_frame = ttk.Frame(details_frame)
            row_frame.pack(fill=tk.X, pady=3)
            
            ttk.Label(row_frame, text=label, width=15, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(row_frame, text=str(value), anchor=tk.W).pack(side=tk.LEFT, padx=5)
        
        # Кнопка закрытия
        ttk.Button(
            main_frame,
            text="Close",
            command=details_window.destroy,
            width=15
        ).pack(pady=15)
        
        # Центрируем
        details_window.update_idletasks()
        x = (self.window.winfo_screenwidth() - details_window.winfo_width()) // 2
        y = (self.window.winfo_screenheight() - details_window.winfo_height()) // 2
        details_window.geometry(f"+{x}+{y}")
