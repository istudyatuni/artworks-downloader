# constants should be before imports
SLUG = 'deviantart'
OAUTH_KEY = 'oauth2'
BASE_URL = 'https://www.deviantart.com'
REDIRECT_URI = 'http://localhost:23445'

from .service import DAService
# next line should be after service
from .download import download
from .register import register

__all__ = [
	'DAService',
	'download',
	'register',
]
