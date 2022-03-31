import asyncio
from collections import namedtuple
from urllib.parse import urlparse
import aiofiles
import aiohttp
import json
import os.path

from app.utils import filename_normalize, filename_unhide, mkdir, print_inline

Art = namedtuple('Art', ['count', 'first_url', 'id', 'artist', 'title'])

HEADERS = {
	'referer': 'https://www.pixiv.net/',
}

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')
	if path[1] == 'artworks':
		return { 'type': 'art', 'id': path[2] }
	return { 'type': 'unknown' }

async def fetch_info(session: aiohttp.ClientSession, url: str, parsed: dict):
	print('Fetching data for', url)
	async with session.get(url) as response:
		data = await response.text()

	id_ind = data.find('meta-preload-data')
	script_ind = data.find('<script async', id_ind)

	# 28 is len of meta-preload-data" content='
	# 3 is back-offset from <script
	json_data = json.loads(data[id_ind + 28:script_ind - 3])
	art = json_data['illust'][parsed['id']]

	return Art(
		art['pageCount'],
		art['urls']['original'],
		parsed['id'],
		# username can begin with a dot
		filename_unhide(filename_normalize(art['userName'])),
		filename_normalize(art['title']),
	)

async def download_art(session: aiohttp.ClientSession, info: Art, save_folder: str):
	# https://i.pximg.net/img-original/img/.../xxx_p0.png
	base_url, ext = os.path.splitext(info.first_url)
	base_url = base_url[:-1]

	name = info.title + ext
	print(' ', 'Download:', name)
	for i in range(info.count):
		name = info.title + f'_p{i}' + ext
		print_inline(' ', i + 1)

		filename = os.path.join(save_folder, name)
		if os.path.exists(filename):
			print(' ', 'Skip existing:', filename)
			continue

		async with session.get(base_url + str(i) + ext) as response:
			async with aiofiles.open(filename, 'wb') as file:
				await file.write(await response.read())

async def download(urls: list[str], data_folder: str):
	async with aiohttp.ClientSession(headers=HEADERS) as session:
		for url in urls:
			parsed = parse_link(url)
			if parsed['type'] != 'art':
				print('Unsupported link:', url)
				continue

			info = await fetch_info(session, url, parsed)

			save_folder = os.path.join(data_folder, info.artist, info.id)
			mkdir(save_folder)

			while True:
				try:
					await download_art(session, info, save_folder)
					break
				except aiohttp.ServerDisconnectedError:
					print('Error, retrying in 5 seconds')
					await asyncio.sleep(5)
