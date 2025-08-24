# backend/app/services/notification_service.py
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from ..websockets.connection_manager import ConnectionManager
from ..models.enhanced_models import TaskStatus
from ..core.config import settings

class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    SYSTEM_ALERT = "system_alert"

class NotificationService:
    """Comprehensive notification service for real-time and email notifications"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.notification_history: List[Dict] = []
        self.user_preferences: Dict[str, Dict] = {}
        
        # Email configuration
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
    
    async def send_notification(self, 
                              notification_type: NotificationType,
                              title: str,
                              message: str,
                              user_id: str = None,
                              data: Dict[str, Any] = None,
                              channels: List[str] = None) -> str:
        """Send notification through multiple channels"""
        
        notification_id = f"notif_{int(datetime.utcnow().timestamp())}"
        
        notification = {
            "id": notification_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "user_id": user_id,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
            "read": False
        }
        
        # Store in history
        self.notification_history.append(notification)
        
        # Default channels if none specified
        if channels is None:
            channels = self._get_default_channels(user_id, notification_type)
        
        # Send through specified channels
        for channel in channels:
            if channel == "websocket":
                await self._send_websocket_notification(notification)
            elif channel == "email":
                await self._send_email_notification(notification)
            elif channel == "system":
                await self._send_system_notification(notification)
        
        return notification_id
    
    async def send_task_notification(self, task_id: str, status: TaskStatus, user_id: str, details: Dict = None):
        """Send task-specific notification"""
        if status == TaskStatus.COMPLETED:
            await self.send_notification(
                NotificationType.TASK_COMPLETE,
                "Task Completed",
                f"Your bioinformatics task {task_id} has completed successfully.",
                user_id,
                {"task_id": task_id, "details": details},
                ["websocket", "email"]
            )
        elif status == TaskStatus.FAILED:
            await self.send_notification(
                NotificationType.TASK_FAILED,
                "Task Failed",
                f"Your bioinformatics task {task_id} has failed. Please check the logs for details.",
                user_id,
                {"task_id": task_id, "details": details},
                ["websocket", "email"]
            )
        elif status == TaskStatus.RUNNING:
            await self.send_notification(
                NotificationType.INFO,
                "Task Started",
                f"Your bioinformatics task {task_id} has started processing.",
                user_id,
                {"task_id": task_id, "details": details},
                ["websocket"]
            )
    
    async def send_workflow_notification(self, workflow_id: str, status: str, user_id: str, step_info: Dict = None):
        """Send workflow-specific notification"""
        if status == "completed":
            await self.send_notification(
                NotificationType.SUCCESS,
                "Workflow Completed",
                f"Your workflow {workflow_id} has completed successfully.",
                user_id,
                {"workflow_id": workflow_id, "step_info": step_info},
                ["websocket", "email"]
            )
        elif status == "failed":
            await self.send_notification(
                NotificationType.ERROR,
                "Workflow Failed",
                f"Your workflow {workflow_id} has encountered an error.",
                user_id,
                {"workflow_id": workflow_id, "step_info": step_info},
                ["websocket", "email"]
            )
        elif status == "step_completed":
            await self.send_notification(
                NotificationType.INFO,
                "Workflow Step Completed",
                f"Step {step_info.get('step_number', 'N/A')} of workflow {workflow_id} completed.",
                user_id,
                {"workflow_id": workflow_id, "step_info": step_info},
                ["websocket"]
            )
    
    async def send_system_alert(self, alert_type: str, message: str, severity: str = "medium", target_users: List[str] = None):
        """Send system-wide alert"""
        notification_type = NotificationType.SYSTEM_ALERT
        if severity == "high":
            notification_type = NotificationType.ERROR
        elif severity == "low":
            notification_type = NotificationType.WARNING
        
        await self.send_notification(
            notification_type,
            f"System Alert: {alert_type}",
            message,
            data={"alert_type": alert_type, "severity": severity},
            channels=["websocket", "system"]
        )
        
        # Send to specific users or all users
        if target_users:
            for user_id in target_users:
                await self.connection_manager.send_to_user({
                    "type": "system_alert",
                    "alert_type": alert_type,
                    "message": message,
                    "severity": severity,
                    "timestamp": datetime.utcnow().isoformat()
                }, user_id)
        else:
            await self.connection_manager.broadcast_system_notification({
                "alert_type": alert_type,
                "message": message,
                "severity": severity
            })
    
    async def get_user_notifications(self, user_id: str, unread_only: bool = False, limit: int = 50) -> List[Dict]:
        """Get notifications for a specific user"""
        user_notifications = [
            notif for notif in self.notification_history 
            if notif.get('user_id') == user_id or notif.get('user_id') is None
        ]
        
        if unread_only:
            user_notifications = [notif for notif in user_notifications if not notif.get('read', False)]
        
        # Sort by timestamp (newest first) and limit
        user_notifications.sort(key=lambda x: x['timestamp'], reverse=True)
        return user_notifications[:limit]
    
    async def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        for notif in self.notification_history:
            if notif['id'] == notification_id and (notif.get('user_id') == user_id or notif.get('user_id') is None):
                notif['read'] = True
                return True
        return False
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """Update user notification preferences"""
        self.user_preferences[user_id] = preferences
    
    def _get_default_channels(self, user_id: str, notification_type: NotificationType) -> List[str]:
        """Get default notification channels based on user preferences and notification type"""
        user_prefs = self.user_preferences.get(user_id, {})
        
        # Default channels
        channels = ["websocket"]
        
        # Add email for important notifications
        if notification_type in [NotificationType.TASK_COMPLETE, NotificationType.TASK_FAILED, NotificationType.ERROR]:
            if user_prefs.get("email_enabled", True):
                channels.append("email")
        
        return channels
    
    async def _send_websocket_notification(self, notification: Dict):
        """Send notification via WebSocket"""
        if notification.get('user_id'):
            await self.connection_manager.send_to_user(notification, notification['user_id'])
        else:
            await self.connection_manager.broadcast_system_notification(notification)
    
    async def _send_email_notification(self, notification: Dict):
        """Send notification via email"""
        if not notification.get('user_id'):
            return  # Cannot send email without user_id
        
        # This would integrate with your user service to get email address
        # For now, assume we have a way to get user email
        user_email = await self._get_user_email(notification['user_id'])
        if not user_email:
            return
        
        try:
            # Create email message
            msg = MimeMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = user_email
            msg['Subject'] = f"[Bioinformatics Platform] {notification['title']}"
            
            # Email body
            body = f"""
            {notification['message']}
            
            Timestamp: {notification['timestamp']}
            
            ---
            This is an automated message from the Bioinformatics Analysis Platform.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    async def _send_system_notification(self, notification: Dict):
        """Send system-level notification (could integrate with external systems)"""
        # This could integrate with Slack, Microsoft Teams, etc.
        logger.info(f"System notification: {notification['title']} - {notification['message']}")
    
    async def _get_user_email(self, user_id: str) -> Optional[str]:
        """Get user email address from user service"""
        # This would integrate with your user management system
        # For now, return a placeholder
        return f"user_{user_id}@example.com"
    
    async def cleanup_old_notifications(self, days_to_keep: int = 30):
        """Clean up old notifications"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        self.notification_history = [
            notif for notif in self.notification_history
            if datetime.fromisoformat(notif['timestamp']) > cutoff_date
        ]

