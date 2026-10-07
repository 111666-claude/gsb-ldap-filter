"""固定场景，用来复现题面里的锚点。"""

import json

from . import core


def _line(obj):
    print(json.dumps(obj, ensure_ascii=False))


def one(text, entry):
    node = core.parse(text, core.Counter())
    return core.match(node, entry, core.Counter())


def run(name):
    if name == "substr":
        _line({"match": one("(cn=a*c)", {"cn": "abc"})})
        return 0
    if name == "esc":
        _line({"match": one("(cn=a\\2ab)", {"cn": "a*b"})})
        return 0
    if name == "not":
        _line({"match": one("(!(cn=x))", {"cn": "y"})})
        return 0
    if name == "multi":
        _line({"match": one("(cn=y)", {"cn": ["x", "y"]})})
        return 0
    if name == "work":
        entries = [{"cn": "c%04d" % i} for i in range(800)]
        db = core.DB(entries)
        counter = core.Counter()
        for i in range(800):
            core.search(db, "(cn=c%04d)" % i, counter)
        _line({"entries": 800, "scanned": counter.scanned})
        return 0
    raise SystemExit("未知场景：" + name)
