"""
Data export utilities
"""
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ExportUtils:
    """Data export utilities"""
    
    @staticmethod
    def export_to_json(data: List[Dict[str, Any]], filepath: str) -> bool:
        """Exports data to a JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return False
    
    @staticmethod
    def export_to_csv(data: List[Dict[str, Any]], filepath: str) -> bool:
        """Exports data to a CSV file"""
        if not data:
            return False
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            return True
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False
    
    @staticmethod
    def export_to_text(data: List[Dict[str, Any]], filepath: str) -> bool:
        """Exports data to a text file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for item in data:
                    f.write("-" * 50 + "\n")
                    for key, value in item.items():
                        f.write(f"{key}: {value}\n")
            return True
        except Exception as e:
            logger.error(f"Error exporting to text: {e}")
            return False
    
    @staticmethod
    def generate_filename(prefix: str, extension: str = "txt") -> str:
        """Generates a filename with a timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
    
    @staticmethod
    def export_tool_assignments(assignments: Dict[int, Dict[str, Any]], 
                               profile_name: str) -> str:
        """Generates a tool assignments report"""
        lines = []
        lines.append(f"Tool Assignments Report")
        lines.append(f"Profile: {profile_name}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        
        head_names = {
            1: "1 Bottom", 2: "1 Top", 3: "1 Right", 4: "1 Left",
            5: "2 Right", 6: "2 Left", 7: "2 Top", 8: "2 Bottom",
            9: "3 Top", 10: "3 Bottom"
        }
        
        assigned_count = 0
        for head_num in range(1, 11):
            head_name = head_names.get(head_num, f"Head {head_num}")
            
            if head_num in assignments:
                assignment = assignments[head_num]
                tool_code = assignment.get('tool_code', '-')
                rpm = assignment.get('rpm', '-')
                pass_depth = assignment.get('pass_depth', '-')
                material = assignment.get('work_material', '-')
                
                lines.append(f"{head_name}:")
                lines.append(f"  Tool: {tool_code}")
                lines.append(f"  RPM: {rpm}")
                lines.append(f"  Pass Depth: {pass_depth}mm")
                lines.append(f"  Material: {material}")
                assigned_count += 1
            else:
                lines.append(f"{head_name}: [No tool assigned]")
            
            lines.append("-" * 40)
        
        lines.append(f"\nSummary: {assigned_count}/10 heads assigned")
        
        return "\n".join(lines)