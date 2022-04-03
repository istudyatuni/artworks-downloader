from functools import partial

print_inline = partial(print, end='\r', flush=True)

def print_inline_end(*values, sep=None, end=' '):
	""" Print with ability to continue printing from the end of line. """
	print(*values, sep=sep, end=end, flush=True)
