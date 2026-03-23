import { useEffect, useState } from 'react';
import { apiFetch } from '../api';

export default function Profile() {
  const [email, setEmail] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [linkCode, setLinkCode] = useState('');
  const [botUsername, setBotUsername] = useState('');
  const [linking, setLinking] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch('/me')
      .then(res => res.json())
      .then(data => {
        setEmail(data.email);
        setTelegramChatId(data.telegram_chat_id || '');
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleLinkTelegram() {
    setLinking(true);
    const res = await apiFetch('/me/telegram-code', { method: 'POST' });
    const data = await res.json();
    setLinkCode(data.code);
    setBotUsername(data.bot_username);
    setLinking(false);
  }

  async function handleUnlink() {
    await apiFetch('/me', {
      method: 'PUT',
      body: JSON.stringify({ telegram_chat_id: null }),
    });
    setTelegramChatId('');
    setLinkCode('');
  }

  if (loading) return <p>Chargement...</p>;

  return (
    <div style={{ maxWidth: 500, margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Mon profil</h1>
      <p><strong>Email :</strong> {email}</p>

      <div style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #ddd', borderRadius: 8 }}>
        <h2 style={{ marginTop: 0 }}>Telegram</h2>

        {telegramChatId ? (
          <>
            <p style={{ color: 'green' }}>Telegram lié (ID: {telegramChatId})</p>
            <button onClick={handleUnlink} style={{ background: '#dc3545', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: 4, cursor: 'pointer' }}>
              Délier Telegram
            </button>
          </>
        ) : linkCode ? (
          <div>
            <p>1. Ouvrez <a href={`https://t.me/${botUsername}`} target="_blank" rel="noopener noreferrer">@{botUsername}</a> sur Telegram</p>
            <p>2. Envoyez ce message au bot :</p>
            <code style={{ display: 'block', padding: '0.75rem', background: '#f5f5f5', borderRadius: 4, fontSize: '1.2rem', textAlign: 'center', userSelect: 'all' }}>
              /link {linkCode}
            </code>
            <p style={{ color: '#666', marginTop: '0.5rem' }}>Le code expire au prochain clic sur "Lier Telegram".</p>
            <button onClick={() => { setLinkCode(''); }} style={{ marginTop: '0.5rem' }}>Annuler</button>
          </div>
        ) : (
          <>
            <p style={{ color: '#666' }}>Liez votre compte Telegram pour recevoir les notifications.</p>
            <button onClick={handleLinkTelegram} disabled={linking}>
              {linking ? 'Génération...' : 'Lier Telegram'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
