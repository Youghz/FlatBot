"""Montreal neighbourhoods registry.

Single source of truth for all neighbourhood definitions used across
the application: frontend display, Centris URL slugs, and text matching.
"""

# Each entry: display name → {
#   "variants": search terms for text matching (lowercase)
#   "centris_slug": Centris URL path segment (or "" if no dedicated page)
# }
# Grouped by: Montreal boroughs, then Greater Montreal cities

NEIGHBOURHOODS: dict[str, dict] = {
    # === Ile de Montreal — Arrondissements ===
    "Ahuntsic-Cartierville": {
        "variants": ["ahuntsic", "cartierville", "sault-au-récollet", "sault-au-recollet", "bordeaux-cartierville"],
        "centris_slug": "montreal-ahuntsic-cartierville",
    },
    "Anjou": {
        "variants": ["anjou"],
        "centris_slug": "montreal-anjou",
    },
    "Côte-des-Neiges—NDG": {
        "variants": ["côte-des-neiges", "cote-des-neiges", "notre-dame-de-grâce", "notre-dame-de-grace", "ndg", "cdn"],
        "centris_slug": "montreal-cote-des-neiges-notre-dame-de-grace",
    },
    "Lachine": {
        "variants": ["lachine"],
        "centris_slug": "montreal-lachine",
    },
    "LaSalle": {
        "variants": ["lasalle", "la salle"],
        "centris_slug": "montreal-lasalle",
    },
    "Le Plateau-Mont-Royal": {
        "variants": [
            "plateau",
            "plateau-mont-royal",
            "plateau mont-royal",
            "mile-end",
            "mile end",
            "mile-ex",
            "mile ex",
        ],
        "centris_slug": "montreal-le-plateau-mont-royal",
    },
    "Le Sud-Ouest": {
        "variants": [
            "sud-ouest",
            "griffintown",
            "saint-henri",
            "st-henri",
            "petite-bourgogne",
            "pointe-saint-charles",
            "pointe-st-charles",
        ],
        "centris_slug": "montreal-le-sud-ouest",
    },
    "L'Île-Bizard—Sainte-Geneviève": {
        "variants": ["île-bizard", "ile-bizard", "sainte-geneviève", "sainte-genevieve"],
        "centris_slug": "montreal-l-ile-bizard-sainte-genevieve",
    },
    "Mercier—Hochelaga-Maisonneuve": {
        "variants": [
            "mercier",
            "hochelaga",
            "hochelaga-maisonneuve",
            "maisonneuve",
            "tétreaultville",
            "tetreaultville",
            "longue-pointe",
        ],
        "centris_slug": "montreal-mercier-hochelaga-maisonneuve",
    },
    "Montréal-Nord": {
        "variants": ["montréal-nord", "montreal-nord", "montreal nord"],
        "centris_slug": "montreal-montreal-nord",
    },
    "Outremont": {
        "variants": ["outremont"],
        "centris_slug": "montreal-outremont",
    },
    "Pierrefonds-Roxboro": {
        "variants": ["pierrefonds", "roxboro"],
        "centris_slug": "montreal-pierrefonds-roxboro",
    },
    "Rivière-des-Prairies—PAT": {
        "variants": [
            "rivière-des-prairies",
            "riviere-des-prairies",
            "rdp",
            "pointe-aux-trembles",
            "pointe aux trembles",
        ],
        "centris_slug": "montreal-riviere-des-prairies-pointe-aux-trembles",
    },
    "Rosemont—La Petite-Patrie": {
        "variants": [
            "rosemont",
            "petite-patrie",
            "petite patrie",
            "la petite-patrie",
            "petite-italie",
            "petite italie",
            "little italy",
        ],
        "centris_slug": "montreal-rosemont-la-petite-patrie",
    },
    "Saint-Laurent": {
        "variants": ["saint-laurent", "st-laurent"],
        "centris_slug": "montreal-saint-laurent",
    },
    "Saint-Léonard": {
        "variants": ["saint-léonard", "saint-leonard", "st-léonard", "st-leonard"],
        "centris_slug": "montreal-saint-leonard",
    },
    "Verdun": {
        "variants": ["verdun", "île-des-soeurs", "ile-des-soeurs", "nuns' island"],
        "centris_slug": "montreal-verdun",
    },
    "Ville-Marie": {
        "variants": [
            "ville-marie",
            "centre-ville",
            "downtown",
            "vieux-montréal",
            "vieux-montreal",
            "old montreal",
            "quartier latin",
            "quartier des spectacles",
        ],
        "centris_slug": "montreal-ville-marie",
    },
    "Villeray—Saint-Michel—Parc-Extension": {
        "variants": [
            "villeray",
            "saint-michel",
            "st-michel",
            "parc-extension",
            "parc extension",
            "marconi-alexandra",
        ],
        "centris_slug": "montreal-villeray-saint-michel-parc-extension",
    },
    # === Villes liees / Grand Montreal ===
    "Westmount": {
        "variants": ["westmount"],
        "centris_slug": "westmount",
    },
    "Mont-Royal": {
        "variants": ["mont-royal", "town of mount royal", "tmr"],
        "centris_slug": "mont-royal",
    },
    "Côte-Saint-Luc": {
        "variants": ["côte-saint-luc", "cote-saint-luc", "côte saint-luc", "cote saint-luc"],
        "centris_slug": "cote-saint-luc",
    },
    "Hampstead": {
        "variants": ["hampstead"],
        "centris_slug": "hampstead",
    },
    "Montréal-Ouest": {
        "variants": ["montréal-ouest", "montreal-ouest", "montreal west"],
        "centris_slug": "montreal-ouest",
    },
    "Dorval": {
        "variants": ["dorval"],
        "centris_slug": "dorval",
    },
    "Pointe-Claire": {
        "variants": ["pointe-claire"],
        "centris_slug": "pointe-claire",
    },
    "Dollard-des-Ormeaux": {
        "variants": ["dollard-des-ormeaux", "ddo"],
        "centris_slug": "dollard-des-ormeaux",
    },
    "Laval": {
        "variants": [
            "laval",
            "chomedey",
            "laval-des-rapides",
            "pont-viau",
            "vimont",
            "auteuil",
            "sainte-dorothée",
            "sainte-dorothee",
            "duvernay",
            "fabreville",
            "sainte-rose",
        ],
        "centris_slug": "laval",
    },
    "Longueuil": {
        "variants": ["longueuil", "vieux-longueuil", "saint-hubert", "st-hubert", "greenfield park"],
        "centris_slug": "longueuil",
    },
    "Brossard": {
        "variants": ["brossard"],
        "centris_slug": "brossard",
    },
}


def get_display_names() -> list[str]:
    """Return all neighbourhood display names."""
    return list(NEIGHBOURHOODS.keys())


def get_variants(name: str) -> list[str]:
    """Return search term variants for a neighbourhood."""
    entry = NEIGHBOURHOODS.get(name, {})
    return entry.get("variants", [name.lower()])


def get_centris_slug(name: str) -> str:
    """Return the Centris URL slug for a neighbourhood."""
    entry = NEIGHBOURHOODS.get(name, {})
    return entry.get("centris_slug", "")


def build_keyword_map() -> dict[str, str]:
    """Build a reverse map: search term → display name (for detection in text)."""
    mapping = {}
    for name, entry in NEIGHBOURHOODS.items():
        for variant in entry["variants"]:
            mapping[variant] = name
    return mapping
