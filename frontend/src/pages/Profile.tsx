import { type FormEvent, useEffect, useState } from 'react';
import { apiFetch } from '../api';

export default function Profile() {
  const [email, setEmail] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
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

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    await apiFetch('/me', {
      method: 'PUT',
      body: JSON.stringify({ telegram_chat_id: telegramChatId || null }),
    });
    setSaving(false);
    setSaved(true);
  }

  if (loading) return <p>Chargement...</p>;

  return (
    <div style={{ maxWidth: 500, margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Mon profil</h1>
      <p><strong>Email :</strong> {email}</p>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <label>Telegram Chat ID</label>
          <input
            type="text"
            value={telegramChatId}
            onChange={e => setTelegramChatId(e.target.value)}
            placeholder="Votre chat ID Telegram"
            style={{ width: '100%' }}
          />
          <small style={{ color: '#666' }}>
            Envoyez /start au bot puis utilisez @userinfobot pour obtenir votre Chat ID.
          </small>
        </div>
        <button type="submit" disabled={saving}>
          {saving ? 'Enregistrement...' : 'Sauvegarder'}
        </button>
        {saved && <p style={{ color: 'green', marginTop: '0.5rem' }}>Profil sauvegardé</p>}
      </form>
    </div>
  );
}
