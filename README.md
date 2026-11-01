# Louie's Recipe Drive

Een snelle, statische receptensite gebouwd met [Astro](https://astro.build).
De recepten staan als losse Markdown-bestanden in `src/content/recepten/` —
dat is de enige bron van waarheid. Er is geen database en geen server.

## Benodigd

- **Node.js** — geïnstalleerd in `~/.local/node`. Zit `node` niet in je
  PATH, voeg dan deze regel toe aan `~/.zshrc` en open een nieuwe terminal:

  ```sh
  export PATH="$HOME/.local/node/bin:$PATH"
  ```

- **uv** — voor de Python-scripts (`import` en `status`). uv regelt zelf de
  juiste Python-versie (zie `.python-version`) en de virtuele omgeving
  (`.venv`) aan de hand van `pyproject.toml` en `uv.lock`.

## Commando's

| Commando          | Wat het doet                                                   |
| ----------------- | -------------------------------------------------------------- |
| `npm install`     | Installeert de site-afhankelijkheden (eenmalig).               |
| `npm run dev`     | Start de site lokaal op <http://localhost:4321>.               |
| `npm run build`   | Bouwt de statische site naar `dist/` (dat zet je online).      |
| `npm run preview` | Bekijkt de gebouwde versie lokaal.                             |
| `npm run import`  | Leest `recepten.txt` en maakt ontbrekende `.md`-bestanden aan. |
| `npm run status`  | Toont wat er per recept nog ontbreekt en schrijft `overzicht.json`. |

## Werkwijze

### Recept aanpassen of toevoegen

Elk recept is één bestand: `src/content/recepten/<slug>.md`. Bewerk de
frontmatter bovenin en de bereiding eronder (gewone Markdown).

```yaml
---
titel: Penne met room en rucola
personen: 4            # aantal personen, of null
prijs: "Circa 3 euro"  # vrij veld, of null
tags: [pasta, snel]    # kleine letters, koppeltekens, uniek
tijd: 20               # bereidingstijd in minuten, of null
concept: false         # true = niet publiceren
intro: null            # persoonlijke noot; Markdown toegestaan
ingredienten:
  - Penne
  - Tofu*              # * verwijst naar de toelichting
toelichting: null      # tekst onder de ingrediënten; begint met "* "
---

De bereiding als Markdown.
```

- **intro** — een persoonlijke noot boven de bereiding. Gebruik `intro: |`
  en laat de regels eronder met twee spaties inspringen beginnen; lege
  regels maken nieuwe alinea's.
- **toelichting** — uitleg bij een ingrediënt met `*`. Begin de tekst met
  `\* ` (de backslash zorgt dat de ster letterlijk zichtbaar blijft).
- **concept: true** — het recept wordt niet gebouwd en nergens getoond.
- Velden die je niet weet: laat ze op `null` staan, haal ze niet weg.

### Foto's toevoegen

Zet foto's in `src/assets/recepten/`. De bestandsnaam bepaalt alles:

- `penne-met-room-en-rucola.jpg` → hoofdfoto
- `penne-met-room-en-rucola-2.jpg`, `-3.jpg`, … → extra foto's

Toegestane formaten: `jpg`, `jpeg`, `png`, `webp`, `avif`. De site vindt,
verkleint en optimaliseert ze automatisch — er hoeft niets in de frontmatter.
Geen foto's is ook prima: de pagina bouwt dan zonder afbeelding.

### Status bekijken

```sh
npm run status
```

Toont per recept wat ontbreekt (foto, personen, tags), hoeveel foto's er
zijn, en waarschuwt bij een `*` zonder toelichting of andersom. Schrijft
ook `overzicht.json` (automatisch gegenereerd, niet aanpassen).

### Opnieuw importeren

```sh
npm run import
```

Bestaande `.md`-bestanden worden **nooit overschreven** — alleen nieuwe
recepten krijgen een bestand. Handmatige aanpassingen blijven dus behouden.

## Online zetten (Cloudflare Pages)

1. Push deze repo naar GitHub.
2. Ga naar de Cloudflare-dashboard → **Workers & Pages** → **Create** →
   **Pages** → **Connect to Git** en kies de repo.
3. Instellingen: build command `npm run build`, output directory `dist`.
4. Elke `git push` naar de hoofdbranch bouwt de site dan automatisch opnieuw.
5. Pas daarna het domein in `astro.config.mjs` (`site:`) en `public/robots.txt`
   aan naar je eigen domein, en commit opnieuw.

## Structuur

```text
recepten.txt              bronbestand (eenmalige import)
scripts/importeren.py     import-script  → npm run import
scripts/status.py         statusscript   → npm run status
src/content/recepten/     de recepten (Markdown, bron van waarheid)
src/assets/recepten/      receptfoto's (naamgeving: <slug>.jpg, <slug>-2.jpg)
src/styles/               design tokens + basisstijl (kleuren, fonts, maten)
src/layouts/              Basis.astro (alles) en Recept.astro (receptpagina)
src/components/           bouwblokken (galerij, ingredienten, kaart, slots, ...)
src/pages/                routes: /, /recepten, /recepten/<slug>, /tags,
                          /tag/<naam>, /zoeken, /over, /privacy, 404
overzicht.json            gegenereerd door `npm run status` (niet bewerken)
```

## Later (al voorbereid)

- **Affiliate/advertenties**: herkenbare slot-componenten
  (`AffiliateSlot`, `NieuwsbriefBlok`) — centraal aan te passen.
- **Analytics**: privacyvriendelijk (Plausible/Umami), geen cookiebanner nodig.
- **Zoeken**: nu simpel in de browser; later uit te breiden met Pagefind.
