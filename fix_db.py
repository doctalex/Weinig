# fix_database.py
import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database():
    """Добавляет недостающие столбцы в базу данных"""
    
    conn = sqlite3.connect('tools_database.db')
    cursor = conn.cursor()
    
    try:
        # Проверить существующие столбцы в profiles
        cursor.execute("PRAGMA table_info(profiles)")
        columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"Existing columns in profiles: {columns}")
        
        # Добавить pdf_path если отсутствует
        if 'pdf_path' not in columns:
            logger.info("Adding pdf_path column to profiles table...")
            cursor.execute("ALTER TABLE profiles ADD COLUMN pdf_path TEXT")
            logger.info("pdf_path column added successfully")
        
        # Проверить другие таблицы на отсутствующие столбцы
        tables_to_check = {
            'profiles': ['name', 'description', 'image_data', 'pdf_path'],
            'tools': ['code', 'profile_id', 'position', 'tool_type', 'set_number', 
                     'knives_count', 'template_id', 'status', 'service_notes', 
                     'notes', 'photo', 'created_at'],
            'heads': ['head_number', 'tool_id', 'parameters', 'notes']
        }
        
        for table, expected_columns in tables_to_check.items():
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            for column in expected_columns:
                if column not in existing_columns:
                    logger.info(f"Adding {column} column to {table} table...")
                    # Определить тип столбца
                    if column in ['image_data', 'photo']:
                        col_type = 'BLOB'
                    elif column in ['created_at']:
                        col_type = 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                    else:
                        col_type = 'TEXT'
                    
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        
        conn.commit()
        logger.info("Database structure updated successfully!")
        
    except Exception as e:
        logger.error(f"Error fixing database: {e}")
        conn.rollback()
    finally:
        conn.close()

def backup_database():
    """Создать резервную копию базы данных"""
    import shutil
    from datetime import datetime
    
    backup_name = f"tools_database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2('tools_database.db', backup_name)
    logger.info(f"Database backed up as {backup_name}")
    return backup_name

if __name__ == "__main__":
    print("=" * 50)
    print("Database Fix Tool")
    print("=" * 50)
    
    # Создать резервную копию
    backup_file = backup_database()
    print(f"✓ Backup created: {backup_file}")
    
    # Исправить базу данных
    fix_database()
    
    print("=" * 50)
    print("Fix completed!")
    print("Please restart the application.")