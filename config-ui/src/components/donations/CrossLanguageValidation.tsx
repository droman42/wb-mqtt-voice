/**
 * CrossLanguageValidation Component - Dedicated cross-language validation UI
 * 
 * Provides a prominent validation panel with parameter consistency checking,
 * method completeness validation, and automated synchronization tools.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Info,
  Settings
} from 'lucide-react';
import { Alert, AlertDescription, Button, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import Badge from '@/components/ui/Badge';

// Status-hued text/icon recipes (stylebook §2 — meaning via status tokens, never raw palette).
const persistedText = 'text-[hsl(var(--lv-status-persisted)_55%_32%)] dark:text-[hsl(var(--lv-status-persisted)_70%_72%)]';
const editedText = 'text-[hsl(var(--lv-status-edited)_55%_32%)] dark:text-[hsl(var(--lv-status-edited)_70%_72%)]';
const testedText = 'text-[hsl(var(--lv-status-tested)_55%_32%)] dark:text-[hsl(var(--lv-status-tested)_70%_72%)]';
import type { 
  ValidationReport, 
  CompletenessReport,
  HandlerLanguageInfo 
} from '@/types/api';

export interface CrossLanguageValidationProps {
  handlerName: string;
  handlerInfo: HandlerLanguageInfo;
  activeLanguage: string;
  validationReport: ValidationReport | null;
  completenessReport: CompletenessReport | null;
  onRefreshValidation: () => void;
  isLoading?: boolean;
  disabled?: boolean;
}

const CrossLanguageValidation: React.FC<CrossLanguageValidationProps> = ({
  // handlerName not used in component logic
  handlerInfo,
  validationReport,
  completenessReport,
  onRefreshValidation,
  isLoading = false,
  disabled = false
}) => {
  const { t } = useTranslation('donations');
  const [expanded, setExpanded] = useState(false);
  const [showParameterDetails, setShowParameterDetails] = useState(false);
  const [showMethodDetails, setShowMethodDetails] = useState(false);

  // Calculate validation summary
  const hasMultipleLanguages = handlerInfo.languages.length > 1;
  const hasValidationData = validationReport || completenessReport;
  
  const parameterIssues = validationReport ? 
    validationReport.missing_parameters.length + validationReport.type_mismatches.length : 0;
  const methodIssues = completenessReport ? 
    completenessReport.missing_methods.length + completenessReport.extra_methods.length : 0;
  
  const totalIssues = parameterIssues + methodIssues;
  const hasIssues = totalIssues > 0;


  if (!hasMultipleLanguages) {
    return (
      <Alert>
        <Info />
        <AlertDescription>{t('crossLang.notApplicable')}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center space-x-2 text-left hover:bg-muted/60 -m-1 p-1 rounded transition-colors duration-200"
              disabled={disabled}
            >
              {expanded ? (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              )}
              <div className="flex items-center space-x-2">
                <Settings className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-semibold text-foreground">{t('crossLang.title')}</h3>
              </div>
            </button>
            
            {/* Status Badge */}
            {hasValidationData && (
              <div className="flex items-center space-x-2">
                {hasIssues ? (
                  <Badge variant="warning" className="flex items-center space-x-1">
                    <AlertTriangle className="w-3 h-3" />
                    <span>{t('crossLang.issues', { count: totalIssues })}</span>
                  </Badge>
                ) : (
                  <Badge variant="success" className="flex items-center space-x-1">
                    <CheckCircle className="w-3 h-3" />
                    <span>{t('crossLang.synchronized')}</span>
                  </Badge>
                )}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onRefreshValidation}
                  disabled={disabled || isLoading}
                >
                  <RefreshCw className={isLoading ? 'animate-spin' : ''} />
                  <span>{t('crossLang.refresh')}</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>{t('crossLang.refreshTitle')}</TooltipContent>
            </Tooltip>

          </div>
        </div>

        {/* Summary Info */}
        <div className="mt-3 text-sm text-muted-foreground">
          <span>
            {t('crossLang.comparing', {
              count: handlerInfo.languages.length,
              languages: handlerInfo.languages.map(lang => lang.toUpperCase()).join(', '),
            })}
          </span>
          {hasValidationData && (
            <span className="ml-2">
              {t('crossLang.lastChecked', {
                time: new Date(
                  (validationReport?.timestamp || completenessReport?.timestamp || 0) * 1000
                ).toLocaleTimeString(),
              })}
            </span>
          )}
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="p-4 space-y-4">
          {!hasValidationData ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <div className="text-center">
                <RefreshCw className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                <p>{t('crossLang.clickRefresh')}</p>
                <p className="text-xs mt-2 text-muted-foreground">
                  {t('crossLang.backendNote')}
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Parameter Consistency Section */}
              {validationReport && (
                <div className="border border-border rounded-lg">
                  <button
                    onClick={() => setShowParameterDetails(!showParameterDetails)}
                    className="w-full flex items-center justify-between p-3 text-left hover:bg-muted/60 transition-colors duration-200"
                  >
                    <div className="flex items-center space-x-3">
                      {validationReport.parameter_consistency ? (
                        <CheckCircle className={`w-5 h-5 ${persistedText}`} />
                      ) : (
                        <AlertTriangle className={`w-5 h-5 ${editedText}`} />
                      )}
                      <div>
                        <h4 className="font-medium text-foreground">{t('crossLang.parameterConsistency')}</h4>
                        <p className="text-sm text-muted-foreground">
                          {validationReport.parameter_consistency
                            ? t('crossLang.parametersConsistent')
                            : t('crossLang.parameterInconsistencies', { count: parameterIssues })
                          }
                        </p>
                      </div>
                    </div>
                    {showParameterDetails ? (
                      <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    )}
                  </button>

                  {showParameterDetails && !validationReport.parameter_consistency && (
                    <div className="px-3 pb-3 border-t border-border">
                      {validationReport.missing_parameters.length > 0 && (
                        <div className="mt-3">
                          <h5 className="text-sm font-medium text-destructive mb-2">{t('crossLang.missingParameters')}</h5>
                          <ul className="space-y-1">
                            {validationReport.missing_parameters.map((issue, index) => (
                              <li key={`missing-${index}`} className="text-sm text-destructive flex items-center space-x-1">
                                <AlertCircle className="w-3 h-3 flex-shrink-0" />
                                <span>{issue}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {validationReport.type_mismatches.length > 0 && (
                        <div className="mt-3">
                          <h5 className={`text-sm font-medium ${editedText} mb-2`}>{t('crossLang.typeMismatches')}</h5>
                          <ul className="space-y-1">
                            {validationReport.type_mismatches.map((issue, index) => (
                              <li key={`mismatch-${index}`} className={`text-sm ${editedText} flex items-center space-x-1`}>
                                <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                                <span>{issue}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Method Completeness Section */}
              {completenessReport && (
                <div className="border border-border rounded-lg">
                  <button
                    onClick={() => setShowMethodDetails(!showMethodDetails)}
                    className="w-full flex items-center justify-between p-3 text-left hover:bg-muted/60 transition-colors duration-200"
                  >
                    <div className="flex items-center space-x-3">
                      {completenessReport.method_completeness ? (
                        <CheckCircle className={`w-5 h-5 ${persistedText}`} />
                      ) : (
                        <AlertTriangle className={`w-5 h-5 ${editedText}`} />
                      )}
                      <div>
                        <h4 className="font-medium text-foreground">{t('crossLang.methodCompleteness')}</h4>
                        <p className="text-sm text-muted-foreground">
                          {completenessReport.method_completeness
                            ? t('crossLang.methodsComplete')
                            : t('crossLang.methodInconsistencies', { count: methodIssues })
                          }
                        </p>
                      </div>
                    </div>
                    {showMethodDetails ? (
                      <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    )}
                  </button>

                  {showMethodDetails && (
                    <div className="px-3 pb-3 border-t border-border">
                      {/* Method counts by language */}
                      <div className="mt-3">
                        <h5 className="text-sm font-medium text-foreground mb-2">{t('crossLang.methodCountsByLanguage')}</h5>
                        <div className="grid grid-cols-2 gap-2">
                          {Object.entries(completenessReport.method_counts_by_language).map(([lang, count]) => (
                            <div key={lang} className="flex items-center justify-between text-sm">
                              <span className="text-muted-foreground">{lang.toUpperCase()}:</span>
                              <Badge variant="info">{t('crossLang.methodsCount', { count })}</Badge>
                            </div>
                          ))}
                        </div>
                      </div>

                      {completenessReport.missing_methods.length > 0 && (
                        <div className="mt-3">
                          <h5 className="text-sm font-medium text-destructive mb-2">{t('crossLang.missingMethods')}</h5>
                          <ul className="space-y-1">
                            {completenessReport.missing_methods.map((issue, index) => (
                              <li key={`missing-method-${index}`} className="text-sm text-destructive flex items-center space-x-1">
                                <AlertCircle className="w-3 h-3 flex-shrink-0" />
                                <span>{issue}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {completenessReport.extra_methods.length > 0 && (
                        <div className="mt-3">
                          <h5 className={`text-sm font-medium ${testedText} mb-2`}>{t('crossLang.extraMethods')}</h5>
                          <ul className="space-y-1">
                            {completenessReport.extra_methods.map((issue, index) => (
                              <li key={`extra-method-${index}`} className={`text-sm ${testedText} flex items-center space-x-1`}>
                                <Info className="w-3 h-3 flex-shrink-0" />
                                <span>{issue}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

            </>
          )}
        </div>
      )}
    </div>
  );
};

export default CrossLanguageValidation;
