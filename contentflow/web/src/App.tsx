import React, { useEffect, useState } from 'react';
import './App.css';
import Editor from './components/Editor';
import Preview from './components/Preview';
import Toolbar from './components/Toolbar';

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
        // For now, allow all users (you can restrict by ID later)
        if (userData.id) {
          setAuthorized(true);
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

  const handleSavePost = async () => {
    try {
      const response = await fetch('/api/posts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(post),
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
      const response = await fetch('/api/posts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ...post, status: 'published' }),
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
