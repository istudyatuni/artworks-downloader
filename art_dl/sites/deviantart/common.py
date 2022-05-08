from art_dl.utils.log import Logger, Progress

SLUG = 'deviantart'
OAUTH_KEY = 'oauth2'
BASE_URL = 'https://www.deviantart.com'
REDIRECT_URI = 'http://localhost:23445'

logger = Logger(prefix=[SLUG, 'download'], inline=True)
progress = Progress()

def make_cache_key(username: str, url: str):
	return ':'.join([
		'art',
		username.lower(),
		'deviationid',
		url.split('/')[-1],
	])
