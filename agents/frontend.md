# Agent Frontend

## Rôle
Composants React, UX dashboard, intégration API, cartographie Leaflet.

## Stack
React 18 · TypeScript · Leaflet · TanStack Query · Zustand · Tailwind CSS · Vite

## Structure
```
frontend/
├── src/
│   ├── components/    ← composants réutilisables (atoms, molecules)
│   ├── features/      ← modules par fonctionnalité
│   │   ├── map/       ← heatmap Leaflet
│   │   ├── properties/← liste, détail, scoring
│   │   ├── alerts/    ← gestion des alertes
│   │   └── billing/   ← Stripe portal
│   ├── api/           ← clients API typés (un fichier par ressource)
│   ├── store/         ← état global Zustand (léger)
│   ├── hooks/         ← hooks custom
│   └── types/         ← types TypeScript partagés
└── public/
```

## Règles
- Typage strict TypeScript — pas de `any`
- TanStack Query pour tout appel API (cache, loading, error states)
- Les types API générés depuis le schéma OpenAPI FastAPI (`openapi-typescript`)
- Composants petits et composables — max 150 lignes par fichier
- Erreurs API toujours gérées et affichées à l'utilisateur
- Leaflet : clustering des markers au-delà de 100 points

## Pattern API client
```typescript
// api/properties.ts
export const propertiesApi = {
  list: (filters: PropertyFilters) =>
    apiClient.get<Page<Property>>('/v1/properties', { params: filters }),
  getScore: (id: string) =>
    apiClient.get<Score>(`/v1/properties/${id}/score`),
}

// usage dans un composant
const { data, isLoading } = useQuery({
  queryKey: ['properties', filters],
  queryFn: () => propertiesApi.list(filters),
})
```

## Priorités UX
1. Dashboard heatmap — vue principale des agents immobiliers
2. Liste filtrée avec score visible — décision rapide
3. Alertes configurables — rétention
4. Onboarding / billing — conversion
