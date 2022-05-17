from typing import Any

from art_dl.utils.db import DB

CACHE_DB = '.cache.db'


class Cache:

	def __init__(self) -> None:
		self.db = DB(CACHE_DB, 'cache')

	@staticmethod
	def _key(slug: str | None, key: str):
		return key if slug is None else slug + ':' + key

	def insert(self, slug: str | None, key: str, value: str | Any, *, as_json=False):
		self.db.insert(self._key(slug, key), value, as_json=as_json)

	def select(self, slug: str | None, key: str, *, as_json=False):
		return self.db.select(self._key(slug, key), as_json=as_json)

	def delete(self, slug: str | None, key: str):
		self.db.delete(self._key(slug, key))


cache = Cache()
