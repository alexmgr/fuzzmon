# -*- coding: utf-8 -*-

import logging
import select
import socket


class StreamDirection(object):
    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"


class ProxyHooks(object):

    def __init__(self):
        self.is_done = False

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
            logging.debug("Successfully connected to upstream server %s: %s" % (connect_data, self.socket_))
            return self.socket_
        except socket.error:
            logging.error()
            return None


class Downstream(object):

    def __init__(self, server_socket, client_socket, upstream_address, proxy_hook=None):
        self.downstream_socket = server_socket
        self.upstream_socket = client_socket
        self.upstream_address = upstream_address
        self.proxy_hook = proxy_hook
        self.inputs = [self.downstream_socket]
        self.channels = []
        self.is_running = False

    def serve(self, buffer_size=4096, timeout=None):
        self.is_running = True
        logging.info("Downstream server listening for new connections")
        while self.is_running and not self.proxy_hook.is_done:
            if timeout is None:
                read_ready, _, _ = select.select(self.inputs, [], [])
            else:
                read_ready, _, _ = select.select(self.inputs, [], [], timeout)
            for socket_ in read_ready:
                if socket_ == self.downstream_socket:
                    self._on_accept()
                else:
                    try:
                        data = socket_.recv(buffer_size)
                    except socket.error:
                        self._on_close(socket_)
                    if len(data) == 0:
                        self._on_close(socket_)
                    else:
                        self._on_read(socket_, data)
        self.is_running = False

    def _on_accept(self):
        downstream_client_socket, client_addr = self.downstream_socket.accept()
        logging.debug("New downstream connection from %s: %s" % (client_addr, downstream_client_socket))
        upstream_client_socket = Upstream(self.upstream_socket).connect(self.upstream_address)
        if upstream_client_socket is not None:
            channel = {StreamDirection.DOWNSTREAM: downstream_client_socket,
                       StreamDirection.UPSTREAM: upstream_client_socket}
            self.channels.append(channel)
            self.inputs.append(downstream_client_socket)
            self.inputs.append(upstream_client_socket)
            logging.debug("Created new socket pair for stream: %s" % channel)
        else:
            logging.error("Failed to connect to upstream server. Closing downstream: %s" % downstream_client_socket)
            downstream_client_socket.close()

    def _on_read(self, socket_, data):
        other_socket = self._other(socket_)
        if other_socket is not None:
            if self.proxy_hook is not None:
                if self._direction(other_socket) == StreamDirection.UPSTREAM:
                    logging.debug("Received data downstream: %s. Forwarding to: %s" % (socket_, other_socket))
                    data = self.proxy_hook.pre_upstream_send(other_socket, data)
                    other_socket.send(data)
                    is_alive = self.proxy_hook.post_upstream_send(other_socket, data)
                elif self._direction(other_socket) == StreamDirection.DOWNSTREAM:
                    logging.debug("Received data upstream: %s. Forwarding to: %s" % (socket_, other_socket))
                    data = self.proxy_hook.pre_downstream_send(other_socket, data)
                    other_socket.send(data)
                    is_alive = self.proxy_hook.post_downstream_send(other_socket, data)
                else:
                    logging.error("Unknown proxy state for current connection")
                    raise RuntimeWarning("Unknown proxy state for current connection")
                if not is_alive:
                    logging.warn("Upstream server appears to be dead: %s" % socket_)
                    self._on_close(socket_)
            else:
                other_socket.send(data)
        else:
            logging.warn("No socket pair found for socket: %s" % socket_)
            self._on_close(socket_)

    def _on_close(self, socket_):
        logging.debug("Removing sockets from select() loop")
        other_socket = self._other(socket_)
        if self._get_socket_pair(socket_) in self.channels:
            self.channels.remove(self._get_socket_pair(socket_))
        if socket_ in self.inputs:
            self.inputs.remove(socket_)
        if other_socket in self.inputs:
            self.inputs.remove(other_socket)
        try:
            socket_.close()
            logging.debug("Closing socket: %s" % socket_)
        except socket.error:
            pass
        try:
            other_socket.close()
            logging.debug("Closing socket: %s" % other_socket)
        except (socket.error, AttributeError):
            pass

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
        for k, v in channel.items():
            if v == socket_:
                return k
        return None
