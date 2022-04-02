from functools import partial

print_inline = partial(print, end='\r', flush=True)

def print_inline_end(*values, sep=None, end=' '):
	""" Print with ability continue printing on the same line. """
	print(*values, sep=sep, end=end, flush=True)
