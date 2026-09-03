import React, { useEffect, useState } from 'react';
import './App.css';
import Editor from './components/Editor.tsx';
import Preview from './components/Preview.tsx';
import Toolbar from './components/Toolbar.tsx';

interface TelegramUser {
  id: number;
  first_name: string;
  username?: string;
  is_bot: boolean;
  is_premium?: boolean;
  language_code?: string;
}

interface Post {
  id?: string;
  source_item_id?: number;
  title: string;
  body: string;
  hashtags: string[];
  media?: string[];
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
        setPost({
          id: postId,
          title: post.title || '',
          body: post.body || '',
          hashtags: post.hashtags || [],
          media: [],
        });
      } else {
        setError('Failed to load post');
      }
    } catch (err) {
      setError('Error loading post');
      console.error(err);
    }
  };

  const handleSavePost = async () => {
    try {
      const TelegramAPI = (window as any).Telegram?.WebApp;
      const initData = TelegramAPI?.initData || '';

      const response = await fetch('/api/posts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `tg-init-data ${initData}`,
        },
        body: JSON.stringify({
          title: post.title,
          body: post.body,
          hashtags: post.hashtags,
          source_item_id: post.source_item_id,
        }),
      });

      if (response.ok) {
        alert('Post saved successfully!');
        setPost({ title: '', body: '', hashtags: [], media: [] });
      } else {
        setError('Failed to save post');
      }
    } catch (err) {
      setError('Error saving post');
      console.error(err);
    }
  };

  const handlePublishPost = async () => {
    try {
      const TelegramAPI = (window as any).Telegram?.WebApp;
      const initData = TelegramAPI?.initData || '';

      const response = await fetch('/api/posts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `tg-init-data ${initData}`,
        },
        body: JSON.stringify({
          title: post.title,
          body: post.body,
          hashtags: post.hashtags,
          source_item_id: post.source_item_id,
          status: 'published',
        }),
      });

      if (response.ok) {
        alert('Post published successfully!');
        setPost({ title: '', body: '', hashtags: [], media: [] });
      } else {
        setError('Failed to publish post');
      }
    } catch (err) {
      setError('Error publishing post');
      console.error(err);
    }
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
              <Editor post={post} setPost={setPost} />
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
