from functools import partial
from os import makedirs
import re

mkdir = partial(makedirs, exist_ok=True)
print_inline = partial(print, end='\r', flush=True)

def filename_normalize(filename: str):
	# max filename size is 255
	# minus 4 for dot and file extension
	return re.sub(r'[<>:"\\\/|?*]', '_', filename)[:251]
