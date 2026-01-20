"""
Сервис для работы с размерами материала и продукта
"""
import sqlite3
import logging
from pathlib import Path
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
    
    def __init__(self, db_path=None):
        """Инициализация сервиса"""
        if db_path is None:
            db_path = Path.cwd() / 'tools_database.db'
            print(f"DEBUG: SizeService using default db_path: {db_path}")
        
        self.db_path = str(db_path)
        print(f"DEBUG: SizeService initialized with db_path: {self.db_path}")
        
        # Инициализируем таблицы если их нет
        self._initialize_tables()
    
    def _initialize_tables(self):
        """Создает необходимые таблицы если их нет"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица material_sizes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS material_sizes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    width REAL NOT NULL,
                    thickness REAL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица product_size_variants
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS product_size_variants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER NOT NULL,
                    width REAL NOT NULL,
                    thickness REAL,
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (profile_id) REFERENCES profiles (id) ON DELETE CASCADE
                )
            ''')
            
            # Индекс для ускорения поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_variants_profile ON product_size_variants(profile_id)')
            
            conn.commit()
            conn.close()
            print("DEBUG: Size tables initialized successfully")
            
        except Exception as e:
            print(f"DEBUG: Error initializing size tables: {e}")
    
    # === Работа с материалом ===
    
    def add_material_size(self, width: float, thickness: float, name: str = None) -> int:
        """
        Добавляет новый размер материала, если такого нет.
        Возвращает ID добавленного или существующего размера.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверка, есть ли уже такой размер
            cursor.execute('''
                SELECT id FROM material_sizes 
                WHERE width = ? AND thickness = ?
            ''', (width, thickness))
            result = cursor.fetchone()
            if result:
                return result[0]  # уже есть
            
            # Генерируем имя, если не указано
            if not name:
                name = f"{width} x {thickness}"
            
            cursor.execute('''
                INSERT INTO material_sizes (width, thickness, name)
                VALUES (?, ?, ?)
            ''', (width, thickness, name))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"DEBUG: Added new material size: {width} x {thickness} (ID {new_id})")
            return new_id
        except Exception as e:
            print(f"DEBUG: Error adding material size: {e}")
            return -1
    
    def get_all_material_sizes(self) -> List[MaterialSize]:
        """Возвращает все размеры материала, отсортированные по ширине и толщине"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, width, thickness, name 
                FROM material_sizes
                ORDER BY width ASC, thickness ASC
            ''')
            sizes = [MaterialSize(id=row[0], width=row[1], thickness=row[2], name=row[3])
                     for row in cursor.fetchall()]
            conn.close()
            return sizes
        except Exception as e:
            print(f"DEBUG: Error getting material sizes: {e}")
            return []
    
    def get_material_size_by_id(self, size_id: int) -> Optional[MaterialSize]:
        """Получает размер материала по ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, width, thickness, name 
                FROM material_sizes 
                WHERE id = ?
            ''', (size_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return MaterialSize(id=row[0], width=row[1], thickness=row[2], name=row[3])
            return None
        except Exception as e:
            print(f"DEBUG: Error getting material size by ID: {e}")
            return None
    
    # === Работа с размерами продукта ===
    
    def get_product_variants_for_profile(self, profile_id: int) -> List[Dict[str, Any]]:
        """Получает все варианты размеров продукта для профиля"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, width, thickness, is_default 
                FROM product_size_variants 
                WHERE profile_id = ?
                ORDER BY id
            ''', (profile_id,))
            
            variants = [{'id': row[0], 'width': row[1], 'thickness': row[2], 'is_default': bool(row[3])} 
                        for row in cursor.fetchall()]
            
            conn.close()
            return variants
        except Exception as e:
            print(f"DEBUG: Error getting product variants: {e}")
            return []
    
    def create_product_variant(self, profile_id: int, width: float, thickness: Optional[float] = None, 
                               is_default: bool = False) -> Optional[int]:
        """Создает новый вариант размера продукта"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO product_size_variants (profile_id, width, thickness, is_default)
                VALUES (?, ?, ?, ?)
            ''', (profile_id, width, thickness, is_default))
            variant_id = cursor.lastrowid
            
            if is_default:
                cursor.execute('''
                    UPDATE product_size_variants
                    SET is_default = 0
                    WHERE profile_id = ? AND id != ?
                ''', (profile_id, variant_id))
            
            conn.commit()
            conn.close()
            return variant_id
        except Exception as e:
            print(f"DEBUG: Error creating product variant: {e}")
            return None
    
    def update_product_variant(self, variant_id: int, width: float, thickness: Optional[float] = None, 
                               is_default: bool = False) -> bool:
        """Обновляет вариант размера продукта"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT profile_id FROM product_size_variants WHERE id = ?', (variant_id,))
            result = cursor.fetchone()
            if not result:
                return False
            profile_id = result[0]
            
            cursor.execute('''
                UPDATE product_size_variants
                SET width = ?, thickness = ?, is_default = ?
                WHERE id = ?
            ''', (width, thickness, is_default, variant_id))
            
            if is_default:
                cursor.execute('''
                    UPDATE product_size_variants
                    SET is_default = 0
                    WHERE profile_id = ? AND id != ?
                ''', (profile_id, variant_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"DEBUG: Error updating product variant: {e}")
            return False
    
    def delete_product_variant(self, variant_id: int) -> bool:
        """Удаляет вариант размера продукта"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM product_size_variants WHERE id = ?', (variant_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"DEBUG: Error deleting product variant: {e}")
            return False
            
    def set_active_product_variant(self, variant_id: int) -> bool:
        """Делает вариант активным (один на профиль)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT profile_id FROM product_size_variants WHERE id = ?",
                (variant_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False

            profile_id = row[0]

            # сброс всех active
            cursor.execute(
                "UPDATE product_size_variants SET is_default = 0 WHERE profile_id = ?",
                (profile_id,)
            )

            # установка active
            cursor.execute(
                "UPDATE product_size_variants SET is_default = 1 WHERE id = ?",
                (variant_id,)
            )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"DEBUG: Error setting active variant: {e}")
            return False
            
    def get_suitable_material_sizes(self, min_width: float, min_thickness: float) -> List[MaterialSize]:
        """
        Получить доски, подходящие для профиля.
        Доска подходит если: width >= min_width AND thickness >= min_thickness
        Сортировка по минимальному перерасходу материала.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, width, thickness, name 
                FROM material_sizes
                WHERE width >= ? AND thickness >= ?
                ORDER BY (width - ?) + (thickness - ?)
            ''', (min_width, min_thickness, min_width, min_thickness))
            
            sizes = [MaterialSize(id=row[0], width=row[1], thickness=row[2], name=row[3])
                     for row in cursor.fetchall()]
            conn.close()
            
            print(f"DEBUG: Found {len(sizes)} suitable boards for {min_width}x{min_thickness}mm")
            return sizes
        except Exception as e:
            print(f"DEBUG: Error getting suitable material sizes: {e}")
            return []
