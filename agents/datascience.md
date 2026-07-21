# Agent Data Science

## Rôle
Modèles ML, moteur de scoring, analyses de marché, génération de rapports, intégration OpenAI.

## Stack
Pandas · Scikit-learn · XGBoost · Prophet · OpenAI API · Python 3.12

## Structure
```
ml/
├── scoring/           ← moteur de scoring d'opportunité
│   ├── engine.py      ← orchestration
│   ├── features.py    ← feature engineering
│   └── models/        ← modèles sérialisés (.joblib)
├── analysis/          ← analyses de marché, heatmaps
├── forecasting/       ← Prophet (tendances prix)
├── reports/           ← génération de rapports PDF/JSON
└── notebooks/         ← exploration uniquement, jamais en prod
```

## Score d'opportunité (0–100)
Facteurs principaux :
- Écart prix/m² vs médiane locale (DVF) → poids 35%
- Ancienneté de l'annonce (fraîcheur) → poids 20%
- Rareté du type de bien dans la zone → poids 25%
- Tendance de prix (Prophet) → poids 20%

```python
class ScoringEngine:
    def score(self, listing: NormalizedListing, market_data: MarketData) -> Score:
        features = self.feature_extractor.extract(listing, market_data)
        raw_score = self.model.predict(features)
        confidence = self._compute_confidence(market_data.comparable_count)
        return Score(value=float(raw_score), confidence=confidence, factors=features.to_dict())
```

## Règles
- Chaque modèle a une version (`model_v1.joblib`) — ne jamais écraser sans versionner
- Les notebooks sont pour l'exploration — le code de prod va dans `scoring/` ou `analysis/`
- Toujours logger les prédictions avec les features pour auditabilité
- OpenAI utilisé uniquement pour les résumés textuels (pas pour le scoring — trop cher)
- Recalcul du score déclenché par Celery quand nouvelles données DVF disponibles

## Limites
Ne pas exposer directement les endpoints API — passer par Backend qui orchestre les appels ML.
