from pathlib import Path

from matplotlib import pyplot as plt


def distance(x1: float, y1: float, x2: float, y2: float) -> float:

	"""Return the Euclidean distance between two points (coordinates are km)."""
	dx = x1 - x2
	dy = y1 - y2
	return (dx * dx + dy * dy) ** 0.5


def read_data(path: str) -> dict[str, tuple]:
	"""Read tab-separated address, x, y, area rows into a dictionary."""
	database = {}
	with open(path, encoding="utf-8") as file:
		for line_number, line in enumerate(file, start=1):
			row = line.rstrip("\r\n").split("\t")
			if len(row) != 4:
				continue
			address, x, y, area = row
			try:
				database[address] = (float(x), float(y), float(area))
			except ValueError as error:
				raise ValueError(f"Invalid numeric data on line {line_number}: {line!r}") from error
	return database


def _scores(database: dict[str, tuple], residents: bool = False) -> list[tuple]:
	"""Return (score, x, y) for each distinct available building coordinate."""
	buildings = list(database.values())
	coordinates = []
	seen = set()
	for x, y, _area in buildings:
		point = (x, y)
		if point not in seen:
			seen.add(point)
			coordinates.append(point)

	scored = []
	for x, y in coordinates:
		score = 0.0
		for bx, by, area in buildings:
			if distance(x, y, bx, by) <= 0.5:
				# Task 3 estimates residents using 70% of building area / 18 m².
				score += area * 0.7 / 18 if residents else 1
		scored.append((score, x, y))
	# Stable sorting makes ties deterministic, retaining input order.
	scored.sort(key=lambda item: item[0], reverse=True)
	return scored


def _choose(database: dict[str, tuple], count: int, residents: bool = False) -> list[tuple]:
	chosen = []
	for _score, x, y in _scores(database, residents):
		if all(distance(x, y, sx, sy) > 1.0 for sx, sy in chosen):
			chosen.append((x, y))
			if len(chosen) == count:
				break
	return chosen


def task1(database: dict[str, tuple]) -> list:
	"""Return the existing building coordinate with the most neighbors in 500 m."""
	_score, x, y = _scores(database)[0]
	return [x, y]


def task2(database: dict[str, tuple]) -> list[tuple]:
	"""Return the 10 best building coordinates, at least 1 km apart."""
	return _choose(database, 10)


def task3(database: dict[str, tuple]) -> list[tuple]:
	"""Return the 15 best coordinates by estimated residents, at least 1 km apart."""
	return _choose(database, 15, residents=True)


def plot(database: dict[str, tuple], best_coords: list):
	"""
	DO NOT CHANGE!
	Args:
		database (dict): изначальный датасет словарь, ключ адрес, значение (x, y, площадь)
		best_coords (list): для задачи 1 это (x, y), для задачи 2-3 это [(x1,y1), (x2,y2) ... (xn,yn)]
	"""
	plt.close()
	fig, ax = plt.subplots(figsize=(8, 8))
	plt.plot(
		[coord[0] for coord in database.values()],
		[coord[1] for coord in database.values()],
		'.', ms=5, color='k', alpha=0.5)
	if isinstance(best_coords[0], tuple):
		for x, y in best_coords:
			circle = plt.Circle((x, y), 0.5, color='r', fill=False, zorder=2)
			ax.add_patch(circle)
		plt.plot(
			[coord[0] for coord in best_coords],
			[coord[1] for coord in best_coords],
			'.', ms=15, color='r')
	elif isinstance(best_coords[0], float):
		x, y = best_coords
		circle = plt.Circle((x, y), 0.5, color='r', fill=False, zorder=2)
		ax.add_patch(circle)
		plt.plot(*best_coords, '.', ms=15, color='r')
	else:
		raise ValueError("Проверь, что подаёшь список кортежей или кортеж из двух координат")
	plt.show()


def homework():
	path = Path(__file__).with_name("buildings")
	database = read_data(str(path))

	best_task1 = task1(database)
	plot(database, best_task1)

	best_task2 = task2(database)
	plot(database, best_task2)

	best_task3 = task3(database)
	plot(database, best_task3)


if __name__ == '__main__':
	homework()
