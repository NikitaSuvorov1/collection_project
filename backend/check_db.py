import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# Список таблиц
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print("=== ТАБЛИЦЫ ===")
for t in cur.fetchall():
    print(f"  {t[0]}")

# Количество записей в основных таблицах
print("\n=== КОЛИЧЕСТВО ЗАПИСЕЙ ===")
tables = [
    'collection_app_client',
    'collection_app_operator', 
    'collection_app_credit',
    'collection_app_creditstate',
    'collection_app_payment',
    'collection_app_intervention',
    'collection_app_assignment',
    'collection_app_scoringresult',
    'collection_app_creditapplication',
    'collection_app_clientbehaviorprofile',
    'collection_app_nextbestaction',
    'collection_app_smartscript',
    'collection_app_returnforecast',
    'collection_app_compliancealert',
    'collection_app_conversationanalysis',
]

for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        name = table.replace('collection_app_', '')
        print(f"  {name}: {count}")
    except:
        pass

# Пример клиента
print("\n=== ПРИМЕР КЛИЕНТА ===")
cur.execute("SELECT id, full_name, phone_mobile, city FROM collection_app_client LIMIT 3")
for row in cur.fetchall():
    print(f"  ID={row[0]}, {row[1]}, {row[2]}, {row[3]}")

conn.close()
