# -*- coding: utf-8 -*-

import collections
import json
import logging
import os
import re
import signal
import subprocess
import time

import ptrace.debugger as pdbg
import ptrace.error as perror
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
        self.is_running = False
        self.logger = logging.getLogger("PtraceDbg")
        super(PtraceDbg, self).__init__()

    def spawn_traced_process(self):
        try:
            process = self.createProcess()
        except pdbg.child.ChildError as ce:
            raise IOError("Failed to create traced process: %s => %s" % (" ".join(self.program), ce))
        self.logger.info("Successfully attached to process: %d" % process.pid)
        process.cont()
        self.logger.info("Moving process to running state: %d" % process.pid)
        self.processes.append(process)
        return process

    def stop(self):
        for process in self.processes:
            try:
                process.detach()
                self.processes.remove(process)
                self.logger.warn("Detached from process: %d" % process.pid)
                process.terminate()
                self.logger.warn("Terminated process: %d" % process.pid)
            except perror.PtraceError:
                pass
        self.is_running = False

    def watch(self, on_signal, on_event, on_exit):
        # Spawning of tracee MUST be done in same thread as event waitProcessEvent() on Linux
        try:
            self.spawn_traced_process()
        except IOError as ioe:
            self.logger.fatal(ioe)
            # This is realy ugly, it relies on the fuzzmon sigint handler to exit
            # TODO: Implement a queue to relay thread satus to spawner
            os.kill(os.getpid(), signal.SIGINT)
            return
        self.is_running = True
        self.logger.info("Debugger entered event monitoring loop")
        while self.is_running and self.processes != []:
            try:
                event = self.debugger.waitProcessEvent()
            except OSError as oe:
                self.logger.fatal("Debugger event loop failed: %s" % oe)
                self.stop()
                return
            process = event.process
            self.logger.info("Caught event on process: %d => \"%s\". Dispatching to callback" % (process.pid, event))
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
                    self.logger.info("Detected process as dead: %d" % process.pid)
                except ValueError:
                    pass
        self.logger.info("Debugger exiting event monitoring loop")
        self.is_running = False


class CrashReport(object):

    # Matches
    # 'MAPS: 0x00007fb7b25ae000-0x00007fb7b2730000 => /lib/x86_64-linux-gnu/libc-2.13.so (r-xp)'
    # 'MAPS: 0x0000000000df5000-0x0000000000e16000 => [heap] (rwxp)'
    # 'MAPS: 0x00007fb7b2b56000-0x00007fb7b2b59000 (rwxp)'
    # Into start/stop address, binary, permissions
    MAPS_REGEXP = "MAPS:\s(0x[0-9a-fA-F]+)-(0x[0-9a-fA-F]+)\s(?:=>\s)?(.*?)\s?\((.+)\)"

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
        self.regexp = re.compile(CrashReport.MAPS_REGEXP)

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
        try:
            start_addr, stop_addr, binary, perms = self.regexp.match(str_).groups()
            self.maps.append(((start_addr, stop_addr), binary, perms))
        except ValueError:
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
