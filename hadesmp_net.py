#!/usr/bin/env python3
"""
HadesMP Networking — TCP/UDP transport between two bridge instances.

Connection model:
  - Host listens on TCP port 26000 + UDP port 26001
  - Client connects to host_ip:port
  - Simple handshake: version + player name

Wire format:
  TCP: [4B length][1B type][JSON payload]
  UDP: [2B sequence][1B type][JSON payload]

Message types:
  0x01 POSITION    — hero pos/angle/anim (20Hz, UDP)
  0x03 GAME_EVENT  — damage, kill, room clear (TCP)
  0x04 ROOM_TRANS  — room name + seed (TCP)
  0x05 BOON_SEL    — choices + pick (TCP)
  0x07 PING        — latency measurement (TCP)
  0x08 HANDSHAKE   — version, name (TCP)
  0x09 FULL_STATE  — room boundary sync (TCP)
"""

import json
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable


# Message type constants
class MsgType(IntEnum):
    POSITION = 0x01
    GAME_EVENT = 0x03
    ROOM_TRANSITION = 0x04
    BOON_SELECTION = 0x05
    PING = 0x07
    HANDSHAKE = 0x08
    FULL_STATE = 0x09
    PONG = 0x0A
    DISCONNECT = 0x0B


VERSION = "0.02"
DEFAULT_TCP_PORT = 26000
DEFAULT_UDP_PORT = 26001


@dataclass
class NetMessage:
    """A network message."""
    msg_type: MsgType
    payload: dict
    timestamp: float = field(default_factory=time.time)


@dataclass
class PeerInfo:
    """Information about the connected peer."""
    name: str = ""
    version: str = ""
    address: tuple = ("", 0)
    connected: bool = False
    last_ping: float = 0
    last_rtt: float | None = None


