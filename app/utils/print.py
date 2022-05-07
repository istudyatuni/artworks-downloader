from functools import partial

print_inline = partial(print, end='\r', flush=True)

def print_inline_end(*values: object, sep=None, end=None):
	""" Print with ability to continue printing from the end of line. """
	print(*values, sep=sep, end=end if end is not None else ' ', flush=True)
