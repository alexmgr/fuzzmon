# -*- coding: utf-8 -*-

import argparse
import socket


proto_table = dict(tcp=socket.SOCK_STREAM, udp=socket.SOCK_DGRAM)
to_host = lambda x: x[0] if len(x) == 1 else x


def socket_type(str_):
    try:
        proto, remaining = str_.split(":", 1)
        proto = proto_table[proto.lower()]
        host, port = remaining.rsplit(":", 1)
        if host.lower() == "uds":
            family = socket.AF_UNIX
            info = (port,)
        else:
            # v4 preferred if fqdn used
            family = socket.getaddrinfo(host, port)[0][0]
            info = (host, int(port))
    except (ValueError, KeyError, socket.gaierror):
        raise argparse.ArgumentTypeError("Invalid protocol description argument. Expecting proto:host:port or "
                                         "proto:uds:file")
    return family, proto, info


class Dequeue(object):
    """ Python collections.deque only supports Hashable entries
    Quick version backed by a list which supports any type of object
    """

    def __init__(self, items=[], maxlen=0):
        if maxlen < 0:
            raise ValueError("maxlen must be non-negative")
        if len(items) >= maxlen:
            self.items = items[-maxlen:]
        else:
            self.items = items[:]
        self.maxlen = maxlen

    def __contains__(self, item):
        return item in self.items

    def __eq__(self, other):
        return True if self.items == other.items else False

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, key):
        return self.items[key]

    def __setitem__(self, key, value):
        self.items[key] = value

    def __delitem__(self, key):
        del (self.items[key])

    def __repr__(self):
        return repr(self.items)

    def __str__(self):
        return str(self.items)

    def append(self, item):
        if len(self.items) >= self.maxlen:
            self.items.remove(self.items[0])
        self.items.append(item)

    def appendleft(self, item):
        if len(self.items) >= self.maxlen:
            self.items.remove(self.items[-1])
        self.insert(0, item)

    def clear(self):
        self.items = []

    def count(self, item):
        return self.items.count(item)

    def extend(self, other):
        self.maxlen = len(self.items) + len(other)
        self.items.extend(other)

    def extendleft(self, other):
        self.maxlen = len(self.items) + len(other)
        self.items = other[:] + self.items[:]

    def index(self, item):
        return self.items.index(item)

    def insert(self, key, item):
        if len(self.items) < self.maxlen:
            self.items.insert(key, item)
        else:
            raise ValueError("Cannot insert in full dequeue list")

    def pop(self):
        return self.items.pop()

    def popleft(self):
        first_item = self.items[0]
        self.items = self.items[1:]
        return first_item

    def remove(self, v):
        self.items.remove(v)

    def reverse(self):
        self.items.reverse()

    def sort(self, cmp_=None, key=None, reverse=False):
        self.items.sort(cmp=cmp_, key=key, reverse=reverse)


def colorize(str_, colour):
    return "%s%s%s" % (colour, str_, TermColors.END)


class TermColors(object):
    # From here: http://stackoverflow.com/questions/287871/print-in-terminal-with-colors-using-python
    PINK = "\033[95m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
