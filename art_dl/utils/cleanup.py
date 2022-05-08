import os

import art_dl.cache as cache

class Cleanup:
	KEY = 'CLEANUP'

	def set(self, filename: str):
		cache.insert(None, self.KEY, filename)

	def remove(self):
		cache.delete(None, self.KEY)

	def clean(self):
		filename = cache.select(None, self.KEY)
		if filename is None:
			return
		if os.path.exists(filename):
			os.remove(filename)
		self.remove()

cleanup = Cleanup()
