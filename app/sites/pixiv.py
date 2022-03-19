from collections import namedtuple
from urllib.parse import urlparse
import aiofiles
import aiohttp
import json
import os.path

from app.utils import filename_normalize, mkdir, print_inline

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

async def download(urls_to_download: list[str] | str, data_folder: str):
	urls = urls_to_download if isinstance(urls_to_download, list) else [urls_to_download]

	async with aiohttp.ClientSession(headers=HEADERS) as session:
		for url in urls:
			parsed = parse_link(url)
			if parsed['type'] != 'art':
				print('Unsupported link:', url)
				continue

			print('Fetching data for', url)
			async with session.get(url) as response:
				data = await response.text()

			id_ind = data.find('meta-preload-data')
			script_ind = data.find('<script async', id_ind)

			# 28 is len of meta-preload-data" content='
			# 3 is back-offset from <script
			json_data = json.loads(data[id_ind + 28:script_ind - 3])
			art = json_data['illust'][parsed['id']]

			info = Art(
				art['pageCount'],
				art['urls']['original'],
				parsed['id'],
				filename_normalize(art['userName']),
				filename_normalize(art['title']),
			)

			save_folder = os.path.join(data_folder, info.artist, info.id)
			mkdir(save_folder)

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
