check: format-check mypy

format:
	python -m yapf -i -r art_dl

format-check:
	python -m yapf --diff -r art_dl

mypy:
	mypy -m art_dl

requirements:
	poetry install
