# backend/app/websockets/connection_manager.py
import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Active connections: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Room subscriptions: {room_name: Set[connection_id]}
        self.room_subscriptions: Dict[str, Set[str]] = {}
        
        # User connections: {user_id: Set[connection_id]}
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Connection metadata: {connection_id: metadata}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Message history for replay: {room_name: List[messages]}
        self.message_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "messages_sent": 0,
            "rooms_created": 0,
            "connection_errors": 0
        }
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None, 
                      client_info: Optional[Dict[str, Any]] = None) -> str:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        
        # Store connection metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.now().isoformat(),
            "client_info": client_info or {},
            "subscribed_rooms": set()
        }
        
        # Associate with user if provided
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        self.stats["total_connections"] += 1
        
        logger.info(f"WebSocket connected: {connection_id} (User: {user_id})")
        
        # Send connection confirmation
        await self.send_personal_message(connection_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return connection_id
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            # Remove from all rooms
            rooms_to_leave = list(self.connection_metadata.get(connection_id, {}).get("subscribed_rooms", set()))
            for room in rooms_to_leave:
                self.leave_room(connection_id, room)
            
            # Remove from user connections
            user_id = self.connection_metadata.get(connection_id, {}).get("user_id")
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Clean up
            del self.active_connections[connection_id]
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]
            
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, connection_id: str, message: Dict[str, Any]):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
                self.stats["messages_sent"] += 1
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {str(e)}")
                self.stats["connection_errors"] += 1
                # Remove broken connection
                self.disconnect(connection_id)
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to all connections of a specific user"""
        if user_id in self.user_connections:
            tasks = []
            for connection_id in self.user_connections[user_id].copy():
                tasks.append(self.send_personal_message(connection_id, message))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    def join_room(self, connection_id: str, room_name: str):
        """Add connection to a room"""
        if connection_id not in self.active_connections:
            return False
        
        # Create room if it doesn't exist
        if room_name not in self.room_subscriptions:
            self.room_subscriptions[room_name] = set()
            self.message_history[room_name] = []
            self.stats["rooms_created"] += 1
        
        # Add connection to room
        self.room_subscriptions[room_name].add(connection_id)
        
        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["subscribed_rooms"].add(room_name)
        
        logger.info(f"Connection {connection_id} joined room {room_name}")
        return True
    
    def leave_room(self, connection_id: str, room_name: str):
        """Remove connection from a room"""
        if room_name in self.room_subscriptions:
            self.room_subscriptions[room_name].discard(connection_id)
            
            # Clean up empty rooms
            if not self.room_subscriptions[room_name]:
                del self.room_subscriptions[room_name]
                if room_name in self.message_history:
                    del self.message_history[room_name]
        
        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["subscribed_rooms"].discard(room_name)
        
        logger.info(f"Connection {connection_id} left room {room_name}")
    
    async def broadcast_to_room(self, room_name: str, message: Dict[str, Any], 
                               exclude_connections: Optional[Set[str]] = None,
                               store_in_history: bool = True):
        """Broadcast message to all connections in a room"""
        if room_name not in self.room_subscriptions:
            logger.warning(f"Attempted to broadcast to non-existent room: {room_name}")
            return
        
        # Add timestamp and room info
        message_with_metadata = {
            **message,
            "room": room_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in history
        if store_in_history:
            self.message_history[room_name].append(message_with_metadata)
            # Keep only last 100 messages per room
            if len(self.message_history[room_name]) > 100:
                self.message_history[room_name] = self.message_history[room_name][-100:]
        
        # Send to all subscribers
        exclude_connections = exclude_connections or set()
        connections_to_notify = self.room_subscriptions[room_name] - exclude_connections
        
        if connections_to_notify:
            tasks = []
            for connection_id in connections_to_notify.copy():
                tasks.append(self.send_personal_message(connection_id, message_with_metadata))
            
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Broadcasted to {len(connections_to_notify)} connections in room {room_name}")
    
    async def broadcast_to_all(self, message: Dict[str, Any], 
                              exclude_connections: Optional[Set[str]] = None):
        """Broadcast message to all active connections"""
        exclude_connections = exclude_connections or set()
        connections_to_notify = set(self.active_connections.keys()) - exclude_connections
        
        message_with_metadata = {
            **message,
            "broadcast": True,
            "timestamp": datetime.now().isoformat()
        }
        
        if connections_to_notify:
            tasks = []
            for connection_id in connections_to_notify:
                tasks.append(self.send_personal_message(connection_id, message_with_metadata))
            
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Broadcasted to {len(connections_to_notify)} connections")
    
    async def send_room_history(self, connection_id: str, room_name: str, limit: int = 50):
        """Send recent message history for a room to a connection"""
        if room_name in self.message_history:
            history = self.message_history[room_name][-limit:]
            await self.send_personal_message(connection_id, {
                "type": "room_history",
                "room": room_name,
                "messages": history,
                "count": len(history)
            })
    
    def get_room_info(self, room_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a room"""
        if room_name not in self.room_subscriptions:
            return None
        
        connection_ids = self.room_subscriptions[room_name]
        users = set()
        
        for conn_id in connection_ids:
            if conn_id in self.connection_metadata:
                user_id = self.connection_metadata[conn_id].get("user_id")
                if user_id:
                    users.add(user_id)
        
        return {
            "room_name": room_name,
            "connection_count": len(connection_ids),
            "unique_users": len(users),
            "message_history_count": len(self.message_history.get(room_name, []))
        }
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific connection"""
        if connection_id not in self.connection_metadata:
            return None
        
        metadata = self.connection_metadata[connection_id].copy()
        metadata["subscribed_rooms"] = list(metadata.get("subscribed_rooms", set()))
        metadata["is_active"] = connection_id in self.active_connections
        
        return metadata
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics"""
        active_rooms = len(self.room_subscriptions)
        total_room_connections = sum(len(conns) for conns in self.room_subscriptions.values())
        
        return {
            **self.stats,
            "active_connections": len(self.active_connections),
            "active_rooms": active_rooms,
            "unique_users": len(self.user_connections),
            "total_room_connections": total_room_connections,
            "average_connections_per_room": total_room_connections / active_rooms if active_rooms > 0 else 0
        }
    
    async def cleanup_stale_connections(self):
        """Remove connections that are no longer active"""
        stale_connections = []
        
        for connection_id, websocket in self.active_connections.items():
            try:
                # Try to ping the connection
                await websocket.ping()
            except Exception:
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            self.disconnect(connection_id)
        
        if stale_connections:
            logger.info(f"Cleaned up {len(stale_connections)} stale connections")
        
        return len(stale_connections)


