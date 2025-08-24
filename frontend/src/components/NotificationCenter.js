// # frontend/src/components/NotificationCenter.js - React Notification Component
import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Badge, 
  Button, 
  Modal, 
  ListGroup, 
  Toast, 
  ToastContainer,
  Dropdown,
  Form
} from 'react-bootstrap';
import { 
  BsBell, 
  BsBellFill, 
  BsCheck, 
  BsTrash, 
  BsGear,
  BsCheckAll
} from 'react-icons/bs';
import { useWebSocket } from '../hooks/useWebSocket';
import './NotificationCenter.css';

const NotificationCenter = ({ userId }) => {
  const { 
    notifications, 
    isConnected, 
    markNotificationRead 
  } = useWebSocket(userId);
  
  const [showModal, setShowModal] = useState(false);
  const [showToasts, setShowToasts] = useState(true);
  const [filter, setFilter] = useState('all'); // all, unread, task, system
  const [toastQueue, setToastQueue] = useState([]);
  
  // Filter notifications based on current filter
  const filteredNotifications = notifications.filter(notification => {
    if (filter === 'unread') return !notification.read;
    if (filter === 'task') return notification.type.includes('task');
    if (filter === 'system') return notification.type === 'system_notification';
    return true;
  });
  
  const unreadCount = notifications.filter(n => !n.read).length;
  
  // Show toast notifications for new notifications
  useEffect(() => {
    if (notifications.length > 0 && showToasts) {
      const latestNotification = notifications[0];
      if (!latestNotification.read && latestNotification.type !== 'connection_established') {
        setToastQueue(prev => [...prev, latestNotification]);
      }
    }
  }, [notifications, showToasts]);
  
  const handleMarkAsRead = (notificationId) => {
    markNotificationRead(notificationId);
  };
  
  const handleMarkAllAsRead = () => {
    notifications
      .filter(n => !n.read)
      .forEach(n => markNotificationRead(n.id));
  };
  
  const removeToast = (toastId) => {
    setToastQueue(prev => prev.filter(toast => toast.id !== toastId));
  };
  
  const getNotificationIcon = (type) => {
    const iconMap = {
      'success': '✅',
      'task_complete': '🎉',
      'error': '❌',
      'task_failed': '⚠️',
      'warning': '⚠️',
      'info': 'ℹ️',
      'system_notification': '🔔',
      'system_alert': '🚨'
    };
    return iconMap[type] || '📬';
  };
  
  const getNotificationVariant = (type) => {
    const variantMap = {
      'success': 'success',
      'task_complete': 'success',
      'error': 'danger',
      'task_failed': 'danger',
      'warning': 'warning',
      'info': 'info',
      'system_notification': 'primary',
      'system_alert': 'danger'
    };
    return variantMap[type] || 'light';
  };
  
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };
  
  return (
    <>
      {/* Notification Bell Icon */}
      <div className="notification-bell" onClick={() => setShowModal(true)}>
        {isConnected ? (
          unreadCount > 0 ? <BsBellFill className="text-warning" /> : <BsBell />
        ) : (
          <BsBell className="text-muted" />
        )}
        {unreadCount > 0 && (
          <Badge 
            bg="danger" 
            className="notification-count"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </Badge>
        )}
      </div>
      
      {/* Connection Status */}
      <small className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
        {isConnected ? '🟢 Live' : '🔴 Offline'}
      </small>
      
      {/* Notification Modal */}
      <Modal 
        show={showModal} 
        onHide={() => setShowModal(false)}
        size="lg"
        centered
      >
        <Modal.Header closeButton>
          <Modal.Title>
            Notifications
            {unreadCount > 0 && (
              <Badge bg="danger" className="ms-2">
                {unreadCount} unread
              </Badge>
            )}
          </Modal.Title>
        </Modal.Header>
        
        <Modal.Body>
          {/* Controls */}
          <div className="d-flex justify-content-between align-items-center mb-3">
            <div className="d-flex gap-2">
              <Form.Select 
                size="sm" 
                style={{ width: 'auto' }}
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                <option value="all">All Notifications</option>
                <option value="unread">Unread Only</option>
                <option value="task">Task Updates</option>
                <option value="system">System Alerts</option>
              </Form.Select>
            </div>
            
            <div className="d-flex gap-2">
              {unreadCount > 0 && (
                <Button 
                  variant="outline-primary" 
                  size="sm"
                  onClick={handleMarkAllAsRead}
                >
                  <BsCheckAll /> Mark All Read
                </Button>
              )}
              
              <Dropdown>
                <Dropdown.Toggle variant="outline-secondary" size="sm">
                  <BsGear />
                </Dropdown.Toggle>
                <Dropdown.Menu>
                  <Dropdown.Item onClick={() => setShowToasts(!showToasts)}>
                    {showToasts ? 'Disable' : 'Enable'} Toast Notifications
                  </Dropdown.Item>
                </Dropdown.Menu>
              </Dropdown>
            </div>
          </div>
          
          {/* Notifications List */}
          {filteredNotifications.length === 0 ? (
            <div className="text-center text-muted py-4">
              <BsBell size={48} className="mb-3 opacity-50" />
              <p>No notifications to display</p>
            </div>
          ) : (
            <ListGroup variant="flush" style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {filteredNotifications.map((notification) => (
                <ListGroup.Item 
                  key={notification.id}
                  className={`notification-item ${notification.read ? 'read' : 'unread'}`}
                >
                  <div className="d-flex align-items-start">
                    <div className="notification-icon me-3">
                      {getNotificationIcon(notification.type)}
                    </div>
                    
                    <div className="flex-grow-1">
                      <div className="d-flex justify-content-between align-items-start">
                        <div>
                          <h6 className="mb-1">
                            {notification.title}
                            {!notification.read && (
                              <Badge bg="primary" className="ms-2 badge-sm">New</Badge>
                            )}
                          </h6>
                          <p className="mb-1 text-muted small">
                            {notification.message}
                          </p>
                          <small className="text-muted">
                            {formatTimestamp(notification.timestamp)}
                          </small>
                        </div>
                        
                        <div className="d-flex gap-1">
                          {!notification.read && (
                            <Button
                              variant="outline-success"
                              size="sm"
                              onClick={() => handleMarkAsRead(notification.id)}
                              title="Mark as read"
                            >
                              <BsCheck />
                            </Button>
                          )}
                        </div>
                      </div>
                      
                      {/* Additional data display */}
                      {notification.data && Object.keys(notification.data).length > 0 && (
                        <div className="mt-2">
                          <details className="small">
                            <summary className="text-muted">View details</summary>
                            <pre className="mt-2 p-2 bg-light rounded small">
                              {JSON.stringify(notification.data, null, 2)}
                            </pre>
                          </details>
                        </div>
                      )}
                    </div>
                  </div>
                </ListGroup.Item>
              ))}
            </ListGroup>
          )}
        </Modal.Body>
      </Modal>
      
      {/* Toast Notifications */}
      <ToastContainer position="top-end" className="p-3">
        {toastQueue.map((notification) => (
          <Toast
            key={notification.id}
            show={true}
            onClose={() => removeToast(notification.id)}
            delay={5000}
            autohide
            bg={getNotificationVariant(notification.type)}
            className="text-white"
          >
            <Toast.Header>
              <span className="me-2">{getNotificationIcon(notification.type)}</span>
              <strong className="me-auto">{notification.title}</strong>
              <small>{formatTimestamp(notification.timestamp)}</small>
            </Toast.Header>
            <Toast.Body>
              {notification.message}
            </Toast.Body>
          </Toast>
        ))}
      </ToastContainer>
    </>
  );
};

export default NotificationCenter;