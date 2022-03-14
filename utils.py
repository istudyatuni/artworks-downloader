from functools import partial
from os import makedirs

mkdir = partial(makedirs, exist_ok=True)
