import asyncio
import aiohttp
from copy import deepcopy
from typing import Any, AsyncGenerator

from . import (
	BASE_URL,
	OAUTH_KEY,
	REDIRECT_URI,
	SLUG,
)
from app.creds import get_creds, save_creds
from app.utils import print_inline

API_URL = '/api/v1/oauth2'
DEFAULT_RATE_LIMIT_TIMEOUT = 1
INVALID_CODE_MSG = 'Incorrect authorization code.'

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

				response.raise_for_status()

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

	async def get_download(self, deviationid: str):
		await self._ensure_access()

		headers = { 'authorization': self._auth_header }
		url = f'{API_URL}/deviation/download/{deviationid}'
		async with aiohttp.ClientSession(BASE_URL, headers=headers) as session:
			async with session.get(url) as response:
				data = await response.json()
				if 'error' in data:
					print('Error when getting download link:', data['error_description'])
					return None
				return data['src']
