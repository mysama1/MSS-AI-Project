"""
WebSocket Server for MSS-AI Real-time Communication
Provides live status streaming, bidirectional messaging, and subscription management
"""

import asyncio
import json
import time
from typing import Dict, Set, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Optional FastAPI integration
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.websockets import WebSocketState
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

# Optional websockets library fallback
try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


# ============================================================================
# Data Models
# ============================================================================

class MessageType(Enum):
    """WebSocket message types"""
    STATUS = "status"           # System status update
    METRICS = "metrics"         # Performance metrics
    EVENT = "event"             # System event
    COMMAND = "command"         # Client command
    RESPONSE = "response"       # Server response
    SUBSCRIBE = "subscribe"     # Subscription request
    UNSUBSCRIBE = "unsubscribe" # Unsubscription request
    ERROR = "error"             # Error message
    PING = "ping"               # Heartbeat ping
    PONG = "pong"               # Heartbeat pong


@dataclass
class WSMessage:
    """WebSocket message structure"""
    type: str
    timestamp: float
    data: Dict[str, Any]
    client_id: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "timestamp": self.timestamp,
            "data": self.data,
            "client_id": self.client_id
        })
    
    @classmethod
    def from_json(cls, raw: str) -> "WSMessage":
        parsed = json.loads(raw)
        return cls(
            type=parsed.get("type", "unknown"),
            timestamp=parsed.get("timestamp", time.time()),
            data=parsed.get("data", {}),
            client_id=parsed.get("client_id")
        )


@dataclass
class ClientInfo:
    """Connected client information"""
    client_id: str
    connected_at: float
    subscriptions: Set[str]
    last_ping: float
    message_count: int = 0


# ============================================================================
# WebSocket Manager
# ============================================================================

