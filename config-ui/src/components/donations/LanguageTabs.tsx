/**
 * LanguageTabs Component - Language selection and management interface
 * 
 * Provides tab-based language switching with creation, deletion, and validation status
 * indicators as outlined in Phase 3 of the language support plan.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, X, AlertTriangle, CheckCircle, Clock, Shield } from 'lucide-react';
import { Button, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import Badge from '@/components/ui/Badge';
import type { ValidationReport, CompletenessReport } from '@/types/api';

// Status-hued text/icon recipes (stylebook §2 — meaning via status tokens, never raw palette).
const persistedText = 'text-[hsl(var(--lv-status-persisted)_55%_32%)] dark:text-[hsl(var(--lv-status-persisted)_70%_72%)]';
const editedText = 'text-[hsl(var(--lv-status-edited)_55%_32%)] dark:text-[hsl(var(--lv-status-edited)_70%_72%)]';
const conflictText = 'text-[hsl(var(--lv-status-conflict)_55%_32%)] dark:text-[hsl(var(--lv-status-conflict)_70%_72%)]';

export interface LanguageInfo {
  code: string;
  label: string;
  status: 'loaded' | 'loading' | 'error' | 'missing';
  validationErrors?: number;
  methodCount?: number;
  lastModified?: string;
}

export interface LanguageTabsProps {
  activeLanguage: string;
  availableLanguages: LanguageInfo[];
  supportedLanguages: string[];
  onLanguageChange: (lang: string) => void;
  onCreateLanguage: (lang: string, templateFrom?: string) => void;
  onDeleteLanguage: (lang: string) => void;
  onCompareLanguages?: (lang1: string, lang2: string) => void;
  disabled?: boolean;
  // Phase 4: Cross-language validation props
  handlerName?: string;
  validationReport?: ValidationReport | null;
  completenessReport?: CompletenessReport | null;
  onRefreshValidation?: () => void;
}

const LanguageTabs: React.FC<LanguageTabsProps> = ({
  activeLanguage,
  availableLanguages,
  supportedLanguages,
  onLanguageChange,
  onCreateLanguage,
  onDeleteLanguage,
  onCompareLanguages,
  disabled = false,
  // Phase 4: Cross-language validation props
  validationReport,
  completenessReport,
  onRefreshValidation
}) => {
  const { t } = useTranslation(['donations', 'common']);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newLanguageCode, setNewLanguageCode] = useState('');
  const [templateLanguage, setTemplateLanguage] = useState('');

  const getLanguageLabel = (code: string): string => {
    const labels: Record<string, string> = {
      'en': 'English',
      'ru': 'Русский',
      'de': 'Deutsch',
      'fr': 'Français',
      'es': 'Español',
      'it': 'Italiano',
      'pt': 'Português',
      'zh': '中文',
      'ja': '日本語',
      'ko': '한국어'
    };
    return labels[code] || code.toUpperCase();
  };

  const getStatusIcon = (status: string, validationErrors?: number) => {
    switch (status) {
      case 'loaded':
        return validationErrors && validationErrors > 0
          ? <AlertTriangle className={`w-3 h-3 ${editedText}`} />
          : <CheckCircle className={`w-3 h-3 ${persistedText}`} />;
      case 'loading':
        return <Clock className="w-3 h-3 text-muted-foreground animate-spin" />;
      case 'error':
        return <AlertTriangle className={`w-3 h-3 ${conflictText}`} />;
      case 'missing':
        return <AlertTriangle className="w-3 h-3 text-muted-foreground" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (language: LanguageInfo) => {
    if (language.validationErrors && language.validationErrors > 0) {
      return <Badge variant="warning">{language.validationErrors}</Badge>;
    }
    if (language.status === 'error') {
      return <Badge variant="error">{t('languageTabs.error')}</Badge>;
    }
    if (language.status === 'missing') {
      return <Badge variant="default">{t('languageTabs.missing')}</Badge>;
    }
    return null;
  };

  const handleCreateLanguage = () => {
    if (newLanguageCode.trim()) {
      onCreateLanguage(newLanguageCode.trim(), templateLanguage || undefined);
      setNewLanguageCode('');
      setTemplateLanguage('');
      setShowCreateForm(false);
    }
  };

  const missingLanguages = supportedLanguages.filter(
    lang => !availableLanguages.some(available => available.code === lang)
  );

  // Cross-language validation helpers
  const hasValidationIssues = () => {
    return (validationReport && !validationReport.parameter_consistency) ||
           (completenessReport && !completenessReport.method_completeness);
  };

  const getValidationSummary = () => {
    const issues = [];
    if (validationReport && !validationReport.parameter_consistency) {
      issues.push(t('languageTabs.parameterIssuesSummary', { count: validationReport.missing_parameters.length + validationReport.type_mismatches.length }));
    }
    if (completenessReport && !completenessReport.method_completeness) {
      issues.push(t('languageTabs.methodIssuesSummary', { count: completenessReport.missing_methods.length + completenessReport.extra_methods.length }));
    }
    return issues.join(', ');
  };

  return (
    <div className="border-b border-border bg-card">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center space-x-1">
          {/* Available Language Tabs */}
          {availableLanguages.map((language) => (
            <div
              key={language.code}
              className={`
                relative flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200
                ${activeLanguage === language.code
                  ? 'bg-primary/10 text-primary border border-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                }
                ${disabled ? 'opacity-50' : 'cursor-pointer'}
                ${language.status === 'error' ? conflictText : ''}
              `}
            >
              <button
                onClick={() => !disabled && onLanguageChange(language.code)}
                disabled={disabled || language.status === 'loading'}
                className="flex items-center space-x-2 flex-1 text-left"
              >
                <span>{getLanguageLabel(language.code)}</span>
                {getStatusIcon(language.status, language.validationErrors)}
                {getStatusBadge(language)}
              </button>
              
              {/* Delete button for non-active languages */}
              {language.code !== activeLanguage && !disabled && language.status !== 'loading' && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteLanguage(language.code);
                      }}
                      className="ml-1 p-0.5 text-muted-foreground hover:text-destructive transition-colors duration-200"
                      aria-label={t('languageTabs.deleteLanguage', { language: getLanguageLabel(language.code) })}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>{t('languageTabs.deleteLanguage', { language: getLanguageLabel(language.code) })}</TooltipContent>
                </Tooltip>
              )}
            </div>
          ))}

          {/* Add Language Button */}
          {!disabled && (
            <div className="relative">
              {!showCreateForm ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowCreateForm(true)}
                    >
                      <Plus />
                      <span>{t('languageTabs.addLanguage')}</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{t('languageTabs.addLanguageTitle')}</TooltipContent>
                </Tooltip>
              ) : (
                <div className="flex items-center space-x-2 p-2 bg-muted rounded-md border border-border">
                  <select
                    value={newLanguageCode}
                    onChange={(e) => setNewLanguageCode(e.target.value)}
                    className="text-sm border border-input bg-background text-foreground rounded-md px-2 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <option value="">{t('languageTabs.selectLanguage')}</option>
                    {missingLanguages.map(lang => (
                      <option key={lang} value={lang}>
                        {getLanguageLabel(lang)}
                      </option>
                    ))}
                  </select>
                  
                  {availableLanguages.length > 0 && (
                    <select
                      value={templateLanguage}
                      onChange={(e) => setTemplateLanguage(e.target.value)}
                      className="text-sm border border-input bg-background text-foreground rounded-md px-2 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="">{t('languageTabs.fromScratch')}</option>
                      {availableLanguages.map(lang => (
                        <option key={lang.code} value={lang.code}>
                          {t('languageTabs.copyFrom', { language: getLanguageLabel(lang.code) })}
                        </option>
                      ))}
                    </select>
                  )}
                  
                  <Button
                    size="sm"
                    onClick={handleCreateLanguage}
                    disabled={!newLanguageCode}
                  >
                    {t('languageTabs.create')}
                  </Button>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setShowCreateForm(false);
                      setNewLanguageCode('');
                      setTemplateLanguage('');
                    }}
                  >
                    {t('common:actions.cancel')}
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Language Info and Cross-Language Validation */}
        <div className="flex items-center space-x-4 text-sm">
          <span className="text-muted-foreground">
            {t('languageTabs.languageCount', { available: availableLanguages.length, total: supportedLanguages.length })}
          </span>
          
          {/* Phase 4: Cross-language validation status */}
          {availableLanguages.length > 1 && (validationReport || completenessReport) && (
            <div className="flex items-center space-x-2">
              {hasValidationIssues() ? (
                <Badge variant="warning" className="flex items-center space-x-1">
                  <AlertTriangle className="w-3 h-3" />
                  <span>{getValidationSummary()}</span>
                </Badge>
              ) : (
                <Badge variant="success" className="flex items-center space-x-1">
                  <CheckCircle className="w-3 h-3" />
                  <span>{t('languageTabs.synchronized')}</span>
                </Badge>
              )}

              {onRefreshValidation && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-primary"
                      onClick={onRefreshValidation}
                      aria-label={t('languageTabs.refreshValidationTitle')}
                    >
                      <Shield />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{t('languageTabs.refreshValidationTitle')}</TooltipContent>
                </Tooltip>
              )}
              
            </div>
          )}
          
          {onCompareLanguages && availableLanguages.length > 1 && (
            <Button
              variant="link"
              className="h-auto p-0"
              onClick={() => {
                const otherLang = availableLanguages.find(l => l.code !== activeLanguage);
                if (otherLang) {
                  onCompareLanguages(activeLanguage, otherLang.code);
                }
              }}
            >
              {t('languageTabs.compareLanguages')}
            </Button>
          )}
        </div>
      </div>

      {/* Missing Languages Warning */}
      {missingLanguages.length > 0 && (
        <div className="px-4 py-2 border-t border-border">
          <div className={`flex items-center space-x-2 text-sm ${editedText}`}>
            <AlertTriangle className="w-4 h-4" />
            <span>
              {t('languageTabs.missingLanguages', { languages: missingLanguages.map(getLanguageLabel).join(', ') })}
            </span>
          </div>
        </div>
      )}

      {/* Phase 4: Cross-Language Validation Details */}
      {availableLanguages.length > 1 && hasValidationIssues() && (validationReport || completenessReport) && (
        <div className="px-4 py-3 border-t border-border">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-destructive">{t('languageTabs.issuesTitle')}</h4>
              {onRefreshValidation && (
                <Button
                  variant="link"
                  className="h-auto p-0 text-xs text-destructive"
                  onClick={onRefreshValidation}
                >
                  {t('languageTabs.refreshValidation')}
                </Button>
              )}
            </div>

            {/* Parameter Consistency Issues */}
            {validationReport && !validationReport.parameter_consistency && (
              <div className="text-sm text-destructive">
                <div className="font-medium mb-1">{t('languageTabs.parameterIssues')}</div>
                <ul className="list-disc list-inside text-xs space-y-1">
                  {validationReport.missing_parameters.map((issue, index) => (
                    <li key={`missing-${index}`}>{t('languageTabs.missingParameter', { issue })}</li>
                  ))}
                  {validationReport.type_mismatches.map((issue, index) => (
                    <li key={`mismatch-${index}`}>{t('languageTabs.typeMismatch', { issue })}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* Method Completeness Issues */}
            {completenessReport && !completenessReport.method_completeness && (
              <div className="text-sm text-destructive">
                <div className="font-medium mb-1">{t('languageTabs.methodIssues')}</div>
                <ul className="list-disc list-inside text-xs space-y-1">
                  {completenessReport.missing_methods.map((issue, index) => (
                    <li key={`missing-method-${index}`}>{t('languageTabs.missingMethod', { issue })}</li>
                  ))}
                  {completenessReport.extra_methods.map((issue, index) => (
                    <li key={`extra-method-${index}`}>{t('languageTabs.extraMethod', { issue })}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default LanguageTabs;
