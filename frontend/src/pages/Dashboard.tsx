import { useEffect, useState } from 'react';
import { apiFetch } from '../api';

interface ListingDetail {
  listing_id: string;
  source: string;
  title: string;
  price: number;
  url: string;
  address: string;
  neighbourhood: string;
  bedrooms: number;
  furnished: boolean | null;
  parking: boolean | null;
  description: string;
  move_in_date: string;
  notified_at: string;
}

export default function Dashboard() {
  const [listings, setListings] = useState<ListingDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch('/listings?limit=50')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        setListings(data.listings);
        setTotal(data.total);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Chargement...</div>;

  return (
    <div className="page">
      <h1>Mes annonces</h1>
      <p className="stats-bar">
        {total} annonce{total !== 1 ? 's' : ''} trouvée{total !== 1 ? 's' : ''}
      </p>

      {listings.length === 0 ? (
        <div className="empty-state">
          <p>Aucune annonce pour le moment.</p>
          <p>Configurez vos <a href="/criteria">critères de recherche</a> et les annonces apparaîtront ici après le prochain scan.</p>
        </div>
      ) : (
        listings.map(l => (
          <div key={l.listing_id} className="listing-card">
            <div className="listing-header">
              <div>
                <a href={l.url} target="_blank" rel="noopener noreferrer" className="listing-title">
                  {l.title || l.address}
                </a>
                <p className="listing-address">{l.address}</p>
              </div>
              <span className="listing-price">{l.price.toFixed(0)}$/mo</span>
            </div>
            <div className="listing-meta">
              <span className="listing-tag">{l.bedrooms} ch.</span>
              <span className={`listing-tag${l.furnished === null ? ' unknown' : ''}`}>
                {l.furnished === true ? 'Meublé' : l.furnished === false ? 'Non meublé' : 'Meublé ?'}
              </span>
              <span className={`listing-tag${l.parking === null ? ' unknown' : ''}`}>
                {l.parking === true ? 'Parking' : l.parking === false ? 'Pas de parking' : 'Parking ?'}
              </span>
              {l.neighbourhood && <span className="listing-tag">{l.neighbourhood}</span>}
              {l.move_in_date && <span className="listing-tag">{l.move_in_date}</span>}
              <span className="listing-tag source">{l.source}</span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
