import aiofiles
import aiohttp
import json
import json
import os
from typing import Any, Dict
from urllib.parse import urlparse
# from functools import reduce

BASE_URL = 'https://www.artstation.com'
USER_PROJECTS_URL = '/users/{user}/projects.json'
PROJECT_INFO_URL = '/projects/{hash}.json'

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.split('/')
	artist = path[0]

	if len(path) == 1:
		# https://www.deviantart.com/<artist>
		return { 'artist': artist }

	if path[1] == 'gallery' and len(path) == 2 or ():
		# https://www.deviantart.com/<artist>/gallery
		# or
		# https://www.deviantart.com/<artist>/gallery/all
		return { 'artist': artist }

	return { 'artist': artist }

	# return { 'type': 'all', 'artist': parsed.path.lstrip('/') }

async def fetch_json(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
	async with session.get(url) as response:
		html = await response.text()

	start_ind = html.find('__INITIAL_STATE__')
	end_ind = html.find(';\n', start_ind)
	# 31 is len of `__INITIAL_STATE__ = JSON.parse(`
	# 1 is len of `)` at the end
	json_data = html[start_ind + 31:end_ind - 1]

	from pprint import pprint
	# first parse with many escape chars, then parse json string
	# '"{\"field\" ...\"' -> '{"field" ...' -> {'field' ...
	try:
		j = json.loads(json_data)
	except json.decoder.JSONDecodeError:
		print(json_data)
		raise
	data = json.loads(j)
	# data = json.loads(json.loads(json_data))
	pprint(data)
	return data['@@entities']['deviation']

async def download(url: str, data_folder: str):
	parsed = parse_link(url)
	artist = parsed['artist']
	save_folder = os.path.join(data_folder, artist)
	os.makedirs(save_folder, exist_ok=True)

	# https://www.deviantart.com/<artist>
	# with this link many other authors
	# https://www.deviantart.com/<artist>/gallery/all
	# for this link I can't get content because of CloudFront

	async with aiohttp.ClientSession() as session:
		for art in (await fetch_json(session, url)).values():
			m = art['media']
			fetch_url = m['baseUri']
			fileext = os.path.splitext(urlparse(fetch_url).path.split('/')[-1])[1]
			filename = os.path.join(save_folder, m['prettyName'] + fileext)

			# additional = [t for t in m['types'] if t['t'] == 'fullview']
			# try:
			# 	fetch_url = fetch_url + '/' + additional[0]['c'].replace('<prettyName>', m['prettyName'])
			# except:
			# 	print(json.dumps(art, indent=4))
			# 	raise

			async with session.get(
				fetch_url,
				params={ 'token': ''.join(m['token']) }
			) as response:
				response.raise_for_status()
				async with aiofiles.open(filename, 'wb') as file:
					await file.write(await response.read())
				print('Download:', filename)
