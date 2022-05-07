from app.utils.print import print_inline_end

class DownloadStats:
	download = 0
	skip = 0

	def __add__(self, other: 'DownloadStats'):
		self.download += other.download
		self.skip += other.skip
		return self

	def __str__(self) -> str:
		return f'download: {self.download}, skip: {self.skip}'

class Logger:
	_log_prefix = None
	_print_func = print

	def __init__(self, *, prefix=None, inline=False) -> None:
		if prefix is not None:
			self.set_prefix(*prefix, inline=inline)
		if inline:
			self._print_func = print_inline_end

	def set_prefix(self, *parts: str, inline=False):
		self._log_prefix = '[' + ']['.join(parts) + ']'
		if inline:
			self._log_prefix = '\r' + self._log_prefix

	def _print(self, *values: object, sep=None, end=None):
		self._print_func(self._log_prefix, *values, sep=sep, end=end)

	def info(self, *values: object, sep=None, end=None):
		self._print(*values, sep=sep, end=end)
