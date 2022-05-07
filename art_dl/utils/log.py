from shutil import get_terminal_size
from typing import Optional

from art_dl.utils.print import print_inline_end

verbose = False
quiet = False

def set_verbosity(q: bool = False, v: bool = False):
	global quiet
	global verbose
	quiet = q
	verbose = v
	if verbose and quiet:
		# is it ok to do that?
		raise Exception('log configuration error: both quiet and verbose are True')

class Progress:
	i: int = 0
	total: int = 0

	def __str__(self) -> str:
		return f'{self.i}/{self.total}'

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

	@staticmethod
	def _term_width():
		return get_terminal_size().columns

	@staticmethod
	def _make_print_str(*values: object, sep=None):
		# this function is for reduce number of the same calculations
		return (sep if sep else ' ').join(str(v) for v in values)

	def _print(
		self,
		*values: object,
		progress: Optional[Progress]=None,
		sep=None,
		end=None
	):
		if quiet:
			return
		if verbose:
			end = end if end else '\n'

		to_print = list(values)
		if progress is not None:
			to_print.insert(0, f'({progress})')
		if self._log_prefix is not None:
			to_print.insert(0, self._log_prefix)
		to_print = self._make_print_str(*to_print, sep=sep)

		# -1 to make cursor visible (subtract '\r')
		spaces_offset = self._term_width() - len(to_print) - 1
		self._print_func(to_print, ' ' * spaces_offset, sep=sep, end=end)

	def info(
		self,
		*values: object,
		progress: Optional[Progress]=None,
		sep=None,
		end=None,
	):
		self._print(*values, progress=progress, sep=sep, end=end)

	def verbose(
		self,
		*values: object,
		progress: Optional[Progress]=None,
		sep=None,
		end=None,
	):
		if verbose is False:
			return

		self._print(*values, progress=progress, sep=sep, end=end)
