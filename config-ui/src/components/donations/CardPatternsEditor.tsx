/**
 * CardPatternsEditor (UI-3) — the persona-facing replacement for the raw TokenPatternsEditor. Edits a list of
 * "ways of saying it" (spaCy `token_patterns` / a slot's patterns) as rows of word cards (CardEditor) on the UI-2
 * patternModel.
 *
 * It is a controlled component over `value: SpacyPattern[]` but keeps the decompiled CardPattern[] in local state
 * and only compiles back on user edits — so editing an Advanced card's raw dict stays stable (no decompile flicker)
 * and an external reset (Cancel/revert/method switch) re-syncs from props.
 */

import { useState, useEffect, useRef } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import CardEditor from './CardEditor';
import {
  type SpacyPattern, type Card, type CardPattern,
  decompilePatterns, compilePatterns,
} from '@/utils/patternModel';

interface CardPatternsEditorProps {
  value: SpacyPattern[];
  onChange: (value: SpacyPattern[]) => void;
  disabled?: boolean;
  /** Persona label for one entry, e.g. "way of saying it" or "way to find the value". */
  itemLabel?: string;
}

export default function CardPatternsEditor({
  value, onChange, disabled = false, itemLabel = 'way of saying it',
}: CardPatternsEditorProps) {
  const [patterns, setPatterns] = useState<CardPattern[]>(() => decompilePatterns(value ?? []));
  const lastEmitted = useRef<SpacyPattern[]>(value ?? []);

  useEffect(() => {
    if (value !== lastEmitted.current) { // external change (revert / method switch) — re-sync
      setPatterns(decompilePatterns(value ?? []));
      lastEmitted.current = value ?? [];
    }
  }, [value]);

  const emit = (next: CardPattern[]): void => {
    setPatterns(next);
    const compiled = compilePatterns(next);
    lastEmitted.current = compiled;
    onChange(compiled);
  };

  const setCard = (pi: number, ci: number, card: Card): void =>
    emit(patterns.map((p, i) => (i === pi ? p.map((c, j) => (j === ci ? card : c)) : p)));
  const removeCard = (pi: number, ci: number): void =>
    emit(patterns.map((p, i) => (i === pi ? p.filter((_, j) => j !== ci) : p)));
  const addCard = (pi: number): void =>
    emit(patterns.map((p, i) => (i === pi ? [...p, { kind: 'word', attr: 'LOWER', word: '' } as Card] : p)));
  const removePattern = (pi: number): void => emit(patterns.filter((_, i) => i !== pi));
  const addPattern = (): void => emit([...patterns, []]);

  return (
    <div className="space-y-3">
      {patterns.length === 0 && (
        <div className="text-sm text-gray-500">No {itemLabel}s yet.</div>
      )}
      {patterns.map((pattern, pi) => (
        <div key={pi} className="border rounded-xl p-3 bg-gray-50">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium capitalize">{itemLabel} {pi + 1}</div>
            <button
              type="button"
              className="p-1 rounded-lg border bg-white hover:bg-gray-50 disabled:opacity-50"
              onClick={() => removePattern(pi)} disabled={disabled} title={`Remove ${itemLabel}`}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {pattern.map((card, ci) => (
              <CardEditor
                key={ci}
                card={card}
                onChange={(c) => setCard(pi, ci, c)}
                onRemove={() => removeCard(pi, ci)}
                disabled={disabled}
              />
            ))}
            <button
              type="button"
              className="inline-flex items-center gap-2 px-3 py-2 border rounded-lg bg-white hover:bg-gray-50 disabled:opacity-50 text-sm"
              onClick={() => addCard(pi)} disabled={disabled}
            >
              <Plus className="w-4 h-4" /> Add word
            </button>
          </div>
        </div>
      ))}
      <button
        type="button"
        className="inline-flex items-center gap-2 px-3 py-2 border rounded-xl hover:bg-gray-50 disabled:opacity-50"
        onClick={addPattern} disabled={disabled}
      >
        <Plus className="w-4 h-4" /> Add another {itemLabel}
      </button>
    </div>
  );
}
