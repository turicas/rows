import contextlib
import warnings

from collections.abc import Mapping, MutableSequence
from functools import wraps
from textwrap import dedent as D

from . import query

class SliceableGetSequenceMixin:
    """
       Automatically handle slices in keys so that implementer classes
        always get a single key in their getitem call
    """
    def __init_subclass__(cls, *args, **kw):
        super().__init_subclass__(*args, **kw)
        if not hasattr(cls, "__getitem__") or getattr(cls.__getitem__, "_unslicer", None):
            return
        cls.__getitem__ = __class__._get_wrapper(cls.__getitem__)\

    def _get_wrapper(original_getitem):
        @wraps(original_getitem)
        def wrapper(self, index):
            if not isinstance(index, slice):
                return original_getitem(self, index)
            return [original_getitem(self, i) for i in range(*index.indices(len(self)))]

        wrapper._unslicer = True
        return wrapper


class FilterableSequence(MutableSequence, SliceableGetSequenceMixin):
    """Inner sequence that actually applies a query filter row by row

    Used in "Table" objects and tightly coupled to .query.Query:
    in particular, it exposes in  the "parent object" (the object
    to which this is associated) "current_record" attribute, pointing
    to the row currently being filtered, which will be fetched by the
    filtering code in the query itself.

    Few things in the Universe are as thread-unsafe as this;
    never try to use a filtered Table in more than one thread.
    """
    def __init__(self, inner, parent):
        self.data = inner
        self.parent = parent
        self._tick = 0
        self.invalidate()
        # uses parent.filter and parent.fields - TODO:  decouple that a bit

    def invalidate(self):
        self._row_map = {}
        self._finished_map = False
        self._tick += 1

    # tied to "per record filtering"
    def __iter__(self):
        current_tick = self._tick
        if self.parent.filter is None:
            return iter(self.data)
        valid_rows_counter = 0
        for i, row in enumerate(self.data):
            self.parent.current_record = row if isinstance (row, Mapping) else {
                key: value for key, value in zip(self.parent.fields, row)}
            if self.parent.filter.value:
                self._row_map[valid_rows_counter] = i
                valid_rows_counter += 1
                yield row
        # Avoids that a iterator that has been paused, with
        # changes taking place in the pauses, marks
        # the rows as incorrectly filtered
        if current_tick == self._tick:
            self._finished_map = True


    def ensure_filtered(self):
        if not self._finished_map:
            # DO NOT REMOVE THE EMPTY LOOP!!
            # consume self.__iter__: updates self._rows_map
            for row in self:
                pass

    def __getitem__(self, index):
        self.ensure_filtered()
        try:
            return self.data[self._row_map[index]]
        except KeyError as e:
            raise IndexError from e

    def __setitem__(self, index, value):
        self.ensure_filtered()
        self.data[self._row_map[index]] = value
        self.invalidate()

    def __delitem__(self, index):
        self.ensure_filtered()
        del self.data[self._row_map[index]]
        self.invalidate()

    def __len__(self):
        if self.parent.filter is None:
            return len(self.data)
        self.ensure_filtered()
        return len(self._row_map)

    def insert(self, position, row):
        """Inserting in a table ignores any filtering

        This behavior is needed because rows are inserted as part of collections.abc.MutableSequence protocol,
        which calls insert for every row, and we do this after the filter object is set if it
        is passed on table creation.
        """
        if self.parent.filter is not None:
            warnings.warn(D("""\
                Inserting rows in a table with an active filter, will ignore the filter,
                and can result in quadratically slow workflows.

                Consider removing the filter for insertion - or using the "pause_filter()"
                context manager on the parent object.
                """))
        self.data.insert(position, row)
        self.invalidate()




class PerRecordFilterable(query.QueryableMixin, MutableSequence):

    # Has to inherit from MutableSequence so thatr this cls.extend have
    # priority over MutableSequence.extend when the mixin is used.

    filter = None

    # current_record in instances is filled in when iterating over the associated "FilterableSequence"
    current_record = None

    @property
    def filtering_strategy(self):
        return self.current_record

    def filter_reset(self):
        self._inner_rows.invalidate()

    @property
    def _rows(self):
        if self.filter is None:
            return self._inner_rows.data
        return self._inner_rows

    @_rows.setter
    def _rows(self, sequence):
        self._inner_rows=FilterableSequence(sequence, self)

    @contextlib.contextmanager
    def pause_filter(self):
        filter_ = getattr(self, "filter", None)
        try:
            self.filter = None
            yield
        finally:
            self.filter = filter_

    def extend(self, iterable):
        with self.pause_filter():
            super().extend(iterable)
