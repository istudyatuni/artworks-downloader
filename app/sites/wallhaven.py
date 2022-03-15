from glob import glob
from urllib.parse import urlparse
import aiofiles
import aiohttp
import os.path

from app.utils import filename_normalize, mkdir

API_URL = 'https://wallhaven.cc/api/v1/w/'

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')

	if parsed.netloc == 'wallhaven.cc':
		# strip 'w'
		path.pop(0)

	return { 'id': path[0] }

async def fetch_image(session: aiohttp.ClientSession, url: str, name: str, folder: str):
	async with session.get(url) as response:
		async with aiofiles.open(os.path.join(folder, name), 'wb') as file:
			await file.write(await response.read())
			print('Download:', name)

async def download(urls_to_download: list[str] | str, data_folder: str):
	urls = urls_to_download if isinstance(urls_to_download, list) else [urls_to_download]
	mkdir(data_folder)

	async with aiohttp.ClientSession() as session:
		for url in urls:
			parsed = parse_link(url)
			existing = glob(f'{data_folder}/{parsed["id"]} - *.*')
			if len(existing) == 1:
				print('Skip existing:', parsed['id'])
				continue

			async with session.get(API_URL + parsed['id']) as response:
				data = (await response.json())['data']

			full_url = data['path']
			name = (
				data['id']
				+ ' - '
				+ ', '.join(map(lambda tag: tag['name'], data['tags']))
			)
			name = filename_normalize(name) + os.path.splitext(full_url)[1]
			await fetch_image(session, full_url, name, data_folder)
