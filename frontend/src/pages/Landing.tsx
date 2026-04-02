import { Link, useNavigate } from 'react-router-dom';
import { isLoggedIn } from '../api';

const DEMO_LISTINGS = [
  { title: "5½ lumineux, renove, proche metro", price: 2100, bedrooms: 3, neighbourhood: "Plateau", move_in_date: "2026-07-01", source: "kijiji", age: "2 min" },
  { title: "4½ tout inclus, balcon sud", price: 1650, bedrooms: 2, neighbourhood: "Villeray", move_in_date: "2026-05-01", source: "centris", age: "18 min" },
  { title: "3½ moderne, vue sur le canal", price: 1800, bedrooms: 1, neighbourhood: "Griffintown", move_in_date: "immediate", source: "rentals", age: "34 min" },
  { title: "5½ spacieux avec cour arriere", price: 1950, bedrooms: 3, neighbourhood: "Rosemont", move_in_date: "2026-07-01", source: "kijiji", age: "51 min" },
  { title: "4½ meuble, terrasse, Mile-End", price: 2300, bedrooms: 2, neighbourhood: "Mile-End", move_in_date: "2026-06-01", source: "centris", age: "1h" },
];

const TELEGRAM_PREVIEW = `
🏠 3 nouveaux logements

5½ lumineux, renove, proche metro
💰 2 100$/mois  •  🛏 3 ch.
📍 Rue Saint-Denis, Plateau-Mont-Royal
🛋 Non meuble • 🅿️ Parking
📅 Emmenagement: 2026-07-01
🔗 Voir l'annonce  (kijiji)

4½ tout inclus, balcon sud
💰 1 650$/mois  •  🛏 2 ch.
📍 Rue Jarry, Villeray
🛋 Meuble • 🚫 Pas de parking
📅 Emmenagement: 2026-05-01
🔗 Voir l'annonce  (centris)

3½ moderne, vue sur le canal
💰 1 800$/mois  •  🛏 1 ch.
📍 Rue Basin, Griffintown
📦 Non meuble • 🅿️ Parking
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
        <p className="hero-tag">Recherche d'appartements a Montreal</p>
        <h1 className="hero-title">
          Ne ratez plus
          <span className="hero-accent"> aucune annonce</span>
        </h1>
        <p className="hero-subtitle">
          Les meilleurs appartements partent en quelques heures.
          FlatBot surveille Kijiji, Centris et Rentals.ca pour vous
          et vous alerte sur Telegram des qu'une annonce correspond a vos criteres.
        </p>
        <div className="hero-cta">
          <Link to="/signup" className="btn-hero">Commencer — c'est gratuit</Link>
          <Link to="/login" className="btn-hero-secondary">J'ai deja un compte</Link>
        </div>
      </section>

      <section className="pain-points">
        <div className="pain-grid">
          <div className="pain-card">
            <span className="pain-icon">X</span>
            <p>Passer des heures a rafraichir Kijiji, Centris, Rentals.ca</p>
          </div>
          <div className="pain-card">
            <span className="pain-icon">X</span>
            <p>Decouvrir une annonce parfaite deja louee</p>
          </div>
          <div className="pain-card">
            <span className="pain-icon">X</span>
            <p>Oublier de verifier un des trois sites</p>
          </div>
        </div>
      </section>

      <section className="telegram-section">
        <h2>Recevez les annonces directement sur Telegram</h2>
        <p className="demo-subtitle">Chaque heure, FlatBot vous envoie les nouvelles annonces qui matchent vos criteres</p>
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
        <p className="demo-subtitle">Filtrez, triez, et reagissez en un clic</p>
        <div className="table-wrapper">
          <table className="listings-table">
            <thead>
              <tr>
                <th>Il y a</th>
                <th>Titre</th>
                <th>Prix</th>
                <th>Ch.</th>
                <th>Quartier</th>
                <th>Emmenagement</th>
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
            <h3>Vos criteres</h3>
            <p>Quartiers, budget, nombre de chambres, meuble ou non, parking.</p>
          </div>
          <div className="step">
            <span className="step-number">2</span>
            <h3>Telegram</h3>
            <p>Liez votre compte en un clic. Chaque nouvelle annonce arrive directement sur votre telephone.</p>
          </div>
          <div className="step">
            <span className="step-number">3</span>
            <h3>Reagissez vite</h3>
            <p>Soyez le premier a contacter le proprio. Plus besoin de surveiller 3 sites.</p>
          </div>
        </div>
      </section>

      <section className="stats-section">
        <div className="stats-grid">
          <div className="stat">
            <span className="stat-number">3</span>
            <span className="stat-label">sites surveilles</span>
          </div>
          <div className="stat">
            <span className="stat-number">150+</span>
            <span className="stat-label">annonces scrapees / heure</span>
          </div>
          <div className="stat">
            <span className="stat-number">28</span>
            <span className="stat-label">quartiers couverts</span>
          </div>
        </div>
      </section>

      <section className="final-cta">
        <h2>Arretez de chercher. Laissez les annonces venir a vous.</h2>
        <Link to="/signup" className="btn-hero">Creer mon compte gratuitement</Link>
      </section>

      <footer className="landing-footer">
        <p>FlatBot — Montreal, QC</p>
      </footer>
    </div>
  );
}
