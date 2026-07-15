/**
 * CardPatternsEditor (UI-3) — the persona-facing replacement for the raw TokenPatternsEditor. Edits a list of
 * "ways of saying it" (spaCy `token_patterns` / a slot's patterns) as rows of word cards (CardEditor) on the UI-2
 * patternModel.
 *
 * It is a controlled component over `value: SpacyPattern[]` but keeps the decompiled CardPattern[] in local state
 * and only compiles back on user edits — so editing an Advanced card's raw dict stays stable (no decompile flicker)
 * and an external reset (Cancel/revert/method switch) re-syncs from props.
 */

import { useTranslation } from 'react-i18next';
import { Plus, Trash2 } from 'lucide-react';
import { Button, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import CardEditor from './CardEditor';
import { useDecompiledPatterns } from '@/hooks/useDecompiledPatterns';
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
  value, onChange, disabled = false, itemLabel,
}: CardPatternsEditorProps) {
  const { t } = useTranslation('donations');
  const item = itemLabel ?? t('cards.list.defaultItemLabel');
  const [patterns, emit] = useDecompiledPatterns<SpacyPattern, CardPattern>(
    value, onChange, decompilePatterns, compilePatterns);

  const setCard = (pi: number, ci: number, card: Card): void =>
    emit(patterns.map((p, i) => (i === pi ? p.map((c, j) => (j === ci ? card : c)) : p)));
  const removeCard = (pi: number, ci: number): void =>
    emit(patterns.map((p, i) => (i === pi ? p.filter((_, j) => j !== ci) : p)));
  const addCard = (pi: number): void =>
    emit(patterns.map((p, i) => (i === pi ? [...p, { kind: 'word', attr: 'LOWER', word: '' }] : p)));
  const removePattern = (pi: number): void => emit(patterns.filter((_, i) => i !== pi));
  const addPattern = (): void => emit([...patterns, []]);

  return (
    <div className="space-y-3">
      {patterns.length === 0 && (
        <div className="text-sm text-muted-foreground">{t('cards.list.empty', { item })}</div>
      )}
      {patterns.map((pattern, pi) => (
        <div key={pi} className="border border-border rounded-xl p-3 bg-muted">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium capitalize">{t('cards.list.entry', { item, index: pi + 1 })}</div>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive"
                  onClick={() => removePattern(pi)} disabled={disabled} aria-label={t('cards.list.removeItem', { item })}
                >
                  <Trash2 />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{t('cards.list.removeItem', { item })}</TooltipContent>
            </Tooltip>
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
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => addCard(pi)} disabled={disabled}
            >
              <Plus /> {t('cards.list.addWord')}
            </Button>
          </div>
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        onClick={addPattern} disabled={disabled}
      >
        <Plus /> {t('cards.list.addAnother', { item })}
      </Button>
    </div>
  );
}
