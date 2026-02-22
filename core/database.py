import sqlite3
import os
import sys
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных SQLite"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            if getattr(sys, "frozen", False):
                project_dir = os.path.dirname(sys.executable)
            else:
                project_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..")
                )

            db_path = os.path.join(project_dir, "tools_database.db")

        self.db_path = os.path.abspath(db_path)

        print(f"Database path: {self.db_path}")
        print(f"Directory exists: {os.path.exists(os.path.dirname(self.db_path))}")
        print(f"Directory writable: {os.access(os.path.dirname(self.db_path), os.W_OK)}")

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._init_database()
        self.migrate_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Создает и возвращает соединение с базой данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            raise
    
    def _init_database(self) -> None:
        """Инициализирует базу данных и создает таблицы"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Сначала создаем Profiles (без Image и с новыми дефолтами)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS Profiles (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Name TEXT NOT NULL UNIQUE,
                        Description TEXT,
                        Feed_rate REAL DEFAULT 30.0,
                        Material_size TEXT DEFAULT '',
                        Product_size TEXT DEFAULT '',
                        pdf_path TEXT,
                        Created_Date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 2. Обязательно создаем material_sizes (она нужна для вариантов!)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS material_sizes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        width REAL NOT NULL,
                        thickness REAL NOT NULL,
                        name TEXT,
                        description TEXT
                    )
                ''')
                
                # 3. Таблица вариантов продукта
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS product_size_variants (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        profile_id INTEGER NOT NULL,
                        width REAL NOT NULL,
                        thickness REAL NOT NULL,
                        material_id INTEGER,
                        is_default BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (profile_id) REFERENCES Profiles (ID) ON DELETE CASCADE,
                        FOREIGN KEY (material_id) REFERENCES material_sizes (id) ON DELETE SET NULL
                    )
                ''')
                
                # Индекс для быстрого поиска
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_product_variants_profile 
                    ON product_size_variants(profile_id)
                ''')
                
                # Таблица инструментов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS Tools (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Profile_ID INTEGER NOT NULL,
                        Position TEXT,
                        Tool_Type TEXT,
                        Set_Number INTEGER DEFAULT 1,
                        Auto_Generated_Code TEXT UNIQUE,
                        Knives_Count INTEGER DEFAULT 6,
                        Template_ID TEXT,
                        Set_Status TEXT DEFAULT 'ready',
                        Notes TEXT,
                        Photo BLOB,
                        FOREIGN KEY (Profile_ID) REFERENCES Profiles (ID) ON DELETE CASCADE
                    )
                ''')
                
                # Проверяем наличие колонки Photo и добавляем её, если её нет
                cursor.execute('''
                    PRAGMA table_info(Tools)
                ''')
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'Photo' not in columns:
                    cursor.execute('''
                        ALTER TABLE Tools ADD COLUMN Photo BLOB
                    ''')
                    conn.commit()
                
                # Таблица шаблонов изображений инструментов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS Tool_Image_Templates (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Profile_ID INTEGER NOT NULL,
                        Position TEXT NOT NULL,
                        Tool_Type TEXT NOT NULL,
                        Image_Data BLOB NOT NULL,
                        Created_Date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (Profile_ID) REFERENCES Profiles (ID) ON DELETE CASCADE,
                        UNIQUE(Profile_ID, Position, Tool_Type)
                    )
                ''')
                
                # Таблица назначений инструментов на головы
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS Tool_Assignments (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Profile_ID INTEGER NOT NULL,
                        Tool_ID INTEGER NOT NULL,
                        Head_Number INTEGER NOT NULL CHECK (Head_Number BETWEEN 1 AND 10),
                        RPM INTEGER,
                        Pass_Depth REAL,
                        Work_Material TEXT,
                        Remarks TEXT,
                        FOREIGN KEY (Profile_ID) REFERENCES Profiles (ID) ON DELETE CASCADE,
                        FOREIGN KEY (Tool_ID) REFERENCES Tools (ID) ON DELETE CASCADE,
                        UNIQUE(Profile_ID, Head_Number)
                    )
                ''')
                
                # Создание индексов
                self._create_indexes(cursor)
                conn.commit()
                
        except sqlite3.Error as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise
    
    def _create_indexes(self, cursor: sqlite3.Cursor) -> None:
        """Создает индексы для ускорения запросов"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_tools_auto_code ON Tools(Auto_Generated_Code)",
            "CREATE INDEX IF NOT EXISTS idx_tools_profile ON Tools(Profile_ID)",
            "CREATE INDEX IF NOT EXISTS idx_tools_position ON Tools(Position)",
            "CREATE INDEX IF NOT EXISTS idx_tools_type ON Tools(Tool_Type)",
            "CREATE INDEX IF NOT EXISTS idx_assignments_profile ON Tool_Assignments(Profile_ID)",
            "CREATE INDEX IF NOT EXISTS idx_assignments_tool ON Tool_Assignments(Tool_ID)",
            "CREATE INDEX IF NOT EXISTS idx_assignments_head ON Tool_Assignments(Profile_ID, Head_Number)"
        ]
        
        for index in indexes:
            try:
                cursor.execute(index)
            except sqlite3.Error as e:
                logger.warning(f"Не удалось создать индекс: {e}")
    
    def migrate_database(self):
        """Миграция для добавления новых столбцов"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем наличие столбцов
                cursor.execute("PRAGMA table_info(Tools)")
                columns = {col[1]: col for col in cursor.fetchall()}
                
                # Добавляем Template_ID если нет
                if 'Template_ID' not in columns:
                    cursor.execute("ALTER TABLE Tools ADD COLUMN Template_ID TEXT")
                    logger.info("Added Template_ID column to Tools table")
                
                # Добавляем Set_Status если нет
                if 'Set_Status' not in columns:
                    cursor.execute("ALTER TABLE Tools ADD COLUMN Set_Status TEXT DEFAULT 'ready'")
                    logger.info("Added Set_Status column to Tools table")
                
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error during database migration: {e}")
    
    def execute_query(self, query: str, params: tuple = (), 
                     fetch_one: bool = False, commit: bool = False) -> Union[List[sqlite3.Row], sqlite3.Row, None]:
        """Выполняет SQL-запрос к базе данных"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                if commit:
                    conn.commit()
                    return cursor.rowcount
                
                if fetch_one:
                    return cursor.fetchone()
                return cursor.fetchall()
                
        except sqlite3.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}\nQuery: {query}\nParams: {params}")
            raise
    
    # CRUD методы для профилей
    def get_all_profiles(self) -> List[sqlite3.Row]:
        """Получает все профили"""
        return self.execute_query('SELECT * FROM Profiles ORDER BY Name')
    
    def get_profile(self, profile_id: int) -> Optional[sqlite3.Row]:
        """Получает профиль по ID"""
        return self.execute_query(
            'SELECT * FROM Profiles WHERE ID = ?',
            (profile_id,),
            fetch_one=True
        )
    
    def add_profile(self, name: str, description: str = '', feed_rate: float = 30.0,
                   material_size: str = '', product_size: str = '',
                   image_data: Optional[bytes] = None, pdf_path: Optional[str] = None) -> int:
        """Добавляет новый профиль (игнорируем image_data)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Убираем Image из списка колонок и VALUES
                cursor.execute('''
                    INSERT INTO Profiles 
                    (Name, Description, Feed_rate, Material_size, Product_size, pdf_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, description, feed_rate, material_size, product_size, pdf_path))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise sqlite3.IntegrityError(f"Профиль с именем '{name}' уже существует") from e
            raise
    
    def update_profile(self, profile_id: int, **kwargs) -> bool:
        """Обновляет профиль"""
        if not kwargs:
            return False
        
        # Map parameter names to column names
        column_mapping = {
            'image_data': 'Image'
        }
        
        # Replace parameter names with column names in the query
        set_clause = ", ".join([f"{column_mapping.get(key, key)} = ?" for key in kwargs.keys()])
        params = list(kwargs.values())
        params.append(profile_id)
        
        query = f"UPDATE Profiles SET {set_clause} WHERE ID = ?"
        result = self.execute_query(query, tuple(params), commit=True)
        return result is not None
    
    def delete_profile(self, profile_id: int) -> bool:
        """Удаляет профиль"""
        result = self.execute_query(
            'DELETE FROM Profiles WHERE ID = ?',
            (profile_id,),
            commit=True
        )
        return result > 0
    
    # CRUD методы для инструментов
    def get_tools_by_profile(self, profile_id: int) -> List[sqlite3.Row]:
        """Получает инструменты профиля"""
        return self.execute_query(
            'SELECT * FROM Tools WHERE Profile_ID = ? ORDER BY Auto_Generated_Code',
            (profile_id,)
        )
    
    def get_tool(self, tool_id: int) -> Optional[sqlite3.Row]:
        """Получает инструмент по ID"""
        return self.execute_query(
            'SELECT * FROM Tools WHERE ID = ?',
            (tool_id,),
            fetch_one=True
        )

    def get_tools_in_set(self, auto_generated_code: str) -> List[sqlite3.Row]:
        """Получает все инструменты в наборе по Auto_Generated_Code"""
        return self.execute_query(
            'SELECT * FROM Tools WHERE Auto_Generated_Code = ?',
            (auto_generated_code,)
        )
    
    # Методы для назначений
    def get_tool_assignments(self, profile_id: int) -> Dict[int, dict]:
        """Получает назначения инструментов"""
        assignments = {}
        results = self.execute_query('''
            SELECT ta.*, t.Auto_Generated_Code as Tool_Code
            FROM Tool_Assignments ta
            JOIN Tools t ON ta.Tool_ID = t.ID
            WHERE ta.Profile_ID = ?
            ORDER BY ta.Head_Number
        ''', (profile_id,))
        
        for row in results:
            assignments[row['Head_Number']] = dict(row)
        
        return assignments
    
    def assign_tool_to_head(self, profile_id: int, head_number: int, 
                           tool_id: int, rpm: int = None, pass_depth: float = None,
                           work_material: str = '', remarks: str = '') -> bool:
        """Назначает инструмент на голову"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Удаляем старое назначение
                cursor.execute('''
                    DELETE FROM Tool_Assignments 
                    WHERE Profile_ID = ? AND Head_Number = ?
                ''', (profile_id, head_number))
                
                # Добавляем новое
                cursor.execute('''
                    INSERT INTO Tool_Assignments
                    (Profile_ID, Tool_ID, Head_Number, RPM, Pass_Depth, Work_Material, Remarks)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (profile_id, tool_id, head_number, rpm, pass_depth, work_material, remarks))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error assigning tool: {e}")
            return False

    def delete_tool(self, tool_id: int) -> bool:
        """
        Удаляет инструмент по ID
        
        Args:
            tool_id: ID инструмента для удаления
            
        Returns:
            bool: True если удаление прошло успешно, False в противном случае
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get the Auto_Generated_Code of the tool being deleted
                cursor.execute('''
                    SELECT Auto_Generated_Code FROM Tools WHERE ID = ?
                ''', (tool_id,))
                result = cursor.fetchone()
                
                if not result:
                    logger.warning(f'Попытка удалить несуществующий инструмент с ID: {tool_id}')
                    return False
                
                auto_generated_code = result[0]
                
                # Delete the tool
                cursor.execute('DELETE FROM Tools WHERE ID = ?', (tool_id,))
                
                # Check if there are any tools left in the set
                cursor.execute('''
                    SELECT COUNT(*) FROM Tools 
                    WHERE Auto_Generated_Code = ?
                ''', (auto_generated_code,))
                
                count = cursor.fetchone()[0]
                if count == 0:
                    logger.info(f'Все инструменты набора {auto_generated_code} удалены')
                
                conn.commit()
                logger.info(f'Успешно удален инструмент с ID: {tool_id}')
                return True
                
        except sqlite3.Error as e:
            logger.error(f'Ошибка при удалении инструмента с ID {tool_id}: {e}')
            if 'conn' in locals():
                conn.rollback()
            return False
            
    def add_tool(self, tool_data: Dict[str, Any]) -> int:
        """Добавляет инструмент и синхронизирует изображение с первым инструментом в наборе"""
        required = ['Profile_ID', 'Position', 'Tool_Type', 'Auto_Generated_Code']
        for field in required:
            if field not in tool_data:
                raise ValueError(f"Missing required field: {field}")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check if the profile exists
                cursor.execute('SELECT ID FROM Profiles WHERE ID = ?', (tool_data['Profile_ID'],))
                if not cursor.fetchone():
                    raise ValueError(f"Profile with ID {tool_data['Profile_ID']} does not exist")

                # Extract the base code (first 5 digits) to find the set
                auto_generated_code = tool_data['Auto_Generated_Code']
                if len(auto_generated_code) != 6 or not auto_generated_code.isdigit():
                    raise ValueError("Auto_Generated_Code must be a 6-digit number")
                    
                base_code = auto_generated_code[:5]
                
                # Check if this is the first tool in the set
                cursor.execute('''
                    SELECT ID, Photo 
                    FROM Tools 
                    WHERE Auto_Generated_Code LIKE ? 
                    AND Profile_ID = ?
                    ORDER BY ID
                    LIMIT 1
                ''', (f"{base_code}%", tool_data['Profile_ID']))
                
                first_tool = cursor.fetchone()
                
                # If there's a first tool in the set and it has a photo, use that photo
                if first_tool and first_tool['Photo']:
                    tool_data['Photo'] = first_tool['Photo']
                    logger.info(f"Using photo from first tool in set {base_code}*")
                elif 'Photo' not in tool_data:
                    tool_data['Photo'] = None

                # Insert the new tool
                cursor.execute('''
                    INSERT INTO Tools 
                    (Profile_ID, Position, Tool_Type, Set_Number, Auto_Generated_Code,
                    Knives_Count, Template_ID, Set_Status, Notes, Photo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tool_data['Profile_ID'],
                    tool_data['Position'],
                    tool_data['Tool_Type'],
                    int(auto_generated_code[5]),  # Set number is the last digit
                    auto_generated_code,
                    tool_data.get('Knives_Count', 6),
                    tool_data.get('Template_ID'),
                    tool_data.get('Set_Status', 'ready'),
                    tool_data.get('Notes', ''),
                    tool_data.get('Photo')
                ))
                
                tool_id = cursor.lastrowid
                logger.info(f"Added new tool ID: {tool_id}, Code: {auto_generated_code}")
                
                conn.commit()
                return tool_id

        except sqlite3.Error as e:
            logger.error(f"Error adding tool: {e}")
            if 'conn' in locals():
                conn.rollback()
            raise

    def update_tool(self, tool_id: int, tool_data: Dict[str, Any]) -> bool:
        """Обновляет данные инструмента с учетом логики кодов инструментов"""
        if not tool_data:
            return False

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Получаем текущие данные (этот блок у вас уже есть)
                cursor.execute('''
                    SELECT ID, Auto_Generated_Code, Profile_ID, Photo 
                    FROM Tools 
                    WHERE ID = ?
                ''', (tool_id,))
                current = cursor.fetchone()
                
                if not current:
                    logger.warning(f"Tool with ID {tool_id} not found")
                    return False

                new_code = tool_data.get('Auto_Generated_Code', current['Auto_Generated_Code'])
                is_image_update = 'Photo' in tool_data
                photo_data = tool_data.get('Photo')
                
                # ... (пропускаем блок проверки фото, он остается прежним) ...

                # 2. А ВОТ ЗДЕСЬ НАЧИНАЮТСЯ ИЗМЕНЕНИЯ:
                update_fields = []
                params = []
                
                # Создаем карту соответствия имен полей Python именам колонок в SQL
                column_mapping = {
                    'status': 'Set_Status',     # <-- ГЛАВНОЕ ИСПРАВЛЕНИЕ
                    'profile_id': 'Profile_ID',
                    'position': 'Position',
                    'tool_type': 'Tool_Type',
                    'set_number': 'Set_Number',
                    'knives_count': 'Knives_Count',
                    'template_id': 'Template_ID',
                    'notes': 'Notes'
                }
                
                for field, value in tool_data.items():
                    # Пропускаем код и фото, они обрабатываются отдельно
                    if field.lower() in ['id', 'auto_generated_code', 'photo']:
                        continue  
                    
                    # Ищем правильное имя колонки в нашей карте
                    db_column = column_mapping.get(field.lower(), field)
                    update_fields.append(f"{db_column} = ?")
                    params.append(value)
                
                # Добавляем обновление кода, если он изменился
                if 'Auto_Generated_Code' in tool_data:
                    update_fields.append("Auto_Generated_Code = ?")
                    params.append(tool_data['Auto_Generated_Code'])
                
                # Выполняем обновление
                if update_fields:
                    query = f"""
                        UPDATE Tools 
                        SET {', '.join(update_fields)}
                        WHERE ID = ?
                    """
                    params.append(tool_id)
                    cursor.execute(query, params)
                    logger.info(f"Updated tool {tool_id} with fields: {update_fields}")

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error updating tool: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
            
    def add_material_size(self, width: float, thickness: float, name: str, description: str) -> int:
        """Добавляет новый типоразмер заготовки в базу данных"""
        query = '''
            INSERT INTO material_sizes (width, thickness, name, description)
            VALUES (?, ?, ?, ?)
        '''
        try:
            # Используем твой существующий метод execute_query
            return self.execute_query(query, (width, thickness, name, description), commit=True)
        except sqlite3.Error as e:
            logger.error(f"Database error adding material: {e}")
            raise