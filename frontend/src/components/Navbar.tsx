import { Link, useLocation, useNavigate } from 'react-router-dom';
import { clearTokens, isLoggedIn } from '../api';

export default function Navbar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const loggedIn = isLoggedIn();

  // Hide navbar on landing page
  if (pathname === '/' && !loggedIn) return null;

  return (
    <nav className="navbar">
      <Link to={loggedIn ? '/dashboard' : '/'} className="logo">FlatBot</Link>
      {loggedIn ? (
        <>
          <Link to="/dashboard" className={pathname === '/dashboard' ? 'active' : ''}>Annonces</Link>
          <Link to="/criteria" className={pathname === '/criteria' ? 'active' : ''}>Critères</Link>
          <Link to="/profile" className={pathname === '/profile' ? 'active' : ''}>Profil</Link>
          <button onClick={() => { clearTokens(); navigate('/'); }}>Déconnexion</button>
        </>
      ) : (
        <>
          <Link to="/login" className="btn-hero-secondary" style={{ marginLeft: 'auto', padding: '0.3rem 1rem', fontSize: '0.85rem' }}>Se connecter</Link>
          <Link to="/signup" className="btn-hero" style={{ padding: '0.3rem 1rem', fontSize: '0.85rem' }}>S'inscrire</Link>
        </>
      )}
    </nav>
  );
}
