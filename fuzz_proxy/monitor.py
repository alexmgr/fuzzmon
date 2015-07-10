# -*- coding: utf-8 -*-

import collections
import json
import re
import signal
import subprocess
import time

import ptrace.debugger as pdbg
import ptrace.signames

crash_signals = (signal.SIGILL, signal.SIGABRT, signal.SIGFPE, signal.SIGBUS, signal.SIGSEGV, signal.SIGSYS)


def get_pids(name):
    pgrep = ("pgrep", name)
    pid = subprocess.Popen(pgrep, stdout=subprocess.PIPE).communicate()[0]
    return list(map(int, pid.split()))


def get_pid_command(pid):
    proc_path = "/proc/%s/cmdline" % pid
    try:
        with open(proc_path, "r") as f:
            cmdline = f.read().replace("\x00", " ").strip()
    except IOError:
        cmdline = None
    return cmdline


class PtraceDbg(pdbg.Application):

    def __init__(self, options):
        self.options = options
        self.program = self.options.program
        self.processes = []
        self.processOptions()
        self.debugger = pdbg.debugger.PtraceDebugger()
        self.setupDebugger()
        self.spawn_traced_process()
        self.is_running = False

    def spawn_traced_process(self):
        try:
            process = self.createProcess()
        except pdbg.child.ChildError as ce:
            raise IOError("Failed to create traced process: %s => %s" % (" ".join(self.program), ce))
        process.cont()
        self.processes.append(process)
        return process

    def stop(self):
        for process in self.processes:
            process.detach()
            self.processes.remove(process)
        self.is_running = False

    def watch(self, on_signal, on_event, on_exit):
        self.is_running = True
        while self.is_running and self.processes != []:
            event = self.debugger.waitProcessEvent()
            process = event.process
            if event.__class__ == pdbg.ProcessSignal:
                on_signal(event)
            elif event.__class__ == pdbg.ProcessEvent:
                on_event(event)
            elif event.__class__ == pdbg.ProcessExit:
                on_exit(event)
            else:
                raise RuntimeError("Unexpected process event: %s" % event)
            if not process.is_attached:
                try:
                    self.processes.remove(process)
                except ValueError:
                    pass
        self.is_running = False


class CrashReport(object):
    def __init__(self, sessid, pid, signum, stream_id):
        self.pid = pid
        self.sessid = sessid
        self.signal = ptrace.signames.signalName(signum)
        self.stream_id = stream_id
        self.time = time.time()
        self.registers = {}
        self.stack = collections.OrderedDict()
        self.backtrace = collections.OrderedDict()
        self.disassembly = collections.OrderedDict()
        self.maps = []
        self.stream = []
        self.history = []

    def to_json(self, f):
        json.dump({"session_id": self.sessid,
                   "stream_count": self.stream_id,
                   "pid": self.pid,
                   "signal": self.signal,
                   "time": self.time,
                   "registers": self.registers,
                   "backtrace": self.backtrace,
                   "disassembly": self.disassembly,
                   "maps": self.maps,
                   "stack": self.stack,
                   "stream": self.stream,
                   "history": self.history},
                  f,
                  indent=4)

    def dump_regs(self, str_):
        try:
            reg, val = list(map(lambda x: x.strip(), str_.split("=")))
            self.registers[reg] = val
        except ValueError:
            pass

    def dump_maps(self, str_):
        pass

    def dump_stack(self, str_):
        try:
            addr, val = list(map(lambda x: x.strip(), str_.split(":")))
            self.stack[addr] = val
        except ValueError:
            pass

    def dump_backtrace(self, frame):
        self.backtrace[hex(frame.ip)] = (frame.name, frame.arguments)

    def dump_code(self, str_):
        self.disassembly[hex(str_.address)] = str_.text
