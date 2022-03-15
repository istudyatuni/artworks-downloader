import asyncio
import aiofiles
import aiohttp
import os
from copy import deepcopy
from typing import Any, AsyncGenerator
from urllib.parse import urlencode, urlparse

from app.creds import get_creds, save_creds
from app.redirect_server import run as run_redirect_catch_server
from app.utils import mkdir, print_inline

SLUG = 'deviantart'
OAUTH_KEY = 'oauth2'

BASE_URL = 'https://www.deviantart.com'
AUTH_URL = BASE_URL + '/oauth2/authorize'
API_URL = '/api/v1/oauth2'
REDIRECT_URI = 'http://localhost:23445'

INVALID_CODE_MSG = 'Incorrect authorization code.'

DEFAULT_RATE_LIMIT_TIMEOUT = 1

# TODO: add revoke
# https://www.deviantart.com/developers/authentication
class DAService():
	"""Perform almost all work with auth and API"""
	def __init__(self):
		self.creds = get_creds() or {}
		if self.creds is None:
			raise Exception('Not authorized')

		creds = self.creds[SLUG]

		self.client_id = creds['client_id']
		self.client_secret = creds['client_secret']
		self.code = creds[OAUTH_KEY].get('code')

		self.access_token = creds[OAUTH_KEY].get('access_token')
		self.refresh_token = creds[OAUTH_KEY].get('refresh_token')

	@property
	def _auth_header(self) -> str:
		return 'Bearer ' + self.access_token

	def _save_tokens(self):
		creds = deepcopy(self.creds)
		creds[SLUG][OAUTH_KEY].pop('code', 0)
		creds[SLUG][OAUTH_KEY]['access_token'] = self.access_token
		creds[SLUG][OAUTH_KEY]['refresh_token'] = self.refresh_token
		save_creds(creds)

	async def _ensure_access(self):
		if self.refresh_token is None:
			return await self._fetch_access_token()

		async with aiohttp.ClientSession(BASE_URL) as session:
			async with session.post('/api/v1/oauth2/placebo', params={
				'access_token': self.access_token
			}) as response:
				if (await response.json())['status'] == 'success':
					return

		await self._refresh_token()

	async def _fetch_access_token(self):
		"""Fetch `access_token` using `authorization_code`"""
		if self.code is None:
			print('Authorize app first')
			quit(1)

		params = {
			'grant_type': 'authorization_code',
			'code': self.code,
			'redirect_uri': REDIRECT_URI,
		}
		await self._authorize(params)

	async def _refresh_token(self):
		"""Refresh `access_token` using `refresh_token`"""
		if self.refresh_token is None:
			raise Exception('No refresh token')

		params = {
			'grant_type': 'refresh_token',
			'refresh_token': self.refresh_token,
		}
		await self._authorize(params)

	async def _authorize(self, add_params):
		params = {
			'client_id': self.client_id,
			'client_secret': self.client_secret,
			**add_params,
		}
		async with aiohttp.ClientSession(BASE_URL) as session:
			async with session.post('/oauth2/token', params=params) as response:
				data = await response.json()
				if 'error' in data:
					print('An error occured during authorization\n ', data['error_description'])
					quit(1)
				elif response.ok:
					self.access_token = data['access_token']
					self.refresh_token = data['refresh_token']
					self._save_tokens()
				elif data['error_description'] == INVALID_CODE_MSG:
					print('Please authorize again') # or refresh token instead

	async def _pager(
		self,
		session: aiohttp.ClientSession,
		method: str,
		url: str,
		**kwargs
	) -> AsyncGenerator[Any, None]:
		rate_limit_sec = DEFAULT_RATE_LIMIT_TIMEOUT
		params = {
			**kwargs.pop('params', {}),
			'offset': 0,
			'limit': 24,
			'mature_content': 'true',
		}
		while True:
			async with session.request(
				method,
				url,
				params=params,
				**kwargs
			) as response:
				data = await response.json()

				if response.status == 429:
					# Rate limit: https://www.deviantart.com/developers/errors
					if rate_limit_sec == DEFAULT_RATE_LIMIT_TIMEOUT:
						print('Rate limit reached for url', response.url)
					elif rate_limit_sec > 64 * 10:  # 10 min
						await self._ensure_access()

					print_inline('Retrying in', rate_limit_sec, 'sec')
					await asyncio.sleep(rate_limit_sec)

					rate_limit_sec *= 2
					continue
				elif rate_limit_sec != DEFAULT_RATE_LIMIT_TIMEOUT:
					rate_limit_sec = DEFAULT_RATE_LIMIT_TIMEOUT
					print()
				elif 'error' in data:
					print('An error occured during fetching', response.url)
					print(' ', data['error_description'])
					quit(1)

				for result in data['results']:
					yield result

				if data['has_more'] is False:
					break

				params['offset'] = data['next_offset']

	async def list_folders(self, username: str) -> AsyncGenerator[Any, None]:
		await self._ensure_access()

		params = { 'username': username }
		headers = { 'authorization': self._auth_header }
		url = f'{API_URL}/gallery/folders'
		async with aiohttp.ClientSession(BASE_URL, headers=headers) as session:
			async for folder in self._pager(session, 'GET', url, params=params):
				name = folder['name']
				# i don't know what is this, so just tell about
				if folder['has_subfolders'] is True:
					print('Folder', name, 'has subfolders, but this feature currently not supported')
				yield {
					'id': folder['folderid'],
					'name': name.lower().replace(' ', '-'),
					'pretty_name': name,
				}

	async def list_folder_arts(self, username: str, folder: str) -> AsyncGenerator[Any, None]:
		await self._ensure_access()

		params = { 'username': username }
		headers = { 'authorization': self._auth_header }
		url = f'{API_URL}/gallery/{folder}'
		async with aiohttp.ClientSession(BASE_URL, headers=headers) as session:
			async for art in self._pager(session, 'GET', url, params=params):
				yield art

