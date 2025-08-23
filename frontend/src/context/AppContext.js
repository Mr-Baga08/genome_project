// frontend/src/context/AppContext.js
import React, { createContext, useContext, useReducer, useEffect } from 'react';
import apiService from '../services/apiService';

// Initial state
const initialState = {
  tasks: [],
  currentTask: null,
  isLoading: false,
  error: null,
  workflowElements: [],
  connections: [],
  selectedElement: null,
  pagination: {
    page: 1,
    size: 10,
    totalCount: 0,
  },
  notifications: [],
};

// Action types
const ActionTypes = {
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  SET_TASKS: 'SET_TASKS',
  SET_CURRENT_TASK: 'SET_CURRENT_TASK',
  ADD_TASK: 'ADD_TASK',
  UPDATE_TASK: 'UPDATE_TASK',
  SET_WORKFLOW_ELEMENTS: 'SET_WORKFLOW_ELEMENTS',
  ADD_WORKFLOW_ELEMENT: 'ADD_WORKFLOW_ELEMENT',
  REMOVE_WORKFLOW_ELEMENT: 'REMOVE_WORKFLOW_ELEMENT',
  UPDATE_WORKFLOW_ELEMENT: 'UPDATE_WORKFLOW_ELEMENT',
  SET_CONNECTIONS: 'SET_CONNECTIONS',
  ADD_CONNECTION: 'ADD_CONNECTION',
  REMOVE_CONNECTION: 'REMOVE_CONNECTION',
  SET_SELECTED_ELEMENT: 'SET_SELECTED_ELEMENT',
  SET_PAGINATION: 'SET_PAGINATION',
  ADD_NOTIFICATION: 'ADD_NOTIFICATION',
  REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
  CLEAR_ERROR: 'CLEAR_ERROR',
};

// Reducer
function appReducer(state, action) {
  switch (action.type) {
    case ActionTypes.SET_LOADING:
      return { ...state, isLoading: action.payload };

    case ActionTypes.SET_ERROR:
      return { ...state, error: action.payload, isLoading: false };

    case ActionTypes.CLEAR_ERROR:
      return { ...state, error: null };

    case ActionTypes.SET_TASKS:
      return { ...state, tasks: action.payload, isLoading: false };

    case ActionTypes.SET_CURRENT_TASK:
      return { ...state, currentTask: action.payload };

    case ActionTypes.ADD_TASK:
      return { ...state, tasks: [action.payload, ...state.tasks] };

    case ActionTypes.UPDATE_TASK:
      return {
        ...state,
        tasks: state.tasks.map(task =>
          task.task_id === action.payload.task_id ? action.payload : task
        ),
        currentTask: state.currentTask?.task_id === action.payload.task_id 
          ? action.payload 
          : state.currentTask,
      };

    case ActionTypes.SET_WORKFLOW_ELEMENTS:
      return { ...state, workflowElements: action.payload };

    case ActionTypes.ADD_WORKFLOW_ELEMENT:
      return { 
        ...state, 
        workflowElements: [...state.workflowElements, action.payload] 
      };

    case ActionTypes.REMOVE_WORKFLOW_ELEMENT:
      const elementId = action.payload;
      return {
        ...state,
        workflowElements: state.workflowElements.filter(el => el.id !== elementId),
        connections: state.connections.filter(
          conn => conn.from !== elementId && conn.to !== elementId
        ),
        selectedElement: state.selectedElement?.id === elementId ? null : state.selectedElement,
      };

    case ActionTypes.UPDATE_WORKFLOW_ELEMENT:
      return {
        ...state,
        workflowElements: state.workflowElements.map(el =>
          el.id === action.payload.id ? { ...el, ...action.payload } : el
        ),
      };

    case ActionTypes.SET_CONNECTIONS:
      return { ...state, connections: action.payload };

    case ActionTypes.ADD_CONNECTION:
      return { 
        ...state, 
        connections: [...state.connections, action.payload] 
      };

    case ActionTypes.REMOVE_CONNECTION:
      return {
        ...state,
        connections: state.connections.filter(
          conn => !(conn.from === action.payload.from && conn.to === action.payload.to)
        ),
      };

    case ActionTypes.SET_SELECTED_ELEMENT:
      return { ...state, selectedElement: action.payload };

    case ActionTypes.SET_PAGINATION:
      return { ...state, pagination: { ...state.pagination, ...action.payload } };

    case ActionTypes.ADD_NOTIFICATION:
      return {
        ...state,
        notifications: [...state.notifications, {
          id: Date.now(),
          ...action.payload,
        }],
      };

    case ActionTypes.REMOVE_NOTIFICATION:
      return {
        ...state,
        notifications: state.notifications.filter(n => n.id !== action.payload),
      };

    default:
      return state;
  }
}

