# -*- coding: utf-8 -*-

import binascii
import logging
import os
try:
    import Queue as queue
except ImportError:
    import queue
import time
import threading

import ptrace.error as perror

import fuzz_proxy.helpers as fuzzhelp
import fuzz_proxy.monitor as fuzzmon
import fuzz_proxy.network as fuzznet


class DebuggingHooks(fuzznet.ProxyHooks):
    def __init__(self, debugger, sessid, crash_folder="metadata", restart_delay=0, max_streams=10,
                 max_pkts_per_stream=10, crash_timeout=0.01):
        self.debugger = debugger
        self.sessid = sessid
        # First stream will get id 0
        self.stream_counter = -1
        self.restart_delay = restart_delay
        if not os.path.isdir(crash_folder):
            os.makedirs(os.path.join(os.path.abspath(os.path.curdir), crash_folder))
        self.crash_folder = crash_folder
        self.crash_events = queue.Queue()
        self.streams = fuzzhelp.Dequeue(maxlen=max_streams)
        self.max_pkts_per_stream = max_pkts_per_stream
        self.crash_timeout = crash_timeout
        self.logger = logging.getLogger("DebuggingHooks")
        threading.Thread(target=self.debugger.watch,
                         args=(self.on_signal, self.on_event, self.on_exit)
                         ).start()
        super(DebuggingHooks, self).__init__()

    def _get_stream(self, channel):
        for stream in self.streams:
            if channel in stream.keys():
                return stream
        return None

    def _get_stream_history(self):
        history = []
        for stream in self.streams:
            history.append([(pkt[0], binascii.hexlify(pkt[1])) for pkt in stream.values()[0]])
        # Remove the stream causing the crash from history
        history.pop()
        return history

    def pre_upstream_send(self, channel, data):
        return self._pre_send(channel, data, fuzznet.StreamDirection.UPSTREAM)

    def post_upstream_send(self, channel, data):
        self.logger.debug("Entering post upstream send callback: %s" % channel)
        immutable_channel = frozenset(channel.items())
        try:
            crash_report = self.crash_events.get(timeout=self.crash_timeout)
            self.logger.warn("Upstream server crashed!")
            # Stream which caused the crash
            crash_report.stream = [(pkt[0], binascii.hexlify(pkt[1])) for pkt in
                                   self._get_stream(immutable_channel).values()[0]]
            # Populate history
            crash_report.history = self._get_stream_history()
            crash_file_name = os.path.join(self.crash_folder, "%s.json" % crash_report.pid)
            self.logger.info("Dumping crash information to: %s" % crash_file_name)
            with open(crash_file_name, "w") as f:
                crash_report.to_json(f)
            return False
        except queue.Empty:
            self.logger.debug("No upstream crash detected")
            return True

    def pre_downstream_send(self, channel, data):
        return self._pre_send(channel, data, fuzznet.StreamDirection.DOWNSTREAM)

    def _pre_send(self, channel, data, direction):
        self.logger.debug("Entering pre %s send callback: %s" % (direction, channel))
        immutable_channel = frozenset(channel.items())
        stream = self._get_stream(immutable_channel)
        if stream is None:
            stream = fuzzhelp.Dequeue([(direction, data)], maxlen=self.max_pkts_per_stream)
            self.streams.append({immutable_channel: stream})
            self.stream_counter += 1
            self.logger.debug("Creating new %s stream %d: %s" % (direction, self.stream_counter, stream))
        else:
            self.streams.remove(stream)
            stream[immutable_channel].append((direction, data))
            self.streams.append(stream)
            self.logger.debug("Appending data to existing %s stream: %s" % (direction, stream))
        return data

    def on_signal(self, signal_):
        process = signal_.process
        signum = signal_.signum
        if signum in fuzzmon.crash_signals:
            self.logger.warn("Received signal %d from process: %d. Gathering crash information" % (signum, process.pid))
            crash_report = fuzzmon.CrashReport(self.sessid, process.pid, signum, self.stream_counter)
            # Populate registers, maps, backtrace, disassembly if available
            self._ignore_ptrace_errors(process.dumpRegs, crash_report.dump_regs)
            self._ignore_ptrace_errors(process.dumpMaps, crash_report.dump_maps)
            self._ignore_ptrace_errors(process.dumpStack, crash_report.dump_stack)
            frames = self._ignore_ptrace_errors(process.getBacktrace)
            instrs = self._ignore_ptrace_errors(process.disassemble)
            for frame in frames:
                crash_report.dump_backtrace(frame)
            for instr in instrs:
                crash_report.dump_code(instr)
            self.crash_events.put(crash_report)
        self.logger.warn("Propagating signal %d to child process: %d" % (signum, process.pid))
        try:
            process.cont(signum)
        except perror.PtraceError as pe:
            self.logger.critical("Failed to propagate signal to traced process: %s" % pe)
            self._shutdown()

    def on_event(self, event):
        self.logger.critical("Currently unhandled event: %s" % event)
        self.logger.critical("A bug report at https://github.com/alexmgr/fuzzmon would be greatly appreciated")
        raise NotImplementedError("Currently unhandled event: %s")

    def on_exit(self, event):
        if self.restart_delay >= 0:
            self.logger.warn("Waiting %d seconds before restarting process" % self.restart_delay)
            time.sleep(self.restart_delay)
            try:
                process = self.debugger.spawn_traced_process()
                self.logger.warn("Spawned new target process: %d" % process.pid)
            except IOError as ioe:
                self.logger.fatal(ioe)
                self._shutdown()
        else:
            self._shutdown()

    def _shutdown(self):
        self.debugger.stop()
        self.is_done = True
        self.logger.warn("Stopped debugger. Exiting now")

    def _ignore_ptrace_errors(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (NotImplementedError, perror.PtraceError):
            pass
