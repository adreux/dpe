from __future__ import annotations

import responses
from tenacity import stop_after_attempt, wait_none

from config.settings import ADEME_API_BASE_URL, ADEME_MAX_RETRIES
from src.extraction import ademe_client
from src.extraction.ademe_client import AdemeApiError, fetch_dpe_for_zip_code


def _disable_retry_delay(monkeypatch, attempts: int = ADEME_MAX_RETRIES) -> None:
    """Les tests ne doivent pas attendre les délais d'exponential backoff réels."""
    monkeypatch.setattr(ademe_client._get.retry, "wait", wait_none())
    monkeypatch.setattr(ademe_client._get.retry, "stop", stop_after_attempt(attempts))


@responses.activate
def test_fetch_dpe_for_zip_code_paginates_all_pages(monkeypatch):
    _disable_retry_delay(monkeypatch)
    next_url = "https://data.ademe.fr/mock-next-page"

    responses.add(
        responses.GET,
        ADEME_API_BASE_URL,
        json={
            "total": 3,
            "next": next_url,
            "results": [
                {"numero_dpe": "A1", "code_postal_ban": "60300"},
                {"numero_dpe": "A2", "code_postal_ban": "60300"},
            ],
        },
        status=200,
    )
    responses.add(
        responses.GET,
        next_url,
        json={
            "total": 3,
            "results": [{"numero_dpe": "A3", "code_postal_ban": "60300"}],
        },
        status=200,
    )

    records = fetch_dpe_for_zip_code("60300")

    assert [r["numero_dpe"] for r in records] == ["A1", "A2", "A3"]
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_dpe_for_zip_code_retries_on_500_then_succeeds(monkeypatch):
    _disable_retry_delay(monkeypatch)

    responses.add(responses.GET, ADEME_API_BASE_URL, status=500)
    responses.add(responses.GET, ADEME_API_BASE_URL, status=500)
    responses.add(
        responses.GET,
        ADEME_API_BASE_URL,
        json={"total": 1, "results": [{"numero_dpe": "A1"}]},
        status=200,
    )

    records = fetch_dpe_for_zip_code("60300")

    assert records == [{"numero_dpe": "A1"}]
    assert len(responses.calls) == 3


@responses.activate
def test_fetch_dpe_for_zip_code_retries_on_429_then_succeeds(monkeypatch):
    _disable_retry_delay(monkeypatch)

    responses.add(responses.GET, ADEME_API_BASE_URL, status=429)
    responses.add(
        responses.GET,
        ADEME_API_BASE_URL,
        json={"total": 1, "results": [{"numero_dpe": "A1"}]},
        status=200,
    )

    records = fetch_dpe_for_zip_code("60300")

    assert records == [{"numero_dpe": "A1"}]
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_dpe_for_zip_code_raises_after_exhausting_retries(monkeypatch):
    max_attempts = 3
    _disable_retry_delay(monkeypatch, attempts=max_attempts)

    for _ in range(max_attempts):
        responses.add(responses.GET, ADEME_API_BASE_URL, status=500)

    try:
        fetch_dpe_for_zip_code("60300")
        raised = False
    except AdemeApiError:
        raised = True

    assert raised
    assert len(responses.calls) == max_attempts


@responses.activate
def test_fetch_dpe_for_zip_code_retries_on_timeout(monkeypatch):
    import requests

    _disable_retry_delay(monkeypatch)

    responses.add(responses.GET, ADEME_API_BASE_URL, body=requests.exceptions.Timeout())
    responses.add(
        responses.GET,
        ADEME_API_BASE_URL,
        json={"total": 1, "results": [{"numero_dpe": "A1"}]},
        status=200,
    )

    records = fetch_dpe_for_zip_code("60300")

    assert records == [{"numero_dpe": "A1"}]
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_dpe_for_zip_code_does_not_retry_on_404(monkeypatch):
    _disable_retry_delay(monkeypatch)

    responses.add(responses.GET, ADEME_API_BASE_URL, status=404, body="not found")

    try:
        fetch_dpe_for_zip_code("60300")
        raised = False
    except AdemeApiError:
        raised = True

    assert raised
    assert len(responses.calls) == 1
