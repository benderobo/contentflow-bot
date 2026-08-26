import React from 'react';
import './Preview.css';

// Safe HTML escaping
const escapeHtml = (text: string): string => {
  const map: { [key: string]: string } = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (char) => map[char]);
};

interface Post {
  title: string;
  body: string;
  hashtags: string[];
  media?: string[];
}

interface PreviewProps {
  post: Post;
}

export default function Preview({ post }: PreviewProps) {
  const renderContent = (text: string) => {
    // Escape HTML first to prevent XSS
    let escaped = escapeHtml(text);

    // Then apply markdown transformations
    let html = escaped
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/&gt; (.*?)(?=\n|$)/g, '<blockquote>$1</blockquote>')
      .replace(/\n/g, '<br />');

    return html;
  };

  return (
    <div className="preview">
      <div className="preview-phone">
        <div className="phone-header">
          <span className="phone-time">9:41</span>
        </div>

        <div className="phone-content">
          <article className="post-preview">
            {post.title && <h2 className="post-title">{post.title}</h2>}

            {post.body && (
              <div
                className="post-body"
                dangerouslySetInnerHTML={{ __html: renderContent(post.body) }}
              />
            )}

            {post.hashtags.length > 0 && (
              <div className="post-hashtags">
                {post.hashtags.map((tag) => (
                  <a key={tag} href="#" className="hashtag-link">
                    {tag}
                  </a>
                ))}
              </div>
            )}

            <div className="post-footer">
              <span className="post-meta">📱 via ContentFlow</span>
            </div>
          </article>
        </div>

        <div className="phone-footer">
          <button className="phone-btn">👍</button>
          <button className="phone-btn">💬</button>
          <button className="phone-btn">↗️</button>
        </div>
      </div>

      <div className="preview-info">
        <h3>Preview on Telegram</h3>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-label">Title</span>
            <span className="info-value">{post.title || '—'}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Length</span>
            <span className="info-value">{post.body.length} chars</span>
          </div>
          <div className="info-item">
            <span className="info-label">Hashtags</span>
            <span className="info-value">{post.hashtags.length}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Words</span>
            <span className="info-value">
              {post.body.split(/\s+/).filter((w) => w.length > 0).length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
