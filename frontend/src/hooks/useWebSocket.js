// # frontend/src/hooks/useWebSocket.js - React WebSocket Hook
import { useState, useEffect, useRef, useCallback } from 'react';

export const useWebSocket = (userId) => {
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [taskUpdates, setTaskUpdates] = useState({});
  const [workflowUpdates, setWorkflowUpdates] = useState({});
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!userId) return;

    try {
      const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/${userId}`;
      const newSocket = new WebSocket(wsUrl);

      newSocket.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setSocket(newSocket);
        reconnectAttempts.current = 0;
      };

      newSocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      newSocket.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        setSocket(null);
        
        // Attempt to reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          setTimeout(() => {
            console.log(`Reconnecting... Attempt ${reconnectAttempts.current}`);
            connect();
          }, Math.pow(2, reconnectAttempts.current) * 1000); // Exponential backoff
        }
      };

      newSocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [userId]);

  const disconnect = useCallback(() => {
    if (socket) {
      socket.close();
      setSocket(null);
      setIsConnected(false);
    }
  }, [socket]);

  const sendMessage = useCallback((message) => {
    if (socket && isConnected) {
      socket.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }, [socket, isConnected]);

  const subscribeToTask = useCallback((taskId) => {
    sendMessage({
      type: 'subscribe_task',
      task_id: taskId
    });
  }, [sendMessage]);

  const subscribeToWorkflow = useCallback((workflowId) => {
    sendMessage({
      type: 'subscribe_workflow',
      workflow_id: workflowId
    });
  }, [sendMessage]);

  const markNotificationRead = useCallback((notificationId) => {
    sendMessage({
      type: 'mark_notification_read',
      notification_id: notificationId
    });
  }, [sendMessage]);

  const handleMessage = (message) => {
    switch (message.type) {
      case 'connection_established':
        console.log('Connection established:', message.connection_id);
        break;

      case 'initial_notifications':
        setNotifications(message.notifications);
        break;

      case 'task_update':
        setTaskUpdates(prev => ({
          ...prev,
          [message.task_id]: message.data
        }));
        break;

      case 'workflow_update':
        setWorkflowUpdates(prev => ({
          ...prev,
          [message.workflow_id]: message.data
        }));
        break;

      case 'system_notification':
      case 'task_complete':
      case 'task_failed':
      case 'info':
      case 'success':
      case 'warning':
      case 'error':
        setNotifications(prev => [message, ...prev.slice(0, 49)]); // Keep last 50
        break;

      case 'subscription_confirmed':
        console.log(`Subscribed to ${message.resource_type}: ${message.resource_id}`);
        break;

      case 'notification_marked_read':
        if (message.success) {
          setNotifications(prev => 
            prev.map(notif => 
              notif.id === message.notification_id 
                ? { ...notif, read: true }
                : notif
            )
          );
        }
        break;

      case 'pong':
        console.log('Pong received');
        break;

      default:
        console.log('Unknown message type:', message.type);
    }
  };

  // Auto-connect on mount and when userId changes
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Ping periodically to keep connection alive
  useEffect(() => {
    if (isConnected) {
      const pingInterval = setInterval(() => {
        sendMessage({ type: 'ping', timestamp: Date.now() });
      }, 30000); // Ping every 30 seconds

      return () => clearInterval(pingInterval);
    }
  }, [isConnected, sendMessage]);

  return {
    isConnected,
    notifications,
    taskUpdates,
    workflowUpdates,
    sendMessage,
    subscribeToTask,
    subscribeToWorkflow,
    markNotificationRead,
    connect,
    disconnect
  };
};

export default useWebSocket;