class HadesMPNet:
    """Bidirectional TCP+UDP networking for HadesMP."""

    def __init__(self, is_host: bool, player_name: str = "Player"):
        self.is_host = is_host
        self.player_name = player_name
        self.peer = PeerInfo()
        self._stop_event = threading.Event()
        self._callbacks: dict[MsgType, list[Callable]] = {}

        # TCP state
        self._tcp_socket: socket.socket | None = None
        self._tcp_client: socket.socket | None = None
        self._tcp_lock = threading.Lock()

        # UDP state
        self._udp_socket: socket.socket | None = None
        self._udp_seq_out = 0
        self._udp_seq_in = 0
        self._udp_peer_addr: tuple | None = None
        self._udp_lock = threading.Lock()

        # Threads
        self._threads: list[threading.Thread] = []

        # Stats
        self.tcp_sent = 0
        self.tcp_recv = 0
        self.udp_sent = 0
        self.udp_recv = 0
        self.udp_dropped = 0

    # ---- Callback registration ----

    def on(self, msg_type: MsgType, callback: Callable[[NetMessage], None]):
        """Register a callback for a message type."""
        self._callbacks.setdefault(msg_type, []).append(callback)

    def _dispatch(self, msg: NetMessage):
        """Dispatch a received message to registered callbacks."""
        for cb in self._callbacks.get(msg.msg_type, []):
            try:
                cb(msg)
            except Exception as e:
                print(f"[net] callback error for {msg.msg_type.name}: {e}")

    # ---- TCP ----

    def _tcp_send(self, sock: socket.socket, msg_type: MsgType, payload: dict):
        """Send a TCP message: [4B length][1B type][JSON]."""
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        header = struct.pack(">IB", len(body) + 1, msg_type.value)
        with self._tcp_lock:
            try:
                sock.sendall(header + body)
                self.tcp_sent += 1
            except (OSError, BrokenPipeError):
                self._handle_disconnect()

    def _tcp_recv_loop(self, sock: socket.socket):
        """Receive TCP messages in a loop."""
        buf = b""
        while not self._stop_event.is_set():
            try:
                sock.settimeout(1.0)
                data = sock.recv(4096)
                if not data:
                    self._handle_disconnect()
                    return
                buf += data
            except socket.timeout:
                continue
            except OSError:
                self._handle_disconnect()
                return

            # Parse messages from buffer
            while len(buf) >= 5:
                length = struct.unpack(">I", buf[:4])[0]
                if len(buf) < 4 + length:
                    break  # Need more data
                msg_type_val = buf[4]
                json_data = buf[5:4 + length]
                buf = buf[4 + length:]

                try:
                    msg_type = MsgType(msg_type_val)
                    payload = json.loads(json_data.decode("utf-8")) if json_data else {}
                    self.tcp_recv += 1
                    msg = NetMessage(msg_type=msg_type, payload=payload)
                    self._handle_tcp_message(msg, sock)
                except (ValueError, json.JSONDecodeError) as e:
                    print(f"[net] TCP parse error: {e}")

    def _handle_tcp_message(self, msg: NetMessage, sock: socket.socket):
        """Handle built-in TCP messages and dispatch to callbacks."""
        if msg.msg_type == MsgType.HANDSHAKE:
            self.peer.name = msg.payload.get("name", "Unknown")
            self.peer.version = msg.payload.get("version", "?")
            self.peer.connected = True
            print(f"[net] Peer connected: {self.peer.name} (v{self.peer.version})")
            # Send handshake back if we're host and received one
            if self.is_host:
                self._tcp_send(sock, MsgType.HANDSHAKE, {
                    "name": self.player_name,
                    "version": VERSION,
                })

        elif msg.msg_type == MsgType.PING:
            # Respond with PONG immediately
            self._tcp_send(sock, MsgType.PONG, {"ts": msg.payload.get("ts", 0)})

        elif msg.msg_type == MsgType.PONG:
            ts = msg.payload.get("ts", 0)
            if ts:
                self.peer.last_rtt = (time.time() - ts) * 1000  # ms

        elif msg.msg_type == MsgType.DISCONNECT:
            self._handle_disconnect()
            return

        self._dispatch(msg)

    # ---- UDP ----

    def _udp_send(self, msg_type: MsgType, payload: dict):
        """Send a UDP message: [2B seq][1B type][JSON]."""
        if not self._udp_peer_addr or not self._udp_socket:
            return

        with self._udp_lock:
            self._udp_seq_out = (self._udp_seq_out + 1) & 0xFFFF

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        header = struct.pack(">HB", self._udp_seq_out, msg_type.value)

        try:
            self._udp_socket.sendto(header + body, self._udp_peer_addr)
            self.udp_sent += 1
        except OSError:
            pass

    def _udp_recv_loop(self):
        """Receive UDP messages."""
        while not self._stop_event.is_set():
            try:
                self._udp_socket.settimeout(1.0)
                data, addr = self._udp_socket.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                return

            if len(data) < 3:
                continue

            seq = struct.unpack(">H", data[:2])[0]
            msg_type_val = data[2]
            json_data = data[3:]

            # Sequence check: drop out-of-order packets
            if self._is_seq_old(seq):
                self.udp_dropped += 1
                continue
            self._udp_seq_in = seq

            # Track peer UDP address (learn from first packet — works for NAT too)
            if not self._udp_peer_addr or self._udp_peer_addr != addr:
                self._udp_peer_addr = addr

            try:
                msg_type = MsgType(msg_type_val)
                payload = json.loads(json_data.decode("utf-8")) if json_data else {}
                self.udp_recv += 1
                msg = NetMessage(msg_type=msg_type, payload=payload)
                self._dispatch(msg)
            except (ValueError, json.JSONDecodeError):
                pass

    def _is_seq_old(self, new_seq: int) -> bool:
        """Check if a sequence number is older than the last received (wrapping-aware)."""
        diff = (new_seq - self._udp_seq_in) & 0xFFFF
        # If diff > 32768, the new seq is "behind" the current one
        return diff > 32768

    # ---- Connection management ----

    def start_host(self, tcp_port: int = DEFAULT_TCP_PORT, udp_port: int = DEFAULT_UDP_PORT):
        """Start as host: listen for TCP connection, bind UDP socket."""
        # TCP server
        self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._tcp_socket.settimeout(1.0)
        self._tcp_socket.bind(("0.0.0.0", tcp_port))
        self._tcp_socket.listen(1)
        print(f"[net] Host listening on TCP:{tcp_port}")

        # UDP socket
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_socket.bind(("0.0.0.0", udp_port))
        print(f"[net] Host listening on UDP:{udp_port}")

        # Accept thread
        t = threading.Thread(target=self._host_accept_loop, daemon=True, name="tcp-accept")
        t.start()
        self._threads.append(t)

        # UDP receive thread
        t2 = threading.Thread(target=self._udp_recv_loop, daemon=True, name="udp-recv")
        t2.start()
        self._threads.append(t2)

        # Ping thread
        t3 = threading.Thread(target=self._ping_loop, daemon=True, name="ping")
        t3.start()
        self._threads.append(t3)

    def _host_accept_loop(self):
        """Accept a single TCP client connection."""
        while not self._stop_event.is_set():
            try:
                client, addr = self._tcp_socket.accept()
                print(f"[net] TCP connection from {addr}")
                self._tcp_client = client
                self.peer.address = addr
                # UDP peer address is learned from first incoming UDP packet

                # Start TCP receive loop for this client
                t = threading.Thread(target=self._tcp_recv_loop, args=(client,),
                                     daemon=True, name="tcp-recv")
                t.start()
                self._threads.append(t)
                return  # Only accept one client
            except socket.timeout:
                continue
            except OSError:
                return

    def start_client(self, host: str, tcp_port: int = DEFAULT_TCP_PORT,
                     udp_port: int = DEFAULT_UDP_PORT):
        """Start as client: connect to host via TCP, set up UDP."""
        # TCP connect
        self._tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_client.settimeout(10.0)
        print(f"[net] Connecting to {host}:{tcp_port}...")
        self._tcp_client.connect((host, tcp_port))
        self._tcp_client.settimeout(None)
        print(f"[net] TCP connected to {host}:{tcp_port}")

        self.peer.address = (host, tcp_port)

        # UDP socket
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_socket.bind(("0.0.0.0", 0))  # Ephemeral port
        self._udp_peer_addr = (host, udp_port)

        # Send handshake
        self._tcp_send(self._tcp_client, MsgType.HANDSHAKE, {
            "name": self.player_name,
            "version": VERSION,
        })

        # Send a UDP packet to establish NAT mapping
        self._udp_send(MsgType.PING, {"ts": time.time()})

        # TCP receive thread
        t = threading.Thread(target=self._tcp_recv_loop, args=(self._tcp_client,),
                             daemon=True, name="tcp-recv")
        t.start()
        self._threads.append(t)

        # UDP receive thread
        t2 = threading.Thread(target=self._udp_recv_loop, daemon=True, name="udp-recv")
        t2.start()
        self._threads.append(t2)

        # Ping thread
        t3 = threading.Thread(target=self._ping_loop, daemon=True, name="ping")
        t3.start()
        self._threads.append(t3)

    # ---- High-level send API ----

    def send_position(self, x: float, y: float, angle: float, anim: str = ""):
        """Send hero position over UDP (high frequency)."""
        self._udp_send(MsgType.POSITION, {
            "x": round(x, 1),
            "y": round(y, 1),
            "a": round(angle, 2),
            "n": anim,
        })

    def send_game_event(self, event_type: str, data: dict | None = None):
        """Send a game event over TCP (reliable)."""
        sock = self._tcp_client
        if sock:
            self._tcp_send(sock, MsgType.GAME_EVENT, {
                "type": event_type,
                "data": data or {},
            })

    def send_room_transition(self, room_name: str, seed: int = 0):
        """Send room transition over TCP."""
        sock = self._tcp_client
        if sock:
            self._tcp_send(sock, MsgType.ROOM_TRANSITION, {
                "room": room_name,
                "seed": seed,
            })

    def send_boon_selection(self, choices: list[str], pick: str):
        """Send boon selection over TCP."""
        sock = self._tcp_client
        if sock:
            self._tcp_send(sock, MsgType.BOON_SELECTION, {
                "choices": choices,
                "pick": pick,
            })

    def send_full_state(self, state: dict):
        """Send full state sync over TCP."""
        sock = self._tcp_client
        if sock:
            self._tcp_send(sock, MsgType.FULL_STATE, state)

    def ping(self):
        """Send a ping for RTT measurement."""
        sock = self._tcp_client
        if sock:
            self.peer.last_ping = time.time()
            self._tcp_send(sock, MsgType.PING, {"ts": time.time()})

    # ---- Lifecycle ----

    def _ping_loop(self):
        """Periodically send pings."""
        while not self._stop_event.is_set():
            if self.peer.connected:
                self.ping()
            self._stop_event.wait(5.0)

    def _handle_disconnect(self):
        """Handle peer disconnection."""
        if self.peer.connected:
            print(f"[net] Peer disconnected: {self.peer.name}")
            self.peer.connected = False

    def stop(self):
        """Stop all networking."""
        self._stop_event.set()

        # Send disconnect message if connected
        sock = self._tcp_client
        if sock and self.peer.connected:
            try:
                self._tcp_send(sock, MsgType.DISCONNECT, {})
            except Exception:
                pass

        # Close sockets
        for s in [self._tcp_client, self._tcp_socket, self._udp_socket]:
            if s:
                try:
                    s.close()
                except OSError:
                    pass

        self._tcp_client = None
        self._tcp_socket = None
        self._udp_socket = None

    def status(self) -> dict:
        """Return networking status."""
        return {
            "mode": "host" if self.is_host else "client",
            "peer_name": self.peer.name,
            "peer_version": self.peer.version,
            "peer_connected": self.peer.connected,
            "peer_rtt_ms": f"{self.peer.last_rtt:.1f}" if self.peer.last_rtt else "n/a",
            "tcp_sent": self.tcp_sent,
            "tcp_recv": self.tcp_recv,
            "udp_sent": self.udp_sent,
            "udp_recv": self.udp_recv,
            "udp_dropped": self.udp_dropped,
        }
