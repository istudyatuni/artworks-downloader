import os.path

from art_dl.utils.db import DB
from art_dl.utils.dirs import DIRS

CONFIG_DB = os.path.join(DIRS.config, 'config.db')
CONFIG_TABLE = 'configuration'


class Config():

	def __init__(self) -> None:
		self.db = DB(CONFIG_DB, CONFIG_TABLE)

	def get(self, key: str, default=None):
		return self.db.select(key) or default

	def set(self, key: str, value: str):
		self.db.insert(key, value)

	def check_value(self, key: str):
		value = self.get(key)
		if value is not None:
			print('Current value:', value)

	def input_entry(self, name=None):
		key = name or input('Enter key: ')
		if key is not None:
			self.check_value(key)

		value = input(f'Enter {name or "value"}: ')

		self.set(key, value)


config = Config()
