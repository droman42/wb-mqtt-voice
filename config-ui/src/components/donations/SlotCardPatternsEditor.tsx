/**
 * SlotCardPatternsEditor (UI-3) — card-based replacement for the raw SlotPatternsEditor. A slot maps a label
 * (e.g. DURATION_VALUE) to a list of "ways to find the value", each edited via CardPatternsEditor on the UI-2
 * patternModel.
 */

import { useState } from 'react';
import { Trash2, Plus } from 'lucide-react';
import CardPatternsEditor from './CardPatternsEditor';
import type { SpacyPattern } from '@/utils/patternModel';

type SlotPatterns = Record<string, SpacyPattern[]>;

interface SlotCardPatternsEditorProps {
  value: SlotPatterns;
  onChange: (value: SlotPatterns) => void;
  disabled?: boolean;
}

export default function SlotCardPatternsEditor({ value, onChange, disabled = false }: SlotCardPatternsEditorProps) {
  const slots = value ?? {};
  const [newSlot, setNewSlot] = useState('');

  const setSlot = (label: string, patterns: SpacyPattern[]): void => onChange({ ...slots, [label]: patterns });
  const delSlot = (label: string): void => {
    const next = { ...slots };
    delete next[label];
    onChange(next);
  };
  const addSlot = (): void => {
    const label = newSlot.trim();
    if (!label || label in slots) return;
    onChange({ ...slots, [label]: [] });
    setNewSlot('');
  };

  return (
    <div className="space-y-3">
      {Object.keys(slots).length === 0 && <div className="text-sm text-gray-500">No value slots.</div>}
      {Object.entries(slots).map(([label, patterns]) => (
        <div key={label} className="border rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium">
              Slot: <span className="font-mono bg-gray-50 px-2 py-0.5 rounded">{label}</span>
            </div>
            <button
              type="button"
              className="p-1 rounded-lg border hover:bg-gray-50 disabled:opacity-50"
              onClick={() => delSlot(label)} disabled={disabled} title="Remove slot"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
          <CardPatternsEditor
            value={patterns ?? []}
            onChange={(p) => setSlot(label, p)}
            disabled={disabled}
            itemLabel="way to find the value"
          />
        </div>
      ))}
      <div className="flex items-center gap-2">
        <input
          className="border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          placeholder="slot name (e.g. DURATION_VALUE)"
          value={newSlot}
          onChange={(e) => setNewSlot(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') addSlot(); }}
          disabled={disabled}
        />
        <button
          type="button"
          className="inline-flex items-center gap-2 px-3 py-2 border rounded-xl hover:bg-gray-50 disabled:opacity-50 text-sm"
          onClick={addSlot} disabled={disabled || !newSlot.trim()}
        >
          <Plus className="w-4 h-4" /> Add slot
        </button>
      </div>
    </div>
  );
}
