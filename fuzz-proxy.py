#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import socket
import thread
from fuzz_proxy.glue import DebuggingHooks
from fuzz_proxy.monitor import get_pids, PtraceDbg
from fuzz_proxy.network import Downstream


def prepare_parser():
    parser = argparse.ArgumentParser(description="A proxy which monitors the backend application state")
    output_format_group = parser.add_mutually_exclusive_group(required=True)
    output_format_group.add_argument("-n", "--name", help="Program name to monitor for faults")
    output_format_group.add_argument("-p", "--pids", help="Comma seperated list of PIDs to monitor for faults")
    return parser

if __name__ == "__main__":
    parser = prepare_parser()
    args = parser.parse_args()

    if args.name is not None:
        pids = get_pids(args.name)
    else:
        pids = [int(pid.strip()) for pid in args.pids.split(",") if pid != ""]

    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setblocking(False)
    server_socket.bind(("localhost", 1234))
    server_socket.listen(1)

    client_socket = socket.socket()
    client_socket.settimeout(1.0)
    server_address = ("localhost", 6666)

    dbg = PtraceDbg(pids)
    hooks = DebuggingHooks(dbg)

    server = Downstream(server_socket, client_socket, server_address, hooks)
    server.serve(timeout=2)
