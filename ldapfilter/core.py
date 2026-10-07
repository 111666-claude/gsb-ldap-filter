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
    return ("simple", attr, _parse_value(value))


def _parse_value(raw):
    """把断言值还原转义并分段。

    返回 ("present",)、("equal", 字面值) 或 ("substr", 词元列表)。
    词元是 ("lit", 文本) 或 ("wild",)；转义过的 * 只出现在 "lit" 里。
    """
    tokens = []
    buf = []
    pending = bytearray()

    def flush_bytes():
        if pending:
            buf.append(bytes(pending).decode("utf-8"))
            del pending[:]

    def flush_lit():
        flush_bytes()
        if buf:
            tokens.append(("lit", "".join(buf)))
            del buf[:]

    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\":
            pending.append(int(raw[i + 1:i + 3], 16))
            i += 3
        elif ch == "*":
            flush_lit()
            tokens.append(("wild",))
            i += 1
        else:
            flush_bytes()
            buf.append(ch)
            i += 1
    flush_lit()

    wilds = [t for t in tokens if t[0] == "wild"]
    if not wilds:
        return ("equal", "".join(t[1] for t in tokens))
    if len(tokens) == 1:
        return ("present",)
    return ("substr", tokens)


def _substr_match(tokens, value):
    pos = 0
    for i, tok in enumerate(tokens):
        if tok[0] == "wild":
            continue
        seg = tok[1]
        if i == 0:
            if not value.startswith(seg):
                return False
            pos = len(seg)
        else:
            found = value.find(seg, pos)
            if found < 0:
                return False
            pos = found + len(seg)
    last = tokens[-1]
    if last[0] == "lit" and not value.endswith(last[1]):
        return False
    return True


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
        attr, pattern = node[1], node[2]
        values = entry.get(attr)
        if values is None:
            return False
        if isinstance(values, str):
            values = [values]
        pkind = pattern[0]
        if pkind == "present":
            return True
        if pkind == "equal":
            return any(v == pattern[1] for v in values)
        return any(_substr_match(pattern[1], v) for v in values)
    return False


class DB:
    def __init__(self, entries):
        self.entries = entries
        self.index = {}
        for i, entry in enumerate(entries):
            for attr, values in entry.items():
                if isinstance(values, str):
                    values = [values]
                for v in values:
                    self.index.setdefault(attr, {}).setdefault(v, []).append(i)


def _candidates(db, node):
    """能用属性索引时返回候选下标（升序），否则返回 None。"""
    kind = node[0]
    if kind == "simple":
        attr, pattern = node[1], node[2]
        if pattern[0] == "equal":
            return list(db.index.get(attr, {}).get(pattern[1], []))
        return None
    if kind == "&":
        best = None
        for child in node[1]:
            found = _candidates(db, child)
            if found is not None and (best is None or len(found) < len(best)):
                best = found
        return best
    return None


def search(db, text, counter):
    node = parse(text, counter)
    candidates = _candidates(db, node)
    if candidates is None:
        candidates = range(len(db.entries))
    out = []
    for i in candidates:
        counter.scanned += 1
        if match(node, db.entries[i], counter):
            out.append(i)
    return out
