from glob import glob
from urllib.parse import urlparse
import aiofiles
import aiohttp
import os.path

from app.utils import mkdir

IMAGE_URL = 'https://w.wallhaven.cc/full/{prefix}/wallhaven-{id}'

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')

	if parsed.netloc == 'wallhaven.cc':
		# strip 'w'
		path.pop(0)
	# id: abcdef, prefix: ab
	return { 'id': path[0], 'prefix': path[0][0:2] }

async def fetch_image(session: aiohttp.ClientSession, url: str, name: str, folder: str):
	async with session.get(url) as response:
		if response.status == 404:
			print('Not found', name)
			return False
		async with aiofiles.open(os.path.join(folder, name), 'wb') as file:
			await file.write(await response.read())
			print('Download:', name)
			return True

async def download(urls_to_download: list[str] | str, data_folder: str):
	urls = urls_to_download if isinstance(urls_to_download, list) else [urls_to_download]
	mkdir(data_folder)

	async with aiohttp.ClientSession() as session:
		for url in urls:
			parsed = parse_link(url)
			existing = glob(f'{data_folder}/{parsed["id"]}.*')
			if len(existing) == 1:
				print('Skip existing:', parsed['id'])
				continue

			full_url = IMAGE_URL.format(prefix=parsed['prefix'], id=parsed['id'])
			name = parsed['id']
			exts = ['.jpg', '.png']

			for ext in exts:
				status = await fetch_image(session, full_url + ext, name + ext, data_folder)
				if status:
					break
