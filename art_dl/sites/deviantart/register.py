from urllib.parse import urlencode

from art_dl.redirect_server import run as run_redirect_catch_server
from art_dl.utils.credentials import creds

from .common import AUTH_LOG_PREFIX, BASE_URL, CREDS_PATHS, REDIRECT_URI, logger

AUTH_URL = BASE_URL + '/oauth2/authorize'


def ask_app_creds():
	client_id = creds.get(CREDS_PATHS.client_id)
	client_secret = creds.get(CREDS_PATHS.client_secret)

	if client_id is not None and client_secret is not None:
		ans = input('Application data already saved, again? [y/N] ')
		if ans.lower() in ['n', '']:
			return
		elif ans.lower() != 'y':
			print('What?')
			quit(1)

	creds.save(CREDS_PATHS.client_id, input('Enter client_id: '))
	creds.save(CREDS_PATHS.client_secret, input('Enter client_secret: '))


def register():
	""" Authorize application """
	ask_app_creds()

	# callback
	def cred_saver(new_code):
		creds.save(CREDS_PATHS.code, new_code)

	query = {
		'response_type': 'code',
		'client_id': creds.get(CREDS_PATHS.client_id),
		'redirect_uri': REDIRECT_URI,
		'scope': ' '.join(['browse']),
		'view': 'login'
	}
	url = f'{AUTH_URL}?{urlencode(query)}'

	try:
		run_redirect_catch_server(url, cred_saver)
	except SystemExit:
		logger.info('server stopped', prefix=AUTH_LOG_PREFIX)

	logger.info('authorized', prefix=AUTH_LOG_PREFIX)
