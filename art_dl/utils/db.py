import sqlite3 as sql
from json import dumps, loads
from typing import Any


class Queries:
	init = '''CREATE TABLE IF NOT EXISTS {table} (
		key TEXT NOT NULL PRIMARY KEY,
		value TEXT
	)'''
	insert = '''INSERT OR IGNORE INTO {table} (key, value) VALUES (:key, :value)'''
	select = '''SELECT value FROM {table} WHERE key = :key'''
	delete = '''DELETE FROM {table} WHERE key = :key'''

	def __init__(self, table: str) -> None:
		for q in ['init', 'insert', 'select', 'delete']:
			self.__setattr__(q, self.__getattribute__(q).format(table=table))


class DB:
	""" Key-value sqlite wrapper """

	def __init__(self, db_name: str, table: str) -> None:
		self.db_name = db_name
		self.queries = Queries(table)
		self.connect()

	def connect(self):
		self.conn = sql.connect(self.db_name)
		self.conn.row_factory = sql.Row
		self.cursor = self.conn.cursor()

		self.cursor.executescript(self.queries.init)
		self.conn.commit()

	def insert(self, key: str, value: str | Any, *, as_json=False):
		# if not as json value should be a string
		if as_json is False and not isinstance(value, str):
			raise TypeError('Value should be a string')

		self.cursor.execute(
			self.queries.insert, {
				'key': key,
				'value': dumps(value) if as_json else value,
			}
		)
		self.conn.commit()

	def select(self, key: str, *, as_json=False):
		res = self.cursor.execute(self.queries.select, {
			'key': key
		}).fetchone()
		if res is None:
			return res
		value = res['value']
		return loads(value) if as_json else value

	def delete(self, key: str):
		self.cursor.execute(self.queries.delete, { 'key': key })
		self.conn.commit()
