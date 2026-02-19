from dataclasses import dataclass, asdict, fields
from typing import Optional, List, Dict, Any, Tuple
import os
import json
from datetime import datetime
from textwrap import dedent
from tabulate import tabulate

@dataclass
class ToolLogEntry:
    """Class to hold tool information for logging."""
    head_number: int
    head_name: str
    tool_type: str
    tool_code: str
    rpm: Optional[int]
    pass_depth: Optional[float]

def format_tool_table(tools: List[ToolLogEntry]) -> str:
    """Format tools list as a pipe-delimited table matching the desired format."""
    if not tools:
        return "| Head | Type    | Tool Code | RPM  | Pass Depth |\n|------|---------|-----------|------|------------|\n"
    
    # Sort tools by head number
    tools_sorted = sorted(tools, key=lambda x: x.head_number)
    
    # Create table header
    table = "| Head | Type    | Tool Code | RPM  | Pass Depth |\n"
    table += "|------|---------|-----------|------|------------|\n"
    
    # Add each tool as a row
    for tool in tools_sorted:
        tool_type = tool.tool_type if tool.tool_type != "[Empty]" else "[Empty]"
        tool_code = tool.tool_code if tool.tool_code != "[Empty]" else "-"
        rpm = str(tool.rpm) if tool.rpm is not None else "-"
        pass_depth = f"{tool.pass_depth}" if tool.pass_depth is not None else "-"
        
        # Format the row with fixed-width columns
        row = f"| {tool.head_number:<4} | {tool_type:<7} | {tool_code:<9} | {rpm:<4} | {pass_depth:<10} |\n"
        table += row
    
    return table + "\n"

def format_profile_header(profile_name: str, feed_rate: float, 
                        material_size: str, product_size: str) -> str:
    """Format profile header information to match the desired output."""
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    return dedent(f"""
    ===========================================
    PROFILE Configuration
    ===========================================
    Date:           {date_str}
    Profile Name:   {profile_name}
    Feed Rate:      {feed_rate} m/min
    Material Size:  {material_size}
    Product Size:   {product_size}
    
    MILLING HEAD CONFIGURATION
    ===========================================
    """)

def log_job_configuration(
    profile_name: str,
    feed_rate: float,
    material_size: str,
    product_size: str,
    tools: List[ToolLogEntry],
    action_type: str = "JOB"
) -> bool:
    """
    Logs job configuration to job_edit.log with detailed information.
    
    Args:
        profile_name: Name of the profile
        feed_rate: Feed rate value in m/min
        material_size: Size of the material (e.g., '100x100')
        product_size: Size of the product (e.g., '90x90')
        tools: List of ToolLogEntry objects
        action_type: Type of action (default: "JOB")
        
    Returns:
        bool: True if logging was successful, False otherwise
    """
    try:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Create log file path with year and month
        month_str = datetime.now().strftime("%Y_%m")
        log_file = os.path.join(log_dir, f"job_edit_{month_str}.log")
        
        # Get current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Format the log content to match the desired format
        log_content = f"""
===========================================
{action_type} Configuration - {timestamp}
===========================================
Date:           {timestamp}
Profile Name:   {profile_name}
Feed Rate:      {feed_rate} m/min
Material Size:  {material_size}
Product Size:   {product_size}

MILLING HEAD CONFIGURATION
=================================================
| Head | Type    | Tool Code | RPM  | Pass Depth |
|------|---------|-----------|------|------------|"""
        
        # Add tool rows
        for tool in sorted(tools, key=lambda x: x.head_number):
            head = tool.head_number
            tool_type = tool.tool_type if tool.tool_type != "[Empty]" else "[Empty]"
            tool_code = tool.tool_code if tool.tool_code != "[Empty]" else "-"
            rpm = str(tool.rpm) if tool.rpm is not None else "-"
            pass_depth = f"{tool.pass_depth:.1f}" if tool.pass_depth is not None else "-"
            
            log_content += f"\n| {head:<4} | {tool_type:<7} | {tool_code:<9} | {rpm:<4} | {pass_depth:<10} |"
        
        # Add final separator
        log_content += "\n\n" + "="*50 + "\n\n"
        
        # Write to log file
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_content)
            
        return True
    except Exception as e:
        print(f"Error writing job configuration to log: {e}")
        return False

def log_profile_change(profile_data: dict) -> bool:
    """
    Log profile changes to profile_edit.log in the specified format.
    
    Args:
        profile_data: Dictionary containing profile data with the following keys:
            - name: Profile name
            - feed_rate: Feed rate value
            - material_size: Material dimensions
            - product_size: Product dimensions
            - tools: List of ToolLogEntry objects for the profile
            
    Returns:
        bool: True if logging was successful, False otherwise
    """
    try:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Create log file path with year and month
        month_str = datetime.now().strftime("%Y_%m")
        log_file = os.path.join(log_dir, f"profile_edit_{month_str}.log")
        
        # Get current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Format the log content
        log_content = f"""
===========================================
PROFILE Configuration - {timestamp}
===========================================
Date:           {timestamp}
Profile Name:   {profile_data.get('name', 'N/A')}
Feed Rate:      {profile_data.get('feed_rate', 'N/A')} m/min
Material Size:  {profile_data.get('material_size', 'N/A')}
Product Size:   {profile_data.get('product_size', 'N/A')}

===========================================
"""
        
        # Write to log file
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_content)
            
        return True
    except Exception as e:
        print(f"Error writing to profile edit log: {e}")
        return False