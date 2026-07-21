"""Génération du document de présentation commerciale (HTML) à partir d'un
rapport de comparaison (ticket 3).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Palette (cf. skill dataviz) : chrome/ink en mode clair, "good" pour la
# situation post-rénovation (amélioration), neutre pour la situation actuelle.
_COLOR_SURFACE = "#fcfcfb"
_COLOR_PAGE = "#f9f9f7"
_COLOR_INK_PRIMARY = "#0b0b0b"
_COLOR_INK_SECONDARY = "#52514e"
_COLOR_INK_MUTED = "#898781"
_COLOR_GRIDLINE = "#e1e0d9"
_COLOR_BASELINE = "#c3c2b7"
_COLOR_GOOD = "#0ca30c"
_COLOR_WARNING_BG = "#fdf3e0"
_COLOR_WARNING_BORDER = "#eda100"


def _fmt_number(value: float | None, decimals: int = 0) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")


def _render_comparables_table(records: list[dict[str, Any]]) -> str:
    if not records:
        return (
            "<p><em>Aucun logement comparable trouvé pour cette zone/surface.</em></p>"
        )

    rows = "\n".join(
        f"<tr>"
        f"<td>{r.get('adresse', 'N/A')}</td>"
        f"<td>{_fmt_number(r.get('surface_m2'), 1)} m²</td>"
        f"<td><span class='label label-{str(r.get('etiquette_dpe', '')).lower()}'>"
        f"{r.get('etiquette_dpe', 'N/A')}</span></td>"
        f"<td>{_fmt_number(r.get('conso_kwh_m2_an'), 0)} kWh/m²/an</td>"
        f"</tr>"
        for r in records
    )
    return f"""
    <table class="comparables">
      <thead>
        <tr><th>Adresse</th><th>Surface</th><th>DPE</th><th>Consommation</th></tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
    """


def _render_label_distribution(distribution: dict[str, int]) -> str:
    if not distribution:
        return ""
    total = sum(distribution.values()) or 1
    order = ["A", "B", "C", "D", "E", "F", "G"]
    bars = "\n".join(
        f"""
        <div class="dist-row">
          <span class="dist-label label-{label.lower()}">{label}</span>
          <div class="dist-bar-track">
            <div class="dist-bar-fill label-fill-{label.lower()}"
                 style="width: {100 * distribution.get(label, 0) / total:.1f}%"></div>
          </div>
          <span class="dist-count">{distribution.get(label, 0)}</span>
        </div>
        """
        for label in order
        if label in distribution
    )
    return f'<div class="distribution">{bars}</div>'


def _render_gain_bars(gain: dict[str, Any]) -> str:
    current = gain["conso_actuelle_kwh_m2_an"]
    estimated = gain["conso_estimee_kwh_m2_an"]
    max_value = max(current, estimated) or 1
    return f"""
    <div class="gain-bars">
      <div class="gain-row">
        <span class="gain-row-label">Consommation actuelle (moyenne comparables)</span>
        <div class="gain-bar-track">
          <div class="gain-bar-fill gain-bar-current"
               style="width: {100 * current / max_value:.1f}%"></div>
        </div>
        <span class="gain-row-value">{_fmt_number(current)} kWh/m²/an</span>
      </div>
      <div class="gain-row">
        <span class="gain-row-label">Consommation estimée après rénovation chanvre</span>
        <div class="gain-bar-track">
          <div class="gain-bar-fill gain-bar-estimated"
               style="width: {100 * estimated / max_value:.1f}%"></div>
        </div>
        <span class="gain-row-value">{_fmt_number(estimated)} kWh/m²/an</span>
      </div>
    </div>
    """


_STYLE = f"""
<style>
  body {{
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: {_COLOR_PAGE};
    color: {_COLOR_INK_PRIMARY};
    margin: 0;
    padding: 2rem;
  }}
  .card {{
    max-width: 860px;
    margin: 0 auto;
    background: {_COLOR_SURFACE};
    border: 1px solid {_COLOR_GRIDLINE};
    border-radius: 12px;
    padding: 2rem 2.5rem;
  }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; border-bottom: 1px solid {_COLOR_GRIDLINE}; padding-bottom: 0.4rem; }}
  .subtitle {{ color: {_COLOR_INK_SECONDARY}; margin-top: 0; }}
  .disclaimer {{
    background: {_COLOR_WARNING_BG};
    border: 1px solid {_COLOR_WARNING_BORDER};
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    font-size: 0.9rem;
    color: {_COLOR_INK_SECONDARY};
    margin: 1.2rem 0;
  }}
  .hero {{
    display: flex;
    gap: 2rem;
    margin: 1.5rem 0;
  }}
  .hero-stat {{ flex: 1; }}
  .hero-value {{ font-size: 2rem; font-weight: 600; color: {_COLOR_GOOD}; }}
  .hero-label {{ color: {_COLOR_INK_SECONDARY}; font-size: 0.9rem; }}
  .gain-bars {{ margin: 1rem 0; }}
  .gain-row {{ display: grid; grid-template-columns: 260px 1fr 140px; align-items: center; gap: 0.75rem; margin: 0.6rem 0; }}
  .gain-row-label {{ font-size: 0.85rem; color: {_COLOR_INK_SECONDARY}; }}
  .gain-bar-track {{ background: {_COLOR_GRIDLINE}; border-radius: 6px; height: 14px; overflow: hidden; }}
  .gain-bar-fill {{ height: 100%; border-radius: 6px; }}
  .gain-bar-current {{ background: {_COLOR_BASELINE}; }}
  .gain-bar-estimated {{ background: {_COLOR_GOOD}; }}
  .gain-row-value {{ font-size: 0.85rem; text-align: right; font-variant-numeric: tabular-nums; }}
  table.comparables {{ width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }}
  table.comparables th, table.comparables td {{
    text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid {_COLOR_GRIDLINE};
  }}
  table.comparables th {{ color: {_COLOR_INK_MUTED}; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; }}
  .label {{
    display: inline-block; min-width: 1.4rem; text-align: center;
    border-radius: 4px; padding: 0.1rem 0.4rem; font-weight: 600; color: white;
  }}
  .label-a {{ background: #0ca30c; }}
  .label-b {{ background: #3a9b3a; }}
  .label-c {{ background: #8ea60e; }}
  .label-d {{ background: #eda100; }}
  .label-e {{ background: #eb6834; }}
  .label-f {{ background: #e34948; }}
  .label-g {{ background: #b32020; }}
  .distribution {{ margin: 1rem 0; }}
  .dist-row {{ display: grid; grid-template-columns: 2rem 1fr 2.5rem; align-items: center; gap: 0.6rem; margin: 0.3rem 0; }}
  .dist-bar-track {{ background: {_COLOR_GRIDLINE}; border-radius: 6px; height: 10px; overflow: hidden; }}
  .dist-bar-fill {{ height: 100%; border-radius: 6px; }}
  .label-fill-a {{ background: #0ca30c; }}
  .label-fill-b {{ background: #3a9b3a; }}
  .label-fill-c {{ background: #8ea60e; }}
  .label-fill-d {{ background: #eda100; }}
  .label-fill-e {{ background: #eb6834; }}
  .label-fill-f {{ background: #e34948; }}
  .label-fill-g {{ background: #b32020; }}
  .dist-count {{ text-align: right; font-size: 0.85rem; color: {_COLOR_INK_SECONDARY}; }}
  footer {{ margin-top: 2rem; font-size: 0.75rem; color: {_COLOR_INK_MUTED}; }}
</style>
"""


def generate_html_report(report: dict[str, Any], output_path: Path) -> Path:
    """Génère le document HTML de présentation commerciale à partir d'un
    rapport de comparaison (`build_comparison_report` du ticket 3).
    """
    stats = report["statistiques_groupe"]
    gain = report.get("estimation_gain_renovation")

    hero_html = ""
    gain_bars_html = (
        "<p><em>Pas assez de logements comparables pour estimer un gain.</em></p>"
    )
    if gain:
        hero_html = f"""
        <div class="hero">
          <div class="hero-stat">
            <div class="hero-value">{_fmt_number(gain["economie_eur_an"])} €/an</div>
            <div class="hero-label">Économie estimée</div>
          </div>
          <div class="hero-stat">
            <div class="hero-value">{_fmt_number(gain["economie_kwh_an"])} kWh/an</div>
            <div class="hero-label">Soit une réduction de {_fmt_number(gain["reduction_pourcentage_estime"] * 100)}%</div>
          </div>
        </div>
        """
        gain_bars_html = _render_gain_bars(gain)

    html = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>INNOVHEMP — Argumentaire rénovation {report["adresse_recherchee"]}</title>
{_STYLE}
</head>
<body>
  <div class="card">
    <h1>Argumentaire rénovation énergétique — INNOVHEMP</h1>
    <p class="subtitle">{report["adresse_recherchee"]} (zone {report["zone"]}, {_fmt_number(report["surface_m2"], 1)} m²)</p>

    <div class="disclaimer">
      ⚠️ <strong>Estimation à valider.</strong> Le pourcentage de réduction de
      consommation et le prix du kWh utilisés ici sont des <strong>hypothèses
      non validées terrain</strong> (voir <code>config/hypotheses.yaml</code>).
      Ce document est un support de discussion commerciale, pas un engagement
      contractuel de performance.
    </div>

    {hero_html}

    <h2>Consommation actuelle vs. estimée après rénovation</h2>
    {gain_bars_html}

    <h2>Logements comparables ({stats["nombre_logements"]} trouvés, même zone et
    surface ± 15%)</h2>
    {_render_comparables_table(report["logements_comparables"])}

    <h2>Répartition des étiquettes DPE du groupe comparable</h2>
    {_render_label_distribution(stats["distribution_etiquettes"])}

    <footer>
      Généré par le pipeline innovhemp-dpe-comparator à partir des données
      DPE publiques ADEME (data.ademe.fr, dataset dpe03existant).
    </footer>
  </div>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info("Document commercial généré : %s", output_path)
    return output_path
