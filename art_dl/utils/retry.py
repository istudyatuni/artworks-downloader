from art_dl.cache import cache


class Retry:
	KEY = 'RETRY'

	_old_list: list[str] = []

	def get(self) -> list[str] | None:
		return cache.select(None, self.KEY, as_json=True)

	def add(self, to_retry: list[str] | str):
		urls = self.get() or []
		if isinstance(to_retry, list):
			urls.extend(to_retry)
		else:
			urls.append(to_retry)

		cache.insert(None, self.KEY, urls, as_json=True)

	def clear(self, *, force=False):
		if force:
			self._old_list = []
		else:
			# save to prevent urls lost, for example on crash
			# replace old list instead of extend to not saving old urls
			self._old_list = self.get() or []

		cache.delete(None, self.KEY)

	def __del__(self):
		if len(self._old_list) > 0:
			self.add(self._old_list)


retry = Retry()
