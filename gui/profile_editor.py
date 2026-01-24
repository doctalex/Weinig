import tkinter as tk
from tkinter import ttk, messagebox
import logging

logger = logging.getLogger(__name__)


class ProfileEditor(tk.Toplevel):
    """
    Модальный редактор профиля (Create / Edit)
    """

    def __init__(self, parent, profile_service, profile=None, on_saved=None):
        super().__init__(parent)

        # --- dependencies ---
        self.parent = parent
        self.profile_service = profile_service
        self.profile = profile
        self.on_saved = on_saved

        # --- state ---
        self.read_only = getattr(
            getattr(parent, "security_manager", None),
            "is_read_only",
            True
        )

        # --- window ---
        self.title("Profile editor")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # --- variables ---
        self.name_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.feed_rate_var = tk.StringVar()
        self.material_size_var = tk.StringVar()
        self.product_size_var = tk.StringVar()

        # --- UI ---
        self._build_ui()

        if self.profile:
            self._load_profile()

        self._apply_read_only()

        self.wait_window(self)

    # ================= UI =================

    def _build_ui(self):
        frm = ttk.Frame(self, padding=10)
        frm.grid(sticky="nsew")

        row = 0

        ttk.Label(frm, text="Name").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.name_var, width=40).grid(row=row, column=1)
        row += 1

        ttk.Label(frm, text="Description").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.description_var, width=40).grid(row=row, column=1)
        row += 1

        ttk.Label(frm, text="Feed rate").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.feed_rate_var, width=20).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(frm, text="Material size").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.material_size_var, width=20).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(frm, text="Product size").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.product_size_var, width=20).grid(row=row, column=1, sticky="w")
        row += 1

        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=2, pady=(10, 0))

        ttk.Button(btns, text="Save", command=self._on_save).grid(row=0, column=0, padx=5)
        ttk.Button(btns, text="Cancel", command=self._on_cancel).grid(row=0, column=1, padx=5)

    # ================= Data =================

    def _load_profile(self):
        self.name_var.set(self.profile.get("name", ""))
        self.description_var.set(self.profile.get("description", ""))
        self.feed_rate_var.set(self.profile.get("feed_rate", ""))
        self.material_size_var.set(self.profile.get("material_size", ""))
        self.product_size_var.set(self.profile.get("product_size", ""))

    def _apply_read_only(self):
        if not self.read_only:
            return

        for child in self.winfo_children():
            for widget in child.winfo_children():
                if isinstance(widget, ttk.Entry):
                    widget.state(["disabled"])

    # ================= Actions =================

    def _on_save(self):
        if self.read_only:
            messagebox.showwarning("Read only", "Editing is disabled")
            return

        try:
            data = {
                "name": self.name_var.get().strip(),
                "description": self.description_var.get().strip(),
                "feed_rate": self._float_or_none(self.feed_rate_var.get()),
                "material_size": self.material_size_var.get().strip(),
                "product_size": self.product_size_var.get().strip(),
            }

            profile_id = self.profile["id"] if self.profile else None

            self.profile_service.save_profile(profile_id, data)

            logger.info("Profile saved")

            if self.on_saved:
                self.on_saved()

            self.destroy()

        except Exception as e:
            logger.exception("Error saving profile")
            messagebox.showerror("Error", str(e))

    def _on_cancel(self):
        self.destroy()

    # ================= Utils =================

    @staticmethod
    def _float_or_none(value):
        value = value.strip()
        if not value:
            return None
        return float(value)
