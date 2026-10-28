export const MAX_IMAGES = 10;
export const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
export const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export interface MediaItem {
  key: string; // stable React key
  id?: number; // set once the image is stored on the server
  file?: File; // set while the image waits to be uploaded
  previewUrl: string; // object URL, revoked when the item is dropped
  uploading?: boolean;
}

export const authHeaders = (): Record<string, string> => {
  const initData = (window as any).Telegram?.WebApp?.initData || '';
  return { Authorization: `tg-init-data ${initData}` };
};

const newKey = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

export const makePendingItem = (file: File): MediaItem => ({
  key: newKey(),
  file,
  previewUrl: URL.createObjectURL(file),
});

export const revokePreview = (item: MediaItem) => URL.revokeObjectURL(item.previewUrl);

/** Client-side pre-check for quick feedback; the server re-validates everything. */
export const validateImage = (file: File, currentCount: number): string | null => {
  if (currentCount >= MAX_IMAGES) return `At most ${MAX_IMAGES} images per post`;
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) return 'Only JPEG, PNG and WEBP images are supported';
  if (file.size > MAX_IMAGE_BYTES) return 'Image is larger than 10 MB';
  if (file.size === 0) return 'File is empty';
  return null;
};

const errorFrom = async (response: Response, fallback: string): Promise<Error> => {
  let detail = '';
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') detail = body.detail;
  } catch {
    /* non-JSON error body */
  }
  return new Error(detail || `${fallback} (${response.status})`);
};

export const uploadImage = async (postId: number, file: File): Promise<number> => {
  const form = new FormData();
  form.append('file', file);
  const response = await fetch(`/api/posts/${postId}/media`, {
    method: 'POST',
    headers: authHeaders(), // no Content-Type: the browser sets the multipart boundary
    body: form,
  });
  if (!response.ok) throw await errorFrom(response, 'Upload failed');
  return (await response.json()).id as number;
};

export const deleteImage = async (postId: number, mediaId: number): Promise<void> => {
  const response = await fetch(`/api/posts/${postId}/media/${mediaId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!response.ok) throw await errorFrom(response, 'Delete failed');
};

/** Load a post's stored images as displayable items (files are fetched with auth as blobs). */
export const loadPostImages = async (postId: number): Promise<MediaItem[]> => {
  const response = await fetch(`/api/posts/${postId}/media`, { headers: authHeaders() });
  if (!response.ok) throw await errorFrom(response, 'Failed to load images');
  const list: { id: number; url: string }[] = await response.json();

  const items = await Promise.all(
    list.map(async (m): Promise<MediaItem | null> => {
      try {
        const file = await fetch(m.url, { headers: authHeaders() });
        if (!file.ok) return null;
        const blob = await file.blob();
        return { key: newKey(), id: m.id, previewUrl: URL.createObjectURL(blob) };
      } catch {
        return null;
      }
    })
  );
  return items.filter((i): i is MediaItem => i !== null);
};
