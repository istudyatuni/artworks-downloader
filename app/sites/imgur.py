from aiohttp import ClientSession
from collections import namedtuple
from typing import Any
from urllib.parse import urlparse
import os.path

from app.utils.download import download_binary
from app.utils.path import filename_normalize, mkdir
from app.utils.print import print_inline_end
import app.cache as cache

# client_id just from devtools
API_ALBUM_URL = 'https://api.imgur.com/post/v1/media/{id}?client_id=546c25a59c58ad7&include=media'
SLUG = 'imgur'

Parsed = namedtuple('Parsed', ['id'])

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')

	if path[0] == 'a' or path[0] == 'gallery':
		# https://imgur.com/a/<id>
		# https://imgur.com/gallery/<id>
		return Parsed(path[1])

	if path[0] == 't':
		# https://imgur.com/t/<tag>/<id>
		return Parsed(path[2])

	if len(path) == 1:
		# https://imgur.com/<id>
		return Parsed(path[0])

	return Parsed(None)

async def fetch_info(session: ClientSession, album_id: str) -> Any:
	async with session.get(API_ALBUM_URL.format(id=album_id)) as response:
		response.raise_for_status()
		info = await response.json()
	return {
		'id': info['id'],
		'title': info['title'],
		'media': list({
			'id': image['id'],
			'url': image['url'],
			'ext': image['ext'],
			'title': image['metadata']['title']
		} for image in info['media'])
	}

async def download_art(
	session: ClientSession,
	url: str,
	save_folder: str,
	name: str,
	indent=False
):
	indent_str = '  ' if indent else ''
	filename = os.path.join(save_folder, name)
	if os.path.exists(filename):
		return print(indent_str + 'Skip existing:', name)

	print_inline_end(indent_str + 'Download', name)
	await download_binary(session, url, filename)
	print('OK')

async def download(urls: list[str], data_folder: str):
	sep = ' - '

	async with ClientSession() as session:
		for url in urls:
			parsed = parse_link(url)

			if parsed.id is None:
				print('Unsupported link', url)
				continue

			cached = cache.select(SLUG, parsed.id, as_json=True)

			if cached is None:
				info = await fetch_info(session, parsed.id)
				cache.insert(SLUG, parsed.id, info, as_json=True)
			else:
				info = cached

			media = info['media']
			one_media = len(media) == 1
			title = sep.join([info['title'], info['id']]).strip(sep)
			title = filename_normalize(title)

			if one_media:
				save_folder = data_folder
			else:
				print(title)
				save_folder = os.path.join(data_folder, title)
				title = ''
			mkdir(save_folder)

			for image in media:
				title = (
					sep
					.join([title, image['title'], image['id']])
					.strip(sep)
					.replace(sep * 2, sep)
				)
				await download_art(
					session,
					image['url'],
					save_folder,
					title + '.' + image['ext'],
					indent=not one_media
				)
