import { statSync } from "node:fs";
import { join } from "node:path";
import type { CollectionEntry } from "astro:content";

type Recept = CollectionEntry<"recipes">;

/** Wijzigingsdatum van het bronbestand = "nieuwste" recept. */
function wijzigingsdatum(recept: Recept): number {
  try {
    const pad = join(process.cwd(), "src/content/recipes", `${recept.id}.md`);
    return statSync(pad).mtimeMs;
  } catch {
    return 0;
  }
}

function normaliseer(tekst: string): string {
  return tekst.trim().toLowerCase().replace(/\s*\*+$/, "");
}

function gedeeldeTags(a: Recept, b: Recept): number {
  const tagsA = new Set(a.data.tags);
  return b.data.tags.filter((t) => tagsA.has(t)).length;
}

function gedeeldeIngredienten(a: Recept, b: Recept): number {
  const setA = new Set(a.data.ingredients.map(normaliseer));
  return b.data.ingredients.filter((i) => setA.has(normaliseer(i))).length;
}

/**
 * Kies suggestierecepten: eerst de meeste gedeelde tags, dan de meeste
 * gedeelde ingrediënten, dan de nieuwste. Zijn er te weinig matches met
 * een gedeelde tag, vul dan aan met de nieuwste recepten.
 */
export function kiesSuggesties(huidig: Recept, alle: Recept[], aantal = 3): Recept[] {
  const anderen = alle.filter((r) => r.id !== huidig.id);
  const gesorteerd = anderen.sort(
    (x, y) =>
      gedeeldeTags(huidig, y) - gedeeldeTags(huidig, x) ||
      gedeeldeIngredienten(huidig, y) - gedeeldeIngredienten(huidig, x) ||
      wijzigingsdatum(y) - wijzigingsdatum(x),
  );
  return gesorteerd.slice(0, aantal);
}
