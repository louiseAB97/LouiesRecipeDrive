"""Statusoverzicht van alle recepten in src/content/recipes/.

Gebruik:
    uv run scripts/status.py

Toont per recept wat er ontbreekt (foto, persons, tags) en schrijft hetzelfde
overzicht naar ``overzicht.json``. De Markdown-bestanden zijn de enige bron
van waarheid; het JSON-bestand wordt elke run opnieuw gegenereerd.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RECEPTEN_MAP = ROOT / "src" / "content" / "recipes"
FOTOS_MAP = ROOT / "src" / "assets" / "recipes"
OVERZICHT = ROOT / "overzicht.json"
FOTO_EXTENSIES = {".jpg", ".jpeg", ".png", ".webp", ".avif"}


@dataclass
class ReceptStatus:
    """Samenvatting van de status van één recept."""

    slug: str
    titel: str
    concept: bool
    aantal_fotos: int
    ontbrekend: list[str] = field(default_factory=list)
    waarschuwingen: list[str] = field(default_factory=list)
    optioneel: list[str] = field(default_factory=list)


def tel_fotos(slug: str) -> int:
    """Tel hoeveel foto's er voor een slug in de fotomap staan."""
    if not FOTOS_MAP.is_dir():
        return 0
    patroon = re.compile(re.escape(slug) + r"(-\d+)?\.[^.]+$")
    return sum(
        1
        for f in FOTOS_MAP.iterdir()
        if f.is_file() and f.suffix.lower() in FOTO_EXTENSIES and patroon.match(f.name)
    )


def lees_frontmatter(pad: Path) -> dict:
    """Lees de YAML-frontmatter van een Markdown-bestand."""
    tekst = pad.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", tekst, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def beoordeel(pad: Path) -> ReceptStatus:
    """Bepaal de status van één receptbestand."""
    data = lees_frontmatter(pad)
    slug = pad.stem
    titel = data.get("title") or slug
    ingredienten = data.get("ingredients") or []
    tags = data.get("tags") or []
    fotos = tel_fotos(slug)

    status = ReceptStatus(
        slug=slug,
        titel=titel,
        concept=bool(data.get("concept")),
        aantal_fotos=fotos,
    )
    if fotos == 0:
        status.ontbrekend.append("foto")
    if data.get("persons") is None:
        status.ontbrekend.append("persons")
    if not tags:
        status.ontbrekend.append("tags")
    if not ingredienten:
        status.ontbrekend.append("ingredients")

    if data.get("intro") is None:
        status.optioneel.append("intro")

    heeft_ster = any(str(i).rstrip().endswith("*") for i in ingredienten)
    heeft_toelichting = data.get("notes") is not None
    if heeft_ster and not heeft_toelichting:
        status.waarschuwingen.append("ingrediënt met * maar geen toelichting")
    if heeft_toelichting and not heeft_ster:
        status.waarschuwingen.append("toelichting maar geen * in ingrediënten")
    return status


def main() -> None:
    """Loop alle recepten door, toon het overzicht en schrijf overzicht.json."""
    paden = sorted(RECEPTEN_MAP.glob("*.md"))
    statussen = [beoordeel(p) for p in paden]
    actief = [s for s in statussen if not s.concept]

    def met(veld: str) -> list[ReceptStatus]:
        return [s for s in statussen if veld in s.ontbrekend]

    zonder_foto = met("foto")
    zonder_personen = met("persons")
    zonder_tags = met("tags")
    zonder_intro = [s for s in statussen if "intro" in s.optioneel]
    met_waarschuwing = [s for s in statussen if s.waarschuwingen]

    print(f"\n{len(statussen)} recepten ({len(actief)} gepubliceerd, "
          f"{len(statussen) - len(actief)} concept)\n")
    print(f"{len(zonder_foto)} recepten missen een foto")
    print(f"{len(zonder_personen)} recepten missen personen")
    print(f"{len(zonder_tags)} recepten missen tags")
    print(f"{len(zonder_intro)} recepten hebben nog geen intro (optioneel)")
    if met_waarschuwing:
        print(f"{len(met_waarschuwing)} recepten hebben een waarschuwing")
    print()

    for s in statussen:
        regels = [f"{s.titel}  [{s.slug}]"]
        regels.append(f"    foto's: {s.aantal_fotos}")
        if s.concept:
            regels.append("    status: concept (wordt niet gepubliceerd)")
        if s.ontbrekend:
            regels.append(f"    ontbreekt: {', '.join(s.ontbrekend)}")
        if s.optioneel:
            regels.append(f"    optioneel nog: {', '.join(s.optioneel)}")
        for w in s.waarschuwingen:
            regels.append(f"    LET OP: {w}")
        print("\n".join(regels))

    overzicht = {
        "_let_op": (
            "Automatisch gegenereerd door `npm run status`. Niet met de hand "
            "bewerken — de Markdown-bestanden in src/content/recipes/ zijn de "
            "enige bron van waarheid."
        ),
        "gegenereerd": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "totaal": len(statussen),
        "samenvatting": {
            "gepubliceerd": len(actief),
            "concepten": len(statussen) - len(actief),
            "zonder_foto": len(zonder_foto),
            "zonder_personen": len(zonder_personen),
            "zonder_tags": len(zonder_tags),
            "zonder_intro": len(zonder_intro),
            "met_waarschuwing": len(met_waarschuwing),
        },
        "recepten": [
            {
                "slug": s.slug,
                "titel": s.titel,
                "concept": s.concept,
                "aantal_fotos": s.aantal_fotos,
                "ontbrekend": s.ontbrekend,
                "optioneel": s.optioneel,
                "waarschuwingen": s.waarschuwingen,
            }
            for s in statussen
        ],
    }
    OVERZICHT.write_text(
        json.dumps(overzicht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nGeschreven naar {OVERZICHT.name}\n")


if __name__ == "__main__":
    main()
