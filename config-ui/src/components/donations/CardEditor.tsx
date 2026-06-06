/**
 * CardEditor (UI-3) — edits ONE word card of a "way of saying it" (UI-1 §3.2), on the UI-2 patternModel.
 *
 * Persona-facing: a kind picker (a word / one of several words / a number / any word / the rest) + the per-kind
 * input + two plain modifiers (optional, can repeat). The raw-spaCy escape hatch (§5) is a per-card "Advanced"
 * button that converts the card to its raw dict (edited via SpacyAttributeEditor); "Back to cards" decompiles it,
 * and if the raw is too advanced to represent it stays raw with a note — data is never lost.
 *
 * (Strings are literal for now; UI-7 moves them to i18n.)
 */

import { Trash2, Wrench } from 'lucide-react';
import Input from '@/components/ui/Input';
import Toggle from '@/components/ui/Toggle';
import ArrayOfStringsEditor from '@/components/editors/ArrayOfStringsEditor';
import SpacyAttributeEditor from '@/components/editors/SpacyAttributeEditor';
import {
  type Card, type Attr, compileToken, decompileToken,
} from '@/utils/patternModel';

type FriendlyKind = 'word' | 'oneOf' | 'number' | 'anyWord' | 'rest';

const KIND_LABELS: Record<FriendlyKind, string> = {
  word: 'A word',
  oneOf: 'One of several words',
  number: 'A number',
  anyWord: 'Any word',
  rest: 'The rest of the sentence',
};
const KIND_HELP: Record<FriendlyKind, string> = {
  word: 'Matches this word. Turn on “include its forms” so “set / sets / setting” all match.',
  oneOf: 'Matches if the user says any one of these — e.g. timer / alarm / countdown.',
  number: 'Matches a number, like 5 or 10.',
  anyWord: 'A placeholder for a single word you’ll capture — e.g. a name or label.',
  rest: 'Captures everything the user says after this point — e.g. a timer note.',
};

function freshCard(kind: FriendlyKind, prev: Card): Card {
  const mods = 'optional' in prev || 'repeat' in prev
    ? { optional: (prev as { optional?: boolean }).optional, repeat: (prev as { repeat?: boolean }).repeat }
    : {};
  switch (kind) {
    case 'word': return { kind: 'word', attr: 'LOWER', word: '', ...mods };
    case 'oneOf': return { kind: 'oneOf', attr: 'LOWER', via: 'in', words: [], ...mods };
    case 'number': return { kind: 'number', via: 'likeNum', ...mods };
    case 'anyWord': return { kind: 'anyWord', ...mods };
    case 'rest': return { kind: 'rest', ...mods };
  }
}

interface CardEditorProps {
  card: Card;
  onChange: (card: Card) => void;
  onRemove: () => void;
  disabled?: boolean;
}

export default function CardEditor({ card, onChange, onRemove, disabled = false }: CardEditorProps) {
  const isAdvanced = card.kind === 'advanced';

  const setForms = (on: boolean): void => {
    const attr: Attr = on ? 'LEMMA' : 'LOWER';
    if (card.kind === 'word' || card.kind === 'oneOf') onChange({ ...card, attr });
  };
  const formsOn = (card.kind === 'word' || card.kind === 'oneOf') && card.attr === 'LEMMA';

  return (
    <div className="border rounded-lg p-2 bg-white">
      <div className="flex items-center gap-2 mb-2">
        {isAdvanced ? (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-purple-700">
            <Wrench className="w-3 h-3" /> Advanced rule
          </span>
        ) : (
          <select
            className="border rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            value={card.kind}
            onChange={(e) => onChange(freshCard(e.target.value as FriendlyKind, card))}
            disabled={disabled}
          >
            {(Object.keys(KIND_LABELS) as FriendlyKind[]).map((k) => (
              <option key={k} value={k}>{KIND_LABELS[k]}</option>
            ))}
          </select>
        )}
        <div className="flex-1" />
        {isAdvanced ? (
          <button
            type="button"
            className="text-xs px-2 py-1 border rounded-lg hover:bg-gray-50 disabled:opacity-50"
            onClick={() => onChange(decompileToken(card.raw))}
            disabled={disabled}
            title="Try to show this as cards"
          >
            Back to cards
          </button>
        ) : (
          <button
            type="button"
            className="text-xs px-2 py-1 border rounded-lg hover:bg-gray-50 disabled:opacity-50"
            onClick={() => onChange({ kind: 'advanced', raw: compileToken(card) })}
            disabled={disabled}
            title="Edit the raw spaCy token"
          >
            Advanced
          </button>
        )}
        <button
          type="button"
          className="p-1 rounded-lg border hover:bg-gray-50 disabled:opacity-50"
          onClick={onRemove} disabled={disabled} title="Remove"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {isAdvanced ? (
        <div>
          <SpacyAttributeEditor
            value={card.raw}
            onChange={(raw) => onChange({ kind: 'advanced', raw })}
            disabled={disabled}
          />
          {Object.keys(card.raw).length === 0 && (
            <p className="text-xs text-gray-500 mt-1">Empty token. Add attributes, or switch back to cards.</p>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-gray-500">{KIND_HELP[card.kind]}</p>
          {card.kind === 'word' && (
            <Input label="" value={card.word} onChange={(v) => onChange({ ...card, word: v })}
              placeholder="word…" disabled={disabled} />
          )}
          {card.kind === 'oneOf' && (
            <ArrayOfStringsEditor label="" value={card.words}
              onChange={(words) => onChange({ ...card, words })} disabled={disabled} placeholder="word…" />
          )}
          {(card.kind === 'word' || card.kind === 'oneOf') && (
            <Toggle label="include its forms (set / sets / setting)" checked={formsOn}
              onChange={setForms} disabled={disabled} />
          )}
          <div className="flex items-center gap-4">
            <Toggle label="optional" checked={!!card.optional}
              onChange={(v) => onChange({ ...card, optional: v, repeat: v ? false : card.repeat })} disabled={disabled} />
            <Toggle label="can repeat" checked={!!card.repeat}
              onChange={(v) => onChange({ ...card, repeat: v, optional: v ? false : card.optional })} disabled={disabled} />
          </div>
        </div>
      )}
    </div>
  );
}
