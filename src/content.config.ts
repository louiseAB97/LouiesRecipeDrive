import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const recipes = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/recipes" }),
  schema: z.object({
    title: z.string().min(1),
    persons: z.number().int().positive().nullable().default(null),
    price: z.string().min(1).nullable().default(null),
    tags: z
      .array(z.string().regex(/^[a-z0-9]+(-[a-z0-9]+)*$/, "Tags: lowercase letters and hyphens"))
      .refine((tags) => new Set(tags).size === tags.length, "Tags must be unique")
      .default([]),
    cookingtime: z.number().int().positive().nullable().default(null),
    concept: z.boolean().default(false),
    intro: z.string().min(1).nullable().default(null),
    ingredients: z.array(z.string().min(1)).default([]),
    notes: z.string().min(1).nullable().default(null),
  }),
});

export const collections = { recipes };