# WebSocket endpoint handlers
async def websocket_endpoint(websocket: WebSocket, connection_manager: ConnectionManager):
    """Main WebSocket endpoint handler"""
    connection_id = None
    
    try:
        # Extract user info from query parameters or headers
        user_id = websocket.query_params.get("user_id")
        client_info = {
            "user_agent": websocket.headers.get("user-agent", ""),
            "origin": websocket.headers.get("origin", "")
        }
        
        connection_id = await connection_manager.connect(websocket, user_id, client_info)
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_client_message(connection_id, message, connection_manager)
            except json.JSONDecodeError:
                await connection_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling client message: {str(e)}")
                await connection_manager.send_personal_message(connection_id, {
                    "type": "error", 
                    "message": "Message processing failed"
                })
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        if connection_id:
            connection_manager.disconnect(connection_id)

async def handle_client_message(connection_id: str, message: Dict[str, Any], 
                               connection_manager: ConnectionManager):
    """Handle messages from WebSocket clients"""
    message_type = message.get("type")
    
    if message_type == "join_room":
        room_name = message.get("room")
        if room_name:
            success = connection_manager.join_room(connection_id, room_name)
            if success:
                # Send room history
                await connection_manager.send_room_history(connection_id, room_name)
                
                # Notify room about new member
                await connection_manager.broadcast_to_room(room_name, {
                    "type": "member_joined",
                    "connection_id": connection_id
                }, exclude_connections={connection_id})
    
    elif message_type == "leave_room":
        room_name = message.get("room")
        if room_name:
            connection_manager.leave_room(connection_id, room_name)
            
            # Notify room about member leaving
            await connection_manager.broadcast_to_room(room_name, {
                "type": "member_left",
                "connection_id": connection_id
            })
    
    elif message_type == "room_message":
        room_name = message.get("room")
        content = message.get("content")
        if room_name and content:
            await connection_manager.broadcast_to_room(room_name, {
                "type": "room_message",
                "from": connection_id,
                "content": content
            })
    
    elif message_type == "get_room_info":
        room_name = message.get("room")
        if room_name:
            room_info = connection_manager.get_room_info(room_name)
            await connection_manager.send_personal_message(connection_id, {
                "type": "room_info",
                "room_info": room_info
            })
    
    elif message_type == "ping":
        await connection_manager.send_personal_message(connection_id, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })
    
    else:
        await connection_manager.send_personal_message(connection_id, {
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        })


