# Agent Backend

## Rôle
Développement API FastAPI, modèles de données SQLAlchemy, logique métier, tâches Celery.

## Stack
Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Alembic · Celery · Redis · PostgreSQL/TimescaleDB

## Structure à respecter
```
backend/
├── app/
│   ├── api/v1/        ← routers FastAPI
│   ├── models/        ← SQLAlchemy ORM
│   ├── schemas/       ← Pydantic (request/response)
│   ├── services/      ← logique métier
│   ├── repositories/  ← accès DB (pas de SQL dans les services)
│   ├── tasks/         ← tâches Celery
│   └── core/          ← config, sécurité, dépendances
└── alembic/
```

## Règles
- Async partout (`async def`, `AsyncSession`)
- Repository pattern : jamais de requête SQL dans les services ou routers
- Schemas Pydantic distincts pour input/output (ne pas exposer le modèle ORM)
- Gestion d'erreurs avec exceptions custom + handlers FastAPI
- Chaque endpoint a son schéma de réponse typé
- Pagination sur tous les endpoints liste (`page`, `size`, `total`)

## Pattern service
```python
# services/property_service.py
class PropertyService:
    def __init__(self, repo: PropertyRepository):
        self.repo = repo

    async def get_by_agency(self, agency_id: UUID, filters: PropertyFilters) -> Page[PropertyOut]:
        return await self.repo.find_by_agency(agency_id, filters)
```

## Sécurité multi-tenant
Chaque requête filtre par `agency_id` extrait du JWT. Ne jamais faire confiance à un `agency_id` passé en paramètre.
