check: format-check mypy

format:
	python -m yapf -i -r art_dl

format-check:
	python -m yapf --diff -r art_dl

mypy:
	mypy -m art_dl

requirements: requirements.txt
	pip install -r requirements.txt

requirements-dev: requirements.txt requirements.dev.txt
	pip install -r requirements.dev.txt
