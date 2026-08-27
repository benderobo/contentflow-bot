import React, { useState } from 'react';
import './RewriteComparison.css';

interface RewriteComparisonProps {
  original: string;
  rewritten: string;
  onAccept: () => void;
  onDiscard: () => void;
  onTryAgain: () => void;
  loading: boolean;
}

export default function RewriteComparison({
  original,
  rewritten,
  onAccept,
  onDiscard,
  onTryAgain,
  loading,
}: RewriteComparisonProps) {
  const [selectedVersion, setSelectedVersion] = useState<'original' | 'rewritten'>('rewritten');

  return (
    <div className="rewrite-comparison">
      <h3>🔄 Сравнение текстов</h3>

      <div className="comparison-container">
        <div className="text-column original">
          <h4>📄 Оригинальный текст</h4>
          <div className="text-content">
            <p>{original}</p>
          </div>
          <button
            className={`version-btn ${selectedVersion === 'original' ? 'active' : ''}`}
            onClick={() => setSelectedVersion('original')}
          >
            ✓ Использовать оригинал
          </button>
        </div>

        <div className="comparison-divider">↔️</div>

        <div className="text-column rewritten">
          <h4>✨ Переписанный текст</h4>
          <div className="text-content">
            <p>{rewritten}</p>
          </div>
          <button
            className={`version-btn ${selectedVersion === 'rewritten' ? 'active' : ''}`}
            onClick={() => setSelectedVersion('rewritten')}
          >
            ✓ Использовать переписанный
          </button>
        </div>
      </div>

      <div className="comparison-info">
        <p>📌 Выбран: <strong>{selectedVersion === 'original' ? 'Оригинальный' : 'Переписанный'}</strong> текст</p>
      </div>

      <div className="comparison-actions">
        <button
          className="btn-accept"
          onClick={onAccept}
          disabled={loading}
        >
          ✅ Применить выбранный вариант
        </button>
        <button
          className="btn-try-again"
          onClick={onTryAgain}
          disabled={loading}
        >
          🔄 Переписать ещё раз
        </button>
        <button
          className="btn-discard"
          onClick={onDiscard}
          disabled={loading}
        >
          ✕ Отменить
        </button>
      </div>
    </div>
  );
}
