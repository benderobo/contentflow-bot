import React, { useEffect, useState } from 'react';
import './PostView.css';

interface PostData {
  id: number;
  title: string;
  body: string;
  status: string;
  created_at: string;
  hashtags?: string[];
}

interface PostViewProps {
  postId: number;
  onClose: () => void;
  onEdit: (post: PostData) => void;
  initData: string;
}

export default function PostView({ postId, onClose, onEdit, initData }: PostViewProps) {
  const [post, setPost] = useState<PostData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadPost();
  }, [postId]);

  const loadPost = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/posts/${postId}`, {
        headers: {
          'Authorization': `tg-init-data ${initData}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPost(data);
      } else {
        setError('Не удалось загрузить пост');
      }
    } catch (err) {
      setError('Ошибка загрузки поста');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="post-view"><p>Загрузка...</p></div>;
  }

  if (error) {
    return (
      <div className="post-view error">
        <p>{error}</p>
        <button onClick={onClose}>✕ Закрыть</button>
      </div>
    );
  }

  if (!post) {
    return <div className="post-view"><p>Пост не найден</p></div>;
  }

  return (
    <div className="post-view">
      <div className="post-header">
        <h2>{post.title}</h2>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>

      <div className="post-content">
        <p>{post.body}</p>
      </div>

      <div className="post-meta">
        <span className="status">📊 {post.status.toUpperCase()}</span>
        <span className="date">📅 {new Date(post.created_at).toLocaleDateString('ru-RU')}</span>
      </div>

      {post.hashtags && post.hashtags.length > 0 && (
        <div className="post-hashtags">
          {post.hashtags.map((tag) => (
            <span key={tag} className="hashtag">#{tag}</span>
          ))}
        </div>
      )}

      <div className="post-actions">
        {post.status === 'draft' && (
          <>
            <button className="btn-edit" onClick={() => onEdit(post)}>✏️ Редактировать</button>
            <button className="btn-publish">📢 Опубликовать</button>
          </>
        )}
        <button className="btn-close" onClick={onClose}>✕ Закрыть</button>
      </div>
    </div>
  );
}
