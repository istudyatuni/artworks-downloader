from typing import Any
import json
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

def insert(slug: str, key: str, value: str | Any, as_json=False):
	# if not as json value should be string
	if as_json is False and not isinstance(value, str):
		raise Exception('Invalid value type')

	cursor.execute(INSERT_QUERY, {
		'key': _key(slug, key),
		'value': json.dumps(value) if as_json else value
	})
	conn.commit()

def select(slug: str, key: str, as_json=False):
	res = cursor.execute(SELECT_QUERY, (_key(slug, key),)).fetchone()
	if res is None:
		return res
	value = res['value']
	return json.loads(value) if as_json else value

def delete(slug: str, key: str):
	cursor.execute(DELETE_QUERY, (_key(slug, key),))
	conn.commit()
