# -*- coding: utf-8 -*-

import unittest
from fuzz_proxy.glue import Dequeue


class TestDequeue(unittest.TestCase):
    def test_negative_maxlen_raises_value_error(self):
        with self.assertRaises(ValueError):
            Dequeue(maxlen=-1)

    def test_list_longer_than_maxlen_is_truncated(self):
        l = [1, 2, 3, 4, 5]
        d = Dequeue(l, 3)
        self.assertEqual(d, Dequeue(l[-3:]))

    def test_when_maxlen_is_reached_leftmost_values_are_removed_on_append(self):
        d = Dequeue([1, 2, 3, 4], 4)
        d.append(5)
        self.assertEqual(d, Dequeue([2, 3, 4, 5]))

    def test_when_maxlen_is_reached_rightmost_values_are_removed_on_appendleft(self):
        d = Dequeue([1, 2, 3, 4], 4)
        d.appendleft(0)
        self.assertEqual(d, Dequeue([0, 1, 2, 3]))

    def test_first_value_is_poped_on_popleft(self):
        d = Dequeue([1, 2, 3, 4], 4)
        v = d.popleft()
        self.assertEqual(v, 1)
        self.assertEqual(d, Dequeue([2, 3, 4]))
