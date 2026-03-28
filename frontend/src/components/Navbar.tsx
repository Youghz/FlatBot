import { Link, useLocation, useNavigate } from 'react-router-dom';
import { clearTokens, isLoggedIn } from '../api';

export default function Navbar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  if (!isLoggedIn()) return null;

  return (
    <nav className="navbar">
      <span className="logo">FlatBot</span>
      <Link to="/dashboard" className={pathname === '/dashboard' ? 'active' : ''}>Annonces</Link>
      <Link to="/criteria" className={pathname === '/criteria' ? 'active' : ''}>Critères</Link>
      <Link to="/profile" className={pathname === '/profile' ? 'active' : ''}>Profil</Link>
      <button onClick={() => { clearTokens(); navigate('/login'); }}>Déconnexion</button>
    </nav>
  );
}
