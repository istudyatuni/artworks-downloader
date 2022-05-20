# from aiohttp import ClientSession
from asyncio import sleep
from typing import Any, AsyncGenerator

from art_dl.cache import cache
from art_dl.utils.credentials import creds
from art_dl.utils.proxy import ClientSession, ProxyClientSession

from .common import (
	AUTH_LOG_PREFIX,
	BASE_URL,
	CREDS_PATHS,
	REDIRECT_URI,
	SLUG,
	logger,
	make_cache_key,
	progress,
)

API_URL = '/api/v1/oauth2'
# start from 32 instead of 1 to skip small timeouts because
# every time I tested it, we always hit 32+ seconds
# but with 32 at start we can wait in most cases only 32 seconds
# (I don't know why, maybe it not works everytime)
DEFAULT_RATE_LIMIT_TIMEOUT = 32
INVALID_CODE_MSG = 'Incorrect authorization code.'


# TODO: add revoke
# https://www.deviantart.com/developers/authentication
class DAService():
	"""Perform almost all work with auth and API"""

	def __init__(self):
		self.client_id = creds.get(CREDS_PATHS.client_id)
		self.client_secret = creds.get(CREDS_PATHS.client_secret)
		self.code = creds.get(CREDS_PATHS.code)

		self.access_token = creds.get(CREDS_PATHS.access_token)
		self.refresh_token = creds.get(CREDS_PATHS.refresh_token)

	@property
	def _headers(self):
		return {
			'authorization': 'Bearer ' + self.access_token
		}

	def _save_tokens(self):
		creds.delete(CREDS_PATHS.code)
		creds.save(CREDS_PATHS.access_token, self.access_token)
		creds.save(CREDS_PATHS.refresh_token, self.refresh_token)

	async def _ensure_access(self):
		if self.refresh_token is None:
			return await self._fetch_access_token()

		async with ProxyClientSession(BASE_URL) as session:
			async with session.post(
				'/api/v1/oauth2/placebo', params={ 'access_token': self.access_token }
			) as response:
				if (await response.json())['status'] == 'success':
					return

		await self._refresh_token()

	async def _fetch_access_token(self):
		"""Fetch `access_token` using `authorization_code`"""
		if self.code is None:
			logger.warn('authorize app first', prefix=AUTH_LOG_PREFIX)
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
		""" Common action for _refresh_token and _fetch_access_token """
		params = {
			'client_id': self.client_id,
			'client_secret': self.client_secret,
			**add_params,
		}
		async with ProxyClientSession(BASE_URL) as session:
			async with session.post('/oauth2/token', params=params) as response:
				data = await response.json()
				if response.ok:
					self.access_token = data['access_token']
					self.refresh_token = data['refresh_token']
					self._save_tokens()
				elif data['error_description'] == INVALID_CODE_MSG:
					logger.warn('please authorize again', prefix=AUTH_LOG_PREFIX)
					# or refresh token instead
				elif 'error' in data:
					logger.warn(
						'an error occured during authorization:',
						data['error_description'],
						prefix=AUTH_LOG_PREFIX
					)
					quit(1)

	async def _pager(self, session: ClientSession, method: str, url: str,
						**kwargs) -> AsyncGenerator[Any, None]:
		rate_limit_sec = DEFAULT_RATE_LIMIT_TIMEOUT
		params = {
			**kwargs.pop('params', {}),
			'offset': 0,
			'limit': 24,
			'mature_content': 'true',
		}
		while True:
			async with session.request(method, url, params=params, **kwargs) as response:
				data = await response.json()

				# Rate limit: https://www.deviantart.com/developers/errors
				if response.status == 429:
					if rate_limit_sec > 64 * 10:  # 10 min
						await self._ensure_access()

					u = params['username']
					logger.info(
						f'rate limit in pager ({u}), offset',
						params['offset'],
						'retrying in',
						rate_limit_sec,
						'sec',
						progress=progress
					)
					await sleep(rate_limit_sec)

					rate_limit_sec *= 2
					continue
				elif rate_limit_sec != DEFAULT_RATE_LIMIT_TIMEOUT:
					rate_limit_sec = DEFAULT_RATE_LIMIT_TIMEOUT
					await self._ensure_access()
				elif 'error' in data:
					logger.warn('an error occured during fetching', response.url, progress=progress)
					logger.warn(' ', data['error_description'])
					quit(1)

				response.raise_for_status()

				for result in data['results']:
					yield result

				if data['has_more'] is False:
					break

				params['offset'] = data['next_offset']

	async def list_folders(self, username: str) -> AsyncGenerator[Any, None]:
		await self._ensure_access()

		params = {
			'username': username
		}
		url = f'{API_URL}/gallery/folders'
		async with ProxyClientSession(BASE_URL, headers=self._headers) as session:
			async for folder in self._pager(session, 'GET', url, params=params):
				name = folder['name']
				# i don't know what is this, so just tell about
				if folder['has_subfolders'] is True:
					logger.warn(
						'folder', name, 'has subfolders, but this feature currently not supported'
					)
				yield {
					'id': folder['folderid'],
					'name': name.lower().replace(' ', '-'),
					'pretty_name': name,
				}

	async def list_folder_arts(self, username: str, folder_id: str) -> AsyncGenerator[Any, None]:
		await self._ensure_access()

		params = {
			'username': username
		}
		url = f'{API_URL}/gallery/{folder_id}'
		async with ProxyClientSession(BASE_URL, headers=self._headers) as session:
			async for art in self._pager(session, 'GET', url, params=params):
				if art is not None:
					cache.insert(
						SLUG, make_cache_key(art['author']['username'], art['url']),
						art['deviationid']
					)
				yield art

	async def get_download(self, deviationid: str):
		await self._ensure_access()

		url = f'{API_URL}/deviation/download/{deviationid}'
		async with ProxyClientSession(BASE_URL, headers=self._headers) as session:
			async with session.get(url) as response:
				data = await response.json()
				if 'error' in data:
					logger.warn(
						'error when getting download link:',
						data['error_description'],
						progress=progress
					)
					return
				return data['src']

	async def get_art_info(self, deviationid: str, _rate_limit_sec=DEFAULT_RATE_LIMIT_TIMEOUT):
		await self._ensure_access()

		url = f'{API_URL}/deviation/{deviationid}'
		async with ProxyClientSession(BASE_URL, headers=self._headers) as session:
			async with session.get(url) as response:
				if response.status == 429:
					logger.info(
						'rate limit reached, spleeping for',
						_rate_limit_sec,
						'seconds',
						progress=progress
					)
					await sleep(_rate_limit_sec)
					return await self.get_art_info(deviationid, _rate_limit_sec * 2)
				elif _rate_limit_sec > DEFAULT_RATE_LIMIT_TIMEOUT:
					pass

				data = await response.json()
				if 'error' in data:
					logger.warn(
						'error when getting art info:',
						data['error_description'],
						progress=progress
					)
					return
				return data
