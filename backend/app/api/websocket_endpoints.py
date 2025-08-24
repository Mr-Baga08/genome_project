# backend/app/api/websocket_endpoints.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Optional
import json
import logging
from ..websockets.connection_manager import ConnectionManager
from ..services.notification_service import NotificationService
from ..core.config import settings

logger = logging.getLogger(__name__)

# Initialize connection manager
connection_manager = ConnectionManager(settings.REDIS_URL)
notification_service = NotificationService(connection_manager)

router = APIRouter()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """Main WebSocket endpoint for real-time communication"""
    connection_id = None
    
    try:
        # Establish connection
        connection_id = await connection_manager.connect(websocket, user_id)
        
        # Send initial user notifications
        notifications = await notification_service.get_user_notifications(user_id, unread_only=True, limit=10)
        if notifications:
            await connection_manager.send_personal_message({
                "type": "initial_notifications",
                "notifications": notifications
            }, connection_id)
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            await handle_websocket_message(message, connection_id, user_id)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        if connection_id:
            connection_manager.disconnect(connection_id, user_id)

async def handle_websocket_message(message: dict, connection_id: str, user_id: str):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "subscribe_task":
        task_id = message.get("task_id")
        if task_id:
            await connection_manager.subscribe_to_task(connection_id, task_id)
            await connection_manager.send_personal_message({
                "type": "subscription_confirmed",
                "resource_type": "task",
                "resource_id": task_id
            }, connection_id)
    
    elif message_type == "subscribe_workflow":
        workflow_id = message.get("workflow_id")
        if workflow_id:
            await connection_manager.subscribe_to_workflow(connection_id, workflow_id)
            await connection_manager.send_personal_message({
                "type": "subscription_confirmed",
                "resource_type": "workflow",
                "resource_id": workflow_id
            }, connection_id)
    
    elif message_type == "unsubscribe_task":
        task_id = message.get("task_id")
        if task_id:
            await connection_manager.unsubscribe_from_task(connection_id, task_id)
    
    elif message_type == "mark_notification_read":
        notification_id = message.get("notification_id")
        if notification_id:
            success = await notification_service.mark_notification_read(notification_id, user_id)
            await connection_manager.send_personal_message({
                "type": "notification_marked_read",
                "notification_id": notification_id,
                "success": success
            }, connection_id)
    
    elif message_type == "get_notifications":
        unread_only = message.get("unread_only", False)
        notifications = await notification_service.get_user_notifications(user_id, unread_only)
        await connection_manager.send_personal_message({
            "type": "notifications_list",
            "notifications": notifications
        }, connection_id)
    
    elif message_type == "ping":
        await connection_manager.send_personal_message({
            "type": "pong",
            "timestamp": message.get("timestamp")
        }, connection_id)
