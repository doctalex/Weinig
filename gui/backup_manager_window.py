"""
Backup Manager Window
"""
import tkinter as tk
from tkinter import ttk, messagebox
import logging
import os
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)

class BackupManagerWindow:
    """Окно управления резервными копиями"""
    
    def __init__(self, parent, backup_manager):
        self.parent = parent
        self.backup_manager = backup_manager
        
        self.window = tk.Toplevel(parent)
        self.window.title("Database Backup Manager")
        self.window.geometry("700x650")  # Увеличили высоту
        self.window.minsize(600, 550)    # Минимальный размер
        
        # Центрируем
        self.center_window()
        
        self.setup_ui()
        self.load_backups()
        
        # Модальное окно
        self.window.transient(parent)
        self.window.grab_set()
        self.window.focus_set()
    
    def center_window(self):
        """Центрирует окно"""
        self.window.update_idletasks()
        width = 700
        height = 650
        
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Настройка интерфейса"""
        # Main container with scrollbar
        main_container = ttk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas for scrollable content
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        
        # Scrollable frame
        self.main_frame = ttk.Frame(canvas)
        
        # Configure scroll
        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            
        self.main_frame.bind("<Configure>", configure_scroll)
        
        # Create window in canvas
        canvas.create_window((0, 0), window=self.main_frame, anchor="nw", width=canvas.winfo_width())
        
        # Configure canvas
        def configure_canvas(event):
            canvas.itemconfig(1, width=event.width)
            
        canvas.bind('<Configure>', configure_canvas)
        
        # Pack canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mouse wheel scrolling
        def on_mouse_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
        canvas.bind_all("<MouseWheel>", on_mouse_wheel)
        
        # Header
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        ttk.Label(
            header_frame,
            text="📦 DATABASE BACKUP MANAGER",
            font=("Arial", 14, "bold")
        ).pack(anchor=tk.W)
        
        # Control buttons frame
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        ttk.Button(
            control_frame,
            text="🔄 Create New Backup",
            command=self.create_backup,
            width=22
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            control_frame,
            text="📂 Open Backup Folder",
            command=self.open_backup_folder,
            width=22
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            control_frame,
            text="🔄 Refresh List",
            command=self.load_backups,
            width=22
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            control_frame,
            text="🧹 Clean Temp Files",
            command=self.cleanup_temp_files,
            width=18
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # Stats frame
        self.stats_frame = ttk.LabelFrame(self.main_frame, text="Backup Statistics", padding="15")
        self.stats_frame.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        # Stats content will be added in load_backups()
        
        # Backups list frame
        list_frame = ttk.LabelFrame(self.main_frame, text="Available Backups", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15), padx=10)
        
        # Create Treeview with scrollbar inside list_frame
        tree_container = ttk.Frame(list_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # Treeview
        self.backup_tree = ttk.Treeview(
            tree_container,
            columns=("name", "size", "date", "type"),
            show="headings",
            height=12  # Увеличили высоту
        )
        
        # Configure columns
        self.backup_tree.heading("name", text="Backup File")
        self.backup_tree.heading("size", text="Size (MB)")
        self.backup_tree.heading("date", text="Created")
        self.backup_tree.heading("type", text="Type")
        
        self.backup_tree.column("name", width=300, anchor=tk.W)
        self.backup_tree.column("size", width=80, anchor=tk.CENTER)
        self.backup_tree.column("date", width=150, anchor=tk.W)
        self.backup_tree.column("type", width=80, anchor=tk.CENTER)
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.backup_tree.yview)
        self.backup_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # Pack treeview and scrollbar
        self.backup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons frame (ВИДИМАЯ, внизу основного фрейма)
        action_frame = ttk.Frame(self.main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
        
        # Left side buttons
        left_btn_frame = ttk.Frame(action_frame)
        left_btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            left_btn_frame,
            text="📥 Restore Selected",
            command=self.restore_selected,
            width=18
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            left_btn_frame,
            text="🗑️ Delete Selected",
            command=self.delete_selected,
            width=18
        ).pack(side=tk.LEFT)
        
        # Right side button (Close)
        ttk.Button(
            action_frame,
            text="✕ Close",
            command=self.window.destroy,
            width=15
        ).pack(side=tk.RIGHT)
        
        # Status bar at the bottom
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            self.main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        status_bar.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Double-click to restore
        self.backup_tree.bind("<Double-1>", lambda e: self.restore_selected())
        
        # Update scroll region after window is shown
        self.window.after(100, lambda: configure_scroll(None))
    
    def load_backups(self):
        """Загружает бэкапы и статистику"""
        try:
            # Очищаем статистику
            for widget in self.stats_frame.winfo_children():
                widget.destroy()
            
            # Получаем статистику
            stats = self.backup_manager.get_backup_stats()
            
            # Отображаем статистику в несколько колонок
            stats_grid = ttk.Frame(self.stats_frame)
            stats_grid.pack(fill=tk.X)
            
            # Колонка 1
            col1 = ttk.Frame(stats_grid)
            col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
            
            ttk.Label(col1, 
                     text=f"📊 Total Backups: {stats['total_backups']}",
                     font=("Arial", 10)).pack(anchor=tk.W, pady=2)
            
            ttk.Label(col1, 
                     text=f"💾 Total Size: {stats['total_size_mb']:.1f} MB",
                     font=("Arial", 10)).pack(anchor=tk.W, pady=2)
            
            # Колонка 2
            col2 = ttk.Frame(stats_grid)
            col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            if stats['oldest_backup']:
                ttk.Label(col2, 
                         text=f"📅 Oldest: {stats['oldest_backup'].strftime('%Y-%m-%d')}",
                         font=("Arial", 10)).pack(anchor=tk.W, pady=2)
            
            if stats['newest_backup']:
                ttk.Label(col2, 
                         text=f"🕒 Latest: {stats['newest_backup'].strftime('%Y-%m-%d %H:%M')}",
                         font=("Arial", 10)).pack(anchor=tk.W, pady=2)
            
            # Путь к папке
            path_label = ttk.Label(
                self.stats_frame,
                text=f"📁 Location: {stats['backup_dir']}",
                font=("Arial", 9),
                foreground="blue"
            )
            path_label.pack(anchor=tk.W, pady=(10, 0))
            
            # Очищаем дерево
            for item in self.backup_tree.get_children():
                self.backup_tree.delete(item)
            
            # Загружаем бэкапы
            backups = self.backup_manager.list_backups()
            
            if not backups:
                # Пустой список
                self.backup_tree.insert("", "end", values=("No backups found", "", "", ""))
            else:
                for backup in backups:
                    # Определяем тип бэкапа
                    backup_type = "Manual"
                    if "auto" in backup['name']:
                        backup_type = "Auto"
                    elif "scheduled" in backup['name']:
                        backup_type = "Scheduled"
                    
                    self.backup_tree.insert(
                        "", "end",
                        values=(
                            backup['name'],
                            f"{backup['size_mb']:.1f}",
                            backup['created'].strftime("%Y-%m-%d %H:%M"),
                            backup_type
                        ),
                        tags=(backup_type.lower(),)
                    )
            
            # Настройка цветов для разных типов
            self.backup_tree.tag_configure('auto', foreground='green')
            self.backup_tree.tag_configure('manual', foreground='blue')
            self.backup_tree.tag_configure('scheduled', foreground='orange')
            
            # Обновляем статус
            self.status_var.set(f"Loaded {len(backups)} backup(s)")
            
        except Exception as e:
            logger.error(f"Error loading backups: {e}")
            self.status_var.set(f"Error: {str(e)}")
    
    def create_backup(self):
        """Создает новый бэкап"""
        if messagebox.askyesno("Create Backup", 
                              "Create new database backup?\n\n"
                              "This may take a few moments..."):
            self.status_var.set("Creating backup...")
            self.window.update()
            
            try:
                result = self.backup_manager.create_backup(backup_type="manual", max_backups=20)
                
                if result:
                    messagebox.showinfo(
                        "Backup Created",
                        f"✓ Database backup created successfully!\n\n"
                        f"File: {result['name']}\n"
                        f"Size: {result['size_mb']:.2f} MB\n"
                        f"Time: {result['timestamp']}"
                    )
                    self.load_backups()
                    self.status_var.set("Backup created successfully")
                else:
                    messagebox.showerror("Backup Error", "Failed to create backup")
                    self.status_var.set("Backup creation failed")
                    
            except Exception as e:
                logger.error(f"Error creating backup: {e}")
                messagebox.showerror("Backup Error", f"Error: {str(e)}")
                self.status_var.set("Backup error occurred")
    
    def open_backup_folder(self):
        """Открывает папку с бэкапами"""
        try:
            backup_dir = self.backup_manager.backup_dir
            
            if os.name == 'nt':  # Windows
                os.startfile(backup_dir)
            elif os.name == 'posix':  # Linux/Mac
                subprocess.Popen(['xdg-open', str(backup_dir)])
            else:
                messagebox.showinfo("Backup Folder", 
                                  f"Backup folder location:\n{backup_dir}")
                
            self.status_var.set("Opened backup folder")
                
        except Exception as e:
            logger.error(f"Error opening backup folder: {e}")
            messagebox.showerror("Error", f"Cannot open folder:\n{str(e)}")
            self.status_var.set("Failed to open folder")
    
    def restore_selected(self):
        """Восстанавливает выбранный бэкап"""
        selected = self.backup_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a backup to restore")
            return
        
        item = self.backup_tree.item(selected[0])
        backup_name = item['values'][0]
        
        if backup_name == "No backups found":
            return
        
        if messagebox.askyesno(
            "Confirm Restore",
            f"⚠️ RESTORE DATABASE FROM BACKUP\n\n"
            f"File: {backup_name}\n\n"
            f"WARNING: Current database will be replaced!\n"
            f"All current data will be lost.\n\n"
            f"Are you sure you want to continue?",
            icon='warning'
        ):
            self.status_var.set("Restoring backup...")
            self.window.update()
            
            try:
                if self.backup_manager.restore_backup(backup_name):
                    messagebox.showinfo(
                        "Restore Complete",
                        "✓ Database restored successfully!\n\n"
                        "Please RESTART the application to use the restored data."
                    )
                    self.status_var.set("Database restored - restart required")
                    # Не закрываем окно, чтобы пользователь видел сообщение
                else:
                    messagebox.showerror("Restore Error", "Failed to restore backup")
                    self.status_var.set("Restore failed")
                    
            except Exception as e:
                logger.error(f"Error restoring backup: {e}")
                messagebox.showerror("Restore Error", f"Error: {str(e)}")
                self.status_var.set("Restore error occurred")
    
    def delete_selected(self):
        """Удаляет выбранный бэкап"""
        selected = self.backup_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a backup to delete")
            return
        
        item = self.backup_tree.item(selected[0])
        backup_name = item['values'][0]
        
        if backup_name == "No backups found":
            return
        
        if messagebox.askyesno(
            "Confirm Delete",
            f"Delete backup file?\n\n"
            f"File: {backup_name}\n\n"
            f"This action cannot be undone.",
            icon='warning'
        ):
            try:
                backup_path = self.backup_manager.backup_dir / backup_name
                os.remove(backup_path)
                
                messagebox.showinfo("Deleted", "Backup file deleted successfully")
                self.load_backups()
                self.status_var.set("Backup deleted")
                
            except Exception as e:
                logger.error(f"Error deleting backup: {e}")
                messagebox.showerror("Delete Error", f"Failed to delete:\n{str(e)}")
                self.status_var.set("Delete failed")
                
    def cleanup_temp_files(self):
        """Очищает временные файлы восстановления"""
        if messagebox.askyesno(
            "Clean Temporary Files",
            "Delete temporary restore files older than 2 hours?\n\n"
            "These files are created automatically before restore operations."
        ):
            deleted = self.backup_manager.cleanup_temp_files(max_age_hours=2)
            messagebox.showinfo(
                "Cleanup Complete",
                f"Deleted {deleted} temporary file(s)"
            )
            self.status_var.set(f"Cleaned up {deleted} temp file(s)")