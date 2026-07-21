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

### Pipeline

`normalisation des types/unités -> exclusion des valeurs aberrantes (loguées) ->
déduplication (1 DPE le plus récent par logement/adresse) -> tagging zone +
tranche de surface`.

### Utilisation du CLI

```bash
python -m src.cleaning.cli --input data/raw/ --output data/processed/dpe_clean.parquet
```

Écrit :
- `data/processed/dpe_clean.parquet` — le jeu de données propre.
- `data/processed/dpe_clean_excluded.csv` — les lignes exclues avec la raison
  (colonne `exclusion_reason`), pour audit.

### Schéma de sortie (`dpe_clean.parquet`)

| Colonne                | Type                    | Unité / description                        |
|-------------------------|-------------------------|---------------------------------------------|
| `numero_dpe`            | string                  | Identifiant unique du DPE                    |
| `adresse`               | string                  | Adresse normalisée (trim, espaces collapsés) |
| `code_postal`           | string                  | 5 chiffres, zéros initiaux conservés         |
| `commune`               | string                  |                                               |
| `etiquette_dpe`         | category ordonnée A→G   | Étiquette énergie                            |
| `etiquette_ges`         | category ordonnée A→G   | Étiquette climat/GES                         |
| `surface_m2`            | float                   | Surface habitable (m²)                       |
| `conso_kwh_m2_an`       | float                   | Consommation énergie primaire (kWhEP/m²/an)  |
| `annee_construction`    | float (nullable int)    | Année de construction, si connue             |
| `date_diagnostic`       | datetime                | Date du DPE                                  |
| `zone`                  | string                  | = `code_postal` (pas de découpage par quartier disponible dans les données ADEME) |
| `surface_bracket_min`   | float                   | Borne basse ± 15% autour de `surface_m2`     |
| `surface_bracket_max`   | float                   | Borne haute ± 15% autour de `surface_m2`     |

### Règles de nettoyage

- **Champs requis** : `numero_dpe`, `code_postal_ban`, `adresse_ban`,
  `surface_habitable_logement`, `conso_5_usages_par_m2_ep`, `etiquette_dpe`,
  `date_etablissement_dpe`. Toute ligne où l'un de ces champs est absent est
  exclue (l'API ADEME omet les clés à valeur nulle, cf. ticket 1).
- **Valeurs aberrantes** exclues (bornes dans `config/settings.py`) :
  surface ≤ 0 ou > 1000 m², consommation ≤ 0 ou > 2000 kWhEP/m²/an, étiquette
  DPE hors A–G.
- **Déduplication** : un seul DPE conservé par adresse normalisée (le plus
  récent selon `date_etablissement_dpe`).

  ⚠️ **Limite connue** : les champs extraits ne contiennent pas d'identifiant
  d'appartement fiable (ex: `complement_adresse_logement` n'est pas extrait).
  Dans un immeuble collectif, plusieurs logements distincts partagent la même
  adresse postale et sont donc fusionnés en un seul lors de la déduplication.
  Sur le jeu de test réel (Senlis, 60300 : 5704 DPE bruts), cela réduit le jeu
  de données à 1896 logements après déduplication — une réduction volontaire
  mais à garder en tête pour l'interprétation des statistiques du ticket 3.
  Piste d'amélioration : ré-extraire `complement_adresse_logement` et
  dédupliquer sur `(adresse, complement_adresse_logement)`.
- **Tagging** : `zone` = code postal ; tranche de surface = bornes ± 15%
  autour de la surface de chaque logement, via la fonction réutilisable
  `surface_bracket()` (aussi utilisée par le ticket 3).

### Tests

```bash
uv run pytest tests/test_cleaning/
```

## Ticket 3 — Comparaison (`src/comparison/`)

### Hypothèses (`config/hypotheses.yaml`)

⚠️ **Le pourcentage de gain énergétique et le prix du kWh sont des hypothèses
fictives non validées terrain** (cf. commentaires dans le fichier). Elles sont
chargées au runtime via `load_hypotheses()` — jamais codées en dur dans
`compare.py`. À valider avec Louis avant tout usage commercial réel.

### Utilisation du CLI

```bash
python -m src.comparison.cli --address "8 Rue de Villevert, 60300 Senlis" \
    --data data/processed/dpe_clean.parquet --output data/processed/
```

Si l'adresse ne correspond à aucun DPE existant dans les données nettoyées, la
surface doit être fournie explicitement via `--surface <m2>`.

Produit `data/processed/comparison_<adresse_slug>.json` contenant : la liste
des logements comparables, les statistiques du groupe (moyenne/médiane,
distribution des étiquettes A–G) et l'estimation de gain de rénovation.

### Logique de sélection des comparables

1. Le code postal est extrait de l'adresse/zone recherchée (`extract_zip_code`).
2. La surface cible est soit fournie explicitement (`--surface`), soit
   retrouvée en cherchant l'adresse dans le jeu de données nettoyé (cas
   fréquent : le logement a déjà un DPE existant).
3. `find_comparables(zone, surface_m2, data)` filtre les logements de la même
   `zone` (code postal) dont la surface est dans la tranche ± 15% autour de
   `surface_m2` (réutilise `surface_bracket()` du ticket 2), en excluant le
   logement cible lui-même s'il a été trouvé dans les données.
4. `estimate_renovation_gain()` applique le pourcentage de réduction de
   consommation à la consommation moyenne du groupe de comparables.

### Tests

```bash
uv run pytest tests/test_comparison/
```

Validé manuellement sur 3 adresses réelles de Senlis (60300) avec les données
du ticket 1/2 (voir `data/processed/comparison_*.json`).

## Ticket 4 — Présentation (`src/presentation/`)

_À documenter à l'issue du ticket 4._
