import React, { useState } from 'react';
import './Toolbar.css';

interface ToolbarProps {
  onPreview: () => void;
  onSave: () => void;
  onPublish: () => void;
  onQuickReplace?: (replaceFrom: string, replaceTo: string) => void;
  showPreview: boolean;
}

export default function Toolbar({
  onPreview,
  onSave,
  onPublish,
  onQuickReplace,
  showPreview,
}: ToolbarProps) {
  const [showQuickMode, setShowQuickMode] = useState(false);
  const [replaceFrom, setReplaceFrom] = useState('');
  const [replaceTo, setReplaceTo] = useState('');

  const handleQuickReplace = () => {
    if (replaceFrom && replaceTo && onQuickReplace) {
      onQuickReplace(replaceFrom, replaceTo);
      setReplaceFrom('');
      setReplaceTo('');
      setShowQuickMode(false);
    }
  };

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
        <button
          onClick={() => setShowQuickMode(!showQuickMode)}
          className={`toolbar-btn ${showQuickMode ? 'active' : ''}`}
          title="Quick mode: replace channel mentions"
        >
          ⚡ Quick Mode
        </button>
      </div>

      {showQuickMode && (
        <div className="quick-mode-panel">
          <div className="quick-mode-field">
            <label>Old mention:</label>
            <input
              type="text"
              placeholder="e.g., @old_channel"
              value={replaceFrom}
              onChange={(e) => setReplaceFrom(e.target.value)}
            />
          </div>
          <div className="quick-mode-field">
            <label>New mention:</label>
            <input
              type="text"
              placeholder="e.g., @new_channel"
              value={replaceTo}
              onChange={(e) => setReplaceTo(e.target.value)}
            />
          </div>
          <button
            onClick={handleQuickReplace}
            className="toolbar-btn btn-primary"
            disabled={!replaceFrom || !replaceTo}
          >
            ✓ Apply
          </button>
        </div>
      )}

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