# Analysis progress tracking
class AnalysisProgressTracker:
    """Track and broadcast analysis progress"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.active_analyses: Dict[str, Dict[str, Any]] = {}
    
    async def start_analysis(self, analysis_id: str, analysis_type: str, user_id: Optional[str] = None):
        """Start tracking an analysis"""
        self.active_analyses[analysis_id] = {
            "type": analysis_type,
            "user_id": user_id,
            "started_at": datetime.now().isoformat(),
            "progress": 0,
            "status": "starting",
            "steps": []
        }
        
        await self.connection_manager.broadcast_to_room("analysis_updates", {
            "type": "analysis_started",
            "analysis_id": analysis_id,
            "analysis_type": analysis_type,
            "user_id": user_id
        })
        
        if user_id:
            await self.connection_manager.send_to_user(user_id, {
                "type": "personal_analysis_started",
                "analysis_id": analysis_id,
                "analysis_type": analysis_type
            })
    
    async def update_progress(self, analysis_id: str, progress: int, status: str, 
                            step_info: Optional[Dict[str, Any]] = None):
        """Update analysis progress"""
        if analysis_id in self.active_analyses:
            analysis = self.active_analyses[analysis_id]
            analysis["progress"] = progress
            analysis["status"] = status
            analysis["last_updated"] = datetime.now().isoformat()
            
            if step_info:
                analysis["steps"].append({
                    **step_info,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Broadcast update
            await self.connection_manager.broadcast_to_room("analysis_updates", {
                "type": "analysis_progress",
                "analysis_id": analysis_id,
                "progress": progress,
                "status": status,
                "step_info": step_info
            })
            
            # Send to specific user
            user_id = analysis.get("user_id")
            if user_id:
                await self.connection_manager.send_to_user(user_id, {
                    "type": "personal_analysis_progress",
                    "analysis_id": analysis_id,
                    "progress": progress,
                    "status": status
                })
    
    async def complete_analysis(self, analysis_id: str, results: Dict[str, Any]):
        """Mark analysis as completed"""
        if analysis_id in self.active_analyses:
            analysis = self.active_analyses[analysis_id]
            analysis["status"] = "completed"
            analysis["completed_at"] = datetime.now().isoformat()
            analysis["results"] = results
            
            await self.connection_manager.broadcast_to_room("analysis_updates", {
                "type": "analysis_completed", 
                "analysis_id": analysis_id,
                "results": results
            })
            
            user_id = analysis.get("user_id")
            if user_id:
                await self.connection_manager.send_to_user(user_id, {
                    "type": "personal_analysis_completed",
                    "analysis_id": analysis_id,
                    "results": results
                })
    
    async def fail_analysis(self, analysis_id: str, error: str):
        """Mark analysis as failed"""
        if analysis_id in self.active_analyses:
            analysis = self.active_analyses[analysis_id]
            analysis["status"] = "failed"
            analysis["failed_at"] = datetime.now().isoformat()
            analysis["error"] = error
            
            await self.connection_manager.broadcast_to_room("analysis_updates", {
                "type": "analysis_failed",
                "analysis_id": analysis_id,
                "error": error
            })
            
            user_id = analysis.get("user_id")
            if user_id:
                await self.connection_manager.send_to_user(user_id, {
                    "type": "personal_analysis_failed",
                    "analysis_id": analysis_id,
                    "error": error
                })
    
    def get_analysis_status(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an analysis"""
        return self.active_analyses.get(analysis_id)