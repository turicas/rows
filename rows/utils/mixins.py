from functools import wraps

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
