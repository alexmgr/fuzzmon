# -*- coding: utf-8 -*-

import binascii
import os
import Queue
import time
import thread

import fuzz_proxy.monitor as fuzzmon
import fuzz_proxy.network as fuzznet


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

class DebuggingHooks(fuzznet.ProxyHooks):

    def __init__(self, debugger, crash_folder="metadata", max_streams=10, max_pkts_per_stream=10, crash_timeout=0.1):
        self.debugger = debugger
        if not os.path.isdir(crash_folder):
            os.makedirs(os.path.join(os.path.abspath(os.path.curdir), crash_folder))
        self.crash_folder = crash_folder
#         self.crash_event = threading.Event()
        self.crash_events = Queue.Queue()
        self.streams = Dequeue(maxlen=max_streams)
        self.max_pkts_per_stream = max_pkts_per_stream
        self.crash_timeout = crash_timeout
        thread.start_new_thread(debugger.watch, (self.on_signal, self.on_event, self.on_exit))

    def _get_stream(self, socket_):
        for stream in self.streams:
            if socket_ in stream.keys():
                return stream
        return None

    def _get_stream_history(self):
        return [stream.values()[0] for stream in self.streams]

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
        try:
            crash_report = self.crash_events.get(timeout=self.crash_timeout)
            crash_report.stream = [binascii.hexlify(pkt) for pkt in self._get_stream(socket_).values()[0]]
            # Populate history
            crash_file_name = os.path.join(self.crash_folder, "%s.json" % crash_report.pid)
            with open(crash_file_name, "w") as f:
                crash_report.to_json(f)
            return False
        except Queue.Empty:
            return True

    def on_signal(self, signal_):
        process = signal_.process
        signum = signal_.signum
        if signum in fuzzmon.crash_signals:
            crash_report = fuzzmon.CrashReport(process.pid, signum, time.time())
            self.crash_events.put(crash_report)
        process.cont(signum)

    def on_event(self, event):
        pass

    def on_exit(self, event):
        process = event.process
        print(process.pid)
        # Restart process
