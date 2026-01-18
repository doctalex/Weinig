# core/models.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class MaterialSize:
    """Справочник размеров материала"""
    id: Optional[int] = None
    width: Optional[float] = None  # ширина в мм
    thickness: Optional[float] = None  # толщина в мм
    length: Optional[float] = None  # длина в мм
    description: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    
    def __repr__(self):
        return f"MaterialSize({self.width}x{self.thickness}x{self.length})"
    
    def display_name(self):
        """Форматированное отображение для UI"""
        parts = []
        if self.width:
            parts.append(f"W:{self.width}")
        if self.thickness:
            parts.append(f"T:{self.thickness}")
        if self.length:
            parts.append(f"L:{self.length}")
        return " × ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database"""
        return {
            'id': self.id,
            'width': self.width,
            'thickness': self.thickness,
            'length': self.length,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_db_row(cls, row) -> 'MaterialSize':
        """Create from database row"""
        if hasattr(row, 'keys'):  # sqlite3.Row
            row_dict = {key: row[key] for key in row.keys()}
            return cls(
                id=row_dict.get('id'),
                width=row_dict.get('width'),
                thickness=row_dict.get('thickness'),
                length=row_dict.get('length'),
                description=row_dict.get('description', ''),
                is_active=bool(row_dict.get('is_active', True)),
                created_at=datetime.fromisoformat(row_dict['created_at']) if row_dict.get('created_at') else None
            )
        else:  # tuple
            return cls(
                id=row[0] if len(row) > 0 else None,
                width=row[1] if len(row) > 1 else None,
                thickness=row[2] if len(row) > 2 else None,
                length=row[3] if len(row) > 3 else None,
                description=row[4] if len(row) > 4 else '',
                is_active=bool(row[5]) if len(row) > 5 else True,
                created_at=datetime.fromisoformat(row[6]) if len(row) > 6 and row[6] else None
            )

@dataclass
class ProductSizeVariant:
    """Вариант размера продукта"""
    id: Optional[int] = None
    profile_id: int = 0
    width: float = 0.0  # ширина продукта в мм
    thickness: Optional[float] = None  # толщина
    tolerance: float = 0.5  # допуск +/- в мм
    notes: str = ""
    is_default: bool = False
    order: int = 0  # порядок сортировки
    
    def __repr__(self):
        thickness_str = f"x{self.thickness}" if self.thickness else ""
        return f"ProductVariant({self.width}{thickness_str} ±{self.tolerance})"
    
    def display_name(self):
        """Форматированное отображение"""
        if self.thickness:
            return f"{self.width} × {self.thickness} mm (±{self.tolerance})"
        return f"{self.width} mm (±{self.tolerance})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database"""
        return {
            'id': self.id,
            'profile_id': self.profile_id,
            'width': self.width,
            'thickness': self.thickness,
            'tolerance': self.tolerance,
            'notes': self.notes,
            'is_default': self.is_default,
            'order': self.order
        }
    
    @classmethod
    def from_db_row(cls, row) -> 'ProductSizeVariant':
        """Create from database row"""
        if hasattr(row, 'keys'):  # sqlite3.Row
            row_dict = {key: row[key] for key in row.keys()}
            return cls(
                id=row_dict.get('id'),
                profile_id=row_dict.get('profile_id', 0),
                width=row_dict.get('width', 0.0),
                thickness=row_dict.get('thickness'),
                tolerance=row_dict.get('tolerance', 0.5),
                notes=row_dict.get('notes', ''),
                is_default=bool(row_dict.get('is_default', False)),
                order=row_dict.get('order', 0)
            )
        else:  # tuple
            return cls(
                id=row[0] if len(row) > 0 else None,
                profile_id=row[1] if len(row) > 1 else 0,
                width=row[2] if len(row) > 2 else 0.0,
                thickness=row[3] if len(row) > 3 else None,
                tolerance=row[4] if len(row) > 4 else 0.5,
                notes=row[5] if len(row) > 5 else '',
                is_default=bool(row[6]) if len(row) > 6 else False,
                order=row[7] if len(row) > 7 else 0
            )

@dataclass
class Profile:
    """Модель профиля"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    feed_rate: Optional[float] = None
    material_size: Optional[str] = None  # старое поле для обратной совместимости
    product_size: Optional[str] = None  # старое поле для обратной совместимости
    image_data: Optional[bytes] = None  # Превью PDF (первая страница)
    pdf_path: Optional[str] = None      # Путь к PDF файлу
    
    # Новые поля (временные, не в БД пока)
    material_size_id: Optional[int] = None
    material_size_obj: Optional[MaterialSize] = None
    product_variants: List[ProductSizeVariant] = field(default_factory=list)
    
    @property
    def material_size_display(self):
        """Для обратной совместимости"""
        if self.material_size_obj:
            return self.material_size_obj.display_name()
        return self.material_size or ""
    
    @property
    def product_sizes_display(self):
        """Для обратной совместимости"""
        if self.product_variants:
            return "; ".join([v.display_name() for v in self.product_variants])
        return self.product_size or ""
    
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
    
    def get_default_product_size(self) -> Optional[ProductSizeVariant]:
        """Получить вариант размера по умолчанию"""
        for variant in self.product_variants:
            if variant.is_default:
                return variant
        return self.product_variants[0] if self.product_variants else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'feed_rate': self.feed_rate,
            'material_size': self.material_size,  # старое поле
            'product_size': self.product_size,    # старое поле
            'image_data': self.image_data,
            'pdf_path': self.pdf_path
        }
    
    @classmethod
    def from_db_row(cls, row) -> 'Profile':
        """Create from database row"""
        # Преобразуем row в словарь если это sqlite3.Row
        if hasattr(row, 'keys'):
            row_dict = {key: row[key] for key in row.keys()}
            
            image_data = row_dict.get('Image') or row_dict.get('image_data')
            pdf_path = row_dict.get('pdf_path')
            
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
                pdf_path=pdf_path
            )
        else:
            image_data = None
            if len(row) > 6 and row[6]:
                image_data = row[6]
            elif len(row) > 8 and row[8]:
                image_data = row[8]
            
            if image_data is not None and isinstance(image_data, str):
                try:
                    image_data = image_data.encode('latin-1')
                except Exception as e:
                    print(f"Warning: Could not encode image_data string: {e}")
                    image_data = None
            
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
                pdf_path=pdf_path
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