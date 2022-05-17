from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector  # type: ignore

from art_dl.utils.config import config

__all__ = ['ClientSession', 'ProxyClientSession']


def _can_use_proxy_url(url: str | None):
	return url is not None and url != ''


class ProxyClientSession(ClientSession):

	def __init__(self, *args, **kwargs):
		proxy_url = config.get('proxy')
		if kwargs.get('connector') is None and _can_use_proxy_url(proxy_url):
			kwargs['connector'] = ProxyConnector.from_url(proxy_url)
			# print('proxy', proxy_url)

		super().__init__(*args, **kwargs)

	# async def _request(self, *args, **kwargs):
	# 	print('_request', *args)
	# 	return await super()._request(*args, **kwargs)
