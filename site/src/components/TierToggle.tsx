import { useEffect } from "preact/hooks";
import { useStored } from "./storage";

/**
 * Hides stretch material outright rather than styling it as optional.
 *
 * "Advanced" sections marked and left on the page still cost attention to skip,
 * and on a bad day that cost is the difference between finishing a lesson and
 * closing the tab. Off means gone.
 *
 * The flag is mirrored onto <html> so CSS can act on it without waiting for
 * this component.
 *
 * DORMANT. Nothing renders this today, because all twenty five exercises are
 * `tier: core` and there is no stretch material for it to hide. It was shipped
 * on the "How this works" page, and both that page and the README described a
 * setting that could not change anything a reader would see.
 *
 * The component and its CSS rule are kept because they are correct and, being
 * unimported, cost nothing in the build. Restoring the control means three
 * things, and missing the third causes stretch content to appear and then
 * vanish on every page load, which is worse than never hiding it:
 *
 *   1. Give at least one exercise `tier: stretch` in its meta.yaml. The gate in
 *      tools/tests/test_content.py refuses the claim without the content.
 *   2. Render <TierToggle client:load /> on how-it-works.mdx again.
 *   3. Put this back in the `head` array of astro.config.ts, so the flag is
 *      applied before first paint rather than after hydration:
 *
 *      try{document.documentElement.dataset.stretch=
 *      JSON.parse(localStorage.getItem('proveit:stretch'))?'shown':'hidden'}
 *      catch(e){document.documentElement.dataset.stretch='hidden'}
 */
export default function TierToggle() {
  const [showStretch, setShowStretch] = useStored("proveit:stretch", false);

  useEffect(() => {
    document.documentElement.dataset.stretch = showStretch ? "shown" : "hidden";
  }, [showStretch]);

  return (
    <div class="tier">
      <label class="tier__control">
        <input
          type="checkbox"
          checked={showStretch}
          onChange={(event) => setShowStretch((event.target as HTMLInputElement).checked)}
        />
        <span>Show stretch material</span>
      </label>
      <p class="tier__help">
        {showStretch
          ? "Stretch exercises and asides are visible. They are genuinely optional."
          : "Showing core material only. Nothing required is hidden."}
      </p>
    </div>
  );
}
