import platformdirs

from art_dl.utils.path import mkdir

appname = 'artworks-downloader'
appauthor = 'istudyatuni'


class DIRS:
	cache = platformdirs.user_cache_dir(appname, appauthor)
	config = platformdirs.user_config_dir(appname, appauthor)


mkdir(DIRS.cache)
mkdir(DIRS.config)