def parse_link(url: str) -> dict[str, str]:
	parsed = urlparse(url)
	path = parsed.path.lstrip('/').split('/')
	artist = path[0]

	if len(path) == 1 or (len(path) > 2 and path[2] == 'all'):
		# https://www.deviantart.com/<artist>
		# https://www.deviantart.com/<artist>/gallery/all
		return { 'type': 'all', 'artist': artist }

	if len(path) == 2 and path[1] == 'gallery':
		# https://www.deviantart.com/<artist>/gallery
		# it's "Featured" collection
		return { 'type': 'folder', 'folder': 'featured', 'artist': artist }

	if path[1] == 'gallery':
		# https://www.deviantart.com/<artist>/gallery/<some number>/<gallery name>
		# gallery name in format one-two-etc
		return { 'type': 'folder', 'folder': path[3], 'artist': artist }

	if path[1] == 'art':
		# https://www.deviantart.com/<artist>/art/<name>
		return { 'type': 'art', 'url': url, 'artist': artist, 'name': path[2] }

	print('Unsupported link:', url)
	return { 'type': 'unknown', 'artist': artist }

async def save_art(session: aiohttp.ClientSession, url: str, folder: str, name: str):
	print_level_prefix = ' ' * 2

	ext = os.path.splitext(urlparse(url).path)[1]
	path = os.path.join(folder, name + ext)
	if os.path.exists(path):
		return print(print_level_prefix + 'Skip existing:', name)

	async with session.get(url) as image:
		async with aiofiles.open(path, 'wb') as file:
			await file.write(await image.read())
			print(print_level_prefix + 'Download:', name)

async def download_folder_by_id(service: DAService, save_folder: str, artist: str, folder: str):
	count_arts = 0
	# this session for downloading images
	async with aiohttp.ClientSession() as session:
		async for art in service.list_folder_arts(artist, folder):
			name = art['url'].split('/')[-1]
			await save_art(session, art['content']['src'], save_folder, name)
			count_arts += 1

	print('Total', count_arts, 'arts')

async def find_and_download_folder(
	service: DAService,
	save_folder: str,
	artist: str,
	folder_name: str
):
	folderid = await search_for_folder(service, artist, folder_name)
	if folderid is None:
		print('Not found gallery', f'"{folder_name}"')
		return
	await download_folder_by_id(service, save_folder, artist, folderid)

async def search_for_folder(service: DAService, artist: str, folder_to_find: str) -> str | None:
	folderid = None
	print('Searching for gallery')
	async for folder in service.list_folders(artist):
		if folder['name'] == folder_to_find:
			folderid = folder['id']
			print('Gallery', folder['pretty_name'], f'({folderid})')
			# not breaking now for catching what is the subfolder
			# break

	return folderid

async def search_for_art(service: DAService, artist: str, url_to_find: str) -> str | None:
	print('Searching for art')
	async for art in service.list_folder_arts(artist, 'all'):
		if art['url'] == url_to_find:
			return art['content']['src']

