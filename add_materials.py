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
    (50, 50, 'Economy Blank', 'Бюджетная заготовка'),
    (75, 50, 'Standard Blank', 'Стандартная заготовка'),
    (100, 50,'Blank', 'Blank'),
    (125, 50, 'Premium Blank', 'Премиум заготовка'),
    (150, 50, 'Small Blank', 'Малая заготовка'),
    (200.0, 50.0, 'Large Blank', 'Большая заготовка'),
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