# -*- coding: utf-8 -*-

import select
import socket


class StreamDirection(object):
    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"

class ProxyHooks(object):

    def pre_downstream_send(self, socket_, data):
        return data

    def post_downstream_send(self, socket_, data):
        return True

    def pre_upstream_send(self, socket_, data):
        return data

    def post_upstream_send(self, socket_, data):
        return True

class Upstream(object):

    def __init__(self, socket_):
        self.socket_ = socket.socket(socket_.family, socket_.type, socket_.proto)
        self.socket_.settimeout(socket_.gettimeout())

    def connect(self, connect_data):
        try:
            self.socket_.connect(connect_data)
            return self.socket_
        except socket.error:
            return None

class Downstream(object):

    def __init__(self, server_socket, client_socket, upstream_address, proxy_hook=None):
        self.downstream_socket = server_socket
        self.upstream_socket = client_socket
        self.upstream_address = upstream_address
        self.proxy_hook = proxy_hook
        self.inputs = [self.downstream_socket]
        self.channels = []

    def serve(self, buffer_size=4096, timeout=None):
        while True:
            if timeout is None:
                read_ready, _, _ = select.select(self.inputs, [], [])
            else:
                read_ready, _, _ = select.select(self.inputs, [], [], timeout)
            for socket_ in read_ready:
                if socket_ == self.downstream_socket:
                    self._on_accept()
                else:
                    data = socket_.recv(buffer_size)
                    if len(data) == 0:
                        self._on_close(socket_)
                    else:
                        self._on_read(socket_, data)

    def _on_accept(self):
        downstream_client_socket, client_addr = self.downstream_socket.accept()
        upstream_client_socket = Upstream(self.upstream_socket).connect(self.upstream_address)
        if upstream_client_socket is not None:
            self.channels.append({StreamDirection.DOWNSTREAM:downstream_client_socket, StreamDirection.UPSTREAM:upstream_client_socket})
            self.inputs.append(downstream_client_socket)
            self.inputs.append(upstream_client_socket)
        else:
            downstream_client_socket.close()

    def _on_read(self, socket_, data):
        other_socket = self._other(socket_)
        if self.proxy_hook is not None:
            if self._direction(other_socket) == StreamDirection.UPSTREAM:
                data = self.proxy_hook.pre_upstream_send(other_socket, data)
                other_socket.send(data)
                is_alive = self.proxy_hook.post_upstream_send(other_socket, data)
            elif self._direction(other_socket) == StreamDirection.DOWNSTREAM:
                data = self.proxy_hook.pre_downstream_send(other_socket, data)
                other_socket.send(data)
                is_alive = self.proxy_hook.post_downstream_send(other_socket, data)
            else:
                raise RuntimeWarning("Unknown proxy state for current connection")
            if not is_alive:
                self._on_close(socket_)
        else:
            other_socket.send(data)

    def _on_close(self, socket_):
        other_socket = self._other(socket_)
        self.channels.remove(self._get_socket_pair(socket_))
        self.inputs.remove(socket_)
        self.inputs.remove(other_socket)
        socket_.close()
        other_socket.close()

    def _get_socket_pair(self, socket_):
        for channel in self.channels:
            if socket_ in channel.values():
                return channel
        return {}

    def _other(self, socket_):
        channel = self._get_socket_pair(socket_)
        for v in channel.values():
            if v != socket_:
                return v
        return None

    def _direction(self, socket_):
        channel = self._get_socket_pair(socket_)
        for k,v in channel.iteritems():
            if v == socket_:
                return k
        return None
