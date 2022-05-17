from json import dumps, loads
from typing import Any
import sqlite3 as sl

CACHE_DB = '.cache.db'

INIT_QUERY = '''CREATE TABLE IF NOT EXISTS cache (
	key TEXT NOT NULL PRIMARY KEY,
	value TEXT
)'''
DELETE_QUERY = '''DELETE FROM cache WHERE key = :key'''
INSERT_QUERY = '''INSERT OR IGNORE INTO cache (key, value) VALUES (:key, :value)'''
SELECT_QUERY = '''SELECT value FROM cache WHERE key = :key'''


class Cache:

	def __init__(self) -> None:
		self.conn = sl.connect(CACHE_DB)
		self.conn.row_factory = sl.Row
		self.cursor = self.conn.cursor()

		self.cursor.executescript(INIT_QUERY)
		self.conn.commit()

	@staticmethod
	def _key(slug: str | None, key: str):
		return key if slug is None else slug + ':' + key

	def insert(self, slug: str | None, key: str, value: str | Any, *, as_json=False):
		# if not as json value should be string
		if as_json is False and not isinstance(value, str):
			raise Exception('Invalid value type')

		self.cursor.execute(
			INSERT_QUERY, {
				'key': self._key(slug, key),
				'value': dumps(value) if as_json else value
			}
		)
		self.conn.commit()

	def select(self, slug: str | None, key: str, *, as_json=False):
		res = self.cursor.execute(SELECT_QUERY, (self._key(slug, key), )).fetchone()
		if res is None:
			return res
		value = res['value']
		return loads(value) if as_json else value

	def delete(self, slug: str | None, key: str):
		self.cursor.execute(DELETE_QUERY, (self._key(slug, key), ))
		self.conn.commit()


cache = Cache()
