from typing import Counter


def counter2str(c: Counter):
	return ', '.join(f'{i}: {v}' for i, v in c.items())
