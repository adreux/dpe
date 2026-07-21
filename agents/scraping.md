# Agent Scraping

## Rôle
Collecte de données (CBRE, JLL, BNP Real Estate, DVF), pipelines ETL, normalisation, gestion des erreurs.

## Stack
Playwright · Scrapy · Celery · Redis · Python 3.12

## Structure
```
scraper/
├── spiders/           ← un fichier par source
│   ├── cbre.py
│   ├── jll.py
│   ├── bnp.py
│   └── dvf.py         ← API publique DVF (pas de scraping)
├── parsers/           ← extraction des champs depuis HTML brut
├── normalizers/       ← uniformisation vers le schéma commun
├── pipeline/          ← validation → déduplication → insertion DB
└── tasks.py           ← tâches Celery (scheduled + on-demand)
```

## Schéma normalisé (sortie de tout spider)
```python
@dataclass
class NormalizedListing:
    source: Literal["cbre", "jll", "bnp"]
    source_id: str          # ID unique chez la source
    source_url: str
    type: Literal["bureau", "entrepot", "local"]
    surface_sqm: float
    price_per_sqm: float | None
    city: str
    postal_code: str
    lat: float | None
    lon: float | None
    raw_data: dict          # HTML/JSON brut conservé
    scraped_at: datetime
```

## Règles
- Toujours conserver `raw_data` — permet de re-parser sans re-scraper
- Déduplication sur `(source, source_id)` avant insertion
- Erreur de parsing = log + skip, jamais de crash du pipeline
- Respecter les délais entre requêtes (min 2s, random jitter)
- User-agent rotatif, pas d'IP banning
- DVF : utiliser l'API officielle `https://api.data.gouv.fr/datasets/5c4ae55a634f4117716d5656`

## Gestion des changements de structure HTML
Les sources changent sans prévenir. Chaque parser a des snapshot tests avec fixtures HTML.
Si un parser retourne `None` sur > 20% des champs obligatoires → alerte Slack + pause du spider.
