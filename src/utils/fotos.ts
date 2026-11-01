import type { ImageMetadata } from "astro";

/**
 * Vindt receptfoto's in src/assets/recepten/ op basis van de slug.
 *
 * Bestandsnamen bepalen de volgorde:
 * - `<slug>.jpg`           -> hoofdfoto
 * - `<slug>-2.jpg` e.d.    -> extra foto's (oplopend)
 */
const modules = import.meta.glob<{ default: ImageMetadata }>(
  "../assets/recepten/*.{jpg,jpeg,png,webp,avif}",
  { eager: true },
);

export function fotosPerRecept(): Map<string, ImageMetadata[]> {
  const map = new Map<string, { volgorde: number; meta: ImageMetadata }[]>();
  for (const [pad, mod] of Object.entries(modules)) {
    const bestand = pad.split("/").pop() ?? "";
    const match = bestand.match(/^(.*?)(?:-(\d+))?\.(jpe?g|png|webp|avif)$/i);
    if (!match) continue;
    const [, slug, nummer] = match;
    const lijst = map.get(slug) ?? [];
    lijst.push({ volgorde: nummer ? Number(nummer) : 0, meta: mod.default });
    map.set(slug, lijst);
  }
  const resultaat = new Map<string, ImageMetadata[]>();
  for (const [slug, lijst] of map) {
    lijst.sort((a, b) => a.volgorde - b.volgorde);
    resultaat.set(
      slug,
      lijst.map((f) => f.meta),
    );
  }
  return resultaat;
}
