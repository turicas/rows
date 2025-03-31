# coding: utf-8

from __future__ import unicode_literals

import sys
import threading
import time
from math import floor

from rows.compat import PYTHON_VERSION

_UNIX = hasattr(sys, "setdlopenflags")  # This function is only available on Python when running on Unix
_WINDOWS = sys.platform in ("win32", "cygwin")

# TODO: make it work on jupyter notebooks?


def format_delta_time(value):
    value = int(value)
    if value < 3600:
        minutes = value // 60
        seconds = value - (minutes * 60)
        return "{minutes:02d}:{seconds:02d}".format(minutes=minutes, seconds=seconds)
    else:
        hours = value // 3600
        minutes = (value - (hours * 3600)) // 60
        seconds = value - (hours * 3600) - (minutes * 60)
        return "{minutes:02d}:{seconds:02d}".format(hours=hours, minutes=minutes, seconds=seconds)


if PYTHON_VERSION >= (3, 3, 0):
    def get_screen_size():  # Works on both Unix and Windows. ~249 ns on Unix, ~7.4 µs on Windows, ~5.03 µs on cygwin
        import os

        size = os.get_terminal_size()
        return size.columns, size.lines

else:
    if _UNIX:
        def get_screen_size():  # ~1.54 µs
            import fcntl
            import struct
            import termios

            result = fcntl.ioctl(sys.stderr, termios.TIOCGWINSZ, b"\x00\x00\x00\x00\x00\x00\x00\x00")
            rows, cols, _, _ = struct.unpack("HHHH", result)
            return cols, rows

    elif _WINDOWS:
        def get_screen_size():  # ~47.2 µs on Windows, ~11.5 µs on cygwin
            import struct
            import ctypes

            # <https://learn.microsoft.com/en-us/windows/console/getstdhandle>
            # <https://learn.microsoft.com/en-us/windows/console/GetConsoleScreenBufferInfo>
            stderr_handle = ctypes.windll.kernel32.GetStdHandle(-12)  # -12 = stderr
            buffer = ctypes.create_string_buffer(22)  # 22 = 4 + 4 + 2 + 8 + 4
            ctypes.windll.kernel32.GetConsoleScreenBufferInfo(stderr_handle, buffer)
            _, _, _, _, _, left, top, right, bottom, _, _ = struct.unpack("hhhhHhhhhhh", buffer.raw)
            return right - left + 1, bottom - top + 1

    else:
        # Don't know what to do, so return a fixed value. Running other programs (like `stty size` on POSIX) was not
        # considered because of the added latency of starting a new process.
        def get_screen_size():
            return 80, 24


