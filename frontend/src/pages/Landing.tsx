import { Link } from 'react-router-dom';
import { isLoggedIn } from '../api';

export default function Landing() {
  if (isLoggedIn()) {
    return <meta httpEquiv="refresh" content="0;url=/dashboard" />;
  }

  return (
    <div className="landing">
      <section className="hero">
        <h1 className="hero-title">
          Trouvez votre appartement
          <span className="hero-accent"> sans effort</span>
        </h1>
        <p className="hero-subtitle">
          FlatBot scrape Kijiji, Centris et Rentals.ca toutes les heures
          et vous notifie sur Telegram quand une annonce correspond a vos criteres.
        </p>
        <div className="hero-cta">
          <Link to="/signup" className="btn-hero">Commencer gratuitement</Link>
          <Link to="/login" className="btn-hero-secondary">Se connecter</Link>
        </div>
      </section>

      <section className="how-it-works">
        <h2>Comment ca marche</h2>
        <div className="steps">
          <div className="step">
            <span className="step-number">1</span>
            <h3>Definissez vos criteres</h3>
            <p>Quartiers, budget, chambres, meuble ou non, parking, date d'emmenagement.</p>
          </div>
          <div className="step">
            <span className="step-number">2</span>
            <h3>Connectez Telegram</h3>
            <p>Liez votre compte en un clic pour recevoir les notifications en temps reel.</p>
          </div>
          <div className="step">
            <span className="step-number">3</span>
            <h3>Recevez les annonces</h3>
            <p>Toutes les heures, FlatBot vous envoie les nouvelles annonces qui matchent.</p>
          </div>
        </div>
      </section>

      <section className="sources">
        <h2>3 sources, un seul endroit</h2>
        <div className="source-list">
          <div className="source-card">
            <strong>Kijiji</strong>
            <p>Annonces de particuliers et professionnels</p>
          </div>
          <div className="source-card">
            <strong>Centris</strong>
            <p>Courtiers immobiliers du Quebec</p>
          </div>
          <div className="source-card">
            <strong>Rentals.ca</strong>
            <p>Immeubles locatifs et condos</p>
          </div>
        </div>
      </section>

      <section className="final-cta">
        <h2>Pret a trouver votre prochain chez-vous ?</h2>
        <Link to="/signup" className="btn-hero">Creer mon compte</Link>
      </section>

      <footer className="landing-footer">
        <p>FlatBot — Recherche d'appartements a Montreal</p>
      </footer>
    </div>
  );
}
