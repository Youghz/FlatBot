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

  async function handlePasswordChange(e: FormEvent) {
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
  }

  if (loading) return <div className="loading">Chargement...</div>;

  return (
    <div className="page-narrow">
      <h1>Mon profil</h1>
      <p style={{ color: 'var(--text-secondary)' }}>{email}</p>

      <div className="card section">
        <h2>Telegram</h2>
        {telegramChatId ? (
          <>
            <p className="success-msg">Telegram lié (ID: {telegramChatId})</p>
            <button onClick={handleUnlink} className="btn-danger">Délier Telegram</button>
          </>
        ) : linkCode ? (
          <div>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
              1. Ouvrez <a href={`https://t.me/${botUsername}`} target="_blank" rel="noopener noreferrer">@{botUsername}</a> sur Telegram
            </p>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>2. Envoyez ce message au bot :</p>
            <code className="code-display">/link {linkCode}</code>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '0.75rem' }}>
              Le code expire au prochain clic sur "Lier Telegram".
            </p>
            <button onClick={() => setLinkCode('')} className="btn-secondary" style={{ marginTop: '0.75rem' }}>Annuler</button>
          </div>
        ) : (
          <>
            <p style={{ color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
              Liez votre compte Telegram pour recevoir les notifications.
            </p>
            <button onClick={handleLinkTelegram} disabled={linking}>
              {linking ? 'Génération...' : 'Lier Telegram'}
            </button>
          </>
        )}
      </div>

      <div className="card section">
        <h2>Mot de passe</h2>
        <form onSubmit={handlePasswordChange}>
          <div className="form-group">
            <label>Mot de passe actuel</label>
            <input type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Nouveau mot de passe (8 car. min.)</label>
            <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required minLength={8} />
          </div>
          {pwdError && <p className="error-msg">{pwdError}</p>}
          {pwdMessage && <p className="success-msg">{pwdMessage}</p>}
          <button type="submit" disabled={pwdChanging}>
            {pwdChanging ? 'Modification...' : 'Changer le mot de passe'}
          </button>
        </form>
      </div>
    </div>
  );
}
