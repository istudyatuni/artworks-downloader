from functools import partial

print_inline = partial(print, end='\r', flush=True)
