"""Eenmalige import van recepten.txt naar Markdown-contentbestanden.

Gebruik:
    uv run scripts/importeren.py

Het script leest ``recepten.txt`` in de projectroot en schrijft per gevonden
recept één Markdown-bestand naar ``src/content/recepten/<slug>.md``.
Bestaande bestanden worden nooit overschreven.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRONBESTAND = ROOT / "recepten.txt"
DOELMAP = ROOT / "src" / "content" / "recepten"

BENODIGDHEDEN_RE = re.compile(r"^\s*benodigdheden\b", re.IGNORECASE)
INDIEN_GEBRUIK_RE = re.compile(r"^\s*indien\s+gebruik\b", re.IGNORECASE)
PRIJS_RE = re.compile(r"^\s*prijs\s*:\s*(.*)$", re.IGNORECASE)
VOETNOOT_RE = re.compile(r"^\s*(\*{1,2})\s*=\s*(.*)$")
PAGINANUMMER_RE = re.compile(r"\s+\d+\s*$")


@dataclass
class Recept:
    """Een parsed recept uit het bronbestand."""

    titel: str
    personen: int | None
    prijs: str | None
    ingredienten: list[str]
    toelichting: str | None
    bereiding: str
    waarschuwingen: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        """Maak een URL-vriendelijke slug van de titel."""
        genormaliseerd = unicodedata.normalize("NFKD", self.titel)
        ascii_titel = genormaliseerd.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]+", "-", ascii_titel.lower()).strip("-")


def yaml_scalar(waarde: str) -> str:
    """Formatteer een string als veilige YAML-scalar.

    Plain scalars waar mogelijk; double-quoted (JSON-stijl) zodra de tekst
    tekens bevat die YAML anders zou interpreteren.
    """
    if re.fullmatch(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9 ./()+\-&'!]*", waarde) and not re.search(
        r"^(null|true|false|yes|no|on|off|\d)", waarde, re.IGNORECASE
    ):
        return waarde
    return json.dumps(waarde, ensure_ascii=False)


def splits_ingredienten(regel: str) -> list[str]:
    """Splits een ingrediëntenregel op komma's buiten haakjes.

    Args:
        regel: De ruwe ingrediëntentekst na de dubbele punt.

    Returns:
        Een lijst met opgeschoonde ingrediëntnamen.
    """
    delen: list[str] = []
    huidig: list[str] = []
    diepte = 0
    for i, teken in enumerate(regel):
        if teken in "([":
            diepte += 1
        elif teken in ")]":
            diepte = max(0, diepte - 1)
        decimaal = (
            i > 0
            and i + 1 < len(regel)
            and regel[i - 1].isdigit()
            and regel[i + 1].isdigit()
        )
        if teken == "," and diepte == 0 and not decimaal:
            delen.append("".join(huidig))
            huidig = []
        else:
            huidig.append(teken)
    delen.append("".join(huidig))

    ingredienten = []
    for deel in delen:
        schoon = re.sub(r"\s+", " ", deel).strip().rstrip(".")
        if schoon:
            ingredienten.append(schoon[0].upper() + schoon[1:])
    return ingredienten


class ReceptenImporter:
    """Leest recepten.txt en schrijft Markdown-bestanden."""

    def __init__(self, bronbestand: Path = BRONBESTAND, doelmap: Path = DOELMAP) -> None:
        """Initialiseer de importer.

        Args:
            bronbestand: Pad naar het platte-tekst bronbestand.
            doelmap: Map waarin de Markdown-bestanden terechtkomen.
        """
        self.bronbestand = bronbestand
        self.doelmap = doelmap
        self.overgeslagen_secties: list[str] = []
        self.overgeslagen_bestanden: list[str] = []
        self.waarschuwingen: list[str] = []
        self.geschreven = 0

    def run(self) -> None:
        """Voer de volledige import uit en toon een rapport."""
        regels = self.bronbestand.read_text(encoding="utf-8").splitlines()
        body_start = self._vind_body_start(regels)
        bekende_titels = self._lees_inhoudsopgave(regels[:body_start])
        recepten = self._parse_body(regels, body_start, bekende_titels)
        self._schrijf_bestanden(recepten)
        self._rapport(recepten)

    def _vind_body_start(self, regels: list[str]) -> int:
        """Vind de regelindex waar de echte inhoud begint.

        De kop "Recepten door de jaren heen" staat zowel in de inhoudsopgave
        als boven de recepten; de laatste variant markeert het begin.

        Raises:
            ValueError: Als de kop niet gevonden wordt.
        """
        start = -1
        for i, regel in enumerate(regels):
            if regel.strip().lower() == "recepten door de jaren heen":
                start = i
        if start == -1:
            raise ValueError(
                "Kop 'Recepten door de jaren heen' niet gevonden in het bronbestand."
            )
        return start

    def _lees_inhoudsopgave(self, regels: list[str]) -> set[str]:
        """Lees de recepttitels uit de inhoudsopgave (zonder paginanummers)."""
        titels = set()
        for regel in regels:
            titel = PAGINANUMMER_RE.sub("", regel).strip().lower().rstrip(":")
            if titel and titel != "recepten door de jaren heen":
                titels.add(titel)
        return titels

    def _titelregel_boven(self, regels: list[str], index: int, minimum: int) -> int | None:
        """Zoek de dichtstbijzijnde niet-lege regel boven ``index``."""
        for i in range(index - 1, minimum - 1, -1):
            if regels[i].strip():
                return i
        return None

    def _parse_body(
        self, regels: list[str], body_start: int, bekende_titels: set[str]
    ) -> list[Recept]:
        """Parse alle recepten uit het bodygedeelte van het bestand."""
        ankers = [
            i
            for i in range(body_start + 1, len(regels))
            if BENODIGDHEDEN_RE.match(regels[i])
        ]
        recepten: list[Recept] = []
        for positie, anker in enumerate(ankers):
            titel_index = self._titelregel_boven(regels, anker, body_start + 1)
            if titel_index is None:
                self.waarschuwingen.append(
                    f"Regel {anker + 1}: Benodigdheden zonder titel erboven."
                )
                continue
            if positie + 1 < len(ankers):
                volgende_titel = self._titelregel_boven(
                    regels, ankers[positie + 1], titel_index + 1
                )
                einde = volgende_titel if volgende_titel is not None else len(regels)
            else:
                einde = len(regels)
            blok = regels[anker + 1 : einde]

            # Knip het blok af bij een bekende titel zonder Benodigdheden;
            # dat is een recept dat we bewust overslaan.
            for j, regel in enumerate(blok):
                if regel.strip().lower().rstrip(":") in bekende_titels:
                    self.overgeslagen_secties.append(regel.strip())
                    blok = blok[:j]
                    break

            recepten.append(
                self._maak_recept(regels[titel_index].strip(), regels[anker], blok)
            )
        return recepten

    def _maak_recept(self, titel: str, ankerregel: str, blok: list[str]) -> Recept:
        """Bouw een Recept op uit titel, benodigdheden-regel en tekstblok."""
        kop, _, ingredienten_tekst = ankerregel.partition(":")
        getallen = re.findall(r"\d+", kop)
        personen = int(getallen[-1]) if getallen else None
        waarschuwingen: list[str] = []
        if len(set(getallen)) > 1:
            waarschuwingen.append(
                f"Meerdere aantallen op de benodigdheden-regel ({', '.join(getallen)})"
                f" -> {personen} personen gebruikt, check dit handmatig."
            )

        ingredienten = splits_ingredienten(ingredienten_tekst)

        # Verwijder lege regels aan de randen van het blok.
        blok = [r.rstrip() for r in blok]
        while blok and not blok[0]:
            blok.pop(0)
        while blok and not blok[-1]:
            blok.pop()

        toelichting_paragrafen: list[list[str]] = []
        bereiding_regels: list[str] = []
        prijs: str | None = None
        modus = "bereiding"  # bereiding | indien_gebruik | voetnoot
        nieuwe_toelichting_paragraaf = True

        for regel in blok:
            if INDIEN_GEBRUIK_RE.match(regel):
                modus = "indien_gebruik"
                continue
            voetnoot = VOETNOOT_RE.match(regel)
            if voetnoot and modus != "indien_gebruik":
                sterren = "".join("\\*" for _ in voetnoot.group(1)) + " "
                toelichting_paragrafen.append([sterren + voetnoot.group(2).strip()])
                modus = "voetnoot"
                continue
            prijs_match = PRIJS_RE.match(regel)
            if prijs_match and modus == "bereiding":
                if prijs is not None:
                    waarschuwingen.append("Meerdere Prijs-regels gevonden; eerste gebruikt.")
                else:
                    prijs = prijs_match.group(1).strip().rstrip(".")
                continue
            if modus == "voetnoot":
                if regel.strip():
                    toelichting_paragrafen[-1].append(regel.strip())
                else:
                    modus = "bereiding"
                continue
            if modus == "indien_gebruik":
                if regel.strip():
                    if nieuwe_toelichting_paragraaf or not toelichting_paragrafen:
                        toelichting_paragrafen.append([])
                    toelichting_paragrafen[-1].append(regel.strip())
                    nieuwe_toelichting_paragraaf = False
                else:
                    nieuwe_toelichting_paragraaf = True
                continue
            bereiding_regels.append(regel)

        toelichting = self._maak_toelichting(toelichting_paragrafen)

        # Paragrafen (blokken gescheiden door lege regels) blijven behouden;
        # regels binnen een paragraaf krijgen een harde regeleinde in Markdown.
        paragrafen: list[list[str]] = []
        for regel in bereiding_regels:
            if regel.strip():
                if not paragrafen or not paragrafen[-1]:
                    paragrafen.append([])
                paragrafen[-1].append(regel.strip())
            elif paragrafen and paragrafen[-1]:
                paragrafen.append([])
        bereiding = "\n\n".join("  \n".join(p) for p in paragrafen if p)

        recept = Recept(
            titel=titel,
            personen=personen,
            prijs=prijs,
            ingredienten=ingredienten,
            toelichting=toelichting,
            bereiding=bereiding,
            waarschuwingen=waarschuwingen,
        )
        if not ingredienten:
            waarschuwingen.append("Geen ingrediënten gevonden.")
        if not bereiding:
            waarschuwingen.append("Geen bereiding gevonden.")
        heeft_ster = any(i.rstrip().endswith("*") for i in ingredienten)
        if heeft_ster and not toelichting:
            waarschuwingen.append("Ingrediënt met * maar geen toelichting gevonden.")
        if toelichting and not heeft_ster:
            waarschuwingen.append("Toelichting gevonden maar geen * in de ingrediënten.")
        return recept

    def _maak_toelichting(self, paragrafen: list[list[str]]) -> str | None:
        """Combineer toelichting-regels tot één Markdown-tekst.

        Elke regelgroep wordt een paragraaf; een ``* =`` aan het begin wordt
        genormaliseerd naar een ge-escapete ``\\* `` zodat Markdown de ster
        letterlijk toont in plaats van een opsomming.
        """
        if not paragrafen:
            return None
        teksten = []
        for groep in paragrafen:
            voetnoot = VOETNOOT_RE.match(groep[0])
            if voetnoot:
                groep[0] = "".join("\\*" for _ in voetnoot.group(1)) + " " + voetnoot.group(
                    2
                ).strip()
            teksten.append("\n".join(groep))
        if not teksten[0].startswith("\\*"):
            teksten[0] = "\\* " + teksten[0]
        return "\n\n".join(teksten)

    def _frontmatter(self, recept: Recept) -> str:
        """Render de YAML-frontmatter voor een recept."""
        regels = ["---", f"titel: {yaml_scalar(recept.titel)}"]
        regels.append(f"personen: {recept.personen if recept.personen is not None else 'null'}")
        regels.append(
            f"prijs: {json.dumps(recept.prijs, ensure_ascii=False) if recept.prijs else 'null'}"
        )
        regels.append("tags: []")
        regels.append("tijd: null")
        regels.append("concept: false")
        regels.append("intro: null")
        if recept.ingredienten:
            regels.append("ingredienten:")
            regels.extend(f"  - {yaml_scalar(i)}" for i in recept.ingredienten)
        else:
            regels.append("ingredienten: []")
        if recept.toelichting:
            regels.append("toelichting: |")
            for regel in recept.toelichting.splitlines():
                regels.append(f"  {regel}" if regel.strip() else "")
        else:
            regels.append("toelichting: null")
        regels.append("---")
        return "\n".join(regels)

    def _schrijf_bestanden(self, recepten: list[Recept]) -> None:
        """Schrijf per recept een Markdown-bestand; overschrijf nooit."""
        self.doelmap.mkdir(parents=True, exist_ok=True)
        self.geschreven = 0
        for recept in recepten:
            pad = self.doelmap / f"{recept.slug}.md"
            if pad.exists():
                self.overgeslagen_bestanden.append(recept.slug)
                continue
            inhoud = self._frontmatter(recept) + "\n\n" + recept.bereiding + "\n"
            pad.write_text(inhoud, encoding="utf-8")
            self.geschreven += 1

    def _rapport(self, recepten: list[Recept]) -> None:
        """Toon een overzicht van de import in de terminal."""
        print(f"\n{len(recepten)} recepten gevonden in {self.bronbestand.name}")
        print(f"{self.geschreven} nieuwe Markdown-bestanden geschreven naar {self.doelmap}")
        if self.overgeslagen_bestanden:
            print(
                f"\n{len(self.overgeslagen_bestanden)} bestanden bestonden al en zijn NIET overschreven:"
            )
            for slug in self.overgeslagen_bestanden:
                print(f"  - {slug}.md")
        if self.overgeslagen_secties:
            print(
                f"\n{len(self.overgeslagen_secties)} secties overgeslagen (geen Benodigdheden):"
            )
            for titel in self.overgeslagen_secties:
                print(f"  - {titel}")
        meldingen = [
            (r.titel, w) for r in recepten for w in r.waarschuwingen
        ] + [("(algemeen)", w) for w in self.waarschuwingen]
        if meldingen:
            print(f"\n{len(meldingen)} punten vragen aandacht:")
            for titel, tekst in meldingen:
                print(f"  - {titel}: {tekst}")
        print()


def main() -> None:
    """Startpunt voor het importscript."""
    ReceptenImporter().run()


if __name__ == "__main__":
    main()
