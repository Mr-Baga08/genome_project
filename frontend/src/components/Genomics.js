// frontend/src/components/NotificationToast.js
import React, { useEffect, useState } from 'react';
import { 
  BsCheckCircle, 
  BsExclamationTriangle, 
  BsInfoCircle, 
  BsXCircle 
} from 'react-icons/bs';

const NotificationToast = ({ notification, onClose }) => {
  const [show, setShow] = useState(false);

  useEffect(() => {
    setShow(true);
    
    // Auto-hide after delay
    const timer = setTimeout(() => {
      handleClose();
    }, notification.duration || 5000);

    return () => clearTimeout(timer);
  }, [notification]);

  const handleClose = () => {
    setShow(false);
    setTimeout(onClose, 300); // Allow fade animation to complete
  };

  const getIcon = () => {
    switch (notification.type) {
      case 'success': return <BsCheckCircle className="text-success" />;
      case 'error': return <BsXCircle className="text-danger" />;
      case 'warning': return <BsExclamationTriangle className="text-warning" />;
      default: return <BsInfoCircle className="text-info" />;
    }
  };

  const getBorderClass = () => {
    switch (notification.type) {
      case 'success': return 'border-success';
      case 'error': return 'border-danger';
      case 'warning': return 'border-warning';
      default: return 'border-info';
    }
  };

  return (
    <div className={`toast align-items-center ${getBorderClass()} mb-2 ${show ? 'show' : ''}`} 
         role="alert" 
         style={{ minWidth: '300px' }}>
      <div className="d-flex">
        <div className="toast-body d-flex align-items-start">
          <div className="me-2 mt-1">
            {getIcon()}
          </div>
          <div className="flex-grow-1">
            {notification.title && (
              <div className="fw-medium text-dark mb-1">{notification.title}</div>
            )}
            <div className="text-muted small">{notification.message}</div>
          </div>
        </div>
        <button 
          type="button" 
          className="btn-close me-2 m-auto" 
          onClick={handleClose}
        ></button>
      </div>
    </div>
  );
};

export default NotificationToast;
