/**
 * useDecompiledPatterns (UI-12 / C6) — the controlled "decompile in local state, compile on edit"
 * scaffold shared by CardPatternsEditor and ExtractionFillersEditor.
 *
 * A pattern editor is controlled over a compiled `value: TCompiled[]` but edits a decompiled view
 * (`TDecompiled[]`) so advanced raw-dict editing stays stable (no decompile flicker); an external
 * change (Cancel/revert/method switch) re-syncs from props. `emit` compiles the edited view, records
 * it so the re-sync effect can tell self-edits from external changes, and bubbles it up via onChange.
 *
 * `decompile`/`compile` are expected to be stable (module-level) functions.
 */
import { useEffect, useRef, useState } from 'react';

export function useDecompiledPatterns<TCompiled, TDecompiled>(
  value: TCompiled[],
  onChange: (value: TCompiled[]) => void,
  decompile: (value: TCompiled[]) => TDecompiled[],
  compile: (value: TDecompiled[]) => TCompiled[],
): [TDecompiled[], (next: TDecompiled[]) => void] {
  const [items, setItems] = useState<TDecompiled[]>(() => decompile(value ?? []));
  const lastEmitted = useRef<TCompiled[]>(value ?? []);

  useEffect(() => {
    if (value !== lastEmitted.current) { // external change (revert / method switch) — re-sync
      setItems(decompile(value ?? []));
      lastEmitted.current = value ?? [];
    }
  }, [value, decompile]);

  const emit = (next: TDecompiled[]): void => {
    setItems(next);
    const compiled = compile(next);
    lastEmitted.current = compiled;
    onChange(compiled);
  };

  return [items, emit];
}
