// frontend/src/hooks/useWebSocket.js
import { useState, useEffect, useRef, useCallback } from 'react';

export const useWebSocket = (url, options = {}) => {
  const [socket, setSocket] = useState(null);
  const [lastMessage, setLastMessage] = useState(null);
  const [readyState, setReadyState] = useState(WebSocket.CONNECTING);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const [messageHistory, setMessageHistory] = useState([]);
  
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = options.maxReconnectAttempts || 5;
  const reconnectInterval = options.reconnectInterval || 3000;
  const heartbeatInterval = options.heartbeatInterval || 30000;
  const heartbeatTimeoutRef = useRef(null);

  // Get user ID from localStorage or context
  const getUserId = () => {
    return localStorage.getItem('userId') || 'anonymous';
  };

  // Build WebSocket URL with query parameters
  const buildUrl = useCallback(() => {
    const urlObj = new URL(url, window.location.origin.replace('http', 'ws'));
    urlObj.searchParams.set('user_id', getUserId());
    urlObj.searchParams.set('client_type', 'web');
    return urlObj.toString();
  }, [url]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    try {
      const wsUrl = buildUrl();
      console.log('Connecting to WebSocket:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = (event) => {
        console.log('WebSocket connected');
        setSocket(ws);
        setReadyState(WebSocket.OPEN);
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttemptsRef.current = 0;
        
        // Start heartbeat
        startHeartbeat(ws);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          setLastMessage({ data: event.data, timestamp: Date.now() });
          
          // Store in message history (keep last 100 messages)
          setMessageHistory(prev => {
            const newHistory = [...prev, message];
            return newHistory.slice(-100);
          });

          // Handle special message types
          if (message.type === 'pong') {
            // Heartbeat response - connection is healthy
            return;
          }
          
          if (message.type === 'error') {
            console.error('WebSocket error message:', message.message);
            setConnectionError(message.message);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionError('Connection error occurred');
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setSocket(null);
        setReadyState(WebSocket.CLOSED);
        setIsConnected(false);
        
        // Stop heartbeat
        if (heartbeatTimeoutRef.current) {
          clearInterval(heartbeatTimeoutRef.current);
          heartbeatTimeoutRef.current = null;
        }

        // Attempt to reconnect if not intentionally closed
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`Attempting to reconnect (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval * reconnectAttemptsRef.current);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setConnectionError('Max reconnection attempts reached');
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionError('Failed to establish connection');
      setIsConnected(false);
    }
  }, [buildUrl, maxReconnectAttempts, reconnectInterval]);

  // Start heartbeat to keep connection alive
  const startHeartbeat = (ws) => {
    heartbeatTimeoutRef.current = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
      }
    }, heartbeatInterval);
  };

  // Send message
  const sendMessage = useCallback((message) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      try {
        const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
        socket.send(messageStr);
        return true;
      } catch (error) {
        console.error('Failed to send message:', error);
        return false;
      }
    } else {
      console.warn('WebSocket not connected, cannot send message');
      return false;
    }
  }, [socket]);

  // Join a room
  const joinRoom = useCallback((roomName) => {
    return sendMessage({
      type: 'join_room',
      room: roomName
    });
  }, [sendMessage]);

  // Leave a room
  const leaveRoom = useCallback((roomName) => {
    return sendMessage({
      type: 'leave_room',
      room: roomName
    });
  }, [sendMessage]);

  // Send message to a room
  const sendToRoom = useCallback((roomName, content) => {
    return sendMessage({
      type: 'room_message',
      room: roomName,
      content: content
    });
  }, [sendMessage]);

  // Get room information
  const getRoomInfo = useCallback((roomName) => {
    return sendMessage({
      type: 'get_room_info',
      room: roomName
    });
  }, [sendMessage]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (heartbeatTimeoutRef.current) {
      clearInterval(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }

    if (socket) {
      socket.close(1000, 'User initiated disconnect');
    }
    
    setSocket(null);
    setIsConnected(false);
  }, [socket]);

  // Initialize connection on mount
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Return WebSocket state and methods
  return {
    socket,
    lastMessage,
    readyState,
    isConnected,
    connectionError,
    messageHistory,
    sendMessage,
    joinRoom,
    leaveRoom,
    sendToRoom,
    getRoomInfo,
    connect,
    disconnect,
    reconnectAttempts: reconnectAttemptsRef.current,
    maxReconnectAttempts
  };
};