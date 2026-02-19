# utils/backup_manager.py
"""
Менеджер резервного копирования базы данных
"""
import os
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
import zipfile

logger = logging.getLogger(__name__)

class BackupManager:
    """Управление резервными копиями базы данных"""
    
    def __init__(self, db_path, backup_dir=None):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir) if backup_dir else self.db_path.parent / "backups"
        
        # Создаем директорию для бэкапов если её нет
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"BackupManager initialized. DB: {self.db_path}, Backups: {self.backup_dir}")
    
    def create_backup(self, backup_type="manual", max_backups=10):
        """
        Создание резервной копии базы данных
        
        Args:
            backup_type: Тип бэкапа ("manual", "auto", "scheduled")
            max_backups: Максимальное количество хранимых бэкапов
        """
        try:
            # Проверяем существование базы данных
            if not self.db_path.exists():
                logger.error(f"Database file not found: {self.db_path}")
                return None
            
            # Генерируем имя файла с timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"weinig_backup_{timestamp}_{backup_type}"
            backup_path = self.backup_dir / f"{backup_name}.db"
            zip_path = self.backup_dir / f"{backup_name}.zip"
            
            # Создаем копию базы данных
            shutil.copy2(self.db_path, backup_path)
            
            # Создаем ZIP архив с базой
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(backup_path, arcname=f"{backup_name}.db")
            
            # Удаляем временный файл .db
            backup_path.unlink()
            
            # Получаем информацию о бэкапе
            backup_info = self._get_backup_info(zip_path)
            
            logger.info(f"Backup created: {zip_path.name} ({backup_info['size_mb']:.2f} MB)")
            
            # Очищаем старые бэкапы если превышен лимит
            self._cleanup_old_backups(max_backups)
            
            return {
                'path': str(zip_path),
                'name': zip_path.name,
                'timestamp': timestamp,
                'type': backup_type,
                'size_mb': backup_info['size_mb'],
                'db_size_mb': backup_info['db_size_mb']
            }
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    def _get_backup_info(self, backup_path):
        """Получает информацию о бэкапе"""
        try:
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            
            # Получаем информацию о базе данных внутри архива
            db_size_mb = 0
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                for file_info in zipf.infolist():
                    if file_info.filename.endswith('.db'):
                        db_size_mb = file_info.file_size / (1024 * 1024)
                        break
            
            return {
                'size_mb': size_mb,
                'db_size_mb': db_size_mb
            }
        except Exception as e:
            logger.error(f"Error getting backup info: {e}")
            return {'size_mb': 0, 'db_size_mb': 0}
    
    def _cleanup_old_backups(self, max_backups):
        """Удаляет старые бэкапы если их больше max_backups"""
        try:
            # Получаем список всех бэкапов
            backups = list(self.backup_dir.glob("weinig_backup_*.zip"))
            
            if len(backups) <= max_backups:
                return
            
            # Сортируем по времени создания (старые первыми)
            backups.sort(key=lambda x: x.stat().st_mtime)
            
            # Удаляем самые старые
            backups_to_delete = backups[:-max_backups]
            for backup in backups_to_delete:
                try:
                    backup.unlink()
                    logger.info(f"Deleted old backup: {backup.name}")
                except Exception as e:
                    logger.error(f"Error deleting backup {backup.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
    
    def list_backups(self):
        """Возвращает список всех доступных бэкапов"""
        backups = []
        
        try:
            for backup_file in self.backup_dir.glob("weinig_backup_*.zip"):
                stat = backup_file.stat()
                backup_info = self._get_backup_info(backup_file)
                
                backups.append({
                    'name': backup_file.name,
                    'path': str(backup_file),
                    'size_mb': backup_info['size_mb'],
                    'created': datetime.fromtimestamp(stat.st_mtime),
                    'modified': datetime.fromtimestamp(stat.st_ctime)
                })
            
            # Сортируем по дате создания (новые первыми)
            backups.sort(key=lambda x: x['created'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
        
        return backups
    
    def restore_backup(self, backup_name, restore_path=None):
        """
        Восстанавливает базу данных из бэкапа
        
        Args:
            backup_name: Имя файла бэкапа
            restore_path: Куда восстановить (по умолчанию оригинальный путь)
        """
        try:
            backup_path = self.backup_dir / backup_name
            
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_name}")
                return False
            
            # Создаем резервную копию текущей базы перед восстановлением
            if self.db_path.exists():
                temp_backup = self.db_path.parent / f"temp_pre_restore_{datetime.now().strftime('%H%M%S')}.db"
                shutil.copy2(self.db_path, temp_backup)
                logger.info(f"Created temporary backup before restore: {temp_backup.name}")
            
            # Восстанавливаем из архива
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Ищем файл .db в архиве
                db_files = [f for f in zipf.namelist() if f.endswith('.db')]
                if not db_files:
                    logger.error(f"No .db file found in backup: {backup_name}")
                    return False
                
                # Извлекаем базу данных
                target_path = restore_path if restore_path else self.db_path
                zipf.extract(db_files[0], path=self.backup_dir)
                
                # Перемещаем в целевое расположение
                extracted_path = self.backup_dir / db_files[0]
                shutil.move(extracted_path, target_path)
            
            logger.info(f"Database restored from backup: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    def get_backup_stats(self):
        """Возвращает статистику по бэкапам"""
        backups = self.list_backups()
        
        total_size = sum(b['size_mb'] for b in backups)
        oldest = min(b['created'] for b in backups) if backups else None
        newest = max(b['created'] for b in backups) if backups else None
        
        return {
            'total_backups': len(backups),
            'total_size_mb': total_size,
            'oldest_backup': oldest,
            'newest_backup': newest,
            'backup_dir': str(self.backup_dir)
        }
        
    def cleanup_temp_files(self, max_age_hours=24):
        """
        Удаляет старые временные файлы восстановления
        
        Args:
            max_age_hours: Максимальный возраст файлов в часах
        
        Returns:
            int: Количество удаленных файлов
        """
        try:
            import time
            from pathlib import Path
            
            # Находим все временные файлы
            db_dir = Path(self.db_path).parent
            temp_files = list(db_dir.glob("temp_pre_restore_*.db"))
            
            if not temp_files:
                logger.debug("No temporary restore files found")
                return 0
            
            current_time = time.time()
            deleted_count = 0
            
            for temp_file in temp_files:
                try:
                    # Проверяем возраст файла
                    file_age = current_time - temp_file.stat().st_mtime
                    file_age_hours = file_age / 3600
                    
                    if file_age_hours > max_age_hours:
                        # Удаляем файл
                        temp_file.unlink()
                        deleted_count += 1
                        logger.info(f"Cleaned up old temp file: {temp_file.name} "
                                  f"({file_age_hours:.1f} hours old)")
                    else:
                        logger.debug(f"Keeping temp file (too new): {temp_file.name} "
                                   f"({file_age_hours:.1f} hours)")
                        
                except FileNotFoundError:
                    # Файл уже удален
                    pass
                except Exception as e:
                    logger.error(f"Error processing temp file {temp_file.name}: {e}")
            
            logger.info(f"Temp files cleanup: {deleted_count} file(s) deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error in temp files cleanup: {e}")
            return 0
    
    def auto_cleanup_on_start(self, max_age_hours=2):
        """
        Автоматическая очистка при старте
        
        Args:
            max_age_hours: Максимальный возраст файлов
        
        Returns:
            int: Количество удаленных файлов
        """
        logger.info("Running automatic cleanup of temporary restore files...")
        return self.cleanup_temp_files(max_age_hours)