async def find_and_download_art(
	service: DAService,
	save_folder: str,
	artist: str,
	url: str,
	name: str
):
	src = await search_for_art(service, artist, url)
	if src is None:
		return print('Art', name, 'not found')
	async with aiohttp.ClientSession() as session:
		await save_art(session, src, save_folder, name)

async def download(url: list[str] | str, data_folder: str) -> None:
	if isinstance(url, list):
		return await download_list(url,data_folder)

	service = DAService()

	parsed = parse_link(url)
	artist = parsed['artist']
	save_folder = os.path.join(data_folder, artist)
	mkdir(save_folder)

	print('Artist', artist)
	print('Saving to folder', save_folder, end='\n\n')

	if parsed['type'] == 'all':
		await download_folder_by_id(service, save_folder, artist, 'all')
	elif parsed['type'] == 'folder':
		await find_and_download_folder(service, save_folder, artist, parsed['folder'])
	elif parsed['type'] == 'art':
		await find_and_download_art(service, save_folder, artist, url, parsed['name'])

async def download_list(urls: list[str], data_folder: str):
	service = DAService()

	print('\nSaving to folder', data_folder)

	# ['artist1', ...]
	mapping_all: list[str] = []
	# { '<artist>': ['folder1', ...] }
	mapping_folder: dict[str, list[str]] = {}
	# { '<artist>': [{ 'name': 'name1', 'url': 'url1' }, ...] }
	mapping_art: dict[str, list[dict[str, str]]] = {}

	# group urls by types and artists
	for u in urls:
		parsed = parse_link(u)
		t = parsed['type']
		a = parsed['artist']
		if t == 'all':
			mapping_all.append(a)
		elif t == 'folder':
			if mapping_folder.get(a) is None:
				mapping_folder[a] = []
			mapping_folder[a].append(parsed['folder'])
		elif t == 'art':
			if mapping_art.get(a) is None:
				mapping_art[a] = []
			mapping_art[a].append({ 'name': parsed['name'], 'url': u })

	# process
	for artist in mapping_all:
		save_folder = os.path.join(data_folder, artist)
		mkdir(save_folder)
		print('\nArtist', artist)

		await download_folder_by_id(service, save_folder, artist, 'all')

	for artist, folder_list in mapping_folder.items():
		save_folder = os.path.join(data_folder, artist)
		mkdir(save_folder)
		print('\nArtist', artist)

		async for folder in service.list_folders(artist):
			if folder['name'] in folder_list:
				print('Gallery', folder['pretty_name'])
				await download_folder_by_id(service, save_folder, artist, folder['id'])

	async with aiohttp.ClientSession() as session:
		for artist, art_list in mapping_art.items():
			arts_count = len(art_list)
			save_folder = os.path.join(data_folder, artist)
			mkdir(save_folder)
			print('\nArtist', artist, '\nSearching for arts')

			async for art in service.list_folder_arts(artist, 'all'):
				url = art['url']
				if any(filter(lambda a: a['url'] == url, art_list)):
					name = url.split('/')[-1]
					await save_art(session, art['content']['src'], save_folder, name)

					arts_count -= 1
					if arts_count == 0:
						break

			print('Total', len(art_list), 'arts')

def ask_app_creds():
	creds = get_creds()
	if (
		creds is not None and
		creds.get(SLUG) is not None and
		creds[SLUG].get('client_id') is not None
	):
		ans = input('Application data already saved, again? [y/N] ')
		if ans.lower() in ['n', '']:
			return {
				'client_id': creds[SLUG]['client_id'],
				'client_secret': creds[SLUG]['client_secret'],
			}
		elif ans.lower() != 'y':
			print('What?')
			quit(1)
	return {
		'client_id': input('Enter client_id: '),
		'client_secret': input('Enter client_secret: ')
	}

def register():
	"""Authorize application"""
	creds = {
		SLUG: {
			**ask_app_creds(),
			OAUTH_KEY: { 'code': None },
		}
	}

	# callback
	def cred_saver(data):
		creds[SLUG][OAUTH_KEY] = data

	query = {
		'response_type': 'code',
		'client_id': creds[SLUG]['client_id'],
		'redirect_uri': REDIRECT_URI,
		'scope': ' '.join(['browse']),
		'view': 'login'
	}
	url = f'{AUTH_URL}?{urlencode(query)}'

	try:
		run_redirect_catch_server(url, cred_saver)
	except SystemExit:
		print('Server stopped')

	if creds[SLUG][OAUTH_KEY].get('code') is not None:
		return creds

	return None
