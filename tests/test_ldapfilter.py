import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ldapfilter import core


def one(text, entry):
    return core.match(core.parse(text, core.Counter()), entry, core.Counter())


class LdapFilterTest(unittest.TestCase):
    def test_presence(self):
        self.assertTrue(one("(cn=*)", {"cn": "x"}))

    def test_equality(self):
        self.assertTrue(one("(cn=x)", {"cn": "x"}))

    def test_and(self):
        self.assertTrue(one("(&(cn=x)(sn=y))", {"cn": "x", "sn": "y"}))

    def test_or(self):
        self.assertTrue(one("(|(cn=z)(sn=y))", {"cn": "x", "sn": "y"}))

    def test_missing_attr(self):
        self.assertFalse(one("(cn=x)", {}))

    def test_counter_counts(self):
        counter = core.Counter()
        core.parse("(cn=x)", counter)
        self.assertGreater(counter.scanned, 0)


if __name__ == "__main__":
    unittest.main()
