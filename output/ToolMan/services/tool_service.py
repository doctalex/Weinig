"""
Tool management service
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from core.database import DatabaseManager
from core.models import Tool, ToolAssignment
from core.tool_codes import ToolCodeGenerator
from core.observable import Observable

# ДОБАВЛЯЕМ ИМПОРТ МЕНЕДЖЕРА БЕЗОПАСНОСТИ
from config.security import SecurityManager

logger = logging.getLogger(__name__)


class ToolService(Observable):
    """Tool management service"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.code_generator = ToolCodeGenerator()
        # ДОБАВЛЯЕМ ИНИЦИАЛИЗАЦИЮ МЕНЕДЖЕРА БЕЗОПАСНОСТИ
        self.security = SecurityManager()
    
    # === ВСПОМОГАТЕЛЬНЫЙ МЕТОД ДЛЯ ПРОВЕРКИ ДОСТУПА ===
    def _check_edit_permission(self) -> bool:
        """Check if editing is allowed in current security mode"""
        return not self.security.is_read_only()
    
    def _raise_if_read_only(self):
        """Raise error if in read-only mode"""
        if self.security.is_read_only():
            raise PermissionError(
                "This operation is not available in Read Only mode.\n\n"
                "Please switch to Full Access mode by pressing Ctrl+Shift+F."
            )
    
    def get_all_tools(self) -> List[Tool]:
        """Получить все инструменты из базы"""
        with self.Session() as session:
            return session.query(Tool).all()
    
    def get_tools_by_profile(self, profile_id: int) -> List[Tool]:
        """Gets tools for a profile"""
        rows = self.db.get_tools_by_profile(profile_id)
        return [Tool.from_db_row(row) for row in rows] if rows else []
    
    def get_tool(self, tool_id: int) -> Optional[Tool]:
        """Gets a tool by ID"""
        row = self.db.get_tool(tool_id)
        if row:
            return Tool.from_db_row(row)
        return None
    
    def get_tool_by_template_id(self, template_id: str) -> Optional[Tool]:
        """Gets a tool by its template ID"""
        if not template_id:
            return None
        row = self.db.execute_query(
            'SELECT * FROM Tools WHERE Template_ID = ?',
            (template_id,),
            fetch_one=True
        )
        return Tool.from_db_row(row) if row else None
    
    def get_tool_by_code(self, tool_code: str) -> Optional[Tool]:
        """Gets a tool by its code"""
        row = self.db.execute_query(
            'SELECT * FROM Tools WHERE Auto_Generated_Code = ?',
            (tool_code,),
            fetch_one=True
        )
        if row:
            return Tool.from_db_row(row)
        return None
    
    def is_tool_assigned(self, tool_id: int) -> bool:
        """Checks if a tool is assigned"""
        result = self.db.execute_query(
            'SELECT COUNT(*) as count FROM Tool_Assignments WHERE Tool_ID = ?',
            (tool_id,),
            fetch_one=True
        )
        return result and result['count'] > 0
    
    def get_available_tools_for_position(self, profile_id: int, 
                                       position: str) -> List[Tool]:
        """Gets tools for the specified position"""
        tools = self.get_tools_by_profile(profile_id)
        return [t for t in tools if t.position == position]
    
    def get_tool_assignments(self, profile_id: int) -> Dict[int, ToolAssignment]:
        """Gets tool assignments"""
        assignments = {}
        assignments_dict = self.db.get_tool_assignments(profile_id)
        
        for head_num, data in assignments_dict.items():
            assignments[head_num] = ToolAssignment(
                id=data['ID'],
                profile_id=data['Profile_ID'],
                tool_id=data['Tool_ID'],
                head_number=data['Head_Number'],
                rpm=data['RPM'],
                pass_depth=data['Pass_Depth'],
                work_material=data.get('Work_Material', ''),
                remarks=data.get('Remarks', ''),
                tool_code=data.get('Tool_Code', '')
            )
    
        return assignments
    
    def get_head_position_mapping(self) -> Dict[int, str]:
        """Returns a mapping of heads to positions"""
        return {
            1: "Bottom", 2: "Top", 3: "Right", 4: "Left",
            5: "Right", 6: "Left", 7: "Top", 8: "Bottom",
            9: "Top", 10: "Bottom"
        }
    
    def get_required_position_for_head(self, head_number: int) -> Optional[str]:
        """Gets the required position for a head"""
        mapping = self.get_head_position_mapping()
        return mapping.get(head_number)
    
    # === МЕТОДЫ РЕДАКТИРОВАНИЯ (добавляем проверки) ===
    
    def create_tool(self, tool: Tool) -> Tuple[Optional[int], Optional[str]]:
        """
        Creates a new tool
        Returns (tool_id, tool_code) or (None, None) on error
        """
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        self._raise_if_read_only()
        
        try:
            # Generate code
            tool.code = self.code_generator.generate(
                tool.profile_id, tool.position, 
                tool.tool_type, tool.set_number
            )
            
            # Check code uniqueness
            existing_tool = self.get_tool_by_code(tool.code)
            if existing_tool:
                raise ValueError(f"Tool with code {tool.code} already exist.")
            
            # Save to database
            tool_id = self.db.add_tool(tool.to_dict())
            
            # Notify observers
            self.notify_observers('tool_created', tool_id, tool.code)
            
            return tool_id, tool.code
                
        except ValueError as ve:
            # Re-raise validation errors to show to user
            raise ve
        except Exception as e:
            logger.error(f"Error creating tool: {e}")
            raise ValueError("An error occurred while creating the tool. Please check the input data and try again.")
    
    def update_tool(self, tool_id: int, tool: Tool) -> bool:
        """Updates a tool"""
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        self._raise_if_read_only()
        
        try:
            # If key parameters changed, generate a new code
            original = self.get_tool(tool_id)
            if original:
                code_changed = (
                    original.profile_id != tool.profile_id or
                    original.position != tool.position or
                    original.tool_type != tool.tool_type or
                    original.set_number != tool.set_number
                )
                
                if code_changed:
                    tool.code = self.code_generator.generate(
                        tool.profile_id, tool.position,
                        tool.tool_type, tool.set_number
                    )
            
            # Update in database
            success = self.db.update_tool(tool_id, tool.to_dict())
            
            if success:
                self.notify_observers('tool_updated', tool_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating tool: {e}")
            return False
    
    def delete_tool(self, tool_id: int) -> bool:
        """Deletes a tool"""
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        self._raise_if_read_only()
        
        try:
            # Check if the tool is in use
            if self.is_tool_assigned(tool_id):
                raise ValueError("Cannot delete tool: The tool is assigned to a head. Please remove it from the head first.")
            
            success = self.db.delete_tool(tool_id)
            
            if success:
                self.notify_observers('tool_deleted', tool_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting tool: {e}")
            return False
    
    def assign_tool_to_head(self, profile_id: int, head_number: int,
                          tool_id: int, rpm: int = None, 
                          pass_depth: float = None,
                          work_material: str = '',
                          remarks: str = '') -> bool:
        """Assigns a tool to a head"""
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        self._raise_if_read_only()
        
        success = self.db.assign_tool_to_head(
            profile_id, head_number, tool_id,
            rpm, pass_depth, work_material, remarks
        )
        
        if success:
            self.notify_observers('tool_assigned', 
                                profile_id, head_number, tool_id)
        
        return success
    
    def clear_head_assignment(self, profile_id: int, head_number: int) -> bool:
        """Clears assignment on a head"""
        # ПРОВЕРКА ДОСТУПА (НОВОЕ)
        self._raise_if_read_only()
        
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM Tool_Assignments WHERE Profile_ID = ? AND Head_Number = ?",
                    (profile_id, head_number)
                )
                conn.commit()
                
                self.notify_observers('assignment_cleared', profile_id, head_number)
                return True
                
        except Exception as e:
            logger.error(f"Error clearing assignment: {e}")
            return False

