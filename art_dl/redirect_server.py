"""
Module to catch redirect oauth callback
"""

from typing import Any, Callable

from aiohttp import web
from aiohttp.typedefs import Handler

saver_func = lambda _: None


@web.middleware
async def middleware(request: web.Request, handler: Handler):
	resp = await handler(request)

	await resp.prepare(request)
	await resp.write_eof()

	# now hardcoded for deviantart
	if resp.status == 200:
		saver_func(request.query['code'])
		# stop server
		raise SystemExit

	return resp


async def redirect_handler(request: web.Request):
	if 'error' in request.query:
		return web.Response(
			text='An error occurred: ' + request.query['error_description'], status=400
		)
	else:
		return web.Response(text='Authorized', status=200)


def run(url: str, saver: Callable[[Any], None]):
	global saver_func
	saver_func = saver

	print('Authorizing\nOpen', url)

	app = web.Application(middlewares=[middleware])
	app.router.add_get('/', redirect_handler)
	web.run_app(app, host='localhost', port=23445)


if __name__ == '__main__':
	print('Do not run this directly')
	quit(1)
