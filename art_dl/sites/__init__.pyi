from typing import Any, Callable, Coroutine

# import for mypy
from .artstation import download as _
from .danbooru import download as _
from .deviantart import download as _
from .imgur import download as _
from .pixiv import download as _
from .reddit import download as _
from .twitter import download as _
from .wallhaven import download as _

def download(slug: str) -> Callable[[list[str], str], Coroutine[Any, Any, None]]: ...
def register(slug: str) -> Callable[[], None]: ...
