import aiohttp
import os
from copy import deepcopy
from urllib.parse import urlencode, urlparse

from creds import get_creds, save_creds
from redirect_server import run

SLUG = 'deviantart'

BASE_URL = 'https://www.deviantart.com'
OAUTH2_URL = BASE_URL + '/oauth2/authorize'
REDIRECT_URI = 'http://localhost:23445'

INVALID_CODE_MSG = 'Incorrect authorization code.'

# TODO: add revoke
# https://www.deviantart.com/developers/authentication
class DAService():
	def __init__(self):
		self.creds = get_creds() or {}
		if self.creds is None:
			raise Exception('Not authorized')

		creds = self.creds[SLUG]

		self.client_id = creds['client_id']
		self.client_secret = creds['client_secret']
		self.code = creds['oauth2']['code']

		self.access_token = creds['oauth2'].get('access_token')
		self.refresh_token = creds['oauth2'].get('refresh_token')

	def _save_tokens(self):
		creds = deepcopy(self.creds)
		creds[SLUG]['oauth2']['access_token'] = self.access_token
		creds[SLUG]['oauth2']['refresh_token'] = self.refresh_token
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
				if response.ok:
					self.access_token = data['access_token']
					self.refresh_token = data['refresh_token']
					self._save_tokens()
				elif data['error_description'] == INVALID_CODE_MSG:
					print('Please authorize again') # or refresh token instead

def parse_link(url: str):
	parsed = urlparse(url)
	path = parsed.path.split('/')
	path.pop(0)
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

async def download(url: str, data_folder: str):
	service = DAService()
	await service._ensure_access()

	parsed = parse_link(url)
	artist = parsed['artist']
	save_folder = os.path.join(data_folder, artist)
	os.makedirs(save_folder, exist_ok=True)

def ask_app_creds():
	creds = get_creds()
	if (
		creds is not None and
		creds.get(SLUG) is not None and
		creds[SLUG].get('client_id') is not None
	):
		ans = input('Application data already saved, again? [y/N] ')
		if ans.lower() in ['n', '']:
			creds = creds[SLUG]
			return { 'client_id': creds['client_id'], 'client_secret': creds['client_secret'] }
		elif ans.lower() != 'y':
			print('What?')
	return {
		'client_id': input('Enter client_id: '),
		'client_secret': input('Enter client_secret: ')
	}

def register():
	creds = {
		SLUG: ask_app_creds(),
		**{
			SLUG: { 'oauth2': { 'code': None } }
		}
	}

	# callback
	def cred_saver(data):
		creds[SLUG]['oauth2'] = data

	query = {
		'response_type': 'code',
		'client_id': creds[SLUG]['client_id'],
		'redirect_uri': REDIRECT_URI,
		'scope': ' '.join(['browse']),
		'view': 'login'
	}
	url = f'{OAUTH2_URL}?{urlencode(query)}'

	try:
		run(url, cred_saver)
	except SystemExit:
		print('Server stopped')

	if creds[SLUG]['oauth2'].get('code') is not None:
		return creds

	return None
