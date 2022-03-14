from importlib import import_module
from typing import Any, Callable, Coroutine

def download(slug: str) -> Callable[[list[str] | str, str], Coroutine[Any, Any, None]]:
	return import_module('sites.' + slug).download

def register(slug: str) -> Callable[[], dict[str, Any] | None]:
	try:
		return import_module('sites.' + slug).register
	except AttributeError:
		print(slug, 'not needed register')
		quit(1)