// Context
const AppContext = createContext();

// Provider component
export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Action creators
  const actions = {
    setLoading: (loading) => dispatch({ type: ActionTypes.SET_LOADING, payload: loading }),
    
    setError: (error) => dispatch({ type: ActionTypes.SET_ERROR, payload: error }),
    
    clearError: () => dispatch({ type: ActionTypes.CLEAR_ERROR }),

    // Task actions
    async loadTasks(page = 1, size = 10) {
      actions.setLoading(true);
      try {
        const response = await apiService.getAllTasks(page, size);
        dispatch({ type: ActionTypes.SET_TASKS, payload: response.tasks });
        dispatch({ 
          type: ActionTypes.SET_PAGINATION, 
          payload: {
            page: response.page,
            size: response.size,
            totalCount: response.total_count,
          }
        });
      } catch (error) {
        actions.setError(error.message);
      }
    },

    async loadTaskDetails(taskId) {
      actions.setLoading(true);
      try {
        const task = await apiService.getTaskDetails(taskId);
        dispatch({ type: ActionTypes.SET_CURRENT_TASK, payload: task });
      } catch (error) {
        actions.setError(error.message);
      }
    },

    async submitWorkflow(priority = 'medium') {
      actions.setLoading(true);
      try {
        const workflowData = {
          nodes: state.workflowElements,
          connections: state.connections,
        };
        
        const response = await apiService.submitWorkflow(workflowData, priority);
        
        actions.addNotification({
          type: 'success',
          title: 'Workflow Submitted',
          message: `Task ${response.task_id} has been submitted for processing.`,
        });
        
        // Refresh tasks list
        actions.loadTasks();
        
        return response.task_id;
      } catch (error) {
        actions.setError(error.message);
        actions.addNotification({
          type: 'error',
          title: 'Submission Failed',
          message: error.message,
        });
      }
    },

    // Workflow actions
    addWorkflowElement: (element) => 
      dispatch({ type: ActionTypes.ADD_WORKFLOW_ELEMENT, payload: element }),
    
    removeWorkflowElement: (elementId) =>
      dispatch({ type: ActionTypes.REMOVE_WORKFLOW_ELEMENT, payload: elementId }),
    
    updateWorkflowElement: (element) =>
      dispatch({ type: ActionTypes.UPDATE_WORKFLOW_ELEMENT, payload: element }),

    addConnection: (connection) =>
      dispatch({ type: ActionTypes.ADD_CONNECTION, payload: connection }),
    
    removeConnection: (connection) =>
      dispatch({ type: ActionTypes.REMOVE_CONNECTION, payload: connection }),

    setSelectedElement: (element) =>
      dispatch({ type: ActionTypes.SET_SELECTED_ELEMENT, payload: element }),

    // Notification actions
    addNotification: (notification) =>
      dispatch({ type: ActionTypes.ADD_NOTIFICATION, payload: notification }),
    
    removeNotification: (notificationId) =>
      dispatch({ type: ActionTypes.REMOVE_NOTIFICATION, payload: notificationId }),

    // Clear workflow
    clearWorkflow: () => {
      dispatch({ type: ActionTypes.SET_WORKFLOW_ELEMENTS, payload: [] });
      dispatch({ type: ActionTypes.SET_CONNECTIONS, payload: [] });
      dispatch({ type: ActionTypes.SET_SELECTED_ELEMENT, payload: null });
    },
  };

  // Auto-refresh tasks every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (state.tasks.length > 0) {
        actions.loadTasks(state.pagination.page, state.pagination.size);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [state.tasks.length, state.pagination.page, state.pagination.size]);

  // Auto-remove notifications after 5 seconds
  useEffect(() => {
    state.notifications.forEach(notification => {
      if (notification.autoRemove !== false) {
        setTimeout(() => {
          actions.removeNotification(notification.id);
        }, 5000);
      }
    });
  }, [state.notifications]);

  return (
    <AppContext.Provider value={{ state, actions }}>
      {children}
    </AppContext.Provider>
  );
}

// Hook to use context
export function useAppContext() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
}
