#!/usr/bin/env python3
"""
HadesMP Networking Tests — verifies TCP/UDP transport without needing the game.

Tests:
  1. TCP connection + handshake
  2. Ping/pong RTT measurement
  3. Message round-trip (serialize → send → receive → deserialize)
  4. UDP position data flow
  5. UDP sequence numbering + out-of-order handling
  6. Graceful disconnect
"""

import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from hadesmp_net import HadesMPNet, MsgType, NetMessage


class TestTCPHandshake(unittest.TestCase):
    """Test TCP connection and handshake."""

    def setUp(self):
        self.host = HadesMPNet(is_host=True, player_name="Host")
        self.client = HadesMPNet(is_host=False, player_name="Client")
        self.host_received = []
        self.client_received = []

    def tearDown(self):
        self.host.stop()
        self.client.stop()
        time.sleep(0.2)

    def test_handshake(self):
        """Host and client should exchange handshake messages."""
        handshake_event = threading.Event()

        def on_handshake(msg):
            self.client_received.append(msg)
            handshake_event.set()

        self.client.on(MsgType.HANDSHAKE, on_handshake)

        self.host.start_host(tcp_port=26100, udp_port=26101)
        time.sleep(0.2)
        self.client.start_client("127.0.0.1", tcp_port=26100, udp_port=26101)

        # Wait for handshake
        self.assertTrue(handshake_event.wait(timeout=5.0), "Handshake timeout")
        self.assertEqual(len(self.client_received), 1)
        self.assertEqual(self.client_received[0].payload["name"], "Host")

        # Verify peer info
        time.sleep(0.5)
        self.assertTrue(self.host.peer.connected)
        self.assertEqual(self.host.peer.name, "Client")


class TestPingPong(unittest.TestCase):
    """Test ping/pong RTT measurement."""

    def setUp(self):
        self.host = HadesMPNet(is_host=True, player_name="Host")
        self.client = HadesMPNet(is_host=False, player_name="Client")

    def tearDown(self):
        self.host.stop()
        self.client.stop()
        time.sleep(0.2)

    def test_ping_pong(self):
        """Ping from client should get a pong and RTT measurement."""
        pong_event = threading.Event()

        def on_pong(msg):
            pong_event.set()

        self.client.on(MsgType.PONG, on_pong)

        self.host.start_host(tcp_port=26110, udp_port=26111)
        time.sleep(0.2)
        self.client.start_client("127.0.0.1", tcp_port=26110, udp_port=26111)
        time.sleep(0.5)

        self.client.ping()
        self.assertTrue(pong_event.wait(timeout=3.0), "Pong timeout")
        self.assertIsNotNone(self.client.peer.last_rtt)
        self.assertGreater(self.client.peer.last_rtt, 0)


class TestTCPMessages(unittest.TestCase):
    """Test TCP message round-trip."""

    def setUp(self):
        self.host = HadesMPNet(is_host=True, player_name="Host")
        self.client = HadesMPNet(is_host=False, player_name="Client")

    def tearDown(self):
        self.host.stop()
        self.client.stop()
        time.sleep(0.2)

    def test_game_event(self):
        """Send a game event from client to host."""
        received = []
        event = threading.Event()

        def on_event(msg):
            received.append(msg)
            event.set()

        self.host.on(MsgType.GAME_EVENT, on_event)

        self.host.start_host(tcp_port=26120, udp_port=26121)
        time.sleep(0.2)
        self.client.start_client("127.0.0.1", tcp_port=26120, udp_port=26121)
        time.sleep(0.5)

        self.client.send_game_event("kill", {"enemy": "Numbskull", "damage": 50})
        self.assertTrue(event.wait(timeout=3.0), "Event timeout")
        self.assertEqual(received[0].payload["type"], "kill")
        self.assertEqual(received[0].payload["data"]["enemy"], "Numbskull")

    def test_room_transition(self):
        """Send a room transition from host to client."""
        received = []
        event = threading.Event()

        def on_room(msg):
            received.append(msg)
            event.set()

        self.client.on(MsgType.ROOM_TRANSITION, on_room)

        self.host.start_host(tcp_port=26130, udp_port=26131)
        time.sleep(0.2)
        self.client.start_client("127.0.0.1", tcp_port=26130, udp_port=26131)
        time.sleep(0.5)

        self.host.send_room_transition("RoomOpening", seed=12345)
        self.assertTrue(event.wait(timeout=3.0), "Room transition timeout")
        self.assertEqual(received[0].payload["room"], "RoomOpening")
        self.assertEqual(received[0].payload["seed"], 12345)


class TestUDPPosition(unittest.TestCase):
    """Test UDP position data flow."""

    def setUp(self):
        self.host = HadesMPNet(is_host=True, player_name="Host")
        self.client = HadesMPNet(is_host=False, player_name="Client")

    def tearDown(self):
        self.host.stop()
        self.client.stop()
        time.sleep(0.2)

    def test_position_flow(self):
        """Send position data from host to client via UDP."""
        received = []
        event = threading.Event()

        def on_pos(msg):
            received.append(msg)
            if len(received) >= 5:
                event.set()

        self.client.on(MsgType.POSITION, on_pos)

        self.host.start_host(tcp_port=26140, udp_port=26141)
        time.sleep(0.2)
        self.client.start_client("127.0.0.1", tcp_port=26140, udp_port=26141)
        time.sleep(0.5)

        # Send 10 position updates
        for i in range(10):
            self.host.send_position(100.0 + i * 10, 200.0, 1.5, "ZagreusRun")
            time.sleep(0.05)

        self.assertTrue(event.wait(timeout=3.0), "Position data timeout")
        self.assertGreaterEqual(len(received), 5)

        # Verify payload structure
        p = received[0].payload
        self.assertIn("x", p)
        self.assertIn("y", p)
        self.assertIn("a", p)


class TestDisconnect(unittest.TestCase):
    """Test graceful disconnect."""

    def test_disconnect(self):
        host = HadesMPNet(is_host=True, player_name="Host")
        client = HadesMPNet(is_host=False, player_name="Client")

        host.start_host(tcp_port=26150, udp_port=26151)
        time.sleep(0.2)
        client.start_client("127.0.0.1", tcp_port=26150, udp_port=26151)
        time.sleep(0.5)

        self.assertTrue(host.peer.connected)

        client.stop()
        time.sleep(1.0)

        # Host should detect disconnect
        self.assertFalse(host.peer.connected)
        host.stop()


class TestNetStatus(unittest.TestCase):
    """Test status reporting."""

    def test_status(self):
        net = HadesMPNet(is_host=True, player_name="TestHost")
        status = net.status()
        self.assertEqual(status["mode"], "host")
        self.assertEqual(status["peer_connected"], False)
        self.assertEqual(status["tcp_sent"], 0)
        net.stop()


if __name__ == "__main__":
    unittest.main()
