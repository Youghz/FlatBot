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
  furnished: boolean;
  parking: boolean;
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

  if (loading) return <p>Chargement...</p>;

  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Mes annonces</h1>
      <p>{total} annonce{total !== 1 ? 's' : ''} trouvée{total !== 1 ? 's' : ''}</p>
      {listings.length === 0 ? (
        <p style={{ color: '#666' }}>
          Aucune annonce pour le moment. Configurez vos <a href="/criteria">critères de recherche</a> et les annonces apparaîtront ici après le prochain scan.
        </p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {listings.map(l => (
            <div key={l.listing_id} style={{ border: '1px solid #ddd', borderRadius: 8, padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <a href={l.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
                    {l.title || l.address}
                  </a>
                  <p style={{ margin: '0.25rem 0', color: '#444' }}>{l.address}</p>
                </div>
                <span style={{ fontWeight: 'bold', fontSize: '1.2rem', whiteSpace: 'nowrap' }}>
                  {l.price.toFixed(0)}$/mois
                </span>
              </div>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', color: '#666', fontSize: '0.9rem', flexWrap: 'wrap' }}>
                <span>{l.bedrooms} chambre{l.bedrooms !== 1 ? 's' : ''}</span>
                <span>{l.furnished ? 'Meublé' : 'Non meublé'}</span>
                <span>{l.parking ? 'Parking' : 'Pas de parking'}</span>
                {l.neighbourhood && <span>{l.neighbourhood}</span>}
                {l.move_in_date && <span>Emménagement: {l.move_in_date}</span>}
                <span style={{ marginLeft: 'auto' }}>{l.source}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
