"""解析与求值 LDAP 过滤表达式。"""

_HEX = set("0123456789abcdefABCDEF")


class Counter:
    """记录比较次数。"""

    def __init__(self):
        self.scanned = 0


def parse(text, counter):
    pos = [0]
    return _parse(text, pos, counter)


def _parse(text, pos, counter):
    counter.scanned += 1
    if pos[0] >= len(text) or text[pos[0]] != "(":
        raise ValueError("bad-filter")
    pos[0] += 1
    ch = text[pos[0]]
    if ch in "&|":
        pos[0] += 1
        children = []
        while pos[0] < len(text) and text[pos[0]] == "(":
            children.append(_parse(text, pos, counter))
        pos[0] += 1
        return (ch, children)
    if ch == "!":
        pos[0] += 1
        child = _parse(text, pos, counter)
        pos[0] += 1
        return ("!", [child])
    start = pos[0]
    while text[pos[0]] != "=":
        pos[0] += 1
    attr = text[start:pos[0]]
    pos[0] += 1
    start = pos[0]
    while text[pos[0]] != ")":
        pos[0] += 1
    value = text[start:pos[0]]
    pos[0] += 1
    return ("simple", attr, value)


def _unescape(value):
    out = []
    i = 0
    while i < len(value):
        if (
            value[i] == "\\"
            and i + 2 < len(value)
            and value[i + 1] in _HEX
            and value[i + 2] in _HEX
        ):
            out.append(chr(int(value[i + 1 : i + 3], 16)))
            i += 3
        else:
            out.append(value[i])
            i += 1
    return "".join(out)


def _split_substrings(value):
    """按未转义的 * 分段，同时还原转义；无通配符时返回 None。"""
    segments = []
    buf = []
    wild = False
    i = 0
    while i < len(value):
        ch = value[i]
        if (
            ch == "\\"
            and i + 2 < len(value)
            and value[i + 1] in _HEX
            and value[i + 2] in _HEX
        ):
            buf.append(chr(int(value[i + 1 : i + 3], 16)))
            i += 3
        elif ch == "*":
            wild = True
            segments.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(ch)
            i += 1
    if not wild:
        return None
    segments.append("".join(buf))
    return segments


def _match_substring(segments, text):
    initial, final = segments[0], segments[-1]
    middles = segments[1:-1]
    pos = 0
    if initial:
        if not text.startswith(initial):
            return False
        pos = len(initial)
    end = len(text)
    if final:
        if len(final) > len(text) - pos or not text.endswith(final):
            return False
        end = len(text) - len(final)
    for seg in middles:
        if not seg:
            continue
        found = text.find(seg, pos, end)
        if found < 0:
            return False
        pos = found + len(seg)
    return True


def _match_simple(attr, value, entry):
    values = entry.get(attr)
    if values is None:
        return False
    if isinstance(values, str):
        values = [values]
    if value == "*":
        return True
    segments = _split_substrings(value)
    if segments is None:
        target = _unescape(value)
        return any(v == target for v in values)
    return any(_match_substring(segments, v) for v in values)


def match(node, entry, counter):
    counter.scanned += 1
    kind = node[0]
    if kind == "&":
        return all(match(child, entry, counter) for child in node[1])
    if kind == "|":
        return any(match(child, entry, counter) for child in node[1])
    if kind == "!":
        return not match(node[1][0], entry, counter)
    if kind == "simple":
        return _match_simple(node[1], node[2], entry)
    return False


class DB:
    def __init__(self, entries):
        self.entries = entries
        self.index = {}
        for i, entry in enumerate(entries):
            for attr, values in entry.items():
                if isinstance(values, str):
                    values = [values]
                bucket = self.index.setdefault(attr, {})
                for v in values:
                    bucket.setdefault(v, []).append(i)


def search(db, text, counter):
    node = parse(text, counter)
    if node[0] == "simple":
        attr, value = node[1], node[2]
        if value != "*" and _split_substrings(value) is None:
            counter.scanned += 1
            hits = db.index.get(attr, {}).get(_unescape(value), [])
            return list(hits)
    out = []
    for i, entry in enumerate(db.entries):
        counter.scanned += 1
        if match(node, entry, counter):
            out.append(i)
    return out
