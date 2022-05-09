from json import load
from os.path import exists

CONFIG_FILE = 'config.json'


class Config():

	def __init__(self):
		if not exists(CONFIG_FILE):
			self._config = {}
			return

		with open(CONFIG_FILE) as file:
			self._config = load(file)

	def get(self, key: str, default=None):
		return self._config.get(key, default)


config = Config()
