import { useCallback, useEffect, useState } from "preact/hooks";

/**
 * Persistent state, scoped to the browser.
 *
 * Everything this course remembers about a learner stays on their machine.
 * There is no account, no backend, and nothing to opt out of.
 */
export function useStored<T>(key: string, initial: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(initial);
  const [loaded, setLoaded] = useState(false);

  // Read after mount so the server-rendered HTML and the first client render
  // agree. Reading during render would cause a hydration mismatch.
  useEffect(() => {
    try {
      const stored = localStorage.getItem(key);
      if (stored !== null) setValue(JSON.parse(stored) as T);
    } catch {
      /* Private mode, disabled storage, or corrupt JSON. Defaults are fine. */
    }
    setLoaded(true);
  }, [key]);

  const update = useCallback(
    (next: T) => {
      setValue(next);
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* Storage unavailable. The page still works for this session. */
      }
    },
    [key],
  );

  return [loaded ? value : initial, update];
}
