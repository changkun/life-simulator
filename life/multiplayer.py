"""Multiplayer networking for competitive mode."""
import json
import queue
import socket
import threading

MP_DEFAULT_PORT = 7654
MP_PLANNING_TIME = 30  # seconds for planning phase
MP_SIM_GENS = 200  # generations per round

class MultiplayerNet:
    """TCP networking for multiplayer mode using background threads.

    Messages are newline-delimited JSON.  A background thread handles I/O so
    the curses event loop never blocks.
    """

    def __init__(self):
        self.role: str | None = None  # "host" or "client"
        self.sock: socket.socket | None = None  # connected socket to peer
        self.server_sock: socket.socket | None = None  # listening (host only)
        self.connected = False
        self.running = False
        self._send_q: queue.Queue = queue.Queue()
        self._recv_q: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._recv_buf = b""

    def start_host(self, port: int) -> bool:
        """Start listening for a connection.  Returns True if bind succeeded."""
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind(("", port))
            self.server_sock.listen(1)
            self.server_sock.settimeout(0.5)
            self.role = "host"
            self.running = True
            self._thread = threading.Thread(target=self._host_loop, daemon=True)
            self._thread.start()
            return True
        except OSError:
            return False

    def connect(self, host: str, port: int) -> bool:
        """Connect to a host.  Returns True on success."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((host, port))
            self.sock.settimeout(0.1)
            self.role = "client"
            self.connected = True
            self.running = True
            self._thread = threading.Thread(target=self._io_loop, daemon=True)
            self._thread.start()
            return True
        except OSError:
            if self.sock:
                self.sock.close()
                self.sock = None
            return False

    def send(self, msg: dict):
        """Queue a message to send to the peer."""
        self._send_q.put(msg)

    def poll(self) -> list[dict]:
        """Return all messages received since last poll."""
        msgs = []
        while True:
            try:
                msgs.append(self._recv_q.get_nowait())
            except queue.Empty:
                break
        return msgs

    def stop(self):
        """Shut down networking."""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass
        self.connected = False
        self.sock = None
        self.server_sock = None

    # ── internal ──

    def _host_loop(self):
        """Host: wait for connection, then do I/O."""
        while self.running and not self.connected:
            try:
                self.sock, _ = self.server_sock.accept()
                self.sock.settimeout(0.1)
                self.connected = True
            except socket.timeout:
                continue
            except OSError:
                break
        if self.connected:
            self._io_loop()

    def _io_loop(self):
        """Send/receive JSON messages over the socket."""
        while self.running and self.connected:
            # Send queued messages
            while not self._send_q.empty():
                try:
                    msg = self._send_q.get_nowait()
                    data = json.dumps(msg, separators=(",", ":")).encode() + b"\n"
                    self.sock.sendall(data)
                except (OSError, queue.Empty):
                    self.connected = False
                    return
            # Receive
            try:
                chunk = self.sock.recv(8192)
                if not chunk:
                    self.connected = False
                    return
                self._recv_buf += chunk
                while b"\n" in self._recv_buf:
                    line, self._recv_buf = self._recv_buf.split(b"\n", 1)
                    try:
                        msg = json.loads(line.decode())
                        self._recv_q.put(msg)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
            except socket.timeout:
                pass
            except OSError:
                self.connected = False
                return
