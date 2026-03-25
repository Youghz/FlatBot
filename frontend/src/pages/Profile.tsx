import { type FormEvent, useEffect, useState } from 'react';
import { apiFetch } from '../api';

export default function Profile() {
  const [email, setEmail] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [linkCode, setLinkCode] = useState('');
  const [botUsername, setBotUsername] = useState('');
  const [linking, setLinking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [pwdChanging, setPwdChanging] = useState(false);
  const [pwdMessage, setPwdMessage] = useState('');
  const [pwdError, setPwdError] = useState('');

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

      <div style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #ddd', borderRadius: 8 }}>
        <h2 style={{ marginTop: 0 }}>Mot de passe</h2>
        <form onSubmit={async (e: FormEvent) => {
          e.preventDefault();
          setPwdChanging(true);
          setPwdMessage('');
          setPwdError('');
          const res = await apiFetch('/me/password', {
            method: 'POST',
            body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
          });
          if (res.ok) {
            setPwdMessage('Mot de passe modifié');
            setCurrentPassword('');
            setNewPassword('');
          } else {
            const data = await res.json();
            setPwdError(data.detail || 'Erreur');
          }
          setPwdChanging(false);
        }}>
          <div style={{ marginBottom: '0.75rem' }}>
            <label>Mot de passe actuel</label>
            <input type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} required style={{ width: '100%' }} />
          </div>
          <div style={{ marginBottom: '0.75rem' }}>
            <label>Nouveau mot de passe (8 car. min.)</label>
            <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required minLength={8} style={{ width: '100%' }} />
          </div>
          {pwdError && <p style={{ color: 'red' }}>{pwdError}</p>}
          {pwdMessage && <p style={{ color: 'green' }}>{pwdMessage}</p>}
          <button type="submit" disabled={pwdChanging}>
            {pwdChanging ? 'Modification...' : 'Changer le mot de passe'}
          </button>
        </form>
      </div>
    </div>
  );
}
