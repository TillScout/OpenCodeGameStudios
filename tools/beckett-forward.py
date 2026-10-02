#!/usr/bin/env python3
"""TCP forwarder: 127.0.0.1:8770 (VM) -> 10.0.2.2:8770 (host).

Beckett's MCP server rejects non-loopback Host headers. By forwarding
through localhost, Vibe sends Host: 127.0.0.1:8770 which Beckett accepts.
"""
import socket
import threading
import sys

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8770
REMOTE_HOST = "10.0.2.2"
REMOTE_PORT = 8770


def forward(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            src.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            dst.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        src.close()
        dst.close()


def handle(client):
    try:
        remote = socket.create_connection((REMOTE_HOST, REMOTE_PORT), timeout=10)
    except OSError as e:
        sys.stderr.write(f"connect to {REMOTE_HOST}:{REMOTE_PORT} failed: {e}\n")
        client.close()
        return
    t1 = threading.Thread(target=forward, args=(client, remote), daemon=True)
    t2 = threading.Thread(target=forward, args=(remote, client), daemon=True)
    t1.start()
    t2.start()


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((LISTEN_HOST, LISTEN_PORT))
    srv.listen(16)
    sys.stderr.write(f"beckett-forward: {LISTEN_HOST}:{LISTEN_PORT} -> {REMOTE_HOST}:{REMOTE_PORT}\n")
    sys.stderr.flush()
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
