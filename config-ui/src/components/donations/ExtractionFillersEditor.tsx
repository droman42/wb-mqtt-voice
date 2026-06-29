/**
 * ExtractionFillersEditor (UI-3 / §3.4) — edits a contract parameter's value-extraction patterns
 * (`parameters[].extraction_patterns`) as labelled rows of word cards, on the UI-2 FillerPattern helpers.
 *
 * Each filler = one "way to find this value" (a card row) + an optional slot label (e.g. DURATION_VALUE) that links
 * it to the method's slot patterns. Controlled over `ExtractionPattern[]` but keeps decompiled fillers in local
 * state and only compiles on edits (stable advanced editing; external revert re-syncs) — same pattern as
 * CardPatternsEditor.
 */

import { useTranslation } from 'react-i18next';
import { Plus, Trash2 } from 'lucide-react';
import CardEditor from './CardEditor';
import Input from '@/components/ui/Input';
import { useDecompiledPatterns } from '@/hooks/useDecompiledPatterns';
import {
  type ExtractionPattern, type FillerPattern, type Card,
  decompileExtractionPatterns, compileExtractionPatterns,
} from '@/utils/patternModel';

interface ExtractionFillersEditorProps {
  value: ExtractionPattern[];
  onChange: (value: ExtractionPattern[]) => void;
  disabled?: boolean;
}

export default function ExtractionFillersEditor({ value, onChange, disabled = false }: ExtractionFillersEditorProps) {
  const { t } = useTranslation('donations');
  const [fillers, emit] = useDecompiledPatterns<ExtractionPattern, FillerPattern>(
    value, onChange, decompileExtractionPatterns, compileExtractionPatterns);

  const setFiller = (fi: number, f: FillerPattern): void => emit(fillers.map((x, i) => (i === fi ? f : x)));
  const setCard = (fi: number, ci: number, card: Card): void =>
    setFiller(fi, { ...fillers[fi], cards: fillers[fi].cards.map((c, j) => (j === ci ? card : c)) });
  const removeCard = (fi: number, ci: number): void =>
    setFiller(fi, { ...fillers[fi], cards: fillers[fi].cards.filter((_, j) => j !== ci) });
  const addCard = (fi: number): void =>
    setFiller(fi, { ...fillers[fi], cards: [...fillers[fi].cards, { kind: 'word', attr: 'LOWER', word: '' }] });
  const removeFiller = (fi: number): void => emit(fillers.filter((_, i) => i !== fi));
  const addFiller = (): void => emit([...fillers, { cards: [], extra: {} }]);

  return (
    <div className="space-y-2">
      {fillers.length === 0 && <div className="text-xs text-gray-500">{t('extraction.empty')}</div>}
      {fillers.map((filler, fi) => (
        <div key={fi} className="border rounded-lg p-2 bg-gray-50">
          <div className="flex items-center gap-2 mb-2">
            <div className="text-xs text-gray-600">{t('extraction.findsValueAs')}</div>
            <div className="flex-1" />
            <Input
              label=""
              value={filler.label ?? ''}
              onChange={(v) => setFiller(fi, { ...filler, label: v || undefined })}
              placeholder={t('extraction.slotLabelPlaceholder')}
              disabled={disabled}
            />
            <button
              type="button"
              className="p-1 rounded-lg border bg-white hover:bg-gray-50 disabled:opacity-50"
              onClick={() => removeFiller(fi)} disabled={disabled} title={t('extraction.removeTitle')}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {filler.cards.map((card, ci) => (
              <CardEditor key={ci} card={card} onChange={(c) => setCard(fi, ci, c)}
                onRemove={() => removeCard(fi, ci)} disabled={disabled} />
            ))}
            <button
              type="button"
              className="inline-flex items-center gap-2 px-3 py-1.5 border rounded-lg bg-white hover:bg-gray-50 disabled:opacity-50 text-sm"
              onClick={() => addCard(fi)} disabled={disabled}
            >
              <Plus className="w-4 h-4" /> {t('extraction.addWord')}
            </button>
          </div>
        </div>
      ))}
      <button
        type="button"
        className="inline-flex items-center gap-2 px-3 py-1.5 border rounded-lg hover:bg-gray-50 disabled:opacity-50 text-sm"
        onClick={addFiller} disabled={disabled}
      >
        <Plus className="w-4 h-4" /> {t('extraction.addWay')}
      </button>
    </div>
  );
}
