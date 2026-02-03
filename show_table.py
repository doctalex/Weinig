import sqlite3

conn = sqlite3.connect("tools_database.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(product_size_variants);")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
