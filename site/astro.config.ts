import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import preact from "@astrojs/preact";
import { sidebarFromLabs, loadReference } from "./src/lib/labs";

export default defineConfig({
  site: "https://h-vance.github.io",
  base: "/prove-it-labs",
  trailingSlash: "ignore",
  integrations: [
    preact(),
    starlight({
      title: "Prove It",
      description:
        "A hands-on Technical Support Engineering course. Real incidents, symptom-only tickets, and a grader that shows its evidence.",
      customCss: ["./src/styles/custom.css"],
      // No `head` entries. There was one, and it read a setting that nothing
      // writes any more: see the note at the top of src/components/TierToggle.tsx
      // for what it did and the exact line to restore alongside that control.
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/h-vance/prove-it-labs",
        },
      ],
      sidebar: [
        { label: "Start here", link: "/" },
        { label: "How this works", link: "/how-it-works" },
        { label: "Where do I begin?", link: "/start" },
        { label: "What you can prove", link: "/proof" },
        ...sidebarFromLabs(),
        {
          label: "Reference",
          items: loadReference().map((doc) => ({
            label: doc.title,
            link: `/reference/${doc.slug}`,
          })),
        },
      ],
      pagination: true,
    }),
  ],
});
