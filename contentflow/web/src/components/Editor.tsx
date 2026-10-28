import React from 'react';
import './Editor.css';
import { MAX_IMAGES, MediaItem } from '../mediaApi';

interface Post {
  title: string;
  body: string;
  hashtags: string[];
  media: MediaItem[];
}

interface EditorProps {
  post: Post;
  setPost: (post: Post) => void;
  onAddImages: (files: File[]) => void;
  onRemoveImage: (item: MediaItem) => void;
}

export default function Editor({ post, setPost, onAddImages, onRemoveImage }: EditorProps) {
  const handleFilesPicked = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    e.target.value = ''; // allow picking the same file again
    if (files.length > 0) onAddImages(files);
  };

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
        <label>
          🖼️ Images ({post.media.length}/{MAX_IMAGES})
        </label>
        <div className="media-grid">
          {post.media.map((item) => (
            <div key={item.key} className={`media-thumb${item.uploading ? ' uploading' : ''}`}>
              <img src={item.previewUrl} alt="" />
              {item.uploading && <span className="media-badge">Uploading…</span>}
              {!item.uploading && !item.id && <span className="media-badge">Not saved yet</span>}
              <button
                type="button"
                className="media-remove"
                aria-label="Remove image"
                disabled={item.uploading}
                onClick={() => onRemoveImage(item)}
              >
                ✕
              </button>
            </div>
          ))}
          {post.media.length < MAX_IMAGES && (
            <label className="media-add">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                hidden
                onChange={handleFilesPicked}
              />
              <span aria-hidden="true">＋</span>
              <span>Add image</span>
            </label>
          )}
        </div>
        <span className="char-count">JPEG, PNG or WEBP, up to 10 MB each</span>
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
