import asyncio
from collections import namedtuple
from urllib.parse import parse_qs, urlparse
import aiofiles
import aiohttp
import json
import os

from app.utils import filename_normalize, filename_unhide, mkdir, print_inline
import app.cache as cache

SLUG = 'pixiv'
HEADERS = {
	'referer': 'https://www.pixiv.net/',
}
URL = 'https://www.pixiv.net/en/artworks/'

Parsed = namedtuple('Parsed', ['id'])

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')
	if parsed.netloc == 'zettai.moe':
		query = parse_qs(parsed.query)
		return Parsed(query['id'][0])
	if path[1] == 'artworks':
		return Parsed(path[2])
	return Parsed(None)

async def fetch_info(session: aiohttp.ClientSession, parsed: Parsed):
	url = URL + parsed.id
	print('Fetching data for', url)
	async with session.get(url) as response:
		data = await response.text()

	id_ind = data.find('meta-preload-data')
	script_ind = data.find('<script async', id_ind)

	# 28 is len of meta-preload-data" content='
	# 3 is back-offset from <script
	json_data = json.loads(data[id_ind + 28:script_ind - 3])
	art = json_data['illust'][parsed.id]

	return {
		'count': art['pageCount'],
		'first_url': art['urls']['original'],
		'id': parsed.id,
		# username can begin with a dot
		'artist': filename_unhide(filename_normalize(art['userName'])),
		'title': filename_normalize(art['title']),
	}

async def download_art(session: aiohttp.ClientSession, info: dict, save_folder: str):
	# https://i.pximg.net/img-original/img/.../xxx_p0.png
	base_url, ext = os.path.splitext(info['first_url'])
	base_url = base_url[:-1]

	name = info['title'] + ext
	print(' ', 'Download:', name)
	for i in range(info['count']):
		name = info['title'] + f'_p{i}' + ext
		print_inline(' ', i + 1)

		filename = os.path.join(save_folder, name)
		if os.path.exists(filename):
			print(' ', 'Skip existing:', filename)
			continue

		async with session.get(base_url + str(i) + ext) as response:
			async with aiofiles.open(filename, 'wb') as file:
				try:
					await file.write(await response.read())
				except:
					print('REMOVING EMPTY FILE')
					os.remove(filename)
					raise

async def download(urls: list[str], data_folder: str):
	async with aiohttp.ClientSession(headers=HEADERS) as session:
		for url in urls:
			parsed = parse_link(url)
			if parsed.id is None:
				print('Unsupported link:', url)
				continue

			cached: dict = cache.select(SLUG, parsed.id, as_json=True)

			if cached is None:
				info = await fetch_info(session, parsed)
				cache.insert(SLUG, parsed.id, info, as_json=True)
			else:
				print(url)
				info = cached

			save_folder = os.path.join(data_folder, info['artist'], info['id'])
			mkdir(save_folder)

			while True:
				try:
					await download_art(session, info, save_folder)
					break
				except aiohttp.ServerDisconnectedError:
					print('Error, retrying in 5 seconds')
					await asyncio.sleep(5)
