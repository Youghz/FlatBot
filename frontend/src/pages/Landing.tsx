import { Link, useNavigate } from 'react-router-dom';
import { isLoggedIn } from '../api';

const DEMO_LISTINGS = [
  { title: "5½ lumineux, rénové, proche métro", price: 2100, bedrooms: 3, neighbourhood: "Plateau", move_in_date: "2026-07-01", source: "kijiji", age: "2 min" },
  { title: "4½ tout inclus, balcon sud", price: 1650, bedrooms: 2, neighbourhood: "Villeray", move_in_date: "2026-05-01", source: "centris", age: "18 min" },
  { title: "3½ moderne, vue sur le canal", price: 1800, bedrooms: 1, neighbourhood: "Griffintown", move_in_date: "immédiat", source: "rentals", age: "34 min" },
  { title: "5½ spacieux avec cour arrière", price: 1950, bedrooms: 3, neighbourhood: "Rosemont", move_in_date: "2026-07-01", source: "kijiji", age: "51 min" },
  { title: "4½ meublé, terrasse, Mile-End", price: 2300, bedrooms: 2, neighbourhood: "Mile-End", move_in_date: "2026-06-01", source: "centris", age: "1h" },
];

const TELEGRAM_PREVIEW = `
🏠 3 nouveaux logements

5½ lumineux, rénové, proche métro
💰 2 100$/mois  •  🛏 3 ch.
📍 Rue Saint-Denis, Plateau-Mont-Royal
🛋 Non meublé • 🅿️ Parking
📅 Emménagement : 2026-07-01
🔗 Voir l'annonce  (kijiji)

4½ tout inclus, balcon sud
💰 1 650$/mois  •  🛏 2 ch.
📍 Rue Jarry, Villeray
🛋 Meublé • 🚫 Pas de parking
📅 Emménagement : 2026-05-01
🔗 Voir l'annonce  (centris)

3½ moderne, vue sur le canal
💰 1 800$/mois  •  🛏 1 ch.
📍 Rue Basin, Griffintown
📦 Non meublé • 🅿️ Parking
🔑 Disponible maintenant
🔗 Voir l'annonce  (rentals)
`.trim();

export default function Landing() {
  const navigate = useNavigate();

  if (isLoggedIn()) {
    navigate('/dashboard', { replace: true });
    return null;
  }

  return (
    <div className="landing">
      <section className="hero">
        <p className="hero-tag">Recherche d'appartements à Montréal</p>
        <h1 className="hero-title">
          Ne ratez plus
          <span className="hero-accent"> aucune annonce</span>
        </h1>
        <p className="hero-subtitle">
          Les meilleurs appartements partent en quelques heures.
          FlatBot surveille Kijiji, Centris et Rentals.ca pour vous
          et vous alerte sur Telegram dès qu'une annonce correspond à vos critères.
        </p>
        <div className="hero-cta">
          <Link to="/signup" className="btn-hero">Commencer — c'est gratuit</Link>
          <Link to="/login" className="btn-hero-secondary">J'ai déjà un compte</Link>
        </div>
      </section>

      <section className="pain-points">
        <div className="pain-grid">
          <div className="pain-card">
            <span className="pain-icon">X</span>
            <p>Passer des heures à rafraîchir Kijiji, Centris, Rentals.ca</p>
          </div>
          <div className="pain-card">
            <span className="pain-icon">X</span>
            <p>Découvrir une annonce parfaite déjà louée</p>
          </div>
          <div className="pain-card">
            <span className="pain-icon">X</span>
            <p>Oublier de vérifier un des trois sites</p>
          </div>
        </div>
      </section>

      <section className="telegram-section">
        <h2>Recevez les annonces directement sur Telegram</h2>
        <p className="demo-subtitle">Chaque heure, FlatBot vous envoie les nouvelles annonces qui correspondent à vos critères</p>
        <div className="telegram-mockup">
          <div className="telegram-header">
            <span className="telegram-avatar">F</span>
            <div>
              <strong>FlatBot</strong>
              <span className="telegram-status">bot</span>
            </div>
          </div>
          <div className="telegram-messages">
            <div className="telegram-bubble">
              <pre className="telegram-text">{TELEGRAM_PREVIEW}</pre>
              <span className="telegram-time">14:32</span>
            </div>
          </div>
        </div>
      </section>

      <section className="demo-section">
        <h2>Toutes vos annonces dans un tableau</h2>
        <p className="demo-subtitle">Filtrez, triez et réagissez en un clic</p>
        <div className="table-wrapper">
          <table className="listings-table">
            <thead>
              <tr>
                <th>Il y a</th>
                <th>Titre</th>
                <th>Prix</th>
                <th>Ch.</th>
                <th>Quartier</th>
                <th>Emménagement</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {DEMO_LISTINGS.map((l, i) => (
                <tr key={i}>
                  <td className="cell-date cell-fresh">{l.age}</td>
                  <td><span className="listing-title">{l.title}</span></td>
                  <td className="cell-price">{l.price}$/mo</td>
                  <td className="cell-center">{l.bedrooms}</td>
                  <td>{l.neighbourhood}</td>
                  <td className="cell-date">{l.move_in_date}</td>
                  <td><span className="listing-tag source">{l.source}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="demo-overlay">
          <Link to="/signup" className="btn-hero">Voir les vraies annonces</Link>
        </div>
      </section>

      <section className="how-it-works">
        <h2>3 minutes pour tout configurer</h2>
        <div className="steps">
          <div className="step">
            <span className="step-number">1</span>
            <h3>Vos critères</h3>
            <p>Quartiers, budget, nombre de chambres, meublé ou non, parking.</p>
          </div>
          <div className="step">
            <span className="step-number">2</span>
            <h3>Telegram</h3>
            <p>Liez votre compte en un clic. Chaque nouvelle annonce arrive directement sur votre téléphone.</p>
          </div>
          <div className="step">
            <span className="step-number">3</span>
            <h3>Réagissez vite</h3>
            <p>Soyez le premier à contacter le proprio. Plus besoin de surveiller 3 sites.</p>
          </div>
        </div>
      </section>

      <section className="stats-section">
        <div className="stats-grid">
          <div className="stat">
            <span className="stat-number">3</span>
            <span className="stat-label">sites surveillés</span>
          </div>
          <div className="stat">
            <span className="stat-number">1h</span>
            <span className="stat-label">fréquence de scan</span>
          </div>
          <div className="stat">
            <span className="stat-number">28</span>
            <span className="stat-label">quartiers couverts</span>
          </div>
        </div>
      </section>

      <section className="final-cta">
        <h2>Arrêtez de chercher. Laissez les annonces venir à vous.</h2>
        <Link to="/signup" className="btn-hero">Créer mon compte gratuitement</Link>
      </section>

      <footer className="landing-footer">
        <p>FlatBot — Montréal, QC</p>
      </footer>
    </div>
  );
}
