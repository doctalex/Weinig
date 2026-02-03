# add_test_materials.py
import sqlite3

conn = sqlite3.connect('tools_database.db')
cursor = conn.cursor()

# Создаем таблицу если нет
cursor.execute('''
    CREATE TABLE IF NOT EXISTS material_sizes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        width REAL NOT NULL,
        thickness REAL NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Добавляем тестовые данные
materials = [
    (50, 50, 'Thermowood', 'WT'),
    (75, 50, 'Thermowood', 'WT'),
    (100, 50,'Thermowood', 'WT'),
    (125, 50, 'Thermowood', 'WT'),
    (150, 50, 'Thermowood', 'WT'),
    (200, 50, 'Thermowood', 'WT'),
    (75, 32, 'Thermowood', 'WT'),
    (100, 32, 'Thermowood', 'WT'),
    (125, 32, 'Thermowood', 'WT'),
    (150, 32, 'Thermowood', 'WT'),
    (150, 38, 'Thermowood', 'WT'),
    (100, 25, 'Thermowood', 'WT'),
    (125, 25, 'Thermowood', 'WT'),
    (150, 25, 'Thermowood', 'WT'),
    (200, 25, 'Thermowood', 'WT'),
]

cursor.executemany(
    'INSERT INTO material_sizes (width, thickness, name, description) VALUES (?, ?, ?, ?)',
    materials
)

conn.commit()
print(f"Добавлено {cursor.rowcount} заготовок")

# Проверяем
cursor.execute('SELECT * FROM material_sizes')
for row in cursor.fetchall():
    print(f"ID {row[0]}: {row[1]}x{row[2]}мм - {row[3]}")

conn.close()