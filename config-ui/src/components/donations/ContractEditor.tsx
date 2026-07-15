/**
 * ContractEditor (UI-5) — edits the language-neutral donation contract.
 *
 * This is the structural half of the donation: per method, the method's `room_context` and its parameters'
 * spec (name / type / required / canonical choices / min-max / entity_type / pattern). It is language-neutral —
 * spoken phrasing (phrases, patterns, choice surface forms) lives in the per-language PhrasingEditor, not here.
 *
 * method_name / intent_suffix are read-only: they're the wiring to the Python handler (validated by the backend
 * contract↔code check, QUAL-42) and renaming them here would silently unwire the method.
 */

import { useTranslation } from 'react-i18next';
import { Plus, Trash2 } from 'lucide-react';
import {
  Button, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Tooltip, TooltipTrigger, TooltipContent,
} from 'locveil-ui-kit';
import Section from '@/components/ui/Section';
import Input from '@/components/ui/Input';
import Toggle from '@/components/ui/Toggle';
import Badge from '@/components/ui/Badge';
import ArrayOfStringsEditor from '@/components/editors/ArrayOfStringsEditor';
import type { DonationContract, ContractMethod, ContractParam, ParameterType, RoomContext } from '@/types';

// UI-14 (E6): each enum value is a key checked against the generated donation-contract union via
// `satisfies Record<…>`, so a backend enum change (new/renamed type, entity_type, room_context) fails
// the build here instead of silently dropping from these dropdowns. The arrays derive from the keys.
type EntityType = NonNullable<ContractParam['entity_type']>;
const PARAMETER_TYPES = Object.keys({
  string: 1, integer: 1, float: 1, datetime: 1, boolean: 1, choice: 1, entity: 1,
} satisfies Record<ParameterType, 1>) as ParameterType[];
const ENTITY_TYPES = Object.keys({
  device: 1, location: 1, room: 1, person: 1, generic: 1,
} satisfies Record<EntityType, 1>) as EntityType[];
const ROOM_CONTEXTS = Object.keys({
  none: 1, required: 1, conditional: 1,
} satisfies Record<RoomContext, 1>) as RoomContext[];

interface ContractEditorProps {
  contract: DonationContract;
  onChange: (contract: DonationContract) => void;
  disabled?: boolean;
}

function ContractParamEditor({
  param, onChange, onRemove, disabled,
}: {
  param: ContractParam;
  onChange: (p: ContractParam) => void;
  onRemove: () => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation('donations');
  const set = <K extends keyof ContractParam>(k: K, v: ContractParam[K]): void => onChange({ ...param, [k]: v });
  const isNumeric = param.type === 'integer' || param.type === 'float';

  return (
    <div className="border border-border rounded-xl p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-medium">{t('contract.parameter')}</div>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-destructive"
              onClick={onRemove} disabled={disabled} aria-label={t('contract.removeParameter')}
            >
              <Trash2 />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('contract.removeParameter')}</TooltipContent>
        </Tooltip>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Input label={t('contract.name')} value={param.name} onChange={(v) => set('name', v)} disabled={disabled} required />
        <label className="block">
          <div className="text-sm font-medium mb-1">{t('contract.type')}</div>
          <Select
            value={param.type}
            onValueChange={(v) => set('type', v as ParameterType)}
            disabled={disabled}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PARAMETER_TYPES.map((pt) => <SelectItem key={pt} value={pt}>{pt}</SelectItem>)}
            </SelectContent>
          </Select>
        </label>
        <Toggle label={t('contract.required')} checked={!!param.required} onChange={(v) => set('required', v)} disabled={disabled} />
        {param.type === 'entity' ? (
          <label className="block">
            <div className="text-sm font-medium mb-1">{t('contract.entityType')}</div>
            <Select
              value={param.entity_type ?? 'generic'}
              onValueChange={(v) => set('entity_type', v as ContractParam['entity_type'])}
              disabled={disabled}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ENTITY_TYPES.map((et) => <SelectItem key={et} value={et}>{et}</SelectItem>)}
              </SelectContent>
            </Select>
          </label>
        ) : null}
        {param.type === 'choice' ? (
          <div className="md:col-span-2">
            <ArrayOfStringsEditor
              label={t('contract.canonicalChoices')}
              value={param.choices ?? []}
              onChange={(v) => set('choices', v)}
              disabled={disabled}
            />
            <p className="text-xs text-muted-foreground mt-1">
              {t('contract.canonicalChoicesHelp')}
            </p>
          </div>
        ) : null}
        {isNumeric ? (
          <div className="grid grid-cols-2 gap-2">
            <Input
              label={t('contract.minValue')} type="number" value={param.min_value == null ? '' : String(param.min_value)}
              onChange={(v) => set('min_value', v === '' ? null : Number(v))} disabled={disabled}
            />
            <Input
              label={t('contract.maxValue')} type="number" value={param.max_value == null ? '' : String(param.max_value)}
              onChange={(v) => set('max_value', v === '' ? null : Number(v))} disabled={disabled}
            />
          </div>
        ) : null}
        {param.type === 'string' ? (
          <Input
            label={t('contract.regexPattern')} value={param.pattern ?? ''}
            onChange={(v) => set('pattern', v || null)} disabled={disabled} placeholder={t('contract.regexPlaceholder')}
          />
        ) : null}
      </div>
    </div>
  );
}

export default function ContractEditor({ contract, onChange, disabled = false }: ContractEditorProps) {
  const { t } = useTranslation('donations');
  const methods = contract.method_donations;

  const setMethod = (idx: number, m: ContractMethod): void => {
    const next = methods.map((x, i) => (i === idx ? m : x));
    onChange({ ...contract, method_donations: next as DonationContract['method_donations'] });
  };

  return (
    <div className="space-y-6">
      <Section title={t('contract.sectionTitle')} defaultCollapsed={false}>
        <p className="text-sm text-muted-foreground mb-4">
          {t('contract.sectionHelp')}
        </p>
        <div className="space-y-4">
          {methods.map((method, mi) => (
            <div key={`${method.method_name}#${method.intent_suffix}`} className="border border-border rounded-xl bg-card p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-foreground">{method.method_name}</span>
                  <Badge variant="info">{method.intent_suffix}</Badge>
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <span className="text-muted-foreground">{t('contract.roomContext')}</span>
                  <Select
                    value={method.room_context ?? 'none'}
                    onValueChange={(v) => setMethod(mi, { ...method, room_context: v as RoomContext })}
                    disabled={disabled}
                  >
                    <SelectTrigger className="h-8 w-auto gap-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ROOM_CONTEXTS.map((rc) => <SelectItem key={rc} value={rc}>{rc}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </label>
              </div>

              <div className="space-y-3">
                {(method.parameters ?? []).map((param, pi) => (
                  <ContractParamEditor
                    key={pi}
                    param={param}
                    disabled={disabled}
                    onChange={(p) => {
                      const params = [...(method.parameters ?? [])];
                      params[pi] = p;
                      setMethod(mi, { ...method, parameters: params });
                    }}
                    onRemove={() => {
                      const params = (method.parameters ?? []).filter((_, i) => i !== pi);
                      setMethod(mi, { ...method, parameters: params });
                    }}
                  />
                ))}
                <Button
                  variant="outline"
                  onClick={() => setMethod(mi, {
                    ...method,
                    parameters: [...(method.parameters ?? []), { name: '', type: 'string', required: false }],
                  })}
                  disabled={disabled}
                >
                  <Plus /> {t('contract.addParameter')}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
