/**
 * DonationValidationPanel (UI-5) — surfaces the QUAL-42 backend services for one handler:
 *   - the contract↔code WIRING report (GET /donations/validation): unwired methods (fatal, normally caught at
 *     boot) + soft warnings (declared-but-unread params, undeclared handler methods);
 *   - LLM translation VALIDATION (POST .../validate-translation): meaning/consistency QA across languages;
 *   - the LLM translation SERVICE (POST .../translate): draft target-language phrases from a source language.
 *
 * Both LLM actions degrade gracefully: when no API-keyed LLM is configured the backend returns
 * llm_available=false with a "validate/translate manually" message, which we show as-is.
 */

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshCw, AlertCircle, AlertTriangle, CheckCircle2, Languages } from 'lucide-react';
import {
  Button, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Tooltip, TooltipTrigger, TooltipContent,
} from 'locveil-ui-kit';
import apiClient from '@/utils/apiClient';

// Status-hued text recipes (stylebook §2 — meaning via status tokens, never raw palette).
const persistedText = 'text-[hsl(var(--lv-status-persisted)_55%_32%)] dark:text-[hsl(var(--lv-status-persisted)_70%_72%)]';
const editedText = 'text-[hsl(var(--lv-status-edited)_55%_32%)] dark:text-[hsl(var(--lv-status-edited)_70%_72%)]';
import type {
  ContractWiringReport, TranslationIssue, TranslatedMethod,
} from '@/types';

interface DonationValidationPanelProps {
  handlerName: string;
  sourceLanguage: string;
  availableLanguages: string[];
  disabled?: boolean;
}

export default function DonationValidationPanel({
  handlerName, sourceLanguage, availableLanguages, disabled = false,
}: DonationValidationPanelProps) {
  const { t } = useTranslation('donations');
  const [wiring, setWiring] = useState<ContractWiringReport | null>(null);
  const [wiringLoading, setWiringLoading] = useState(false);

  const [target, setTarget] = useState<string>('');
  const [llmBusy, setLlmBusy] = useState(false);
  const [llmMessage, setLlmMessage] = useState<string | null>(null);
  const [issues, setIssues] = useState<TranslationIssue[] | null>(null);
  const [drafts, setDrafts] = useState<TranslatedMethod[] | null>(null);

  const loadWiring = useCallback(async () => {
    setWiringLoading(true);
    try {
      const report = await apiClient.getContractValidation();
      setWiring((report.handlers ?? []).find((h) => h.handler_name === handlerName) ?? null);
    } catch {
      setWiring(null);
    } finally {
      setWiringLoading(false);
    }
  }, [handlerName]);

  useEffect(() => { void loadWiring(); }, [loadWiring]);

  // Default the translation target to the first language that isn't the source.
  useEffect(() => {
    if (!target || target === sourceLanguage) {
      setTarget(availableLanguages.find((l) => l !== sourceLanguage) ?? '');
    }
  }, [availableLanguages, sourceLanguage, target]);

  const runValidate = useCallback(async () => {
    setLlmBusy(true); setIssues(null); setDrafts(null); setLlmMessage(null);
    try {
      const res = await apiClient.validateTranslation(handlerName);
      setLlmMessage(res.message);
      setIssues(res.llm_available ? (res.issues ?? []) : null);
    } catch (e) {
      setLlmMessage(e instanceof Error ? e.message : t('validation.translationValidationFailed'));
    } finally {
      setLlmBusy(false);
    }
  }, [handlerName, t]);

  const runTranslate = useCallback(async () => {
    if (!target) return;
    setLlmBusy(true); setIssues(null); setDrafts(null); setLlmMessage(null);
    try {
      const res = await apiClient.translateDonation(handlerName, {
        sourceLanguage, targetLanguage: target,
      });
      setLlmMessage(res.message);
      setDrafts(res.llm_available ? (res.translations ?? []) : null);
    } catch (e) {
      setLlmMessage(e instanceof Error ? e.message : t('validation.translationFailed'));
    } finally {
      setLlmBusy(false);
    }
  }, [handlerName, sourceLanguage, target, t]);

  const errors = wiring?.errors ?? [];
  const warnings = wiring?.warnings ?? [];

  return (
    <div className="border border-border rounded-xl bg-card p-4 space-y-4">
      {/* Wiring (contract <-> code) */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-semibold text-foreground">{t('validation.wiringTitle')}</div>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                onClick={() => void loadWiring()} disabled={wiringLoading}
              >
                <RefreshCw className={wiringLoading ? 'animate-spin' : ''} /> {t('validation.wiringRefreshTitle')}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t('validation.wiringRefreshTitle')}</TooltipContent>
          </Tooltip>
        </div>
        {errors.length === 0 && warnings.length === 0 ? (
          <div className={`flex items-center gap-2 text-sm ${persistedText}`}>
            <CheckCircle2 className="w-4 h-4" /> {t('validation.wiringOk')}
          </div>
        ) : (
          <div className="space-y-1">
            {errors.map((e, i) => (
              <div key={`e${i}`} className="flex items-start gap-2 text-sm text-destructive">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" /> <span>{e}</span>
              </div>
            ))}
            {warnings.map((w, i) => (
              <div key={`w${i}`} className={`flex items-start gap-2 text-sm ${editedText}`}>
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" /> <span>{w}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* LLM translation validation + drafting */}
      <div className="border-t border-border pt-3">
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <Languages className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-semibold text-foreground">{t('validation.translationTitle')}</span>
          <span className="text-xs text-muted-foreground">{t('validation.from')} <b>{sourceLanguage}</b> {t('validation.to')}</span>
          <Select value={target} onValueChange={setTarget} disabled={disabled || llmBusy}>
            <SelectTrigger className="h-8 w-auto gap-1 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {availableLanguages.filter((l) => l !== sourceLanguage).map((l) => (
                <SelectItem key={l} value={l}>{l}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void runValidate()} disabled={disabled || llmBusy}
          >
            {t('validation.validateQuality')}
          </Button>
          <Button
            size="sm"
            onClick={() => void runTranslate()} disabled={disabled || llmBusy || !target}
          >
            {t('validation.draftTranslations')}
          </Button>
          {llmBusy ? <RefreshCw className="w-4 h-4 animate-spin text-muted-foreground" /> : null}
        </div>

        {llmMessage ? <div className="text-sm text-muted-foreground mb-2">{llmMessage}</div> : null}

        {issues && issues.length > 0 ? (
          <div className="space-y-1">
            {issues.map((it, i) => (
              <div key={i} className={`flex items-start gap-2 text-sm ${editedText}`}>
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><b>{it.language}</b>{it.method_key ? ` · ${it.method_key}` : ''}: {it.message}</span>
              </div>
            ))}
          </div>
        ) : null}

        {drafts && drafts.length > 0 ? (
          <div className="space-y-2">
            {drafts.map((d, i) => (
              <div key={i} className="border border-border rounded-lg p-2">
                <div className="text-xs font-mono text-muted-foreground mb-1">{d.method_key}</div>
                <ul className="list-disc list-inside text-sm text-foreground">
                  {(d.suggested_phrases ?? []).map((p, j) => <li key={j}>{p}</li>)}
                </ul>
              </div>
            ))}
            <p className="text-xs text-muted-foreground">{t('validation.draftsHint')}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
