import React from 'react';
import './Editor.css';

interface Post {
  title: string;
  body: string;
  hashtags: string[];
  media?: string[];
}

interface EditorProps {
  post: Post;
  setPost: (post: Post) => void;
}

export default function Editor({ post, setPost }: EditorProps) {
  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPost({ ...post, title: e.target.value });
  };

  const handleBodyChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setPost({ ...post, body: e.target.value });
  };

  const handleHashtagsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const hashtags = e.target.value
      .split(' ')
      .filter((tag) => tag.length > 0)
      .map((tag) => tag.startsWith('#') ? tag : `#${tag}`);
    setPost({ ...post, hashtags });
  };

  const addHashtag = (tag: string) => {
    const newTag = tag.startsWith('#') ? tag : `#${tag}`;
    if (!post.hashtags.includes(newTag)) {
      setPost({ ...post, hashtags: [...post.hashtags, newTag] });
    }
  };

  const removeHashtag = (tag: string) => {
    setPost({
      ...post,
      hashtags: post.hashtags.filter((t) => t !== tag),
    });
  };

  const applyFormatting = (start: string, end: string = '') => {
    const textarea = document.getElementById('body') as HTMLTextAreaElement;
    if (!textarea) return;

    const { selectionStart, selectionEnd, value } = textarea;
    const selectedText = value.substring(selectionStart, selectionEnd);

    if (!selectedText) return;

    const newText =
      value.substring(0, selectionStart) +
      start +
      selectedText +
      end +
      value.substring(selectionEnd);

    setPost({ ...post, body: newText });
  };

  return (
    <div className="editor">
      <div className="editor-field">
        <label htmlFor="title">📰 Title</label>
        <input
          id="title"
          type="text"
          placeholder="Enter post title..."
          value={post.title}
          onChange={handleTitleChange}
          maxLength={256}
          className="editor-input"
        />
        <span className="char-count">{post.title.length}/256</span>
      </div>

      <div className="editor-field">
        <label htmlFor="body">✍️ Content</label>
        <div className="formatting-toolbar">
          <button
            title="Bold"
            onClick={() => applyFormatting('**', '**')}
            className="format-btn"
          >
            <strong>B</strong>
          </button>
          <button
            title="Italic"
            onClick={() => applyFormatting('*', '*')}
            className="format-btn"
          >
            <em>I</em>
          </button>
          <button
            title="Code"
            onClick={() => applyFormatting('`', '`')}
            className="format-btn"
          >
            {'<>'}
          </button>
          <button
            title="Link"
            onClick={() => applyFormatting('[', '](url)')}
            className="format-btn"
          >
            🔗
          </button>
          <button
            title="Quote"
            onClick={() => applyFormatting('> ', '')}
            className="format-btn"
          >
            💬
          </button>
        </div>
        <textarea
          id="body"
          placeholder="Write your post content here..."
          value={post.body}
          onChange={handleBodyChange}
          maxLength={4000}
          className="editor-textarea"
          rows={12}
        />
        <span className="char-count">{post.body.length}/4000</span>
      </div>

      <div className="editor-field">
        <label htmlFor="hashtags">#️⃣ Hashtags</label>
        <input
          id="hashtags"
          type="text"
          placeholder="Type hashtags separated by spaces..."
          onChange={handleHashtagsChange}
          className="editor-input"
        />
        <div className="hashtags-list">
          {post.hashtags.map((tag) => (
            <span key={tag} className="hashtag-badge">
              {tag}
              <button
                onClick={() => removeHashtag(tag)}
                className="hashtag-remove"
              >
                ✕
              </button>
            </span>
          ))}
        </div>
      </div>

      <div className="editor-field">
        <label>🏷️ Quick Tags</label>
        <div className="quick-tags">
          {['AI', 'Tech', 'News', 'Guide', 'Tutorial', 'Tips'].map((tag) => (
            <button
              key={tag}
              onClick={() => addHashtag(tag)}
              className="quick-tag-btn"
            >
              #{tag}
            </button>
          ))}
        </div>
      </div>

      <div className="editor-stats">
        <span>📊 Stats</span>
        <div className="stats-grid">
          <div className="stat">
            <span className="stat-label">Words</span>
            <span className="stat-value">
              {post.body.split(/\s+/).filter((w) => w.length > 0).length}
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">Characters</span>
            <span className="stat-value">{post.body.length}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Hashtags</span>
            <span className="stat-value">{post.hashtags.length}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
