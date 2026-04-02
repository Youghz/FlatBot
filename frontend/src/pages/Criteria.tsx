import { type FormEvent, useEffect, useState } from 'react';
import { apiFetch } from '../api';

// Montreal boroughs + Greater Montreal cities
const AVAILABLE_NEIGHBOURHOODS: Record<string, string[]> = {
  // --- Ile de Montreal ---
  'Ahuntsic-Cartierville': ['ahuntsic', 'cartierville', 'sault-au-récollet'],
  'Anjou': ['anjou'],
  'CDN-NDG': ['côte-des-neiges', 'cote-des-neiges', 'notre-dame-de-grâce', 'ndg'],
  'Lachine': ['lachine'],
  'LaSalle': ['lasalle', 'la salle'],
  'Plateau-Mont-Royal': ['plateau', 'plateau-mont-royal', 'mile-end', 'mile end', 'mile-ex', 'mile ex'],
  'Le Sud-Ouest': ['sud-ouest', 'griffintown', 'saint-henri', 'petite-bourgogne', 'pointe-saint-charles'],
  'Mercier-Hochelaga': ['mercier', 'hochelaga', 'hochelaga-maisonneuve', 'maisonneuve'],
  'Montréal-Nord': ['montréal-nord', 'montreal-nord'],
  'Outremont': ['outremont'],
  'Pierrefonds-Roxboro': ['pierrefonds', 'roxboro'],
  'RDP-PAT': ['rivière-des-prairies', 'rdp', 'pointe-aux-trembles'],
  'Rosemont-Petite-Patrie': ['rosemont', 'petite-patrie', 'petite patrie', 'petite-italie', 'little italy'],
  'Saint-Laurent': ['saint-laurent', 'st-laurent'],
  'Saint-Léonard': ['saint-léonard', 'saint-leonard'],
  'Verdun': ['verdun', 'île-des-soeurs', 'ile-des-soeurs'],
  'Ville-Marie': ['ville-marie', 'centre-ville', 'downtown', 'vieux-montréal', 'quartier latin'],
  'Villeray-Saint-Michel-PE': ['villeray', 'saint-michel', 'parc-extension', 'parc extension'],
  // --- Villes liées ---
  'Westmount': ['westmount'],
  'Mont-Royal': ['mont-royal', 'tmr'],
  'Côte-Saint-Luc': ['côte-saint-luc', 'cote-saint-luc'],
  'Dorval': ['dorval'],
  'Pointe-Claire': ['pointe-claire'],
  'DDO': ['dollard-des-ormeaux', 'ddo'],
  'Laval': ['laval', 'chomedey', 'laval-des-rapides', 'vimont', 'sainte-dorothée', 'fabreville', 'sainte-rose'],
  'Longueuil': ['longueuil', 'saint-hubert', 'greenfield park'],
  'Brossard': ['brossard'],
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
  const [dirty, setDirty] = useState(false);

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

  function markDirty() {
    setDirty(true);
    setSaved(false);
  }

  function toggleHood(name: string) {
    setSelectedHoods(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
    markDirty();
  }

  function selectAllHoods() {
    setSelectedHoods(new Set(Object.keys(AVAILABLE_NEIGHBOURHOODS)));
    markDirty();
  }

  function clearAllHoods() {
    setSelectedHoods(new Set());
    markDirty();
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
    setDirty(false);
  }

  if (loading) return <div className="loading">Chargement...</div>;

  const allNames = Object.keys(AVAILABLE_NEIGHBOURHOODS);
  const allSelected = selectedHoods.size === allNames.length;
  const noneSelected = selectedHoods.size === 0;

  return (
    <div className="page-medium">
      <h1>Critères de recherche</h1>

      {noneSelected && !dirty && (
        <div className="criteria-banner warning">
          Aucun quartier sélectionné — le scraper ne cherchera aucune annonce.
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>
            Quartiers
            <span className="legend-count">{selectedHoods.size}/{allNames.length}</span>
          </legend>

          <div className="hood-actions">
            <button type="button" onClick={selectAllHoods} className="btn-link" disabled={allSelected}>Tout sélectionner</button>
            <button type="button" onClick={clearAllHoods} className="btn-link" disabled={noneSelected}>Tout désélectionner</button>
          </div>

          <div className="hood-grid">
            {allNames.map(name => (
              <button
                key={name}
                type="button"
                className={`hood-chip${selectedHoods.has(name) ? ' selected' : ''}`}
                onClick={() => toggleHood(name)}
              >
                {selectedHoods.has(name) && <span className="hood-check">&#10003;</span>}
                {name}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend>Budget et taille</legend>
          <div className="form-row">
            <div className="form-group">
              <label>Prix min ($)</label>
              <input type="number" value={priceMin} onChange={e => { setPriceMin(+e.target.value); markDirty(); }} />
            </div>
            <div className="form-group">
              <label>Prix max ($)</label>
              <input type="number" value={priceMax} onChange={e => { setPriceMax(+e.target.value); markDirty(); }} />
            </div>
            <div className="form-group">
              <label>Chambres min</label>
              <input type="number" value={bedroomsMin} onChange={e => { setBedroomsMin(+e.target.value); markDirty(); }} min={0} />
            </div>
            <div className="form-group">
              <label>Chambres max</label>
              <input type="number" value={bedroomsMax} onChange={e => { setBedroomsMax(e.target.value ? +e.target.value : ''); markDirty(); }} min={0} placeholder="Illimité" />
            </div>
          </div>
        </fieldset>

        <fieldset>
          <legend>Options</legend>
          <div className="option-row">
            <label className="option-label">
              <input type="checkbox" checked={furnished} onChange={e => { setFurnished(e.target.checked); markDirty(); }} />
              Meublé uniquement
            </label>
            <label className="option-label">
              <input type="checkbox" checked={parking} onChange={e => { setParking(e.target.checked); markDirty(); }} />
              Parking requis
            </label>
          </div>

          <div className="form-group">
            <label>Emménagement après le</label>
            <input type="date" value={moveInAfter} onChange={e => { setMoveInAfter(e.target.value); markDirty(); }} />
          </div>
        </fieldset>

        <button type="submit" disabled={saving || (!dirty && !saved)} className={`btn-full${dirty ? ' btn-pulse' : ''}`}>
          {saving ? 'Enregistrement...' : dirty ? 'Sauvegarder les modifications' : 'Sauvegarder'}
        </button>
        {saved && !dirty && <p className="success-msg" style={{ marginTop: '0.5rem', textAlign: 'center' }}>Critères sauvegardés — les changements seront appliqués au prochain scan</p>}
      </form>
    </div>
  );
}