class WebSocketManager:
    """
    Manages WebSocket connections, subscriptions, and message broadcasting
    """
    
    def __init__(self, ping_interval: float = 30.0, ping_timeout: float = 10.0):
        self.clients: Dict[str, Any] = {}  # client_id -> websocket
        self.client_info: Dict[str, ClientInfo] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # channel -> set of client_ids
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.logger = logging.getLogger("websocket")
        self._shutdown = False
        self._message_handlers: Dict[str, Callable] = {}
        
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler"""
        self._message_handlers[message_type] = handler
    
    async def connect(self, websocket: Any, client_id: str) -> None:
        """Handle new client connection"""
        self.clients[client_id] = websocket
        self.client_info[client_id] = ClientInfo(
            client_id=client_id,
            connected_at=time.time(),
            subscriptions=set(),
            last_ping=time.time()
        )
        self.logger.info(f"Client {client_id} connected. Total: {len(self.clients)}")
        
        # Send welcome message (fire and forget, don't block on mock)
        try:
            await self.send_to_client(client_id, WSMessage(
                type=MessageType.STATUS.value,
                timestamp=time.time(),
                data={"status": "connected", "client_id": client_id}
            ))
        except Exception:
            pass
    
    async def disconnect(self, client_id: str) -> None:
        """Handle client disconnection"""
        if client_id in self.clients:
            del self.clients[client_id]
        
        if client_id in self.client_info:
            info = self.client_info[client_id]
            # Remove from all subscriptions
            for channel in info.subscriptions:
                if channel in self.subscriptions:
                    self.subscriptions[channel].discard(client_id)
            del self.client_info[client_id]
        
        self.logger.info(f"Client {client_id} disconnected. Total: {len(self.clients)}")
    
    async def handle_message(self, client_id: str, raw_message: str) -> None:
        """Process incoming message from client"""
        try:
            message = WSMessage.from_json(raw_message)
            
            if client_id in self.client_info:
                self.client_info[client_id].message_count += 1
            
            # Handle subscription management
            if message.type == MessageType.SUBSCRIBE.value:
                await self._handle_subscribe(client_id, message)
            elif message.type == MessageType.UNSUBSCRIBE.value:
                await self._handle_unsubscribe(client_id, message)
            elif message.type == MessageType.PING.value:
                await self._handle_ping(client_id)
            elif message.type in self._message_handlers:
                # Route to registered handler
                await self._message_handlers[message.type](client_id, message)
            else:
                await self.send_to_client(client_id, WSMessage(
                    type=MessageType.ERROR.value,
                    timestamp=time.time(),
                    data={"error": f"Unknown message type: {message.type}"}
                ))
                
        except json.JSONDecodeError:
            await self.send_to_client(client_id, WSMessage(
                type=MessageType.ERROR.value,
                timestamp=time.time(),
                data={"error": "Invalid JSON"}
            ))
        except Exception as e:
            self.logger.error(f"Error handling message from {client_id}: {e}")
    
    async def _handle_subscribe(self, client_id: str, message: WSMessage) -> None:
        """Handle subscription request"""
        channels = message.data.get("channels", [])
        for channel in channels:
            if channel not in self.subscriptions:
                self.subscriptions[channel] = set()
            self.subscriptions[channel].add(client_id)
            
            if client_id in self.client_info:
                self.client_info[client_id].subscriptions.add(channel)
        
        await self.send_to_client(client_id, WSMessage(
            type=MessageType.RESPONSE.value,
            timestamp=time.time(),
            data={"subscribed": channels}
        ))
    
    async def _handle_unsubscribe(self, client_id: str, message: WSMessage) -> None:
        """Handle unsubscription request"""
        channels = message.data.get("channels", [])
        for channel in channels:
            if channel in self.subscriptions:
                self.subscriptions[channel].discard(client_id)
            
            if client_id in self.client_info:
                self.client_info[client_id].subscriptions.discard(channel)
        
        await self.send_to_client(client_id, WSMessage(
            type=MessageType.RESPONSE.value,
            timestamp=time.time(),
            data={"unsubscribed": channels}
        ))
    
    async def _handle_ping(self, client_id: str) -> None:
        """Handle heartbeat ping"""
        if client_id in self.client_info:
            self.client_info[client_id].last_ping = time.time()
        
        await self.send_to_client(client_id, WSMessage(
            type=MessageType.PONG.value,
            timestamp=time.time(),
            data={}
        ))
    
    async def send_to_client(self, client_id: str, message: WSMessage) -> bool:
        """Send message to specific client"""
        if client_id not in self.clients:
            return False
        
        try:
            websocket = self.clients[client_id]
            json_msg = message.to_json()
            
            # Handle both AsyncMock (unittest) and real websockets
            if hasattr(websocket, 'send_text'):
                # FastAPI WebSocket
                if asyncio.iscoroutinefunction(websocket.send_text):
                    await websocket.send_text(json_msg)
                else:
                    websocket.send_text(json_msg)
            elif hasattr(websocket, 'send'):
                # websockets library or mock
                if asyncio.iscoroutinefunction(websocket.send):
                    await websocket.send(json_msg)
                else:
                    websocket.send(json_msg)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send to {client_id}: {e}")
            await self.disconnect(client_id)
            return False
    
    async def broadcast(self, message: WSMessage, channel: Optional[str] = None) -> int:
        """Broadcast message to all or channel subscribers"""
        if channel:
            targets = self.subscriptions.get(channel, set())
        else:
            targets = set(self.clients.keys())
        
        sent = 0
        for client_id in list(targets):
            if await self.send_to_client(client_id, message):
                sent += 1
        
        return sent
    
    async def broadcast_status(self, status_data: Dict[str, Any]) -> int:
        """Broadcast system status update"""
        return await self.broadcast(WSMessage(
            type=MessageType.STATUS.value,
            timestamp=time.time(),
            data=status_data
        ), channel="status")
    
    async def broadcast_metrics(self, metrics_data: Dict[str, Any]) -> int:
        """Broadcast metrics update"""
        return await self.broadcast(WSMessage(
            type=MessageType.METRICS.value,
            timestamp=time.time(),
            data=metrics_data
        ), channel="metrics")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_clients": len(self.clients),
            "total_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
            "channels": list(self.subscriptions.keys()),
            "clients": {
                cid: {
                    "connected_at": info.connected_at,
                    "subscriptions": list(info.subscriptions),
                    "message_count": info.message_count,
                    "last_ping": info.last_ping
                }
                for cid, info in self.client_info.items()
            }
        }
    
    async def shutdown(self) -> None:
        """Graceful shutdown"""
        self._shutdown = True
        for client_id in list(self.clients.keys()):
            await self.send_to_client(client_id, WSMessage(
                type=MessageType.STATUS.value,
                timestamp=time.time(),
                data={"status": "shutdown", "message": "Server shutting down"}
            ))
            await self.disconnect(client_id)


# ============================================================================
# FastAPI Integration
# ============================================================================

if HAS_FASTAPI:
    def create_websocket_routes(app: FastAPI, manager: WebSocketManager) -> None:
        """Add WebSocket routes to FastAPI app"""
        
        @app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await websocket.accept()
            await manager.connect(websocket, client_id)
            
            try:
                while not manager._shutdown:
                    # Receive message
                    raw = await websocket.receive_text()
                    await manager.handle_message(client_id, raw)
                    
            except WebSocketDisconnect:
                await manager.disconnect(client_id)
            except Exception as e:
                manager.logger.error(f"WebSocket error for {client_id}: {e}")
                await manager.disconnect(client_id)
        
        @app.get("/ws/stats")
        async def get_websocket_stats():
            return manager.get_stats()


# ============================================================================
# Standalone Server (websockets library)
# ============================================================================

if HAS_WEBSOCKETS:
    async def run_standalone_server(host: str = "0.0.0.0", port: int = 8765) -> None:
        """Run standalone WebSocket server"""
        manager = WebSocketManager()
        
        async def handler(websocket, path):
            client_id = f"client_{id(websocket)}"
            await manager.connect(websocket, client_id)
            
            try:
                async for message in websocket:
                    await manager.handle_message(client_id, message)
            except websockets.exceptions.ConnectionClosed:
                await manager.disconnect(client_id)
        
        server = await websockets.serve(handler, host, port)
        print(f"WebSocket server running on ws://{host}:{port}")
        await server.wait_closed()


# ============================================================================
# Example Usage
# ============================================================================

async def example_metrics_producer(manager: WebSocketManager):
    """Example: Periodically broadcast metrics"""
    import random
    
    while not manager._shutdown:
        await manager.broadcast_metrics({
            "cpu_percent": random.uniform(10, 80),
            "memory_percent": random.uniform(30, 70),
            "active_connections": len(manager.clients),
            "timestamp": time.time()
        })
        await asyncio.sleep(5)


if __name__ == "__main__":
    # Simple test
    print("WebSocket Server Module")
    print(f"FastAPI support: {HAS_FASTAPI}")
    print(f"websockets support: {HAS_WEBSOCKETS}")
    
    if HAS_WEBSOCKETS:
        print("\nRun with: python websocket_server.py")
        print("Then connect with: wscat -c ws://localhost:8765")
        # asyncio.run(run_standalone_server())
