#!/usr/bin/env python
"""
Test GUI integration with SecurityManager
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.security import SecurityManager

class TestSecurityGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Security GUI Test")
        self.root.geometry("500x400")
        
        # Используем SecurityManager
        self.security = SecurityManager()
        
        self.create_widgets()
        self.update_ui()
        
        # Настраиваем горячие клавиши
        self.root.bind('<Control-Shift-F>', self.toggle_security)
        self.root.bind('<Control-Shift-f>', self.toggle_security)
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Security Mode Test", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Current mode display
        self.mode_frame = ttk.LabelFrame(main_frame, text="Current Mode", padding="10")
        self.mode_frame.grid(row=1, column=0, columnspan=3, pady=(0, 20), sticky=(tk.W, tk.E))
        
        self.mode_label = ttk.Label(self.mode_frame, text="", font=("Arial", 14))
        self.mode_label.pack()
        
        # Status label
        self.status_label = ttk.Label(self.mode_frame, text="")
        self.status_label.pack()
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="Set Full Access", 
                  command=self.set_full_access).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Set Read Only", 
                  command=self.set_read_only).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Toggle Mode", 
                  command=self.toggle_security).pack(side=tk.LEFT, padx=5)
        
        # Simulated edit buttons
        edit_frame = ttk.LabelFrame(main_frame, text="Simulated Edit Controls", padding="10")
        edit_frame.grid(row=3, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E))
        
        self.edit_button = ttk.Button(edit_frame, text="Edit Tool", command=self.simulate_edit)
        self.edit_button.pack(pady=5)
        
        self.delete_button = ttk.Button(edit_frame, text="Delete Tool", command=self.simulate_delete)
        self.delete_button.pack(pady=5)
        
        # Hotkey info
        info_frame = ttk.LabelFrame(main_frame, text="Hotkeys", padding="10")
        info_frame.grid(row=4, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        ttk.Label(info_frame, text="Press Ctrl+Shift+F to toggle security mode").pack()
        ttk.Label(info_frame, text="Or use the buttons above").pack()
        
        # Debug info
        debug_frame = ttk.LabelFrame(main_frame, text="Debug Info", padding="10")
        debug_frame.grid(row=5, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        self.debug_label = ttk.Label(debug_frame, text="", font=("Courier", 9))
        self.debug_label.pack()
    
    def update_ui(self):
        """Update UI based on security mode"""
        mode_text = self.security.get_mode_text()
        mode = self.security.get_current_mode()
        
        # Update mode display
        self.mode_label.config(text=mode_text)
        
        if self.security.is_read_only():
            self.status_label.config(text="READ ONLY - Editing disabled")
            self.mode_label.config(foreground="red")
            
            # Disable edit buttons
            self.edit_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)
        else:
            self.status_label.config(text="FULL ACCESS - Editing enabled")
            self.mode_label.config(foreground="green")
            
            # Enable edit buttons
            self.edit_button.config(state=tk.NORMAL)
            self.delete_button.config(state=tk.NORMAL)
        
        # Update debug info
        debug_text = f"Mode: {mode}\n"
        debug_text += f"is_read_only: {self.security.is_read_only()}\n"
        debug_text += f"is_full_access: {self.security.is_full_access()}"
        self.debug_label.config(text=debug_text)
    
    def set_full_access(self):
        self.security.set_full_access()
        self.update_ui()
        messagebox.showinfo("Success", "Switched to Full Access mode")
    
    def set_read_only(self):
        self.security.set_read_only()
        self.update_ui()
        messagebox.showinfo("Success", "Switched to Read Only mode")
    
    def toggle_security(self, event=None):
        was_read_only = self.security.is_read_only()
        self.security.toggle_security_mode()
        self.update_ui()
        
        new_mode = self.security.get_mode_text()
        messagebox.showinfo("Success", f"Toggled to {new_mode} mode")
        
        print(f"DEBUG: Toggled from {'Read Only' if was_read_only else 'Full Access'} to {new_mode}")
    
    def simulate_edit(self):
        messagebox.showinfo("Edit", "Edit button clicked")
    
    def simulate_delete(self):
        messagebox.showinfo("Delete", "Delete button clicked")

def main():
    root = tk.Tk()
    app = TestSecurityGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()