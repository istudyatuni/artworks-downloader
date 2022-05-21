import os

from art_dl.cache import CACHE_DB
from art_dl.utils.db import DB


class Cleanup:
	KEY = 'filename'

	def __init__(self) -> None:
		self.db = DB(CACHE_DB, 'cleanup')

	def set(self, filename: str):
		""" Remember file for cleaning """
		self.db.insert(self.KEY, filename)

	def forget(self):
		self.db.delete(self.KEY)

	def clean(self):
		""" Perform cleanup """
		filename = self.db.select(self.KEY)
		if filename is None:
			return
		if os.path.exists(filename):
			os.remove(filename)
		self.forget()


cleanup = Cleanup()
