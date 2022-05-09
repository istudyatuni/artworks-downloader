from sys import version_info

if version_info < (3, 10):
	print('Requires python 3.10+')
	quit(1)

# https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/__main__.py
import sys

if __package__ is None and not hasattr(sys, 'frozen'):
	# direct call of __main__.py
	import os.path
	path = os.path.realpath(os.path.abspath(__file__))
	sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

import art_dl

if __name__ == '__main__':
	art_dl.main()
