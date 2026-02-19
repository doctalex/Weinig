"""
Сервис для работы с размерами материала и продукта
"""
import sqlite3
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class MaterialSize:
    """Модель размера материала"""
    def __init__(self, id=None, width=None, thickness=None, name=""):
        self.id = id
        self.width = width
        self.thickness = thickness
        self.name = name
    
    def display_name(self):
        """Возвращает отображаемое имя размера"""
        if self.thickness:
            return f"{self.width} x {self.thickness} ({self.name})"
        return f"{self.width} ({self.name})"
    
    def __repr__(self):
        return f"MaterialSize(id={self.id}, width={self.width}, thickness={self.thickness}, name='{self.name}')"


class SizeService:
    """Сервис для работы с размерами материала и продукта"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        print(f"[SizeService] Using database: {self.db_path}")

    # === Работа с материалом ===

    def add_material_size(self, width: float, thickness: float, name: str = None) -> int:
        """Добавляет новый размер материала, если такого нет."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id FROM material_sizes WHERE width = ? AND thickness = ?",
                (width, thickness)
            )
            result = cursor.fetchone()
            if result:
                return result[0]

            if not name:
                name = f"{width} x {thickness}"

            cursor.execute(
                "INSERT INTO material_sizes (width, thickness, name) VALUES (?, ?, ?)",
                (width, thickness, name)
            )
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()

            print(f"[SizeService] Added material size {width} x {thickness} (ID={new_id})")
            return new_id

        except Exception as e:
            print(f"[SizeService] Error adding material size: {e}")
            return -1

    def get_all_material_sizes(self) -> List[MaterialSize]:
        """Возвращает все размеры материала."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, width, thickness, name
                FROM material_sizes
                ORDER BY width ASC, thickness ASC
            """)

            sizes = [
                MaterialSize(id=row[0], width=row[1], thickness=row[2], name=row[3])
                for row in cursor.fetchall()
            ]

            conn.close()
            return sizes

        except Exception as e:
            print(f"[SizeService] Error getting material sizes: {e}")
            return []

    def get_material_size_by_id(self, size_id: int) -> Optional[MaterialSize]:
        """Получает размер материала по ID."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, width, thickness, name
                FROM material_sizes
                WHERE id = ?
            """, (size_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return MaterialSize(id=row[0], width=row[1], thickness=row[2], name=row[3])

            return None

        except Exception as e:
            print(f"[SizeService] Error getting material size by ID: {e}")
            return None

    # === Работа с размерами продукта ===

    def get_product_variants_for_profile(self, profile_id: int) -> List[Dict[str, Any]]:
        """Возвращает список вариантов размеров продукта."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, width, thickness, is_default, material_id
                FROM product_size_variants
                WHERE profile_id = ?
                ORDER BY id
            """, (profile_id,))

            variants = [
                {
                    "id": row[0],
                    "width": row[1],
                    "thickness": row[2],
                    "is_default": bool(row[3]),
                    "material_id": row[4]
                }
                for row in cursor.fetchall()
            ]

            conn.close()
            return variants

        except Exception as e:
            print(f"[SizeService] Error getting product variants: {e}")
            return []

    def insert_product_variant(self, profile_id, width, thickness, is_default, material_id):
        """Добавляет новый вариант размера продукта."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO product_size_variants (profile_id, width, thickness, is_default, material_id)
                VALUES (?, ?, ?, ?, ?)
            """, (profile_id, width, thickness, int(is_default), material_id))

            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            return new_id

        except Exception as e:
            print(f"[SizeService] Error inserting product variant: {e}")
            return None

    def update_product_variant(self, variant_id, width, thickness, is_default, material_id):
        """Обновляет существующий вариант размера продукта."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE product_size_variants
                SET width = ?, thickness = ?, is_default = ?, material_id = ?
                WHERE id = ?
            """, (width, thickness, int(is_default), material_id, variant_id))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"[SizeService] Error updating product variant: {e}")
            return False

    def delete_product_variant(self, variant_id):
        """Удаляет вариант размера продукта."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM product_size_variants WHERE id = ?", (variant_id,))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"[SizeService] Error deleting product variant: {e}")
            return False
