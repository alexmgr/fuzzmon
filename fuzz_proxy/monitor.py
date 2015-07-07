# -*- coding: utf-8 -*-

import subprocess
import ptrace.debugger.debugger


def get_pids(name):
    pgrep = ("pgrep", name)
    pid = subprocess.Popen(pgrep, stdout=subprocess.PIPE).communicate()[0]
    return list(map(int, pid.split()))

class PtraceDbg(object):

    def __init__(self, pids):
        self.pids = pids
        is_attached = False
        self.dbg = ptrace.debugger.debugger.PtraceDebugger()
        self.processes = []
        for pid in self.pids:
            process = self.dbg.addProcess(pid, is_attached)
            self.processes.append(process)
            process.cont()

    @classmethod
    def attach(cls, pids):
        return cls(pids)

    def watch(self, on_signal):
        while self.processes != []:
    #         signal = self.dbg.waitProcessEvent()
            signal = self.dbg.waitSignals()
            process = signal.process
            on_signal(signal)
            if not process.is_attached:
                try:
                    self.processes.remove(process)
                except ValueError:
                    pass
