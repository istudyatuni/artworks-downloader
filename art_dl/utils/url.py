def parse_range(rng: str) -> list[int] | None:
	"""
	Convert range like `1-3,5` to `[1, 2, 3, 5]`.
	Result is sorted.
	Empty string converts to `None`
	"""
	if rng == '':
		return None

	parts = rng.split(',')
	result: set[int] = set()
	for p in parts:
		if '-' in p:
			[start, end] = p.split('-')
			result.update(range(int(start), int(end) + 1))
		else:
			result.add(int(p))

	return sorted(list(result))
