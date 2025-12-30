import os
import shutil
from pathlib import Path

def delete_files_by_extension(directory, extensions):
    """Delete files with given extensions in directory and subdirectories"""
    deleted = []
    for ext in extensions:
        for file_path in Path(directory).rglob(f"*{ext}"):
            try:
                file_path.unlink()
                deleted.append(str(file_path))
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
    return deleted

def delete_dirs(directory, dir_names):
    """Delete directories with given names in directory and subdirectories"""
    deleted = []
    for dir_name in dir_names:
        for dir_path in Path(directory).rglob(dir_name):
            try:
                if dir_path.is_dir():
                    shutil.rmtree(dir_path)
                    deleted.append(str(dir_path))
            except Exception as e:
                print(f"Error deleting directory {dir_path}: {e}")
    return deleted

def delete_specific_files(directory, file_names):
    """Delete specific files by name in directory and subdirectories"""
    deleted = []
    for file_name in file_names:
        for file_path in Path(directory).rglob(file_name):
            try:
                if file_path.is_file():
                    file_path.unlink()
                    deleted.append(str(file_path))
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
    return deleted

def main():
    # Get the project root directory
    project_dir = Path(__file__).parent.absolute()
    print(f"Cleaning up project in: {project_dir}")
    
    # 1. Delete Python cache files
    print("\nDeleting Python cache files...")
    deleted_pyc = delete_files_by_extension(project_dir, ['.pyc', '.pyo', '.pyd'])
    print(f"Deleted {len(deleted_pyc)} .pyc/.pyo/.pyd files")
    
    # 2. Delete __pycache__ directories
    print("\nDeleting __pycache__ directories...")
    deleted_dirs = delete_dirs(project_dir, ['__pycache__'])
    print(f"Deleted {len(deleted_dirs)} __pycache__ directories")
    
    # 3. Delete build and distribution files
    print("\nDeleting build and distribution files...")
    build_files = [
        'Weinig_Hydromat.spec', 'main.spec', 'setup.iss',
        'build.py', 'prep_exe.py', 'requirements-build.txt'
    ]
    deleted_build = delete_specific_files(project_dir, build_files)
    print(f"Deleted {len(deleted_build)} build/distribution files")
    
    # 4. Delete test/utility scripts (if they exist)
    print("\nDeleting test/utility scripts...")
    test_files = ['check_pil.py', 'check_win7.py']
    deleted_tests = delete_specific_files(project_dir, test_files)
    print(f"Deleted {len(deleted_tests)} test/utility files")
    
    # 5. Delete empty __init__.py files
    print("\nChecking for empty __init__.py files...")
    empty_inits = []
    for init_path in Path(project_dir).rglob('__init__.py'):
        try:
            if os.path.getsize(init_path) == 0:
                init_path.unlink()
                empty_inits.append(str(init_path))
        except Exception as e:
            print(f"Error checking {init_path}: {e}")
    print(f"Deleted {len(empty_inits)} empty __init__.py files")
    
    # 6. Clean up build and dist directories
    print("\nCleaning up build and dist directories...")
    build_dirs = ['build', 'dist']
    deleted_build_dirs = []
    for dir_name in build_dirs:
        dir_path = project_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            try:
                shutil.rmtree(dir_path)
                deleted_build_dirs.append(str(dir_path))
            except Exception as e:
                print(f"Error deleting {dir_path}: {e}")
    print(f"Deleted {len(deleted_build_dirs)} build/dist directories")
    
    # Print summary
    print("\n" + "="*50)
    print("Cleanup Complete!")
    print("="*50)
    print(f"Total files deleted: {len(deleted_pyc) + len(deleted_build) + len(deleted_tests) + len(empty_inits)}")
    print(f"Total directories deleted: {len(deleted_dirs) + len(deleted_build_dirs)}")
    print("\nProject cleanup completed successfully!")

if __name__ == "__main__":
    main()
