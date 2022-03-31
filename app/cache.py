import sqlite3 as sl

CACHE_DB = '.cache.db'

INIT_QUERY = '''CREATE TABLE IF NOT EXISTS cache (
	key TEXT NOT NULL PRIMARY KEY,
	value TEXT
)'''
DELETE_QUERY = '''DELETE FROM cache WHERE key = :key'''
INSERT_QUERY = '''INSERT OR IGNORE INTO cache (key, value) VALUES (:key, :value)'''
SELECT_QUERY = '''SELECT value FROM cache WHERE key = :key'''

conn = sl.connect(CACHE_DB)
conn.row_factory = sl.Row
cursor = conn.cursor()

cursor.executescript(INIT_QUERY)
conn.commit()

def _key(slug: str, key: str):
	return slug + ':' + key

def insert(slug: str, key: str, value: str):
	cursor.execute(INSERT_QUERY, {
		'key': _key(slug, key),
		'value': value
	})
	conn.commit()

def select(slug: str, key: str):
	res = cursor.execute(SELECT_QUERY, (_key(slug, key),)).fetchone()
	return res if res is None else res['value']

def delete(slug: str, key: str):
	cursor.execute(DELETE_QUERY, (_key(slug, key),))
	conn.commit()
