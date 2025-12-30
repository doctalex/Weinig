from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class Profile:
    """Модель профиля обработки"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    feed_rate: float = 2.5
    material_size: str = "100x100"
    product_size: str = "90x90"
    image_data: Optional[bytes] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'feed_rate': self.feed_rate,
            'material_size': self.material_size,
            'product_size': self.product_size,
            'image_data': self.image_data
        }
    
    @classmethod
    def from_db_row(cls, row) -> 'Profile':
        """Create from database row"""
        # The database has both 'Image' (index 6) and 'image_data' (index 8) columns
        # We'll use 'Image' if it has data, otherwise fall back to 'image_data'
        image_data = None
        if len(row) > 6 and row[6]:  # Check Image column first
            image_data = row[6]
        elif len(row) > 8 and row[8]:  # Fall back to image_data column
            image_data = row[8]
        
        return cls(
            id=row[0] if len(row) > 0 else None,
            name=row[1] if len(row) > 1 else "",
            description=row[2] if len(row) > 2 else "",
            feed_rate=row[3] if len(row) > 3 else 2.5,
            material_size=row[4] if len(row) > 4 else "100x100",
            product_size=row[5] if len(row) > 5 else "90x90",
            image_data=image_data
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