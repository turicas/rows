from copy import copy


SIDES = "left top right bottom".split()


class Rect:
    def __init__(self, rect):
        #rect = {key: value for key, value in rect.items() if key in SIDES}
        self.__dict__.update(rect)

    def __hash__(self):
        return hash((self.left, self.top, self.right, self.bottom))

    def __getitem__(self, item):
        return self.__dict__[item]

    def __setitem__(self, item, value):
        self.__dict__[item] = value

    def __eq__(self, other):
        return all(self[side] == other[side] for side in SIDES)

    def __repr__(self):
        return "<{left}, {top}, {right}, {bottom}>".format(**self.__dict__)


def consolidate(new_rect, rect1, rect2):
    if new_rect is None:
        new_rect = copy(rect1)
    for op, side in zip((min, max, max, min), SIDES):
        new_rect[side] = op(r[side] for r in (new_rect, rect1, rect2))

    return new_rect


def mag(x, y):
    return x ** 2 + y ** 2


def find_paired_rects(rects, tolerance):

    rects_by_left = {}
    for r in rects:
        rects_by_left.setdefault(r.left, []).append(r)

    left_right_pairs = []
    paired = {}
    for rect in rects:
        mag_alignment = None
        for offset_x in range(-tolerance, tolerance + 1):
            if (rect.right + offset_x) not in rects_by_left:
                continue
            for aligned_rect in rects_by_left[rect.right + offset_x]:
                if aligned_rect is rect: continue
                for offset_y in range(-tolerance, tolerance + 1):
                    if (rect.top + offset_y) == aligned_rect.top:
                        new_mag = mag(offset_x, offset_y)
                        if mag_alignment is None or new_mag < mag_alignment:
                            paired[rect] = aligned_rect
                            mag_alignment = new_mag

    return paired


def join_contiguous_rects(rect_dicts, tolerance=1):
    rects = [Rect(rect) for rect in rect_dicts]

    paired = find_paired_rects(rects, tolerance)

    consolidated = []
    to_remove = set()

    for rect in sorted(rects, key=lambda r:r.left):
        if rect in to_remove:
            continue
        new_rect = None
        chars = ""
        while rect in paired:
            chars += rect.char
            new_rect = consolidate(new_rect, rect, paired[rect])
            to_remove.add(rect)
            rect = paired[rect]

        chars += rect.char
        if new_rect:
            new_rect.char = chars
            to_remove.add(rect)
            consolidated.append(new_rect)

    result = [
        r.__dict__ for r in sorted(
            consolidated + [rect for rect in rects if rect not in to_remove],
            key= lambda r: (-r.top, r.left)
        )
    ]
    return result

