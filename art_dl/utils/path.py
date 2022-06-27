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


def _filename_shortening_ascii(filename: str, length=255, with_ext=False):
	if with_ext:
		file, ext = os.path.splitext(filename)
		return file[:length - len(ext)] + ext

	return filename[:length]


def _filename_shortening_unicode(filename: str, length=255, with_ext=False):
	""" Strip filename to `length` bytes """
	new_filename = ''
	ext = ''
	bytes_len = 0

	if with_ext:
		filename, ext = os.path.splitext(filename)
		length -= len(ext)

	for ch in filename:
		bytes_len += len(bytes(ch, encoding='utf-8'))
		if bytes_len > length:
			break

		new_filename += ch

	return new_filename + ext


def filename_shortening(filename: str, length=255, *, with_ext=False):
	"""
	Strip filename to `length` symbols if it's a valid ascii string
	and to `length` bytes if a string contains unicode characters
	"""
	if len(bytes(filename, encoding='utf-8')) == len(filename):
		return _filename_shortening_ascii(filename, length, with_ext)

	return _filename_shortening_unicode(filename, length, with_ext)
