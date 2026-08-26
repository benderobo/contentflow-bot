import React from 'react';
import './Toolbar.css';

interface ToolbarProps {
  onPreview: () => void;
  onSave: () => void;
  onPublish: () => void;
  showPreview: boolean;
}

export default function Toolbar({
  onPreview,
  onSave,
  onPublish,
  showPreview,
}: ToolbarProps) {
  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <button
          onClick={onPreview}
          className={`toolbar-btn ${showPreview ? 'active' : ''}`}
          title="Toggle preview"
        >
          👁️ {showPreview ? 'Edit' : 'Preview'}
        </button>
      </div>

      <div className="toolbar-group">
        <button
          onClick={onSave}
          className="toolbar-btn btn-secondary"
          title="Save as draft"
        >
          💾 Save
        </button>
        <button
          onClick={onPublish}
          className="toolbar-btn btn-primary"
          title="Publish now"
        >
          🚀 Publish
        </button>
      </div>
    </div>
  );
}
