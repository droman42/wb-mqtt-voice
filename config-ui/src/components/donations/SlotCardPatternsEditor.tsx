/**
 * SlotCardPatternsEditor (UI-3) — card-based replacement for the raw SlotPatternsEditor. A slot maps a label
 * (e.g. DURATION_VALUE) to a list of "ways to find the value", each edited via CardPatternsEditor on the UI-2
 * patternModel.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Trash2, Plus } from 'lucide-react';
import { Button, Input, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import CardPatternsEditor from './CardPatternsEditor';
import type { SpacyPattern } from '@/utils/patternModel';

type SlotPatterns = Record<string, SpacyPattern[]>;

interface SlotCardPatternsEditorProps {
  value: SlotPatterns;
  onChange: (value: SlotPatterns) => void;
  disabled?: boolean;
}

export default function SlotCardPatternsEditor({ value, onChange, disabled = false }: SlotCardPatternsEditorProps) {
  const { t } = useTranslation('donations');
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
      {Object.keys(slots).length === 0 && <div className="text-sm text-muted-foreground">{t('slots.empty')}</div>}
      {Object.entries(slots).map(([label, patterns]) => (
        <div key={label} className="border border-border rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium">
              {t('slots.slotLabel')} <span className="font-mono bg-muted px-2 py-0.5 rounded">{label}</span>
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-destructive"
                  onClick={() => delSlot(label)} disabled={disabled} aria-label={t('slots.removeSlot')}
                >
                  <Trash2 />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{t('slots.removeSlot')}</TooltipContent>
            </Tooltip>
          </div>
          <CardPatternsEditor
            value={patterns ?? []}
            onChange={(p) => setSlot(label, p)}
            disabled={disabled}
            itemLabel={t('slots.itemLabel')}
          />
        </div>
      ))}
      <div className="flex items-center gap-2">
        <Input
          className="max-w-xs"
          placeholder={t('slots.newSlotPlaceholder')}
          value={newSlot}
          onChange={(e) => setNewSlot(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') addSlot(); }}
          disabled={disabled}
        />
        <Button
          type="button"
          variant="outline"
          onClick={addSlot} disabled={disabled || !newSlot.trim()}
        >
          <Plus /> {t('slots.addSlot')}
        </Button>
      </div>
    </div>
  );
}
