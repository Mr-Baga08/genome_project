import React from 'react';
import { BsCheckCircle, BsExclamationTriangle, BsXCircle } from 'react-icons/bs';

const ElementSupportIndicator = ({ element, showLabel = false }) => {
  const getSupportIcon = () => {
    if (element.backendSupported) {
      return <BsCheckCircle className="text-success" title="Fully supported by backend" />;
    } else if (element.type) {
      return <BsExclamationTriangle className="text-warning" title="Basic support - may have limited functionality" />;
    } else {
      return <BsXCircle className="text-muted" title="Not yet supported by backend" />;
    }
  };

  const getSupportText = () => {
    if (element.backendSupported) return "Supported";
    if (element.type) return "Limited";
    return "Not Supported";
  };

  return (
    <span className="d-flex align-items-center">
      {getSupportIcon()}
      {showLabel && <small className="ms-1 text-muted">{getSupportText()}</small>}
    </span>
  );
};

export default ElementSupportIndicator;