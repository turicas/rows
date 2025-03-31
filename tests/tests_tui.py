# coding: utf-8

from __future__ import unicode_literals

import threading
import time
from io import StringIO

from rows.tui import ProgressBar


# TODO: add test for percentage
# TODO: add test for first update (must be 0, not -1)
# TODO: add test for different values in .update
# TODO: add test for text
# TODO: add test for bar filling
# TODO: add test for unit scale
# TODO: add test for fixed size values


class DummyIterableWithLength:
    def __init__(self, n):
        self.n = n
        self.current = 0

    def __iter__(self):
        return self

    def __next__(self):
        result = self.current
        self.current += 1
        if self.current == self.n:
            raise StopIteration
        return result

    def __len__(self):
        return self.n


def test_iterable_auto_total():
    elements = 100
    iterable = range(elements)
    bar = ProgressBar(iterable, file=StringIO(), total=None)
    assert bar.total == elements

    iterable = DummyIterableWithLength(2 * elements)
    bar = ProgressBar(iterable, file=StringIO(), total=None)
    assert bar.total == 2 * elements


def test_iterable_version_doesnt_use_threads():
    threads_qty = [len(threading.enumerate())]
    for _ in ProgressBar(range(10), file=StringIO()):
        threads_qty.append(len(threading.enumerate()))
    threads_qty.append(len(threading.enumerate()))
    assert set(threads_qty) == {1}


def test_context_manager_version_uses_one_thread():
    threads_qty = [len(threading.enumerate())]
    with ProgressBar(file=StringIO()) as bar:
        threads_qty.append(len(threading.enumerate()))
    threads_qty.append(len(threading.enumerate()))
    assert threads_qty[0] == threads_qty[-1] == 1
    assert set(threads_qty[1:-1]) == {2}


def test_iterable_version_limit_number_of_updates():
    iterations = 150
    iteration_duration = 0.005
    fps = 20  # should update more or less every 0.05s
    fobj = StringIO()
    bar = ProgressBar(range(iterations), file=fobj, fps=fps)
    for i in bar:  # 0.75s total
        time.sleep(iteration_duration)
    fobj.seek(0)
    data = fobj.read()
    updates = data.split("\r")
    assert updates[0] == ""
    updates = updates[1:]
    expected_updates = 1 + int(iterations * iteration_duration * fps)
    # 1 on `__init__` + 1 on `StopIteration` + 1 every ~0.05s (20 fps) - 1 (last one will be together with end of loop)
    assert len(updates) == expected_updates


def test_context_manager_version_number_of_updates():
    iterations = 10
    iteration_duration = 0.01
    fps = 50
    fobj = StringIO()
    with ProgressBar(file=fobj, fps=fps) as bar:
        for i in range(iterations):
            start = time.time()
            bar.update()
            end = time.time()
            time.sleep(iteration_duration - (end - start))
    fobj.seek(0)
    data = fobj.read()
    updates = data.split("\r")
    assert updates[0] == ""
    updates = updates[1:]
    assert updates[-1].endswith("\x1b[K\n")  # Last update will be the only to print the new line char
    assert all("\n" not in line for line in updates[:-1])
    assert all(line.endswith("\x1b[K") for line in updates[:-1])
    expected_updates = 2 + int(iterations * iteration_duration * fps)
    # 1 on `__init__` + 1 on `close` + 1 for each "frame" update
    assert len(updates) == expected_updates


def test_context_manager_and_iterable_version_number_of_updates():
    iterations = 10
    iteration_duration = 0.01
    fps = 50
    fobj = StringIO()
    with ProgressBar(range(iterations), file=fobj, fps=fps) as bar:
        for i in bar:
            time.sleep(iteration_duration)
    fobj.seek(0)
    data = fobj.read()
    updates = data.split("\r")
    assert updates[0] == ""
    updates = updates[1:]
    assert updates[-1].endswith("\x1b[K\n")  # Last update will be the only to print the new line char
    assert all("\n" not in line for line in updates[:-1])
    assert all(line.endswith("\x1b[K") for line in updates[:-1])
    expected_updates = 2 + int(iterations * iteration_duration * fps)
    # 1 on `__init__` + 1 on `close` + 1 for each "frame" update
    assert len(updates) == expected_updates
