/**
 * CardEditor (UI-3) — edits ONE word card of a "way of saying it" (UI-1 §3.2), on the UI-2 patternModel.
 *
 * Persona-facing: a kind picker (a word / one of several words / a number / any word / the rest) + the per-kind
 * input + two plain modifiers (optional, can repeat). The raw-spaCy escape hatch (§5) is a per-card "Advanced"
 * button that converts the card to its raw dict (edited via SpacyAttributeEditor); "Back to cards" decompiles it,
 * and if the raw is too advanced to represent it stays raw with a note — data is never lost.
 */

import { useTranslation } from 'react-i18next';
import { Trash2, Wrench } from 'lucide-react';
import {
  Button, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Tooltip, TooltipTrigger, TooltipContent,
} from 'locveil-ui-kit';
import Badge from '@/components/ui/Badge';
import Input from '@/components/ui/Input';
import Toggle from '@/components/ui/Toggle';
import ArrayOfStringsEditor from '@/components/editors/ArrayOfStringsEditor';
import SpacyAttributeEditor from '@/components/editors/SpacyAttributeEditor';
import {
  type Card, type Attr, compileToken, decompileToken,
} from '@/utils/patternModel';

type FriendlyKind = 'word' | 'oneOf' | 'number' | 'anyWord' | 'rest';

const FRIENDLY_KINDS: FriendlyKind[] = ['word', 'oneOf', 'number', 'anyWord', 'rest'];

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
  const { t } = useTranslation('donations');
  const kindLabel = (k: FriendlyKind): string => t(`cards.kind.${k}.label`);
  const kindHelp = (k: FriendlyKind): string => t(`cards.kind.${k}.help`);
  const isAdvanced = card.kind === 'advanced';

  const setForms = (on: boolean): void => {
    const attr: Attr = on ? 'LEMMA' : 'LOWER';
    if (card.kind === 'word' || card.kind === 'oneOf') onChange({ ...card, attr });
  };
  const formsOn = (card.kind === 'word' || card.kind === 'oneOf') && card.attr === 'LEMMA';

  return (
    <div className="border border-border rounded-lg p-2 bg-card">
      <div className="flex items-center gap-2 mb-2">
        {isAdvanced ? (
          <Badge variant="custom" className="inline-flex items-center gap-1">
            <Wrench className="w-3 h-3" /> {t('cards.advancedRule')}
          </Badge>
        ) : (
          <Select
            value={card.kind}
            onValueChange={(v) => onChange(freshCard(v as FriendlyKind, card))}
            disabled={disabled}
          >
            <SelectTrigger className="h-8 w-auto gap-1 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FRIENDLY_KINDS.map((k) => (
                <SelectItem key={k} value={k}>{kindLabel(k)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <div className="flex-1" />
        {isAdvanced ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onChange(decompileToken(card.raw))}
                disabled={disabled}
              >
                {t('cards.backToCards')}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t('cards.backToCardsTitle')}</TooltipContent>
          </Tooltip>
        ) : (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onChange({ kind: 'advanced', raw: compileToken(card) })}
                disabled={disabled}
              >
                {t('cards.advanced')}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t('cards.advancedTitle')}</TooltipContent>
          </Tooltip>
        )}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-destructive"
              onClick={onRemove} disabled={disabled} aria-label={t('cards.removeTitle')}
            >
              <Trash2 />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('cards.removeTitle')}</TooltipContent>
        </Tooltip>
      </div>

      {isAdvanced ? (
        <div>
          <SpacyAttributeEditor
            value={card.raw}
            onChange={(raw) => onChange({ kind: 'advanced', raw })}
            disabled={disabled}
          />
          {Object.keys(card.raw).length === 0 && (
            <p className="text-xs text-muted-foreground mt-1">{t('cards.emptyToken')}</p>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">{kindHelp(card.kind)}</p>
          {card.kind === 'word' && (
            <Input label="" value={card.word} onChange={(v) => onChange({ ...card, word: v })}
              placeholder={t('cards.wordPlaceholder')} disabled={disabled} />
          )}
          {card.kind === 'oneOf' && (
            <ArrayOfStringsEditor label="" value={card.words}
              onChange={(words) => onChange({ ...card, words })} disabled={disabled} placeholder={t('cards.wordPlaceholder')} />
          )}
          {(card.kind === 'word' || card.kind === 'oneOf') && (
            <Toggle label={t('cards.includeForms')} checked={formsOn}
              onChange={setForms} disabled={disabled} />
          )}
          <div className="flex items-center gap-4">
            <Toggle label={t('cards.optional')} checked={!!card.optional}
              onChange={(v) => onChange({ ...card, optional: v, repeat: v ? false : card.repeat })} disabled={disabled} />
            <Toggle label={t('cards.canRepeat')} checked={!!card.repeat}
              onChange={(v) => onChange({ ...card, repeat: v, optional: v ? false : card.optional })} disabled={disabled} />
          </div>
        </div>
      )}
    </div>
  );
}
