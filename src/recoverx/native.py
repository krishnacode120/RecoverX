"""Optional accelerator; the tested Python implementation remains fully functional."""

try:
    from _recoverx_native import find_all as _native_find
except ImportError:
    _native_find = None


def find_offsets(data, needle):
    if _native_find:
        yield from _native_find(data, needle)
        return
    position, count = 0, 0
    while True:
        position = data.find(needle, position)
        if position < 0:
            return
        count += 1
        if count > 4096:
            raise ValueError("Signature density limit exceeded")
        yield position
        position += 1
