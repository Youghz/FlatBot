import { useEffect, useState } from 'react';
import { apiFetch } from '../api';

interface ListingEntry {
  listing_id: string;
  notified_at: string;
}

export default function Dashboard() {
  const [listings, setListings] = useState<ListingEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch('/listings?limit=50')
      .then(res => res.json())
      .then(data => {
        setListings(data.listings);
        setTotal(data.total);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Chargement...</p>;

  return (
    <div style={{ maxWidth: 800, margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Mes annonces</h1>
      <p>{total} annonce{total !== 1 ? 's' : ''} trouvée{total !== 1 ? 's' : ''}</p>
      {listings.length === 0 ? (
        <p style={{ color: '#666' }}>
          Aucune annonce pour le moment. Configurez vos <a href="/criteria">critères de recherche</a> et les annonces apparaîtront ici après le prochain scan.
        </p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {listings.map(l => (
            <li key={l.listing_id} style={{ padding: '0.75rem', borderBottom: '1px solid #eee' }}>
              <strong>{l.listing_id}</strong>
              <span style={{ color: '#666', marginLeft: '1rem' }}>
                {new Date(l.notified_at).toLocaleDateString('fr-CA')}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
