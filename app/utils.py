from functools import partial
from os import makedirs
import re

mkdir = partial(makedirs, exist_ok=True)
print_inline = partial(print, end='\r', flush=True)

def filename_normalize(filename: str):
	return re.sub(r'[<>:"\\\/|?*]', '_', filename)
