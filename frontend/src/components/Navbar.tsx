import { Link, useNavigate } from 'react-router-dom';
import { clearTokens, isLoggedIn } from '../api';

export default function Navbar() {
  const navigate = useNavigate();

  function handleLogout() {
    clearTokens();
    navigate('/login');
  }

  if (!isLoggedIn()) return null;

  return (
    <nav style={{ display: 'flex', gap: '1rem', padding: '1rem', borderBottom: '1px solid #ddd' }}>
      <Link to="/dashboard">Annonces</Link>
      <Link to="/criteria">Critères</Link>
      <Link to="/profile">Profil</Link>
      <button onClick={handleLogout} style={{ marginLeft: 'auto' }}>Déconnexion</button>
    </nav>
  );
}
