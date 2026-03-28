import { useCallback, useEffect, useState } from 'react';
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

type SortKey = 'notified_at' | 'price' | 'bedrooms' | 'neighbourhood' | 'source' | 'furnished' | 'parking' | 'move_in_date';
type SortDir = 'asc' | 'desc';

const PAGE_SIZE = 50;

function furnishedLabel(v: boolean | null): string {
  if (v === true) return 'Meublé';
  if (v === false) return 'Non meublé';
  return '?';
}

function parkingLabel(v: boolean | null): string {
  if (v === true) return 'Oui';
  if (v === false) return 'Non';
  return '?';
}

function furnishedSort(v: boolean | null): number {
  if (v === true) return 2;
  if (v === null) return 1;
  return 0;
}

export default function Dashboard() {
  const [allListings, setAllListings] = useState<ListingDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState<SortKey>('notified_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [filter, setFilter] = useState('');

  // Load all listings from the API (paginated server-side fetching)
  useEffect(() => {
    apiFetch('/listings?limit=200')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        setAllListings(data.listings);
        setTotal(data.total);
      })
      .finally(() => setLoading(false));
  }, []);

  // Sort
  const sorted = useCallback(() => {
    const filtered = filter
      ? allListings.filter(l => {
          const q = filter.toLowerCase();
          return (
            l.title.toLowerCase().includes(q) ||
            l.address.toLowerCase().includes(q) ||
            l.neighbourhood.toLowerCase().includes(q) ||
            l.source.toLowerCase().includes(q)
          );
        })
      : allListings;

    return [...filtered].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'price': cmp = a.price - b.price; break;
        case 'bedrooms': cmp = a.bedrooms - b.bedrooms; break;
        case 'neighbourhood': cmp = a.neighbourhood.localeCompare(b.neighbourhood); break;
        case 'source': cmp = a.source.localeCompare(b.source); break;
        case 'furnished': cmp = furnishedSort(a.furnished) - furnishedSort(b.furnished); break;
        case 'parking': cmp = furnishedSort(a.parking) - furnishedSort(b.parking); break;
        case 'move_in_date': cmp = a.move_in_date.localeCompare(b.move_in_date); break;
        case 'notified_at': default: cmp = a.notified_at.localeCompare(b.notified_at); break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [allListings, sortKey, sortDir, filter]);

  const sortedListings = sorted();
  const totalPages = Math.ceil(sortedListings.length / PAGE_SIZE);
  const pageListings = sortedListings.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir(key === 'price' || key === 'bedrooms' ? 'asc' : 'desc');
    }
    setPage(0);
  }

  function sortIcon(key: SortKey) {
    if (sortKey !== key) return '';
    return sortDir === 'asc' ? ' ▲' : ' ▼';
  }

  if (loading) return <div className="loading">Chargement...</div>;

  return (
    <div className="page" style={{ maxWidth: 1100 }}>
      <h1>Mes annonces</h1>

      <div className="table-toolbar">
        <span className="stats-bar" style={{ border: 'none', paddingBottom: 0, marginBottom: 0 }}>
          {total} annonce{total !== 1 ? 's' : ''} trouvée{total !== 1 ? 's' : ''}
          {filter && ` · ${sortedListings.length} affichée${sortedListings.length !== 1 ? 's' : ''}`}
        </span>
        <input
          type="text"
          placeholder="Filtrer par titre, adresse, quartier..."
          value={filter}
          onChange={e => { setFilter(e.target.value); setPage(0); }}
          className="table-filter"
        />
      </div>

      {sortedListings.length === 0 ? (
        <div className="empty-state">
          <p>{allListings.length === 0 ? 'Aucune annonce pour le moment.' : 'Aucun résultat pour ce filtre.'}</p>
          {allListings.length === 0 && (
            <p>Configurez vos <a href="/criteria">critères de recherche</a> et les annonces apparaîtront ici après le prochain scan.</p>
          )}
        </div>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="listings-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('notified_at')} className="sortable">Date{sortIcon('notified_at')}</th>
                  <th>Titre</th>
                  <th onClick={() => handleSort('price')} className="sortable">Prix{sortIcon('price')}</th>
                  <th onClick={() => handleSort('bedrooms')} className="sortable">Ch.{sortIcon('bedrooms')}</th>
                  <th onClick={() => handleSort('furnished')} className="sortable">Meublé{sortIcon('furnished')}</th>
                  <th onClick={() => handleSort('parking')} className="sortable">Parking{sortIcon('parking')}</th>
                  <th onClick={() => handleSort('neighbourhood')} className="sortable">Quartier{sortIcon('neighbourhood')}</th>
                  <th onClick={() => handleSort('move_in_date')} className="sortable">Emménagement{sortIcon('move_in_date')}</th>
                  <th onClick={() => handleSort('source')} className="sortable">Source{sortIcon('source')}</th>
                </tr>
              </thead>
              <tbody>
                {pageListings.map(l => (
                  <tr key={l.listing_id}>
                    <td className="cell-date">{l.notified_at.slice(0, 10)}</td>
                    <td>
                      <a href={l.url} target="_blank" rel="noopener noreferrer" className="listing-title">
                        {l.title || l.address}
                      </a>
                      <span className="cell-address">{l.address}</span>
                    </td>
                    <td className="cell-price">{l.price.toFixed(0)}$</td>
                    <td className="cell-center">{l.bedrooms}</td>
                    <td className={`cell-center${l.furnished === null ? ' unknown' : ''}`}>{furnishedLabel(l.furnished)}</td>
                    <td className={`cell-center${l.parking === null ? ' unknown' : ''}`}>{parkingLabel(l.parking)}</td>
                    <td>{l.neighbourhood}</td>
                    <td className="cell-date">{l.move_in_date}</td>
                    <td><span className="listing-tag source">{l.source}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button onClick={() => setPage(p => p - 1)} disabled={page === 0} className="btn-secondary">
                ← Précédent
              </button>
              <span className="page-info">
                Page {page + 1} / {totalPages}
              </span>
              <button onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1} className="btn-secondary">
                Suivant →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
