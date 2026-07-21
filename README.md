# INNOVHEMP — Comparateur DPE

Pipeline pour générer, à partir d'une adresse ou d'une zone, un argumentaire
commercial chiffré montrant l'économie d'énergie qu'une rénovation en blocs de
chanvre INNOVHEMP permettrait, en comparant avec des logements réels similaires
(données DPE publiques ADEME).

## Installation

```bash
uv sync
```

(ou `pip install -r requirements.txt` si vous n'utilisez pas `uv` — voir
`pyproject.toml` pour la liste figée des dépendances).

## Pipeline

1. **Extraction** (`src/extraction/`) — interroge l'API Open Data ADEME.
2. **Nettoyage** (`src/cleaning/`) — déduplique, normalise, tague par zone/surface.
3. **Comparaison** (`src/comparison/`) — sélectionne les logements comparables et
   estime le gain de rénovation.
4. **Présentation** (`src/presentation/`) — génère le document commercial final.

---

## Ticket 1 — Extraction (`src/extraction/`)

### Source de données

⚠️ **Précision importante** : le jeu de données `dpe-france` évoqué dans certaines
docs correspond au jeu de données **legacy** "DPE Logements (avant juillet 2021)".
Vérification faite le 2026-07-21 : le jeu de données **actif et à jour** est
`dpe03existant` ("DPE Logements existants (depuis juillet 2021)"), utilisé ici :

```
https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines
```

Pas de clé API nécessaire (Open Data). Quotas anonymes : 600 requêtes / 60s.

### Filtrage et pagination (vérifiés en conditions réelles)

- Filtrage par code postal : paramètre structuré `code_postal_ban_in=60300,60100`
  (accepte plusieurs codes séparés par des virgules).
  Le paramètre `qs` (recherche avancée ElasticSearch) déclenche un **403 WAF**
  dès qu'il contient certains caractères (`:`, `"`) — il est donc volontairement
  évité au profit du filtre structuré par colonne.
- Pagination : la réponse contient `{"total", "next", "results"}`. `next` est une
  URL complète à rappeler telle quelle pour obtenir la page suivante ; elle est
  absente sur la dernière page. Le client suit ce curseur jusqu'à épuisement.
- Taille de page : 1000 lignes/requête (paramétrable, max autorisé par l'API :
  10 000).

### Champs conservés

| Champ API              | Description                                  |
|-------------------------|-----------------------------------------------|
| `numero_dpe`            | Identifiant unique du DPE                     |
| `adresse_ban`           | Adresse normalisée (BAN)                      |
| `code_postal_ban`       | Code postal normalisé                         |
| `nom_commune_ban`       | Commune                                       |
| `etiquette_dpe`         | Étiquette énergie (A–G)                       |
| `etiquette_ges`         | Étiquette climat/GES (A–G)                    |
| `surface_habitable_logement` | Surface habitable (m²)                  |
| `conso_5_usages_par_m2_ep` | Consommation énergie primaire (kWhEP/m²/an) |
| `annee_construction`    | Année de construction (peut être absent)      |
| `date_etablissement_dpe`| Date du diagnostic                            |

Note : l'API omet les clés dont la valeur est nulle (elles n'apparaissent pas du
tout dans le JSON plutôt que d'apparaître à `null`) — le code de nettoyage
(ticket 2) en tient compte via des accès `.get()`.

### Utilisation du CLI

```bash
python -m src.extraction.cli --zip-codes 60300,60100 --output data/raw/
```

Produit un fichier JSON par code postal : `data/raw/dpe_raw_<code_postal>.json`.

### Gestion des erreurs

Retry exponentiel (`tenacity`, jusqu'à 5 tentatives, backoff 1s→30s) sur :
timeout réseau, erreurs de connexion, HTTP 429, HTTP 5xx. Les autres erreurs
HTTP (ex: 404) échouent immédiatement sans retry.

### Tests

```bash
uv run pytest tests/test_extraction/
```

Tout est mocké via `responses` — aucun appel réseau réel dans les tests.

---

## Ticket 2 — Nettoyage (`src/cleaning/`)

_À documenter à l'issue du ticket 2._

## Ticket 3 — Comparaison (`src/comparison/`)

_À documenter à l'issue du ticket 3._

## Ticket 4 — Présentation (`src/presentation/`)

_À documenter à l'issue du ticket 4._
