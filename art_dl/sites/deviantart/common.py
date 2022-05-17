from art_dl.log import Logger, Progress

SLUG = 'deviantart'
BASE_URL = 'https://www.deviantart.com'
REDIRECT_URI = 'http://localhost:23445'


class CREDS_PATHS:
	OAUTH_KEY = 'oauth2'

	client_id = [SLUG, 'client_id']
	client_secret = [SLUG, 'client_secret']
	code = [SLUG, OAUTH_KEY, 'code']
	access_token = [SLUG, OAUTH_KEY, 'access_token']
	refresh_token = [SLUG, OAUTH_KEY, 'refresh_token']


AUTH_LOG_PREFIX = [SLUG, 'auth']

logger = Logger(prefix=[SLUG, 'download'], inline=True)
progress = Progress()


def make_cache_key(username: str, url: str):
	return ':'.join([
		'art',
		username.lower(),
		'deviationid',
		url.split('/')[-1],
	])
