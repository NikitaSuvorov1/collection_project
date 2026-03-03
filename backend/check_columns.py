import sqlite3
c = sqlite3.connect('db.sqlite3')
cols = [i[1] for i in c.execute('PRAGMA table_info(collection_app_intervention)').fetchall()]
with open('columns.txt', 'w') as f:
    f.write('\n'.join(cols))
print('Done')
