# -*- coding: utf-8 -*-

import json
import signal
import subprocess

import ptrace.debugger as pdbg
import ptrace.signames


crash_signals = (signal.SIGILL, signal.SIGABRT, signal.SIGEMT, signal.SIGFPE, signal.SIGBUS, signal.SIGSEGV, signal.SIGSYS)

def get_pids(name):
    pgrep = ("pgrep", name)
    pid = subprocess.Popen(pgrep, stdout=subprocess.PIPE).communicate()[0]
    return list(map(int, pid.split()))

class PtraceDbg(object):

    def __init__(self, pids):
        self.pids = pids
        is_attached = False
        self.dbg = pdbg.debugger.PtraceDebugger()
        self.processes = []
        self.is_running = False
        for pid in self.pids:
            process = self.dbg.addProcess(pid, is_attached)
            self.processes.append(process)
            process.cont()

    @classmethod
    def attach(cls, pids):
        return cls(pids)

    def watch(self, on_signal, on_event, on_exit):
        self.is_running = True
        while self.is_running and self.processes != []:
            event = self.dbg.waitProcessEvent()
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

    def __init__(self, pid, signum, time_):
        self.pid = pid
        self.signal = ptrace.signames.signalName(signum)
        self.time = time_
        self.registers = {}
        self.backtrace = []
        self.disassembly = []
        self.maps = []
        self.stream = []
        self.history = []

    def to_json(self, f):
        json.dump({"pid":self.pid,
                   "signal":self.signal,
                   "time":self.time,
                   "registers":self.registers,
                   "backtrace":self.backtrace,
                   "disassembly":self.disassembly,
                   "maps":self.maps,
                   "stream":self.stream,
                   "history":self.history},
                  f,
                  indent=4)
