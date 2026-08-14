import { useCallback, useEffect, useRef, useState } from "preact/hooks";

type Updater<T> = T | ((previous: T) => T);

/**
 * Persistent state, scoped to the browser.
 *
 * Everything this course remembers about a learner stays on their machine.
 * There is no account, no backend, and nothing to opt out of.
 *
 * The setter accepts an updater function as well as a value, and callers
 * should prefer it whenever the next state depends on the current one. Two
 * updates dispatched before the next render both close over the same stale
 * value, so `set(value + 1)` twice in a tick advances by one and the first
 * change is silently lost. The quiz hit exactly that: answering two questions
 * quickly recorded only the second.
 */
export function useStored<T>(key: string, initial: T): [T, (next: Updater<T>) => void] {
  const [value, setValue] = useState<T>(initial);
  const [loaded, setLoaded] = useState(false);
  // Tracks the newest value synchronously, so an updater run before the next
  // render still sees what the previous call just wrote.
  const latest = useRef<T>(initial);

  // Read after mount so the server-rendered HTML and the first client render
  // agree. Reading during render would cause a hydration mismatch.
  useEffect(() => {
    try {
      const stored = localStorage.getItem(key);
      if (stored !== null) {
        const parsed = JSON.parse(stored) as T;
        latest.current = parsed;
        setValue(parsed);
      }
    } catch {
      /* Private mode, disabled storage, or corrupt JSON. Defaults are fine. */
    }
    setLoaded(true);
  }, [key]);

  const update = useCallback(
    (next: Updater<T>) => {
      const resolved =
        typeof next === "function" ? (next as (previous: T) => T)(latest.current) : next;
      latest.current = resolved;
      setValue(resolved);
      try {
        localStorage.setItem(key, JSON.stringify(resolved));
      } catch {
        /* Storage unavailable. The page still works for this session. */
      }
    },
    [key],
  );

  return [loaded ? value : initial, update];
}
