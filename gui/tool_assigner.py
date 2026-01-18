<<<<<<< HEAD
"""
Назначение инструментов на головы
"""
import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, List

from core.models import Tool
from services.profile_service import ProfileService
from services.tool_service import ToolService
from gui.base.dialogs import show_error, show_info, ask_yesno

logger = logging.getLogger(__name__)

class ToolAssigner:
    """Окно назначения инструментов"""
    
    def __init__(self, parent, profile_service: ProfileService,
                 tool_service: ToolService, profile_id: int, head_number: int,
                 callback: Optional[callable] = None):
        self.parent = parent
        self.profile_service = profile_service
        self.tool_service = tool_service
        self.profile_id = profile_id
        self.head_number = head_number
        self.callback = callback
        
        # Получаем требуемую позицию
        self.required_position = self.tool_service.get_required_position_for_head(head_number)
        
        self.setup_ui()
        self.load_tools()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        # Создание окна
        self.window = tk.Toplevel(self.parent)
        
        # Заголовок
        head_names = self.tool_service.get_head_position_mapping()
        head_name = head_names.get(self.head_number, f"Head {self.head_number}")
        title = f"Assign Tool to {head_name}"
        
        # Добавляем имя профиля если есть
        profile = self.profile_service.get_profile(self.profile_id)
        if profile:
            title = f"Assign Tool to {head_name} - {profile.name}"
        
        self.window.title(title)
        self.window.geometry("500x600")
        
        # Делаем модальным
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.focus_set()
        
        # Основной фрейм
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Информация о требованиях
        self._setup_info(main_frame)
        
        # Список инструментов
        self._setup_tool_list(main_frame)
        
        # Параметры
        self._setup_parameters(main_frame)
        
        # Кнопки
        self._setup_buttons(main_frame)
        
        # Центрируем
        self.center_window()
        
        # Привязка клавиш
        self.window.bind('<Escape>', lambda e: self.window.destroy())
    
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
    
    def _setup_info(self, parent):
        """Настройка информационной панели"""
        info_frame = ttk.LabelFrame(parent, text="Requirements", padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Имя головы
        head_names = self.tool_service.get_head_position_mapping()
        head_name = head_names.get(self.head_number, f"Head {self.head_number}")
        
        ttk.Label(info_frame, text=f"Head: {head_name}",
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=2)
        
        # Требуемая позиция
        ttk.Label(info_frame, text=f"Required position: {self.required_position}",
                 font=("Arial", 10, "bold"), foreground="blue").pack(anchor=tk.W, pady=2)
        
        # Информация о профиле
        profile = self.profile_service.get_profile(self.profile_id)
        if profile:
            ttk.Label(info_frame, text=f"Profile: {profile.name}").pack(anchor=tk.W, pady=2)
    
    def _setup_tool_list(self, parent):
        """Настройка списка инструментов"""
        list_frame = ttk.LabelFrame(parent, text="Available Tools", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Заголовок
        ttk.Label(list_frame, text=f"Select a {self.required_position} tool:",
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # Контейнер для списка и прокрутки
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # Прокрутка
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Список инструментов
        self.tool_listbox = tk.Listbox(
            list_container,
            height=8,
            yscrollcommand=scrollbar.set,
            font=("Arial", 10)
        )
        self.tool_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.tool_listbox.yview)
        
        # Привязка двойного клика
        self.tool_listbox.bind("<Double-Button-1>", lambda e: self.assign())
    
    def _setup_parameters(self, parent):
        """Настройка параметров обработки"""
        params_frame = ttk.LabelFrame(parent, text="Machining Parameters", padding="10")
        params_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Сетка для параметров
        params_frame.grid_columnconfigure(1, weight=1)
        
        # RPM
        ttk.Label(params_frame, text="RPM:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.rpm_var = tk.StringVar(value="8000")
        rpm_entry = ttk.Entry(params_frame, textvariable=self.rpm_var, width=15)
        rpm_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        ttk.Label(params_frame, text="(1000-8000)", 
                 font=("Arial", 8)).grid(row=0, column=2, sticky=tk.W, pady=5, padx=(5, 0))
        
        # Глубина резания
        ttk.Label(params_frame, text="Pass Depth:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.pass_var = tk.StringVar(value="0.5")
        pass_entry = ttk.Entry(params_frame, textvariable=self.pass_var, width=15)
        pass_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        ttk.Label(params_frame, text="mm (0.1-10.0)", 
                 font=("Arial", 8)).grid(row=1, column=2, sticky=tk.W, pady=5, padx=(5, 0))
        
        # Материал
        ttk.Label(params_frame, text="Material:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.material_var = tk.StringVar(value="")
        material_entry = ttk.Entry(params_frame, textvariable=self.material_var, width=25)
        material_entry.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Замечания
        ttk.Label(params_frame, text="Remarks:").grid(row=3, column=0, sticky=tk.NW, pady=5)
        self.remarks_text = tk.Text(params_frame, width=25, height=3)
        self.remarks_text.grid(row=3, column=1, columnspan=2, sticky=tk.W+tk.E, 
                              pady=5, padx=(10, 0))
    
    def _setup_buttons(self, parent):
        """Настройка кнопок"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Assign", 
                  command=self.assign, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=self.window.destroy, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear", 
                  command=self.clear_assignment, width=12).pack(side=tk.RIGHT, padx=5)
    
    def load_tools(self):
        """Загружает доступные инструменты"""
        # Очищаем список
        self.tool_listbox.delete(0, tk.END)
        self.tools = []
        
        # Получаем инструменты для требуемой позиции
        available_tools = self.tool_service.get_available_tools_for_position(
            self.profile_id, self.required_position
        )
        
        # Получаем текущее назначение для этой головы
        assignments = self.tool_service.get_tool_assignments(self.profile_id)
        current_assignment = assignments.get(self.head_number)
        
        # Предварительно заполняем поля, если есть назначение
        if current_assignment:
            # Устанавливаем значения полей
            if current_assignment.rpm:
                self.rpm_var.set(str(current_assignment.rpm))
            if current_assignment.pass_depth:
                self.pass_var.set(str(current_assignment.pass_depth))
            if current_assignment.work_material:
                self.material_var.set(current_assignment.work_material)
            if current_assignment.remarks:
                self.remarks_text.delete("1.0", tk.END)
                self.remarks_text.insert("1.0", current_assignment.remarks)
        
        if not available_tools:
            self.tool_listbox.insert(tk.END, f"No {self.required_position} tools available")
            self.tool_listbox.config(state=tk.DISABLED) 
            return
        
        # Добавляем инструменты в список
        selected_index = 0
        for i, tool in enumerate(available_tools):
            # Форматируем отображение
            status_icon = {
                'ready': '✅',
                'worn': '⚠️',
                'in_service': '🔧'
            }.get(tool.status, '')
            
            display_text = f"{status_icon} {tool.code} - {tool.tool_type} (Set {tool.set_number})"
            self.tool_listbox.insert(tk.END, display_text)
            self.tools.append(tool)
            
            # Если это текущий назначенный инструмент, запоминаем его индекс
            if current_assignment and tool.id == current_assignment.tool_id:
                selected_index = i
        
        # Автоматически выбираем текущий инструмент или первый в списке
        if self.tools:
            self.tool_listbox.selection_set(selected_index)
            self.tool_listbox.see(selected_index)  # Прокручиваем к выбранному элементу
            self.tool_listbox.config(state=tk.NORMAL)
    
    def assign(self):
        """Назначает выбранный инструмент"""
        # Проверяем выбор
        selection = self.tool_listbox.curselection()
        if not selection:
            show_error(self.window, "Warning", "Please select a tool")
            return
        
        index = selection[0]
        tool = self.tools[index]
        
        # Валидация параметров
        rpm = None
        rpm_str = self.rpm_var.get().strip()
        if rpm_str:
            try:
                rpm = int(rpm_str)
                if not 1000 <= rpm <= 8000:
                    show_error(self.window, "Error", "RPM must be between 1000 and 8000")
                    return
            except ValueError:
                show_error(self.window, "Error", "RPM must be a valid number")
                return
        
        pass_depth = None
        pass_str = self.pass_var.get().strip()
        if pass_str:
            try:
                pass_depth = float(pass_str)
                if not 0.1 <= pass_depth <= 10.0:
                    show_error(self.window, "Error", "Pass depth must be between 0.1 and 10.0 mm")
                    return
            except ValueError:
                show_error(self.window, "Error", "Pass depth must be a valid number")
                return
        
        material = self.material_var.get().strip()
        remarks = self.remarks_text.get("1.0", tk.END).strip()
        
        try:
            # Проверяем, не назначен ли инструмент уже на другую голову
            if self.tool_service.is_tool_assigned(tool.id):
                # Получаем текущие назначения
                assignments = self.tool_service.get_tool_assignments(self.profile_id)
                for head_num, assignment in assignments.items():
                    if assignment.tool_id == tool.id and head_num != self.head_number:
                        head_names = self.tool_service.get_head_position_mapping()
                        current_head = head_names.get(head_num, f"Head {head_num}")
                        target_head = head_names.get(self.head_number, f"Head {self.head_number}")
                        
                        response = ask_yesno(
                            self.window,
                            "Tool Already Assigned",
                            f"Tool {tool.code} is already assigned to {current_head}.\n"
                            f"Do you want to move it to {target_head}?"
                        )
                        
                        if not response:
                            return
                        break
            
            # Назначаем инструмент
            success = self.tool_service.assign_tool_to_head(
                self.profile_id,
                self.head_number,
                tool.id,
                rpm,
                pass_depth,
                material,
                remarks
            )
            
            if success:
                head_names = self.tool_service.get_head_position_mapping()
                head_name = head_names.get(self.head_number, f"Head {self.head_number}")
                show_info(self.window, "Success", 
                         f"Tool {tool.code} assigned to {head_name}")
                
                self.window.destroy()
                if self.callback:
                    self.callback()
            else:
                show_error(self.window, "Error", "Failed to assign tool")
                
        except Exception as e:
            show_error(self.window, "Error", f"Failed to assign tool: {e}")
    
    def clear_assignment(self):
        """Очищает назначение на этой голове"""
        head_names = self.tool_service.get_head_position_mapping()
        head_name = head_names.get(self.head_number, f"Head {self.head_number}")
        
        if not ask_yesno(self.window, "Confirm Clear",
                        f"Clear assignment from {head_name}?"):
            return
        
        try:
            success = self.tool_service.clear_head_assignment(
                self.profile_id, self.head_number
            )
            
            if success:
                show_info(self.window, "Success", 
                         f"Assignment cleared from {head_name}")
                
                self.window.destroy()
                if self.callback:
                    self.callback()
            else:
                show_error(self.window, "Error", "Failed to clear assignment")
                
        except Exception as e:
=======
"""
Назначение инструментов на головы
"""
import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, List

from core.models import Tool
from services.profile_service import ProfileService
from services.tool_service import ToolService
from gui.base.dialogs import show_error, show_info, ask_yesno

logger = logging.getLogger(__name__)

class ToolAssigner:
    """Окно назначения инструментов"""
    
    def __init__(self, parent, profile_service: ProfileService,
                 tool_service: ToolService, profile_id: int, head_number: int,
                 callback: Optional[callable] = None):
        self.parent = parent
        self.profile_service = profile_service
        self.tool_service = tool_service
        self.profile_id = profile_id
        self.head_number = head_number
        self.callback = callback
        
        # Получаем требуемую позицию
        self.required_position = self.tool_service.get_required_position_for_head(head_number)
        
        self.setup_ui()
        self.load_tools()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        # Создание окна
        self.window = tk.Toplevel(self.parent)
        
        # Заголовок
        head_names = self.tool_service.get_head_position_mapping()
        head_name = head_names.get(self.head_number, f"Head {self.head_number}")
        title = f"Assign Tool to {head_name}"
        
        # Добавляем имя профиля если есть
        profile = self.profile_service.get_profile(self.profile_id)
        if profile:
            title = f"Assign Tool to {head_name} - {profile.name}"
        
        self.window.title(title)
        self.window.geometry("500x600")
        
        # Делаем модальным
        self.window.transient(self.parent)
        self.window.grab_set()
        self.window.focus_set()
        
        # Основной фрейм
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Информация о требованиях
        self._setup_info(main_frame)
        
        # Список инструментов
        self._setup_tool_list(main_frame)
        
        # Параметры
        self._setup_parameters(main_frame)
        
        # Кнопки
        self._setup_buttons(main_frame)
        
        # Центрируем
        self.center_window()
        
        # Привязка клавиш
        self.window.bind('<Escape>', lambda e: self.window.destroy())
    
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
    
    def _setup_info(self, parent):
        """Настройка информационной панели"""
        info_frame = ttk.LabelFrame(parent, text="Requirements", padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Имя головы
        head_names = self.tool_service.get_head_position_mapping()
        head_name = head_names.get(self.head_number, f"Head {self.head_number}")
        
        ttk.Label(info_frame, text=f"Head: {head_name}",
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=2)
        
        # Требуемая позиция
        ttk.Label(info_frame, text=f"Required position: {self.required_position}",
                 font=("Arial", 10, "bold"), foreground="blue").pack(anchor=tk.W, pady=2)
        
        # Информация о профиле
        profile = self.profile_service.get_profile(self.profile_id)
        if profile:
            ttk.Label(info_frame, text=f"Profile: {profile.name}").pack(anchor=tk.W, pady=2)
    
    def _setup_tool_list(self, parent):
        """Настройка списка инструментов"""
        list_frame = ttk.LabelFrame(parent, text="Available Tools", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Заголовок
        ttk.Label(list_frame, text=f"Select a {self.required_position} tool:",
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # Контейнер для списка и прокрутки
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # Прокрутка
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Список инструментов
        self.tool_listbox = tk.Listbox(
            list_container,
            height=8,
            yscrollcommand=scrollbar.set,
            font=("Arial", 10)
        )
        self.tool_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.tool_listbox.yview)
        
        # Привязка двойного клика
        self.tool_listbox.bind("<Double-Button-1>", lambda e: self.assign())
    
    def _setup_parameters(self, parent):
        """Настройка параметров обработки"""
        params_frame = ttk.LabelFrame(parent, text="Machining Parameters", padding="10")
        params_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Сетка для параметров
        params_frame.grid_columnconfigure(1, weight=1)
        
        # RPM
        ttk.Label(params_frame, text="RPM:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.rpm_var = tk.StringVar(value="8000")
        rpm_entry = ttk.Entry(params_frame, textvariable=self.rpm_var, width=15)
        rpm_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        ttk.Label(params_frame, text="(1000-8000)", 
                 font=("Arial", 8)).grid(row=0, column=2, sticky=tk.W, pady=5, padx=(5, 0))
        
        # Глубина резания
        ttk.Label(params_frame, text="Pass Depth:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.pass_var = tk.StringVar(value="0.5")
        pass_entry = ttk.Entry(params_frame, textvariable=self.pass_var, width=15)
        pass_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        ttk.Label(params_frame, text="mm (0.1-10.0)", 
                 font=("Arial", 8)).grid(row=1, column=2, sticky=tk.W, pady=5, padx=(5, 0))
        
        # Материал
        ttk.Label(params_frame, text="Material:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.material_var = tk.StringVar(value="")
        material_entry = ttk.Entry(params_frame, textvariable=self.material_var, width=25)
        material_entry.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Замечания
        ttk.Label(params_frame, text="Remarks:").grid(row=3, column=0, sticky=tk.NW, pady=5)
        self.remarks_text = tk.Text(params_frame, width=25, height=3)
        self.remarks_text.grid(row=3, column=1, columnspan=2, sticky=tk.W+tk.E, 
                              pady=5, padx=(10, 0))
    
    def _setup_buttons(self, parent):
        """Настройка кнопок"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Assign", 
                  command=self.assign, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=self.window.destroy, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear", 
                  command=self.clear_assignment, width=12).pack(side=tk.RIGHT, padx=5)
    
    def load_tools(self):
        """Загружает доступные инструменты"""
        # Очищаем список
        self.tool_listbox.delete(0, tk.END)
        self.tools = []
        
        # Получаем инструменты для требуемой позиции
        available_tools = self.tool_service.get_available_tools_for_position(
            self.profile_id, self.required_position
        )
        
        # Получаем текущее назначение для этой головы
        assignments = self.tool_service.get_tool_assignments(self.profile_id)
        current_assignment = assignments.get(self.head_number)
        
        # Предварительно заполняем поля, если есть назначение
        if current_assignment:
            # Устанавливаем значения полей
            if current_assignment.rpm:
                self.rpm_var.set(str(current_assignment.rpm))
            if current_assignment.pass_depth:
                self.pass_var.set(str(current_assignment.pass_depth))
            if current_assignment.work_material:
                self.material_var.set(current_assignment.work_material)
            if current_assignment.remarks:
                self.remarks_text.delete("1.0", tk.END)
                self.remarks_text.insert("1.0", current_assignment.remarks)
        
        if not available_tools:
            self.tool_listbox.insert(tk.END, f"No {self.required_position} tools available")
            self.tool_listbox.config(state=tk.DISABLED) 
            return
        
        # Добавляем инструменты в список
        selected_index = 0
        for i, tool in enumerate(available_tools):
            # Форматируем отображение
            status_icon = {
                'ready': '✅',
                'worn': '⚠️',
                'in_service': '🔧'
            }.get(tool.status, '')
            
            display_text = f"{status_icon} {tool.code} - {tool.tool_type} (Set {tool.set_number})"
            self.tool_listbox.insert(tk.END, display_text)
            self.tools.append(tool)
            
            # Если это текущий назначенный инструмент, запоминаем его индекс
            if current_assignment and tool.id == current_assignment.tool_id:
                selected_index = i
        
        # Автоматически выбираем текущий инструмент или первый в списке
        if self.tools:
            self.tool_listbox.selection_set(selected_index)
            self.tool_listbox.see(selected_index)  # Прокручиваем к выбранному элементу
            self.tool_listbox.config(state=tk.NORMAL)
    
    def assign(self):
        """Назначает выбранный инструмент"""
        # Проверяем выбор
        selection = self.tool_listbox.curselection()
        if not selection:
            show_error(self.window, "Warning", "Please select a tool")
            return
        
        index = selection[0]
        tool = self.tools[index]
        
        # Валидация параметров
        rpm = None
        rpm_str = self.rpm_var.get().strip()
        if rpm_str:
            try:
                rpm = int(rpm_str)
                if not 1000 <= rpm <= 8000:
                    show_error(self.window, "Error", "RPM must be between 1000 and 8000")
                    return
            except ValueError:
                show_error(self.window, "Error", "RPM must be a valid number")
                return
        
        pass_depth = None
        pass_str = self.pass_var.get().strip()
        if pass_str:
            try:
                pass_depth = float(pass_str)
                if not 0.1 <= pass_depth <= 10.0:
                    show_error(self.window, "Error", "Pass depth must be between 0.1 and 10.0 mm")
                    return
            except ValueError:
                show_error(self.window, "Error", "Pass depth must be a valid number")
                return
        
        material = self.material_var.get().strip()
        remarks = self.remarks_text.get("1.0", tk.END).strip()
        
        try:
            # Проверяем, не назначен ли инструмент уже на другую голову
            if self.tool_service.is_tool_assigned(tool.id):
                # Получаем текущие назначения
                assignments = self.tool_service.get_tool_assignments(self.profile_id)
                for head_num, assignment in assignments.items():
                    if assignment.tool_id == tool.id and head_num != self.head_number:
                        head_names = self.tool_service.get_head_position_mapping()
                        current_head = head_names.get(head_num, f"Head {head_num}")
                        target_head = head_names.get(self.head_number, f"Head {self.head_number}")
                        
                        response = ask_yesno(
                            self.window,
                            "Tool Already Assigned",
                            f"Tool {tool.code} is already assigned to {current_head}.\n"
                            f"Do you want to move it to {target_head}?"
                        )
                        
                        if not response:
                            return
                        break
            
            # Назначаем инструмент
            success = self.tool_service.assign_tool_to_head(
                self.profile_id,
                self.head_number,
                tool.id,
                rpm,
                pass_depth,
                material,
                remarks
            )
            
            if success:
                head_names = self.tool_service.get_head_position_mapping()
                head_name = head_names.get(self.head_number, f"Head {self.head_number}")
                show_info(self.window, "Success", 
                         f"Tool {tool.code} assigned to {head_name}")
                
                self.window.destroy()
                if self.callback:
                    self.callback()
            else:
                show_error(self.window, "Error", "Failed to assign tool")
                
        except Exception as e:
            show_error(self.window, "Error", f"Failed to assign tool: {e}")
    
    def clear_assignment(self):
        """Очищает назначение на этой голове"""
        head_names = self.tool_service.get_head_position_mapping()
        head_name = head_names.get(self.head_number, f"Head {self.head_number}")
        
        if not ask_yesno(self.window, "Confirm Clear",
                        f"Clear assignment from {head_name}?"):
            return
        
        try:
            success = self.tool_service.clear_head_assignment(
                self.profile_id, self.head_number
            )
            
            if success:
                show_info(self.window, "Success", 
                         f"Assignment cleared from {head_name}")
                
                self.window.destroy()
                if self.callback:
                    self.callback()
            else:
                show_error(self.window, "Error", "Failed to clear assignment")
                
        except Exception as e:
>>>>>>> temp
            show_error(self.window, "Error", f"Failed to clear assignment: {e}")