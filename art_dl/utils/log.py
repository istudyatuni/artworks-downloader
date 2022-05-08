from shutil import get_terminal_size
from typing import Optional

from art_dl.utils.print import print_inline_end

_verbose = False
_quiet = False

def set_verbosity(q: bool = False, v: bool = False):
	global _quiet
	global _verbose
	_quiet = q
	_verbose = v
	if _verbose and _quiet:
		# is it ok to do that?
		raise Exception('log configuration error: both quiet and verbose are True')

class Progress:
	i: int = 0
	total: int = 0

	def set(self, i: int, total: int):
		self.i = i
		self.total = total

	def __str__(self) -> str:
		return f'{self.i}/{self.total}'

class Logger:
	_log_prefix_str = None
	_inline = False

	def __init__(self, *, prefix=None, inline=False) -> None:
		self._inline = inline
		if prefix is not None:
			self.set_prefix(*prefix)

	def set_prefix(self, *parts: str, inline: bool | None=None):
		if inline is not None:
			self._inline = inline
		if len(parts) > 0:
			self._log_prefix_str = '[' + ']['.join(parts) + ']'

	@property
	def _print_func(self):
		return print_inline_end if self._inline else print

	@property
	def _log_prefix(self):
		if self._log_prefix_str is not None:
			prefix = '\r' if self._inline else ''
			return prefix + self._log_prefix_str

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
		if _verbose:
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
		if _quiet:
			return

		self._print(*values, progress=progress, sep=sep, end=end)

	def verbose(
		self,
		*values: object,
		progress: Optional[Progress]=None,
		sep=None,
		end=None,
	):
		if not _verbose:
			return

		self._print(*values, progress=progress, sep=sep, end=end)

	def warn(
		self,
		*values: object,
		progress: Optional[Progress]=None,
		sep=None,
		end='\n',
	):
		self._print(*values, progress=progress, sep=sep, end=end)

	@staticmethod
	def newline(*, quiet = False, verbose = False, normal = False):
		"""
		Pass `quiet=True` to print when quiet enabled, `verbose=True` to print
		when verbose enabled, `normal=True` when not quiet and not verbose enabled
		"""
		if (
			quiet and _quiet or
			verbose and _verbose or
			normal and _quiet is False and _verbose is False
		):
			print()
