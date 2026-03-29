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
  furnished: boolean;
  parking: boolean;
  description: string;
  move_in_date: string;
  published_date: string;
  surface_sqft: number;
  notified_at: string;
}

interface EditState {
  price: number;
  bedrooms: number;
  furnished: boolean;
  parking: boolean;
  neighbourhood: string;
  move_in_date: string;
  surface_sqft: number;
}

type SortKey = 'published_date' | 'price' | 'bedrooms' | 'neighbourhood' | 'source' | 'furnished' | 'parking' | 'move_in_date' | 'surface_sqft';
type SortDir = 'asc' | 'desc';

const PAGE_SIZE = 50;

export default function Dashboard() {
  const [allListings, setAllListings] = useState<ListingDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState<SortKey>('published_date');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [filter, setFilter] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editState, setEditState] = useState<EditState | null>(null);
  const [saving, setSaving] = useState(false);

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
        case 'surface_sqft': cmp = a.surface_sqft - b.surface_sqft; break;
        case 'neighbourhood': cmp = a.neighbourhood.localeCompare(b.neighbourhood); break;
        case 'source': cmp = a.source.localeCompare(b.source); break;
        case 'furnished': cmp = Number(a.furnished) - Number(b.furnished); break;
        case 'parking': cmp = Number(a.parking) - Number(b.parking); break;
        case 'move_in_date': cmp = a.move_in_date.localeCompare(b.move_in_date); break;
        case 'published_date': default: {
          const da = a.published_date || a.notified_at;
          const db = b.published_date || b.notified_at;
          cmp = da.localeCompare(db);
          break;
        }
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
      setSortDir(key === 'price' || key === 'bedrooms' || key === 'surface_sqft' ? 'asc' : 'desc');
    }
    setPage(0);
  }

  function sortIcon(key: SortKey) {
    if (sortKey !== key) return '';
    return sortDir === 'asc' ? ' \u25B2' : ' \u25BC';
  }

  function startEdit(listing: ListingDetail) {
    setEditingId(listing.listing_id);
    setEditState({
      price: listing.price,
      bedrooms: listing.bedrooms,
      furnished: listing.furnished,
      parking: listing.parking,
      neighbourhood: listing.neighbourhood,
      move_in_date: listing.move_in_date,
      surface_sqft: listing.surface_sqft,
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setEditState(null);
  }

  async function saveEdit() {
    if (!editingId || !editState) return;
    setSaving(true);
    const res = await apiFetch(`/listings/${editingId}`, {
      method: 'PATCH',
      body: JSON.stringify(editState),
    });
    if (res.ok) {
      const updated = await res.json();
      setAllListings(prev => prev.map(l => l.listing_id === editingId ? { ...l, ...updated } : l));
      setEditingId(null);
      setEditState(null);
    }
    setSaving(false);
  }

  if (loading) return <div className="loading">Chargement...</div>;

  return (
    <div className="page" style={{ maxWidth: 1200 }}>
      <h1>Mes annonces</h1>

      <div className="table-toolbar">
        <span className="stats-bar" style={{ border: 'none', paddingBottom: 0, marginBottom: 0 }}>
          {total} annonce{total !== 1 ? 's' : ''} trouv&eacute;e{total !== 1 ? 's' : ''}
          {filter && ` \u00B7 ${sortedListings.length} affich\u00E9e${sortedListings.length !== 1 ? 's' : ''}`}
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
          <p>{allListings.length === 0 ? 'Aucune annonce pour le moment.' : 'Aucun r\u00E9sultat pour ce filtre.'}</p>
          {allListings.length === 0 && (
            <p>Configurez vos <a href="/criteria">crit&egrave;res de recherche</a> et les annonces appara&icirc;tront ici apr&egrave;s le prochain scan.</p>
          )}
        </div>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="listings-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('published_date')} className="sortable">Publi&eacute;e{sortIcon('published_date')}</th>
                  <th>Titre</th>
                  <th onClick={() => handleSort('price')} className="sortable">Prix{sortIcon('price')}</th>
                  <th onClick={() => handleSort('surface_sqft')} className="sortable">Surface{sortIcon('surface_sqft')}</th>
                  <th onClick={() => handleSort('bedrooms')} className="sortable">Ch.{sortIcon('bedrooms')}</th>
                  <th onClick={() => handleSort('furnished')} className="sortable">Meubl&eacute;{sortIcon('furnished')}</th>
                  <th onClick={() => handleSort('parking')} className="sortable">Parking{sortIcon('parking')}</th>
                  <th onClick={() => handleSort('neighbourhood')} className="sortable">Quartier{sortIcon('neighbourhood')}</th>
                  <th onClick={() => handleSort('move_in_date')} className="sortable">Emm&eacute;nagement{sortIcon('move_in_date')}</th>
                  <th onClick={() => handleSort('source')} className="sortable">Source{sortIcon('source')}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {pageListings.map(l => {
                  const isEditing = editingId === l.listing_id;
                  const ed = isEditing ? editState! : null;
                  return (
                    <tr key={l.listing_id} className={isEditing ? 'editing-row' : ''}>
                      <td className="cell-date">{(l.published_date || l.notified_at).slice(0, 10)}</td>
                      <td>
                        <a href={l.url} target="_blank" rel="noopener noreferrer" className="listing-title">
                          {l.title || l.address}
                        </a>
                        <span className="cell-address">{l.address}</span>
                      </td>
                      <td className="cell-price">
                        {isEditing ? (
                          <input type="number" className="edit-input edit-num" value={ed!.price} onChange={e => setEditState({ ...ed!, price: +e.target.value })} />
                        ) : `${l.price.toFixed(0)}$`}
                      </td>
                      <td className="cell-center">
                        {isEditing ? (
                          <input type="number" className="edit-input edit-num" value={ed!.surface_sqft} onChange={e => setEditState({ ...ed!, surface_sqft: +e.target.value })} />
                        ) : l.surface_sqft ? `${l.surface_sqft}` : '-'}
                      </td>
                      <td className="cell-center">
                        {isEditing ? (
                          <input type="number" className="edit-input edit-num" value={ed!.bedrooms} min={1} onChange={e => setEditState({ ...ed!, bedrooms: +e.target.value })} />
                        ) : l.bedrooms}
                      </td>
                      <td className="cell-center">
                        {isEditing ? (
                          <input type="checkbox" checked={ed!.furnished} onChange={e => setEditState({ ...ed!, furnished: e.target.checked })} />
                        ) : l.furnished ? 'Oui' : 'Non'}
                      </td>
                      <td className="cell-center">
                        {isEditing ? (
                          <input type="checkbox" checked={ed!.parking} onChange={e => setEditState({ ...ed!, parking: e.target.checked })} />
                        ) : l.parking ? 'Oui' : 'Non'}
                      </td>
                      <td>
                        {isEditing ? (
                          <input type="text" className="edit-input" value={ed!.neighbourhood} onChange={e => setEditState({ ...ed!, neighbourhood: e.target.value })} />
                        ) : l.neighbourhood}
                      </td>
                      <td className="cell-date">
                        {isEditing ? (
                          <input type="text" className="edit-input" value={ed!.move_in_date} placeholder="YYYY-MM-DD" onChange={e => setEditState({ ...ed!, move_in_date: e.target.value })} />
                        ) : l.move_in_date}
                      </td>
                      <td><span className="listing-tag source">{l.source}</span></td>
                      <td className="cell-actions">
                        {isEditing ? (
                          <div className="edit-actions">
                            <button onClick={saveEdit} disabled={saving} className="btn-save">{saving ? '...' : '\u2713'}</button>
                            <button onClick={cancelEdit} className="btn-cancel">\u2715</button>
                          </div>
                        ) : (
                          <button onClick={() => startEdit(l)} className="btn-edit" title="Modifier">\u270E</button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button onClick={() => setPage(p => p - 1)} disabled={page === 0} className="btn-secondary">
                \u2190 Pr&eacute;c&eacute;dent
              </button>
              <span className="page-info">
                Page {page + 1} / {totalPages}
              </span>
              <button onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1} className="btn-secondary">
                Suivant \u2192
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
