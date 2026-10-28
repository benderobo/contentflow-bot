import React, { useEffect, useState } from 'react';
import './App.css';
import Editor from './components/Editor';
import Preview from './components/Preview';
import Toolbar from './components/Toolbar';
import {
  MediaItem,
  authHeaders,
  deleteImage,
  loadPostImages,
  makePendingItem,
  revokePreview,
  uploadImage,
  validateImage,
} from './mediaApi';

interface TelegramUser {
  id: number;
  first_name: string;
  username?: string;
  is_bot: boolean;
  is_premium?: boolean;
  language_code?: string;
}

interface Post {
  id?: number;
  source_item_id?: number;
  title: string;
  body: string;
  hashtags: string[];
  media: MediaItem[];
}

const ALLOWED_USER_IDS = [
  // Add your Telegram ID here
  // You can find it with @userinfobot in Telegram
];

export default function App() {
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [post, setPost] = useState<Post>({
    title: '',
    body: '',
    hashtags: [],
    media: [],
  });
  const [showPreview, setShowPreview] = useState(false);
  const [authorized, setAuthorized] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Initialize Telegram Web App
    if (typeof window !== 'undefined' && (window as any).Telegram) {
      const TelegramAPI = (window as any).Telegram.WebApp;
      TelegramAPI.ready();

      const initData = TelegramAPI.initDataUnsafe;
      if (initData?.user) {
        const userData = initData.user as TelegramUser;
        setUser(userData);

        // Check if user is authorized
        if (userData.id) {
          setAuthorized(true);
          // Load source item if item_id is in URL, or post if post_id is in URL
          const params = new URLSearchParams(window.location.search);
          const itemId = params.get('item_id');
          const postId = params.get('post_id');
          if (itemId) {
            loadSourceItem(parseInt(itemId), userData.id);
          } else if (postId) {
            loadPost(parseInt(postId), userData.id);
          }
        } else {
          setError('Unauthorized user');
          setAuthorized(false);
        }

        // Expand app to full screen
        TelegramAPI.expand();
      } else {
        setError('Could not retrieve user data');
      }
    } else {
      // Fallback for development/testing
      setAuthorized(true);
      setUser({
        id: 123456789,
        first_name: 'Test',
        is_bot: false,
      });
    }
  }, []);

  const loadSourceItem = async (itemId: number, _userId: number) => {
    try {
      const TelegramAPI = (window as any).Telegram?.WebApp;
      const initData = TelegramAPI?.initData || '';

      const response = await fetch(`/api/sources/items/${itemId}`, {
        headers: {
          'Authorization': `tg-init-data ${initData}`,
        },
      });

      if (response.ok) {
        const item = await response.json();
        setPost({
          title: item.title || '',
          body: item.content || item.description || '',
          hashtags: [],
          media: [],
          source_item_id: itemId,
        });
      } else {
        setError('Failed to load article');
      }
    } catch (err) {
      setError('Error loading article');
      console.error(err);
    }
  };

  const loadPost = async (postId: number, _userId: number) => {
    try {
      const TelegramAPI = (window as any).Telegram?.WebApp;
      const initData = TelegramAPI?.initData || '';

      const response = await fetch(`/api/posts/${postId}`, {
        headers: {
          'Authorization': `tg-init-data ${initData}`,
        },
      });

      if (response.ok) {
        const post = await response.json();
        let media: MediaItem[] = [];
        try {
          media = await loadPostImages(postId);
        } catch (err) {
          console.error(err);
          setError('Post loaded, but its images could not be loaded');
        }
        setPost({
          id: postId,
          title: post.title || '',
          body: post.body || '',
          hashtags: post.hashtags || [],
          media,
        });
      } else {
        setError('Failed to load post');
      }
    } catch (err) {
      setError('Error loading post');
      console.error(err);
    }
  };

  const resetPost = () => {
    post.media.forEach(revokePreview);
    setPost({ title: '', body: '', hashtags: [], media: [] });
  };

  /**
   * Create or update the post, then upload queued images.
   * The status is applied last: published posts are locked against media changes.
   */
  const persistPost = async (status?: string): Promise<boolean> => {
    const headers = {
      'Content-Type': 'application/json',
      ...authHeaders(),
    };
    const fields = { title: post.title, body: post.body, hashtags: post.hashtags };

    let postId = post.id;
    if (postId) {
      const response = await fetch(`/api/posts/${postId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify(fields),
      });
      if (!response.ok) throw new Error('Failed to save post');
    } else {
      const response = await fetch('/api/posts/', {
        method: 'POST',
        headers,
        body: JSON.stringify({ ...fields, source_item_id: post.source_item_id }),
      });
      if (!response.ok) throw new Error('Failed to save post');
      postId = (await response.json()).id as number;
      // Remember the id right away: a later failure must not make the next save create a duplicate.
      setPost((p) => ({ ...p, id: postId }));
    }

    const failed: { item: MediaItem; reason: string }[] = [];
    const uploaded = new Map<string, number>();
    for (const item of post.media) {
      if (!item.file || item.id) continue;
      try {
        uploaded.set(item.key, await uploadImage(postId, item.file));
      } catch (err) {
        failed.push({ item, reason: err instanceof Error ? err.message : 'Upload failed' });
      }
    }

    if (failed.length > 0) {
      // Keep the post id so the next save updates this post instead of creating a duplicate.
      setPost((p) => ({
        ...p,
        id: postId,
        media: p.media.map((m) => (uploaded.has(m.key) ? { ...m, id: uploaded.get(m.key), file: undefined } : m)),
      }));
      setError(`${failed.length} image(s) not uploaded: ${failed[0].reason}`);
      return false;
    }

    if (status) {
      const response = await fetch(`/api/posts/${postId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ status }),
      });
      if (!response.ok) throw new Error('Failed to update post status');
    }
    return true;
  };

  const handleSavePost = async () => {
    try {
      if (await persistPost()) {
        alert('Post saved successfully!');
        resetPost();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error saving post');
      console.error(err);
    }
  };

  const handlePublishPost = async () => {
    try {
      if (await persistPost('published')) {
        alert('Post published successfully!');
        resetPost();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error publishing post');
      console.error(err);
    }
  };

  const handleAddImages = async (files: File[]) => {
    const accepted: MediaItem[] = [];
    let count = post.media.length;
    for (const file of files) {
      const problem = validateImage(file, count);
      if (problem) {
        setError(`${file.name}: ${problem}`);
        continue;
      }
      accepted.push(makePendingItem(file));
      count += 1;
    }
    if (accepted.length === 0) return;

    const postId = post.id;
    // New posts have no id yet: images wait locally and are uploaded on save.
    setPost((p) => ({ ...p, media: [...p.media, ...accepted.map((m) => ({ ...m, uploading: !!postId }))] }));
    if (!postId) return;

    for (const item of accepted) {
      try {
        const id = await uploadImage(postId, item.file as File);
        setPost((p) => ({
          ...p,
          media: p.media.map((m) => (m.key === item.key ? { ...m, id, file: undefined, uploading: false } : m)),
        }));
      } catch (err) {
        revokePreview(item);
        setPost((p) => ({ ...p, media: p.media.filter((m) => m.key !== item.key) }));
        setError(`${(item.file as File).name}: ${err instanceof Error ? err.message : 'Upload failed'}`);
      }
    }
  };

  const handleRemoveImage = async (item: MediaItem) => {
    if (item.id && post.id) {
      try {
        await deleteImage(post.id, item.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to remove image');
        return;
      }
    }
    revokePreview(item);
    setPost((p) => ({ ...p, media: p.media.filter((m) => m.key !== item.key) }));
  };

  const handleQuickReplace = async (replaceFrom: string, replaceTo: string) => {
    try {
      if (!user) return;

      const TelegramAPI = (window as any).Telegram?.WebApp;
      const initData = TelegramAPI?.initData || '';

      const response = await fetch('/api/ai/rewrite', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `tg-init-data ${initData}`,
        },
        body: JSON.stringify({
          text: post.body,
          style: 'neutral',
          replace_from: replaceFrom,
          replace_to: replaceTo,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setPost({ ...post, body: result.rewritten });
        alert('Channel mention replaced!');
      } else {
        setError('Failed to apply replacement');
      }
    } catch (err) {
      setError('Error applying replacement');
      console.error(err);
    }
  };

  if (!authorized) {
    return (
      <div className="auth-error">
        <div className="error-box">
          <h1>⚠️ Unauthorized</h1>
          <p>This Mini App is only available for authorized users.</p>
          {error && <p className="error-text">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>📝 ContentFlow Editor</h1>
        <p className="user-info">Welcome, {user?.first_name}!</p>
      </header>

      <main className="app-main">
        <div className="editor-section">
          <Toolbar
            onPreview={() => setShowPreview(!showPreview)}
            onSave={handleSavePost}
            onPublish={handlePublishPost}
            onQuickReplace={handleQuickReplace}
            showPreview={showPreview}
          />

          <div className="editor-container">
            {showPreview ? (
              <Preview post={post} />
            ) : (
              <Editor
                post={post}
                setPost={setPost}
                onAddImages={handleAddImages}
                onRemoveImage={handleRemoveImage}
              />
            )}
          </div>
        </div>
      </main>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError('')}>✕</button>
        </div>
      )}
    </div>
  );
}
