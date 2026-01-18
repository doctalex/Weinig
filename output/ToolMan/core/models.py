from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class Profile:
    """Модель профиля"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    feed_rate: Optional[float] = None
    material_size: Optional[str] = None
    product_size: Optional[str] = None
    image_data: Optional[bytes] = None  # Превью PDF (первая страница)
    pdf_path: Optional[str] = None      # Путь к PDF файлу
    
    @property
    def has_pdf(self) -> bool:
        """Проверяет, есть ли у профиля PDF файл"""
        import os
        return self.pdf_path is not None and os.path.exists(self.pdf_path)
    
    @property
    def has_preview(self) -> bool:
        """Проверяет, есть ли превью"""
        return self.image_data is not None
    
    def get_preview(self) -> Optional[bytes]:
        """Получает изображение для превью"""
        return self.image_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'feed_rate': self.feed_rate,
            'material_size': self.material_size,
            'product_size': self.product_size,
            'image_data': self.image_data,
            'pdf_path': self.pdf_path  # ДОБАВЛЕНО!
        }
    
    @classmethod
    def from_db_row(cls, row) -> 'Profile':
        """Create from database row"""
        # Преобразуем row в словарь если это sqlite3.Row
        if hasattr(row, 'keys'):
            # Если это sqlite3.Row (имеет метод keys)
            row_dict = {key: row[key] for key in row.keys()}
            
            # Извлекаем данные
            image_data = row_dict.get('Image') or row_dict.get('image_data')
            pdf_path = row_dict.get('pdf_path')
            
            # Преобразуем image_data в bytes если нужно
            if image_data is not None and isinstance(image_data, str):
                try:
                    image_data = image_data.encode('latin-1')
                except Exception as e:
                    print(f"Warning: Could not encode image_data string: {e}")
                    image_data = None
            
            return cls(
                id=row_dict.get('ID'),
                name=row_dict.get('Name', ""),
                description=row_dict.get('Description', ""),
                feed_rate=row_dict.get('Feed_rate', 2.5),
                material_size=row_dict.get('Material_size', "100x100"),
                product_size=row_dict.get('Product_size', "90x90"),
                image_data=image_data,
                pdf_path=pdf_path  # <-- ВАЖНО!
            )
        else:
            # Если это tuple (старый код)
            # Индексы на основе структуры таблицы:
            # 0: ID, 1: Name, 2: Description, 3: Feed_rate, 4: Material_size, 
            # 5: Product_size, 6: Image, 7: Created_Date, 8: pdf_path
            
            image_data = None
            if len(row) > 6 and row[6]:  # Check Image column
                image_data = row[6]
            elif len(row) > 8 and row[8]:  # Fall back to image_data column
                image_data = row[8]
            
            # Fix: convert string to bytes if needed
            if image_data is not None and isinstance(image_data, str):
                try:
                    image_data = image_data.encode('latin-1')
                except Exception as e:
                    print(f"Warning: Could not encode image_data string: {e}")
                    image_data = None
            
            # Get pdf_path (index 8 based on table structure)
            pdf_path = None
            if len(row) > 8:
                pdf_path = row[8]
            
            return cls(
                id=row[0] if len(row) > 0 else None,
                name=row[1] if len(row) > 1 else "",
                description=row[2] if len(row) > 2 else "",
                feed_rate=row[3] if len(row) > 3 else 2.5,
                material_size=row[4] if len(row) > 4 else "100x100",
                product_size=row[5] if len(row) > 5 else "90x90",
                image_data=image_data,
                pdf_path=pdf_path  # <-- ВАЖНО!
            )

@dataclass
class Tool:
    """Модель инструмента"""
    id: Optional[int] = None
    profile_id: int = 0
    position: str = "Bottom"
    tool_type: str = "Profile"
    set_number: int = 1
    code: str = ""
    knives_count: int = 6
    template_id: Optional[str] = None
    status: str = "ready"
    notes: str = ""
    photo: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database"""
        return {
            'ID': self.id,
            'Profile_ID': self.profile_id,
            'Position': self.position,
            'Tool_Type': self.tool_type,
            'Set_Number': self.set_number,
            'Auto_Generated_Code': self.code,
            'Knives_Count': self.knives_count,
            'Template_ID': self.template_id,
            'Set_Status': self.status,
            'Notes': self.notes,
            'Photo': self.photo
        }
    
    @classmethod
    def from_db_row(cls, row) -> 'Tool':
        """Create from database row"""
        return cls(
            id=row[0] if len(row) > 0 else None,
            profile_id=row[1] if len(row) > 1 else 0,
            position=row[2] if len(row) > 2 else "Bottom",
            tool_type=row[3] if len(row) > 3 else "Profile",
            set_number=row[4] if len(row) > 4 else 1,
            code=row[5] if len(row) > 5 else "",
            knives_count=row[6] if len(row) > 6 else 6,
            template_id=row[7] if len(row) > 7 else None,
            status=row[8] if len(row) > 8 else "ready",
            notes=row[9] if len(row) > 9 else "",
            photo=row[10] if len(row) > 10 else None
        )

@dataclass
class ToolAssignment:
    """Модель назначения инструмента на голову"""
    id: Optional[int] = None
    profile_id: int = 0
    tool_id: int = 0
    head_number: int = 0
    rpm: Optional[int] = None
    pass_depth: Optional[float] = None
    work_material: str = ""
    remarks: str = ""
    tool_code: str = ""  # для удобства
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'profile_id': self.profile_id,
            'tool_id': self.tool_id,
            'head_number': self.head_number,
            'rpm': self.rpm,
            'pass_depth': self.pass_depth,
            'work_material': self.work_material,
            'remarks': self.remarks
        }