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
