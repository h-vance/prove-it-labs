import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import preact from "@astrojs/preact";
import { sidebarFromLabs, loadReference } from "./src/lib/labs";

export default defineConfig({
  site: "https://h-vance.github.io",
  base: "/technical-support-engineering",
  trailingSlash: "ignore",
  integrations: [
    preact(),
    starlight({
      title: "Prove It",
      description:
        "A hands-on Technical Support Engineering course. Real incidents, symptom-only tickets, and a grader that shows its evidence.",
      customCss: ["./src/styles/custom.css"],
      head: [
        {
          // Applied before first paint so stretch material never flashes in
          // and then disappears, which is worse than never hiding it.
          tag: "script",
          content:
            "try{document.documentElement.dataset.stretch=" +
            "JSON.parse(localStorage.getItem('proveit:stretch'))?'shown':'hidden'}" +
            "catch(e){document.documentElement.dataset.stretch='hidden'}",
        },
      ],
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/h-vance/technical-support-engineering",
        },
      ],
      sidebar: [
        { label: "Start here", link: "/" },
        { label: "How this works", link: "/how-it-works" },
        { label: "Where do I begin?", link: "/start" },
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
