"""解析与求值 LDAP 过滤表达式。"""


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


def match(node, entry, counter):
    counter.scanned += 1
    kind = node[0]
    if kind == "&":
        return all(match(child, entry, counter) for child in node[1])
    if kind == "|":
        return any(match(child, entry, counter) for child in node[1])
    if kind == "!":
        return match(node[1][0], entry, counter)
    if kind == "simple":
        attr, value = node[1], node[2]
        values = entry.get(attr)
        if values is None:
            return False
        if isinstance(values, str):
            values = [values]
        if value == "*":
            return True
        return values[0] == value
    return False


class DB:
    def __init__(self, entries):
        self.entries = entries


def search(db, text, counter):
    node = parse(text, counter)
    out = []
    for i, entry in enumerate(db.entries):
        counter.scanned += 1
        if match(node, entry, counter):
            out.append(i)
    return out
