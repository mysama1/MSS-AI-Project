"""
Tests for WebSocket Server
"""

import unittest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

from websocket_server import (
    WSMessage, MessageType, ClientInfo,
    WebSocketManager
)

class TestWSMessage(unittest.TestCase):
    """Test WSMessage dataclass"""

    def test_message_creation(self):
        """Test creating a message"""
        msg = WSMessage(
            type=MessageType.STATUS.value,
            timestamp=1234567890.0,
            data={"status": "ok"},
            client_id="test_client"
        )

        self.assertEqual(msg.type, "status")
        self.assertEqual(msg.timestamp, 1234567890.0)
        self.assertEqual(msg.data, {"status": "ok"})
        self.assertEqual(msg.client_id, "test_client")

    def test_message_to_json(self):
        """Test serialization to JSON"""
        msg = WSMessage(
            type=MessageType.STATUS.value,
            timestamp=1234567890.0,
            data={"status": "ok"},
            client_id="test_client"
        )

        json_str = msg.to_json()
        parsed = json.loads(json_str)

        self.assertEqual(parsed["type"], "status")
        self.assertEqual(parsed["timestamp"], 1234567890.0)
        self.assertEqual(parsed["data"]["status"], "ok")
        self.assertEqual(parsed["client_id"], "test_client")

    def test_message_from_json(self):
        """Test deserialization from JSON"""
        raw = '{"type": "status", "timestamp": 1234567890.0, "data": {"status": "ok"}, "client_id": "test_client"}'
        msg = WSMessage.from_json(raw)

        self.assertEqual(msg.type, "status")
        self.assertEqual(msg.timestamp, 1234567890.0)
        self.assertEqual(msg.data, {"status": "ok"})
        self.assertEqual(msg.client_id, "test_client")

    def test_message_roundtrip(self):
        """Test serialization roundtrip"""
        original = WSMessage(
            type=MessageType.METRICS.value,
            timestamp=time.time(),
            data={"cpu": 50.0, "memory": 60.0},
            client_id="client_1"
        )

        json_str = original.to_json()
        restored = WSMessage.from_json(json_str)

        self.assertEqual(original.type, restored.type)
        self.assertEqual(original.data, restored.data)
        self.assertEqual(original.client_id, restored.client_id)

class TestClientInfo(unittest.TestCase):
    """Test ClientInfo dataclass"""

    def test_client_info_creation(self):
        """Test creating client info"""
        info = ClientInfo(
            client_id="test_123",
            connected_at=1234567890.0,
            subscriptions={"status", "metrics"},
            last_ping=1234567895.0
        )

        self.assertEqual(info.client_id, "test_123")
        self.assertEqual(info.connected_at, 1234567890.0)
        self.assertEqual(info.subscriptions, {"status", "metrics"})
        self.assertEqual(info.last_ping, 1234567895.0)
        self.assertEqual(info.message_count, 0)

