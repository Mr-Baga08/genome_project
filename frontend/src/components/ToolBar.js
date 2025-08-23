// frontend/src/components/ToolBar.js
import React, { useRef } from 'react';
import {
  BsPlusCircle,
  BsFileEarmark,
  BsFloppy,
  BsFileEarmarkPlus,
  BsCloudUpload,
  BsCheckCircle,
  BsPlayCircle,
  BsTrash,
  BsGear,
  BsQuestionCircle,
} from 'react-icons/bs';
import { useAppContext } from '../context/AppContext';

const ToolBar = ({ onRemoveElement, onGenerateJson, onRunWorkflow }) => {
  const { actions } = useAppContext();
  const fileInputRef = useRef(null);

  const handleFileChange = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length > 0) {
      try {
        // Upload files using API service
        await actions.uploadFiles?.(files);
        actions.addNotification({
          type: 'success',
          title: 'Files Uploaded',
          message: `Successfully uploaded ${files.length} file(s)`
        });
      } catch (error) {
        actions.addNotification({
          type: 'error',
          title: 'Upload Failed',
          message: error.message
        });
      }
    }
    // Reset file input
    event.target.value = '';
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleNewProject = () => {
    actions.clearWorkflow();
    actions.addNotification({
      type: 'info',
      title: 'New Project',
      message: 'Created new project'
    });
  };

  const handleSaveAll = () => {
    // Implement save functionality
    actions.addNotification({
      type: 'info',
      title: 'Save All',
      message: 'Save functionality will be implemented'
    });
  };

  const handleNewWorkflow = () => {
    actions.clearWorkflow();
    actions.addNotification({
      type: 'info',
      title: 'New Workflow',
      message: 'Created new workflow'
    });
  };

  return (
    <>
      <input
        type="file"
        ref={fileInputRef}
        className="d-none"
        multiple
        onChange={handleFileChange}
        accept=".fastq,.fasta,.csv,.txt"
      />

      <div className="d-flex flex-wrap gap-1" role="toolbar">
        {/* Project Controls */}
        <div className="btn-group" role="group">
          <button 
            type="button" 
            className="btn btn-outline-primary btn-sm" 
            title="New Project" 
            onClick={handleNewProject}
          >
            <BsPlusCircle />
          </button>
          <button 
            type="button" 
            className="btn btn-outline-primary btn-sm" 
            title="Open File" 
            onClick={handleUploadClick}
          >
            <BsFileEarmark />
          </button>
          <button 
            type="button" 
            className="btn btn-outline-primary btn-sm" 
            title="Save All" 
            onClick={handleSaveAll}
          >
            <BsFloppy />
          </button>
        </div>

        {/* Workflow Controls */}
        <div className="btn-group" role="group">
          <button 
            type="button" 
            className="btn btn-outline-info btn-sm" 
            title="New Workflow" 
            onClick={handleNewWorkflow}
          >
            <BsFileEarmarkPlus />
          </button>
          <button
            type="button"
            className="btn btn-outline-info btn-sm"
            title="Upload Workflow"
            onClick={handleUploadClick}
          >
            <BsCloudUpload />
          </button>
        </div>

        {/* Execution Controls */}
        <div className="btn-group" role="group">
          <button 
            type="button" 
            className="btn btn-outline-success btn-sm" 
            title="Generate JSON" 
            onClick={onGenerateJson}
          >
            <BsCheckCircle />
          </button>
          <button 
            type="button" 
            className="btn btn-success btn-sm" 
            title="Run Workflow" 
            onClick={onRunWorkflow}
          >
            <BsPlayCircle />
          </button>
          <button
            type="button"
            className="btn btn-outline-danger btn-sm"
            onClick={onRemoveElement}
            title="Remove Element"
          >
            <BsTrash />
          </button>
        </div>

        {/* Settings */}
        <div className="btn-group" role="group">
          <button 
            type="button" 
            className="btn btn-outline-secondary btn-sm" 
            title="Settings"
          >
            <BsGear />
          </button>
          <button 
            type="button" 
            className="btn btn-outline-secondary btn-sm" 
            title="Help"
          >
            <BsQuestionCircle />
          </button>
        </div>
      </div>
    </>
  );
};

export default ToolBar;