class ProgressBar(object):
    """
    Two modes of operation: threaded and non-threaded.

    The bar is refreshed automatically when:
    - `__init__` is called (`bar = ProgressBar()`)
    - Text is changed (`bar.text = X`)
    - Total is changed (`bar.total = X`)
    - Value is updated (`bar.update()`) (not always, depends on fps)
    - `bar.close` is called (happens when the `StopIteration` is raised or when exists context manager)
    - During thread execution (updates automatically based on `fps`)
    """
    def __init__(self, iterable=None, text=None, total=None, unit=" it", file=sys.stderr, fps=4):
        import sys

        # TODO: use_unicode = sys.stdout.encoding and "UTF-8" in sys.stdout.encoding.upper()
        self._total = total
        self._text = text
        self._file = file
        self._unit = unit
        self._done = -1
        self._fps = fps
        self._interval = 1 / self._fps
        self._lock = threading.Lock()
        self._update_screen_size()
        if _UNIX:
            import signal
            signal.signal(signal.SIGWINCH, self._handle_resize)
        # TODO: deal with terminal resize on Windows (how?)
        if total is None and iterable is not None and hasattr(iterable, "__len__"):
            # TODO: what if this `len` is heavy to process?
            self._total = len(iterable)
        if iterable is not None:
            self._iterable = iter(iterable)
        self._thread = None
        self._threaded = False
        self._active = True
        self._start_time = time.time()
        self._timings = [(self._start_time, 0)]
        self._last_refresh = None
        self.refresh()

    def _handle_resize(self, number, stack_frame):
        self._update_screen_size()

    @property
    def screen_rows(self):
        return self._rows

    @property
    def screen_cols(self):
        return self._cols

    def _update_screen_size(self):
        with self._lock:
            self._cols, self._rows = get_screen_size()

    def _update_output(self):
        splits = 10  # TODO: add as an attribute or calculate automatically based on fps?
        while self._active:
            self.refresh()
            sleep_intervals = self._interval - ((time.time() - self._last_refresh) if self._last_refresh else 0)
            mini_sleep = sleep_intervals / splits
            for _ in range(splits):
                if not self._active:
                    break
                time.sleep(mini_sleep)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            value = next(self._iterable)
        except StopIteration:
            with self._lock:
                self._done += 1
                if self._total is None:
                    self._total = self._done
            self.close()
            raise
        else:
            self.update(last_done=1)
            return value

    def __enter__(self):
        self._threaded = True
        self._thread = threading.Thread(target=self._update_output)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # TODO: if exception, add "!" or ⚠ to progress
        self.close()

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        with self._lock:
            self._text = value
        self.refresh()

    @property
    def done(self):
        return self._done

    @property
    def total(self):
        return self._total

    @total.setter
    def total(self, value):
        with self._lock:
            self._total = value
        self.refresh()

    def update(self, last_done=1, total_done=None):
        if (last_done is None and total_done is None) or (last_done is not None and total_done is not None):
            raise ValueError("Either last_done or total_done must be specified")
        now = time.time()
        with self._lock:
            if last_done is not None:
                self._done += last_done
            elif total_done is not None:
                self._done = total_done
            self._timings.append((now, self._done))  # TODO: this is making everything slower
            # TODO: limit the total number of values to store
        if not self._threaded and (self._last_refresh is None or now - self._last_refresh >= self._interval):
            self.refresh()

    def __str__(self):
        # TODO: implement unit scaling
        elapsed = time.time() - self._start_time  # TODO: freeze the value after finishes (store self._end_time)
        alpha = 0.5  # TODO: add as an attribute?
        done, total, percent, eta, unit = self._done if self._done >= 0 else 0, self._total, None, None, self._unit
        started = total is not None and total > 0
        finished = started and done == total
        #self._speed = alpha * XXX + (1 - alpha) * self._speed  # TODO: implement EMA
        if len(self._timings) < 2:
            avg_speed = 0
        elif done == total:
            eta = 0
            avg_speed = done / elapsed
        else:
            first, last = self._timings[0], self._timings[-1]
            avg_speed = (last[1] - first[1]) / (last[0] - first[0])
        if avg_speed > 0 and total is not None:
            eta = (total - done) / avg_speed
        # TODO: move speed logic to where _done is incremented? what about elapsed?
        text_part = "" if not self._text else self._text
        # TODO: self._done must have fixed size in string representation
        if started:
            percent = floor(10000 * (done / total)) / 100
            percent_part = "{:6.2f}%".format(percent)
            done_total_part = " {done:,}/{total:,}".format(done=done, total=total)  # TODO: add unit
        else:
            percent_part = ""
            done_total_part = "{done:,}{unit}".format(done=done, unit=unit)
            bar_part = ""
        speed_part = " {speed:6.2f}{unit}/s".format(speed=avg_speed, unit=unit)
        elapsed_part = "{done} {elapsed}".format(done=" done in" if finished else "", elapsed=format_delta_time(elapsed))
        eta_part = " ETA: {eta}".format(eta=format_delta_time(eta)) if eta else ""
        before_bar = text_part + percent_part
        after_bar = done_total_part + speed_part + elapsed_part + eta_part
        if started:
            bar_width = self._cols - len(before_bar + after_bar) - 1
            filled = int(bar_width * percent / 100)
            partial_filled = (bar_width * percent / 100) - filled
            partial_chars = (" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█")
            index = int(partial_filled * len(partial_chars))
            bar_part = (
                " "
                + partial_chars[-1] * filled
                + (partial_chars[index] + partial_chars[0] * (bar_width - filled - 1) if filled < bar_width else "")
            )
        # TODO: speed width must be fixed
        # TODO: unit scale should apply to speed also
        # TODO: move elapsed and eta to always use hours? must be fixed?
        # TODO: add "metrics"
        return before_bar + bar_part + after_bar

    def refresh(self):
        # TODO: check if terminal size was updated?
        with self._lock:
            self._file.write("\r" + str(self) + "\x1b[K")
            self._file.flush()
            self._last_refresh = time.time()

    def __del__(self):
        if self._active:
            with self._lock:
                self._active = False
        if self._thread is not None:
            self._thread.join()

    def close(self):
        if self._active:
            with self._lock:
                self._active = False
            if self._thread is not None:
                self._thread.join()
            self.refresh()
            self._file.write("\n")
            self._file.flush()


# TODO: optimize:
# import time
# from rows.tui import ProgressBar
# from tqdm import tqdm
#
# start = time.time()
# for i in tqdm(range(10000)):
#     pass
# print(time.time() - start)
#
# start = time.time()
# for i in ProgressBar(range(10000), fps=1):
#     pass
# print(time.time() - start)


# TODO: corrigir
# python@17ceaf2167da:~$ python -m cProfile -s cumtime olar.py |head
#          13882 function calls (13462 primitive calls) in 0.009 seconds
#
#    Ordered by: cumulative time
#
#    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
#         5    0.000    0.000    0.010    0.002 __init__.py:1(<module>)
#      24/1    0.000    0.000    0.009    0.009 {built-in method builtins.exec}
#         1    0.000    0.000    0.009    0.009 olar.py:1(<module>)
#      31/1    0.000    0.000    0.008    0.008 <frozen importlib._bootstrap>:1349(_find_and_load)
#      31/1    0.000    0.000    0.008    0.008 <frozen importlib._bootstrap>:1304(_find_and_load_unlocked)
# Exception ignored in: <function ProgressBar.__del__ at 0x7f1243026ac0>
# Traceback (most recent call last):
#   File "/app/rows/tui/progress.py", line 233, in __del__
#     if self._active:
# AttributeError: 'ProgressBar' object has no attribute '_active'
