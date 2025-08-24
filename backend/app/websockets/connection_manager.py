# backend/app/websockets/connection_manager.py
import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import uuid
import redis
import logging
from ..models.enhanced_models import TaskStatus

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self, redis_url: str):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self.task_subscriptions: Dict[str, Set[str]] = {}  # task_id -> connection_ids
        self.workflow_subscriptions: Dict[str, Set[str]] = {}  # workflow_id -> connection_ids
        self.redis_client = redis.Redis.from_url(redis_url)
        self.pubsub = self.redis_client.pubsub()
        
        # Start Redis subscriber task
        asyncio.create_task(self._redis_subscriber())
    
    async def connect(self, websocket: WebSocket, user_id: str = None) -> str:
        """Accept WebSocket connection and return connection ID"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} for user: {user_id}")
        
        # Send connection confirmation
        await self.send_personal_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
        
        return connection_id
    
    def disconnect(self, connection_id: str, user_id: str = None):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from all subscriptions
        for task_id in list(self.task_subscriptions.keys()):
            self.task_subscriptions[task_id].discard(connection_id)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
        
        for workflow_id in list(self.workflow_subscriptions.keys()):
            self.workflow_subscriptions[workflow_id].discard(connection_id)
            if not self.workflow_subscriptions[workflow_id]:
                del self.workflow_subscriptions[workflow_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                # Remove dead connection
                self.disconnect(connection_id)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """Send message to all connections of a user"""
        if user_id in self.user_connections:
            connection_ids = list(self.user_connections[user_id])
            for connection_id in connection_ids:
                await self.send_personal_message(message, connection_id)
    
    async def subscribe_to_task(self, connection_id: str, task_id: str):
        """Subscribe connection to task updates"""
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        self.task_subscriptions[task_id].add(connection_id)
        
        # Subscribe to Redis channel for this task
        channel = f"task_updates:{task_id}"
        await self.pubsub.subscribe(channel)
        
        logger.info(f"Connection {connection_id} subscribed to task {task_id}")
    
    async def subscribe_to_workflow(self, connection_id: str, workflow_id: str):
        """Subscribe connection to workflow updates"""
        if workflow_id not in self.workflow_subscriptions:
            self.workflow_subscriptions[workflow_id] = set()
        self.workflow_subscriptions[workflow_id].add(connection_id)
        
        # Subscribe to Redis channel for this workflow
        channel = f"workflow_updates:{workflow_id}"
        await self.pubsub.subscribe(channel)
        
        logger.info(f"Connection {connection_id} subscribed to workflow {workflow_id}")
    
    async def unsubscribe_from_task(self, connection_id: str, task_id: str):
        """Unsubscribe connection from task updates"""
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(connection_id)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
                # Unsubscribe from Redis channel
                channel = f"task_updates:{task_id}"
                await self.pubsub.unsubscribe(channel)
    
    async def broadcast_task_update(self, task_id: str, update: Dict[str, Any]):
        """Broadcast task update to subscribed connections"""
        message = {
            "type": "task_update",
            "task_id": task_id,
            "data": update,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send via Redis pub/sub for scalability
        channel = f"task_updates:{task_id}"
        await self.redis_client.publish(channel, json.dumps(message))
        
        # Also send directly to local connections
        if task_id in self.task_subscriptions:
            connection_ids = list(self.task_subscriptions[task_id])
            for connection_id in connection_ids:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast_workflow_update(self, workflow_id: str, update: Dict[str, Any]):
        """Broadcast workflow update to subscribed connections"""
        message = {
            "type": "workflow_update",
            "workflow_id": workflow_id,
            "data": update,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send via Redis pub/sub
        channel = f"workflow_updates:{workflow_id}"
        await self.redis_client.publish(channel, json.dumps(message))
        
        # Send to local connections
        if workflow_id in self.workflow_subscriptions:
            connection_ids = list(self.workflow_subscriptions[workflow_id])
            for connection_id in connection_ids:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast_system_notification(self, notification: Dict[str, Any], target_users: List[str] = None):
        """Broadcast system notification"""
        message = {
            "type": "system_notification",
            "data": notification,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if target_users:
            # Send to specific users
            for user_id in target_users:
                await self.send_to_user(message, user_id)
        else:
            # Broadcast to all connections
            for connection_id in list(self.active_connections.keys()):
                await self.send_personal_message(message, connection_id)
    
    async def _redis_subscriber(self):
        """Background task to handle Redis pub/sub messages"""
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        channel = message['channel'].decode('utf-8')
                        
                        # Route message based on channel pattern
                        if channel.startswith('task_updates:'):
                            task_id = channel.replace('task_updates:', '')
                            await self._handle_task_update(task_id, data)
                        elif channel.startswith('workflow_updates:'):
                            workflow_id = channel.replace('workflow_updates:', '')
                            await self._handle_workflow_update(workflow_id, data)
                        
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
        except Exception as e:
            logger.error(f"Redis subscriber error: {e}")
    
    async def _handle_task_update(self, task_id: str, data: Dict[str, Any]):
        """Handle task update from Redis"""
        if task_id in self.task_subscriptions:
            connection_ids = list(self.task_subscriptions[task_id])
            for connection_id in connection_ids:
                await self.send_personal_message(data, connection_id)
    
    async def _handle_workflow_update(self, workflow_id: str, data: Dict[str, Any]):
        """Handle workflow update from Redis"""
        if workflow_id in self.workflow_subscriptions:
            connection_ids = list(self.workflow_subscriptions[workflow_id])
            for connection_id in connection_ids:
                await self.send_personal_message(data, connection_id)

