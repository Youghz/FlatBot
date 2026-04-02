import { Link, useNavigate } from 'react-router-dom';
import { isLoggedIn } from '../api';

const DEMO_LISTINGS = [
  { title: "5½ lumineux, Plateau-Mont-Royal", price: 2100, bedrooms: 3, neighbourhood: "Plateau", furnished: false, parking: true, move_in_date: "2026-07-01", source: "kijiji" },
  { title: "4½ renove, Villeray proche metro", price: 1650, bedrooms: 2, neighbourhood: "Villeray", furnished: true, parking: false, move_in_date: "2026-05-01", source: "centris" },
  { title: "3½ moderne, Griffintown", price: 1800, bedrooms: 1, neighbourhood: "Griffintown", furnished: false, parking: true, move_in_date: "immediate", source: "rentals" },
  { title: "5½ spacieux, Rosemont", price: 1950, bedrooms: 3, neighbourhood: "Rosemont", furnished: false, parking: false, move_in_date: "2026-07-01", source: "kijiji" },
  { title: "4½ meuble, Mile-End", price: 2300, bedrooms: 2, neighbourhood: "Mile-End", furnished: true, parking: true, move_in_date: "2026-06-01", source: "centris" },
];

export default function Landing() {
  const navigate = useNavigate();

  if (isLoggedIn()) {
    navigate('/dashboard', { replace: true });
    return null;
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
          et vous notifie sur Telegram des nouvelles annonces.
        </p>
        <div className="hero-cta">
          <Link to="/signup" className="btn-hero">Commencer gratuitement</Link>
          <Link to="/login" className="btn-hero-secondary">J'ai deja un compte</Link>
        </div>
      </section>

      <section className="demo-section">
        <h2>Apercu des annonces en temps reel</h2>
        <p className="demo-subtitle">Voici un extrait des dernieres annonces trouvees a Montreal</p>
        <div className="table-wrapper">
          <table className="listings-table">
            <thead>
              <tr>
                <th>Titre</th>
                <th>Prix</th>
                <th>Ch.</th>
                <th>Meuble</th>
                <th>Parking</th>
                <th>Quartier</th>
                <th>Emmenagement</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {DEMO_LISTINGS.map((l, i) => (
                <tr key={i}>
                  <td><span className="listing-title">{l.title}</span></td>
                  <td className="cell-price">{l.price}$</td>
                  <td className="cell-center">{l.bedrooms}</td>
                  <td className="cell-center">{l.furnished ? 'Oui' : 'Non'}</td>
                  <td className="cell-center">{l.parking ? 'Oui' : 'Non'}</td>
                  <td>{l.neighbourhood}</td>
                  <td className="cell-date">{l.move_in_date}</td>
                  <td><span className="listing-tag source">{l.source}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="demo-overlay">
          <Link to="/signup" className="btn-hero">Creer mon compte pour voir toutes les annonces</Link>
        </div>
      </section>

      <section className="how-it-works">
        <h2>Comment ca marche</h2>
        <div className="steps">
          <div className="step">
            <span className="step-number">1</span>
            <h3>Definissez vos criteres</h3>
            <p>Quartiers, budget, chambres, meuble, parking, date d'emmenagement.</p>
          </div>
          <div className="step">
            <span className="step-number">2</span>
            <h3>Connectez Telegram</h3>
            <p>Liez votre compte en un clic pour recevoir les notifications.</p>
          </div>
          <div className="step">
            <span className="step-number">3</span>
            <h3>Recevez les annonces</h3>
            <p>Toutes les heures, FlatBot vous envoie les nouvelles annonces.</p>
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
