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
 * this component, and an inline script in the head applies it before first
 * paint so stretch content never flashes in and out.
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
