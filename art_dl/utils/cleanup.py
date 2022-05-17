import os

from art_dl.cache import cache


class Cleanup:
	KEY = 'CLEANUP'

	def set(self, filename: str):
		""" Remember file for cleaning """
		cache.insert(None, self.KEY, filename)

	def forget(self):
		cache.delete(None, self.KEY)

	def clean(self):
		""" Perform cleanup """
		filename = cache.select(None, self.KEY)
		if filename is None:
			return
		if os.path.exists(filename):
			os.remove(filename)
		self.forget()


cleanup = Cleanup()