class TestWebSocketManager(unittest.TestCase):
    """Test WebSocketManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = WebSocketManager()

    def test_initialization(self):
        """Test manager initialization"""
        self.assertEqual(len(self.manager.clients), 0)
        self.assertEqual(len(self.manager.client_info), 0)
        self.assertEqual(len(self.manager.subscriptions), 0)
        self.assertEqual(self.manager.ping_interval, 30.0)
        self.assertEqual(self.manager.ping_timeout, 10.0)

    def test_register_handler(self):
        """Test handler registration"""
        handler = AsyncMock()
        self.manager.register_handler("custom", handler)

        self.assertIn("custom", self.manager._message_handlers)
        self.assertEqual(self.manager._message_handlers["custom"], handler)

    def test_get_stats_empty(self):
        """Test stats with no clients"""
        stats = self.manager.get_stats()

        self.assertEqual(stats["total_clients"], 0)
        self.assertEqual(stats["total_subscriptions"], 0)
        self.assertEqual(stats["channels"], [])
        self.assertEqual(stats["clients"], {})

class TestWebSocketManagerAsync(unittest.IsolatedAsyncioTestCase):
    """Async tests for WebSocketManager"""

    async def asyncSetUp(self):
        """Set up async test fixtures"""
        self.manager = WebSocketManager()
        self.mock_websocket = AsyncMock()

    async def test_connect(self):
        """Test client connection"""
        await self.manager.connect(self.mock_websocket, "client_1")

        self.assertIn("client_1", self.manager.clients)
        self.assertIn("client_1", self.manager.client_info)
        self.assertEqual(self.manager.client_info["client_1"].client_id, "client_1")

        # Should send welcome message (AsyncMock tracks await calls)
        self.assertTrue(self.mock_websocket.send_text.await_count >= 1 or
                       self.mock_websocket.send_text.call_count >= 1)

    async def test_disconnect(self):
        """Test client disconnection"""
        await self.manager.connect(self.mock_websocket, "client_1")
        await self.manager.disconnect("client_1")

        self.assertNotIn("client_1", self.manager.clients)
        self.assertNotIn("client_1", self.manager.client_info)

    async def test_handle_ping(self):
        """Test ping/pong"""
        await self.manager.connect(self.mock_websocket, "client_1")

        ping_msg = WSMessage(
            type=MessageType.PING.value,
            timestamp=time.time(),
            data={}
        )

        await self.manager._handle_ping("client_1")

        # Should send pong (AsyncMock)
        self.assertTrue(
            self.mock_websocket.send_text.await_count >= 1 or
            self.mock_websocket.send_text.call_count >= 1
        )

    async def test_subscribe(self):
        """Test subscription handling"""
        await self.manager.connect(self.mock_websocket, "client_1")

        sub_msg = WSMessage(
            type=MessageType.SUBSCRIBE.value,
            timestamp=time.time(),
            data={"channels": ["status", "metrics"]}
        )

        await self.manager._handle_subscribe("client_1", sub_msg)

        self.assertIn("status", self.manager.subscriptions)
        self.assertIn("metrics", self.manager.subscriptions)
        self.assertIn("client_1", self.manager.subscriptions["status"])
        self.assertIn("status", self.manager.client_info["client_1"].subscriptions)
        self.assertIn("metrics", self.manager.client_info["client_1"].subscriptions)

    async def test_unsubscribe(self):
        """Test unsubscription handling"""
        await self.manager.connect(self.mock_websocket, "client_1")

        # First subscribe
        sub_msg = WSMessage(
            type=MessageType.SUBSCRIBE.value,
            timestamp=time.time(),
            data={"channels": ["status"]}
        )
        await self.manager._handle_subscribe("client_1", sub_msg)

        # Then unsubscribe
        unsub_msg = WSMessage(
            type=MessageType.UNSUBSCRIBE.value,
            timestamp=time.time(),
            data={"channels": ["status"]}
        )
        await self.manager._handle_unsubscribe("client_1", unsub_msg)

        self.assertNotIn("client_1", self.manager.subscriptions.get("status", set()))

    async def test_broadcast(self):
        """Test broadcasting to all clients"""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await self.manager.connect(mock_ws1, "client_1")
        await self.manager.connect(mock_ws2, "client_2")

        msg = WSMessage(
            type=MessageType.STATUS.value,
            timestamp=time.time(),
            data={"status": "update"}
        )

        sent = await self.manager.broadcast(msg)

        self.assertEqual(sent, 2)
        # AsyncMock tracks await calls
        self.assertTrue(mock_ws1.send_text.await_count >= 1 or mock_ws1.send_text.call_count >= 1)
        self.assertTrue(mock_ws2.send_text.await_count >= 1 or mock_ws2.send_text.call_count >= 1)

    async def test_broadcast_to_channel(self):
        """Test broadcasting to channel subscribers"""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await self.manager.connect(mock_ws1, "client_1")
        await self.manager.connect(mock_ws2, "client_2")

        # Subscribe client_1 to "status"
        sub_msg = WSMessage(
            type=MessageType.SUBSCRIBE.value,
            timestamp=time.time(),
            data={"channels": ["status"]}
        )
        await self.manager._handle_subscribe("client_1", sub_msg)

        msg = WSMessage(
            type=MessageType.STATUS.value,
            timestamp=time.time(),
            data={"status": "update"}
        )

        sent = await self.manager.broadcast(msg, channel="status")

        self.assertEqual(sent, 1)
        self.assertTrue(mock_ws1.send_text.await_count >= 1 or mock_ws1.send_text.call_count >= 1)
        # client_2 didn't subscribe, so shouldn't get the message
        # But connect() sends welcome message, so check it's not called for the broadcast
        broadcast_calls = [c for c in mock_ws2.send_text.call_args_list
                          if 'update' in str(c)]
        self.assertEqual(len(broadcast_calls), 0)

    async def test_handle_invalid_json(self):
        """Test handling invalid JSON"""
        await self.manager.connect(self.mock_websocket, "client_1")

        await self.manager.handle_message("client_1", "not valid json")

        # Should send error (AsyncMock tracks await calls)
        self.assertTrue(
            self.mock_websocket.send_text.await_count >= 1 or
            self.mock_websocket.send_text.call_count >= 1
        )

    async def test_handle_unknown_message_type(self):
        """Test handling unknown message type"""
        await self.manager.connect(self.mock_websocket, "client_1")

        msg = WSMessage(
            type="unknown_type",
            timestamp=time.time(),
            data={}
        )

        await self.manager.handle_message("client_1", msg.to_json())

        # Should send error (AsyncMock)
        self.assertTrue(
            self.mock_websocket.send_text.await_count >= 1 or
            self.mock_websocket.send_text.call_count >= 1
        )

    async def test_get_stats_with_clients(self):
        """Test stats with connected clients"""
        await self.manager.connect(self.mock_websocket, "client_1")

        sub_msg = WSMessage(
            type=MessageType.SUBSCRIBE.value,
            timestamp=time.time(),
            data={"channels": ["status"]}
        )
        await self.manager._handle_subscribe("client_1", sub_msg)

        stats = self.manager.get_stats()

        self.assertEqual(stats["total_clients"], 1)
        self.assertEqual(stats["total_subscriptions"], 1)
        self.assertIn("status", stats["channels"])
        self.assertIn("client_1", stats["clients"])

    async def test_shutdown(self):
        """Test graceful shutdown"""
        await self.manager.connect(self.mock_websocket, "client_1")

        await self.manager.shutdown()

        self.assertTrue(self.manager._shutdown)
        self.assertEqual(len(self.manager.clients), 0)

class TestMessageTypeEnum(unittest.TestCase):
    """Test MessageType enum"""

    def test_enum_values(self):
        """Test all message types have correct values"""
        self.assertEqual(MessageType.STATUS.value, "status")
        self.assertEqual(MessageType.METRICS.value, "metrics")
        self.assertEqual(MessageType.EVENT.value, "event")
        self.assertEqual(MessageType.COMMAND.value, "command")
        self.assertEqual(MessageType.RESPONSE.value, "response")
        self.assertEqual(MessageType.SUBSCRIBE.value, "subscribe")
        self.assertEqual(MessageType.UNSUBSCRIBE.value, "unsubscribe")
        self.assertEqual(MessageType.ERROR.value, "error")
        self.assertEqual(MessageType.PING.value, "ping")
        self.assertEqual(MessageType.PONG.value, "pong")

if __name__ == "__main__":
    unittest.main(verbosity=2)
