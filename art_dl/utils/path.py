from functools import partial
from os import makedirs
import os.path
import re

mkdir = partial(makedirs, exist_ok=True)


def filename_unhide(filename: str):
	return '_' + filename if filename.startswith('.') else filename


def filename_normalize(filename: str):
	""" Normalize filename: replace `<` `>` `:` `"` `\\` `/` `|` `?` `*` with `_` """
	return re.sub(r'[<>:"\\\/|?*]', '_', filename)


def filename_shortening(filename: str, with_ext=False):
	""" Strip filename to 255 symbols """
	if with_ext:
		file, ext = os.path.splitext(filename)
		return file[:255 - len(ext)] + ext

	return filename[:255]
