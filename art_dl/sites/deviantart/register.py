from urllib.parse import urlencode

from .common import BASE_URL, OAUTH_KEY, REDIRECT_URI, SLUG
from art_dl.creds import get_creds
from art_dl.redirect_server import run as run_redirect_catch_server

AUTH_URL = BASE_URL + '/oauth2/authorize'

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
