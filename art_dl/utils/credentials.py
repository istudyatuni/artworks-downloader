from art_dl.utils.db import DB

CREDS_DB = 'config.db'
CREDS_TABLE = 'credentials'


class Credentials:

	def __init__(self) -> None:
		self.db = DB(CREDS_DB, CREDS_TABLE)

	@staticmethod
	def _key(path: list[str]):
		return '.'.join(path)

	def get(self, path: list[str]):
		return self.db.select(self._key(path))

	def save(self, path: list[str], value: str):
		self.db.insert(self._key(path), value)

	def delete(self, path: list[str]):
		self.db.delete(self._key(path))


creds = Credentials()
