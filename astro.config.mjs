// @ts-check
import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

// Vul hier het definitieve domein in zodra de site live staat,
// bijvoorbeeld "https://louiesrecipedrive.nl".
export default defineConfig({
  site: "https://louies-recipe-drive.pages.dev",
  integrations: [sitemap()],
});
