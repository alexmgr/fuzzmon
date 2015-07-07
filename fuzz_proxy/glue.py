# -*- coding: utf-8 -*-

from __future__ import print_function
import thread
import threading
import network

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
        del(self.items[key])

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
            raise ValueError("Cannot insert on full dequeue list")

    def pop(self):
        return self.items.pop()

    def popleft(self):
        first_item = self.items[0]
        self.items = self.items[1:]
        return first_item

    def remove(self, v):
        self.items.remove(v)

    def reverse(self):
        self.items.revers()

    def sort(self, cmp=None, key=None, reverse=False):
        self.items.sort(cmp=None, key=None, reverse=False)

class DebuggingHooks(network.ProxyHooks):

    def __init__(self, debugger, max_streams=10, max_pkts_per_stream=10, crash_timeout=0.1):
        self.debugger = debugger
        self.crash_event = threading.Event()
        self.streams = Dequeue(maxlen=max_streams)
        self.max_pkts_per_stream = max_pkts_per_stream
        self.crash_timeout = crash_timeout
        thread.start_new_thread(debugger.watch, (self.on_signal,))

    def _get_stream(self, socket_):
        for stream in self.streams:
            if socket_ in stream.keys():
                return stream
        return None

    def _to_tuple(self, socket_):
        server_tuple = socket_.getpeername()
        client_tuple = socket_.getsockname()
        return(client_tuple, server_tuple)

    def pre_upstream_send(self, socket_, data):
        stream = self._get_stream(socket_)
        if stream is None:
            stream = Dequeue([data], maxlen=self.max_pkts_per_stream)
            self.streams.append({socket_:stream})
        else:
            self.streams.remove(stream)
            stream[socket_].append(data)
            self.streams.append(stream)
        return data

    def post_upstream_send(self, socket_, data):
        self.crash_event.wait(self.crash_timeout)
        if self.crash_event.is_set():
            print("Dead, data: %s" % data)
            # Restart process
            # Reset event flag
            return False
        else:
            return True

    def on_signal(self, signal):
        process = signal.process
        signum = signal.signum
        self.crash_event.set()
        # log
        signal.display(log=print)
        process.dumpRegs(log=print)
#         process.dumpMaps(log=print)
#         process.dumpStack(log=print)
        process.cont(signum)
