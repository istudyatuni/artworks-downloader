import os.path
import re
from functools import partial
from os import makedirs

mkdir = partial(makedirs, exist_ok=True)


def filename_unhide(filename: str):
	return '_' + filename if filename.startswith('.') else filename


def filename_normalize(filename: str):
	""" Normalize filename: replace `<` `>` `:` `"` `\\` `/` `|` `?` `*` with `_` """
	return re.sub(r'[<>:"\\\/|?*]', '_', filename)


def filename_shortening(filename: str, length=255, with_ext=False):
	""" Strip filename to 255 symbols """
	if with_ext:
		file, ext = os.path.splitext(filename)
		return file[:length - len(ext)] + ext

	return filename[:length]
