# backend/app/api/notification_endpoints.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from ..services.notification_service import NotificationService, NotificationType
from ..models.enhanced_models import User

router = APIRouter()

@router.get("/notifications")
async def get_notifications(
    user_id: str = Query(...),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100)
):
    """Get user notifications"""
    notifications = await notification_service.get_user_notifications(user_id, unread_only, limit)
    return {
        "notifications": notifications,
        "total_count": len(notifications)
    }

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user_id: str):
    """Mark notification as read"""
    success = await notification_service.mark_notification_read(notification_id, user_id)
    if success:
        return {"message": "Notification marked as read"}
    else:
        raise HTTPException(status_code=404, detail="Notification not found")

@router.post("/notifications/preferences")
async def update_notification_preferences(user_id: str, preferences: Dict[str, Any]):
    """Update user notification preferences"""
    await notification_service.update_user_preferences(user_id, preferences)
    return {"message": "Preferences updated successfully"}

@router.post("/notifications/send")
async def send_custom_notification(
    notification_type: NotificationType,
    title: str,
    message: str,
    user_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
):
    """Send custom notification (admin only)"""
    notification_id = await notification_service.send_notification(
        notification_type, title, message, user_id, data
    )
    return {"notification_id": notification_id, "message": "Notification sent successfully"}
