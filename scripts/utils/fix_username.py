import sqlite3

conn = sqlite3.connect('data/onlyfans.db')
cursor = conn.cursor()
cursor.execute('UPDATE creators SET username=? WHERE username=?', ('lenatheplugtv', 'lenatheplug'))
conn.commit()
print(f'✅ 已更新 {cursor.rowcount} 条记录')
conn.close()
