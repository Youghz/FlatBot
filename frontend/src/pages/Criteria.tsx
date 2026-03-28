import { type FormEvent, useEffect, useState } from 'react';
import { apiFetch } from '../api';

const AVAILABLE_NEIGHBOURHOODS: Record<string, string[]> = {
  'Villeray': ['villeray', 'saint-michel', 'parc-extension', 'parc extension'],
  'Mile-Ex': ['mile-ex', 'mile ex', 'marconi-alexandra'],
  'Mile-End': ['mile-end', 'mile end'],
  'Plateau': ['plateau', 'plateau-mont-royal', 'plateau mont-royal'],
  'Petite-Patrie': ['petite-patrie', 'petite patrie', 'la petite-patrie'],
  'Rosemont': ['rosemont'],
  'Petite-Italie': ['petite-italie', 'petite italie', 'little italy', 'jean-talon'],
  'Ahuntsic': ['ahuntsic', 'cartierville', 'sault-au-récollet'],
};

export default function Criteria() {
  const [selectedHoods, setSelectedHoods] = useState<Set<string>>(new Set());
  const [priceMin, setPriceMin] = useState(1000);
  const [priceMax, setPriceMax] = useState(3000);
  const [bedroomsMin, setBedroomsMin] = useState(1);
  const [bedroomsMax, setBedroomsMax] = useState<number | ''>('');
  const [furnished, setFurnished] = useState(false);
  const [parking, setParking] = useState(false);
  const [moveInAfter, setMoveInAfter] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch('/criteria')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        const hoods = Object.keys(data.neighbourhoods || {});
        setSelectedHoods(new Set(hoods));
        setPriceMin(data.price_min);
        setPriceMax(data.price_max);
        setBedroomsMin(data.bedrooms_min);
        setBedroomsMax(data.bedrooms_max ?? '');
        setFurnished(data.furnished);
        setParking(data.parking);
        setMoveInAfter(data.move_in_after || '');
      })
      .finally(() => setLoading(false));
  }, []);

  function toggleHood(name: string) {
    setSelectedHoods(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
    setSaved(false);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaved(false);

    const neighbourhoods: Record<string, string[]> = {};
    for (const name of selectedHoods) {
      neighbourhoods[name] = AVAILABLE_NEIGHBOURHOODS[name] || [name.toLowerCase()];
    }

    await apiFetch('/criteria', {
      method: 'PUT',
      body: JSON.stringify({
        neighbourhoods,
        price_min: priceMin,
        price_max: priceMax,
        bedrooms_min: bedroomsMin,
        bedrooms_max: bedroomsMax || null,
        furnished,
        parking,
        move_in_after: moveInAfter || null,
      }),
    });
    setSaving(false);
    setSaved(true);
  }

  if (loading) return <div className="loading">Chargement...</div>;

  return (
    <div className="page-medium">
      <h1>Critères de recherche</h1>
      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>Quartiers</legend>
          <div className="hood-grid">
            {Object.keys(AVAILABLE_NEIGHBOURHOODS).map(name => (
              <label key={name} className="hood-chip">
                <input type="checkbox" checked={selectedHoods.has(name)} onChange={() => toggleHood(name)} />
                {name}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="form-row">
          <div className="form-group">
            <label>Prix min ($)</label>
            <input type="number" value={priceMin} onChange={e => setPriceMin(+e.target.value)} />
          </div>
          <div className="form-group">
            <label>Prix max ($)</label>
            <input type="number" value={priceMax} onChange={e => setPriceMax(+e.target.value)} />
          </div>
          <div className="form-group">
            <label>Chambres min</label>
            <input type="number" value={bedroomsMin} onChange={e => setBedroomsMin(+e.target.value)} min={0} />
          </div>
          <div className="form-group">
            <label>Chambres max</label>
            <input type="number" value={bedroomsMax} onChange={e => setBedroomsMax(e.target.value ? +e.target.value : '')} min={0} placeholder="Illimité" />
          </div>
        </div>

        <div className="option-row">
          <label className="option-label">
            <input type="checkbox" checked={furnished} onChange={e => setFurnished(e.target.checked)} />
            Meublé uniquement
          </label>
          <label className="option-label">
            <input type="checkbox" checked={parking} onChange={e => setParking(e.target.checked)} />
            Parking requis
          </label>
        </div>

        <div className="form-group">
          <label>Emménagement après le</label>
          <input type="date" value={moveInAfter} onChange={e => setMoveInAfter(e.target.value)} />
        </div>

        <button type="submit" disabled={saving} className="btn-full" style={{ marginTop: '0.5rem' }}>
          {saving ? 'Enregistrement...' : 'Sauvegarder'}
        </button>
        {saved && <p className="success-msg" style={{ marginTop: '0.5rem' }}>Critères sauvegardés</p>}
      </form>
    </div>
  );
}
