import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const recepten = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/recepten" }),
  schema: z.object({
    titel: z.string().min(1),
    personen: z.number().int().positive().nullable().default(null),
    prijs: z.string().min(1).nullable().default(null),
    tags: z
      .array(z.string().regex(/^[a-z0-9]+(-[a-z0-9]+)*$/, "Tags: kleine letters en koppeltekens"))
      .refine((tags) => new Set(tags).size === tags.length, "Tags moeten uniek zijn")
      .default([]),
    tijd: z.number().int().positive().nullable().default(null),
    concept: z.boolean().default(false),
    intro: z.string().min(1).nullable().default(null),
    ingredienten: z.array(z.string().min(1)).default([]),
    toelichting: z.string().min(1).nullable().default(null),
  }),
});

export const collections = { recepten };
