"""Client pour l'API Open Data ADEME (jeu de données DPE Logements existants).

Doc vérifiée le 2026-07-21 sur https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/api-docs.json
- Pagination en profondeur via le champ "next" de la réponse (URL complète à
  rappeler telle quelle) — pas de paramètre "page" au-delà des premiers résultats.
- Filtrage par code postal via le paramètre structuré "<champ>_in=val1,val2"
  (le paramètre "qs" déclenche un 403 WAF avec certains caractères, on l'évite).
"""

from __future__ import annotations

import logging
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import (
    ADEME_API_BASE_URL,
    ADEME_FIELDS,
    ADEME_MAX_RETRIES,
    ADEME_PAGE_SIZE,
    ADEME_REQUEST_TIMEOUT_SECONDS,
    ADEME_ZIP_FIELD,
)

logger = logging.getLogger(__name__)


class AdemeApiError(Exception):
    """Erreur non transitoire ou épuisement des tentatives de retry."""


class _RetryableAdemeError(Exception):
    """Erreur transitoire (timeout, 429, 5xx) : doit déclencher un retry."""


def _is_retryable_status(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


@retry(
    retry=retry_if_exception_type(_RetryableAdemeError),
    stop=stop_after_attempt(ADEME_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    reraise=True,
)
def _get(
    url: str, params: dict[str, Any] | None, session: requests.Session
) -> dict[str, Any]:
    try:
        response = session.get(
            url, params=params, timeout=ADEME_REQUEST_TIMEOUT_SECONDS
        )
    except (requests.Timeout, requests.ConnectionError) as exc:
        logger.warning("Erreur réseau sur %s : %s — nouvelle tentative", url, exc)
        raise _RetryableAdemeError(str(exc)) from exc

    if _is_retryable_status(response.status_code):
        logger.warning(
            "Statut HTTP %s sur %s — nouvelle tentative", response.status_code, url
        )
        raise _RetryableAdemeError(f"HTTP {response.status_code}")

    if response.status_code != 200:
        raise AdemeApiError(
            f"Erreur non transitoire HTTP {response.status_code} sur {url}: "
            f"{response.text[:300]}"
        )

    return response.json()


def fetch_dpe_for_zip_code(
    zip_code: str,
    session: requests.Session | None = None,
    page_size: int = ADEME_PAGE_SIZE,
    fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Récupère l'intégralité des DPE pour un code postal, toutes pages confondues."""
    session = session or requests.Session()
    fields = fields or ADEME_FIELDS

    results: list[dict[str, Any]] = []
    url = ADEME_API_BASE_URL
    params: dict[str, Any] | None = {
        f"{ADEME_ZIP_FIELD}_in": zip_code,
        "size": page_size,
        "select": ",".join(fields),
    }

    page_count = 0
    while url:
        try:
            payload = _get(url, params, session)
        except _RetryableAdemeError as exc:
            raise AdemeApiError(
                f"Échec après {ADEME_MAX_RETRIES} tentatives pour le code postal "
                f"{zip_code} : {exc}"
            ) from exc

        page_results = payload.get("results", [])
        results.extend(page_results)
        page_count += 1
        logger.info(
            "Code postal %s : page %d récupérée (%d lignes, total cumulé %d/%s)",
            zip_code,
            page_count,
            len(page_results),
            len(results),
            payload.get("total"),
        )

        url = payload.get("next")
        # Le "next" retourné par l'API est déjà une URL complète avec ses propres
        # paramètres (ex: "after=..."). On ne doit pas lui rajouter nos params.
        params = None

    return results


def fetch_dpe_for_zip_codes(
    zip_codes: list[str],
    session: requests.Session | None = None,
    page_size: int = ADEME_PAGE_SIZE,
    fields: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Récupère les DPE pour une liste de codes postaux, un par un."""
    session = session or requests.Session()
    return {
        zip_code: fetch_dpe_for_zip_code(
            zip_code, session=session, page_size=page_size, fields=fields
        )
        for zip_code in zip_codes
    }
