"""Configuration centralisée : chemins, URLs et paramètres partagés par tout le pipeline.

Ne pas dupliquer ces constantes ailleurs — importer depuis ce module.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"
CONFIG_DIR = PROJECT_ROOT / "config"
HYPOTHESES_FILE = CONFIG_DIR / "hypotheses.yaml"

# API ADEME — Data Fair.
#
# ATTENTION : le jeu de données "dpe-france" mentionné dans certaines docs/tickets
# correspond en réalité au jeu de données LEGACY "DPE Logements (avant juillet 2021)".
# Vérification faite le 2026-07-21 sur data.ademe.fr : le jeu de données actif et à jour
# pour les logements existants est "dpe03existant" ("DPE Logements existants
# (depuis juillet 2021)"), qui expose des champs différents (ex: `etiquette_dpe`,
# `code_postal_ban`, `surface_habitable_logement`, `conso_5_usages_par_m2_ep`).
# C'est ce jeu de données qui est utilisé ici.
ADEME_DATASET_ID = "dpe03existant"
ADEME_API_BASE_URL = (
    f"https://data.ademe.fr/data-fair/api/v1/datasets/{ADEME_DATASET_ID}/lines"
)

# Le paramètre "qs" (recherche avancée ElasticSearch) déclenche un 403 (WAF) dès
# qu'il contient certains caractères (":", '"'). On utilise donc exclusivement le
# filtre structuré par colonne "<champ>_in=val1,val2" qui est fiable et documenté.
ADEME_ZIP_FIELD = "code_postal_ban"

# Champs conservés à l'extraction (cf. ticket 1 : adresse, code postal, DPE,
# surface, consommation, année de construction, identifiant, date du diagnostic).
ADEME_FIELDS = [
    "numero_dpe",
    "adresse_ban",
    "code_postal_ban",
    "nom_commune_ban",
    "etiquette_dpe",
    "etiquette_ges",
    "surface_habitable_logement",
    "conso_5_usages_par_m2_ep",
    "annee_construction",
    "date_etablissement_dpe",
]

ADEME_PAGE_SIZE = 1000
ADEME_REQUEST_TIMEOUT_SECONDS = 30
ADEME_MAX_RETRIES = 5

# Tolérance pour le regroupement par tranche de surface (± 15% autour d'une valeur).
SURFACE_BRACKET_TOLERANCE = 0.15
