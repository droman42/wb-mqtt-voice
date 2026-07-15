/**
 * DonationsPage Component - Main donations management interface
 * 
 * Integrates handler list, donation editor, and apply changes workflow
 * with full API integration for real-time donation management.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, Trash2, FileText, ChevronDown, ChevronRight } from 'lucide-react';
import { Button, Alert, AlertTitle, AlertDescription, Skeleton, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';

// Import components
import HandlerList from '@/components/donations/HandlerList';
import LanguageTabs, { LanguageInfo } from '@/components/donations/LanguageTabs';
import CrossLanguageValidation from '@/components/donations/CrossLanguageValidation';
import ContractEditor from '@/components/donations/ContractEditor';
import DonationValidationPanel from '@/components/donations/DonationValidationPanel';
import ChoiceSurfacesEditor from '@/components/donations/ChoiceSurfacesEditor';
import ExtractionFillersEditor from '@/components/donations/ExtractionFillersEditor';
import type { ExtractionPattern } from '@/utils/patternModel';
import ApplyChangesBar from '@/components/common/ApplyChangesBar';

// Import analysis components
import { 
  ConflictStatusBar, 
  SuggestionPanel 
} from '@/components/analysis';

// Import analysis hooks
import { useRealtimeAnalysis } from '@/hooks';

// Import existing form components
import Section from '@/components/ui/Section';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import ArrayOfStringsEditor from '@/components/editors/ArrayOfStringsEditor';
import CardPatternsEditor from '@/components/donations/CardPatternsEditor';
import SlotCardPatternsEditor from '@/components/donations/SlotCardPatternsEditor';
import PatternTester from '@/components/donations/PatternTester';
import ExamplesEditor from '@/components/editors/ExamplesEditor';
import LemmasEditor from '@/components/editors/LemmasEditor';

import apiClient from '@/utils/apiClient';
import type { 
  DonationData, 
  ValidationResult,
  JsonSchema,
  HandlerLanguageInfo,
  DonationHandlerListResponse,
  LanguageDonationContentResponse,
  // Phase 4: Cross-language validation types
  ValidationReport,
  CompletenessReport,
  CrossLanguageValidationResponse,
  // v1.1 contract (UI-5)
  DonationContract
} from '@/types';

// Note: Utility functions available for future use
// function download(filename: string, text: string): void { ... }
// function fileToText(file: File): Promise<string> { ... }

// Method Donation Editor
interface MethodDonationEditorProps {
  value: DonationData;
  onChange: (value: DonationData) => void;
  globalParamNames: string[];
  schema?: JsonSchema;
  validationResult?: ValidationResult;
  disabled?: boolean;
  showRawJson?: boolean;
  onToggleRawJson?: () => void;
  selectedHandler?: string;
  expandedMethods?: Record<string, Set<number>>;
  onToggleMethodExpansion?: (handlerName: string, methodIndex: number) => void;
  contract?: DonationContract | null;
}

// Minimal typed view of a phrasing parameter (the v1.0 DonationData types params as any[]).
interface PhrasingParam {
  name: string;
  choice_surfaces?: Record<string, string[]>;
  extraction_patterns?: ExtractionPattern[];
  [k: string]: unknown;
}

function MethodDonationEditor({ 
  value, 
  onChange, 
  globalParamNames,
  disabled = false,
  selectedHandler,
  expandedMethods,
  onToggleMethodExpansion,
  currentLanguage,
  contract
}: MethodDonationEditorProps & { currentLanguage?: string }) {
  const { t } = useTranslation('donations');

  // Real-time analysis for conflict detection
  const { 
    conflicts, 
    analysisStatus
  } = useRealtimeAnalysis(selectedHandler || null, currentLanguage || null, value, {
    debounceMs: 800, // Slightly longer debounce for editing
    autoAnalyze: true,
    enableCaching: true
  });
  
  const v = value ?? { description: '', handler_domain: '', method_donations: [] };
  const set = (k: keyof DonationData, val: any): void => {
    onChange({ ...(value ?? {}), [k]: val });
  };

  // Helper functions for method expansion state
  const isMethodExpanded = (methodIndex: number): boolean => {
    return selectedHandler ? (expandedMethods?.[selectedHandler]?.has(methodIndex) || false) : false;
  };

  const toggleMethodExpansion = (methodIndex: number): void => {
    if (selectedHandler && onToggleMethodExpansion) {
      onToggleMethodExpansion(selectedHandler, methodIndex);
    }
  };

  return (
    <div className="space-y-6">
      {/* Real-time Analysis Status */}
      <ConflictStatusBar 
        conflicts={conflicts} 
        status={analysisStatus}
        className="mb-4"
      />
      
      <Section title={t('page.basicInformation')} defaultCollapsed={false}>
        <div className="space-y-4">
          {/* Structural/Metadata fields - Read only */}
          <div className="p-4 bg-muted rounded-lg border border-border">
            <h4 className="text-sm font-medium text-muted-foreground mb-3">{t('page.structureMetadata')}</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <Input
                  label={t('page.handlerDomain')}
                  value={v.handler_domain || ''}
                  onChange={() => {}} // No-op since it's readonly
                  disabled={true}
                  required
                />
                <p className="text-xs text-muted-foreground mt-1">{t('page.handlerDomainHelp')}</p>
              </div>
              <div>
                <Input
                  label={t('page.language')}
                  value={currentLanguage || t('page.unknown')}
                  onChange={() => {}} // No-op since it's readonly
                  disabled={true}
                />
                <p className="text-xs text-muted-foreground mt-1">{t('page.languageHelp')}</p>
              </div>
              <div>
                <Input
                  label={t('page.schemaVersion')}
                  value={v.schema_version || '1.0'}
                  onChange={() => {}} // No-op since it's readonly
                  disabled={true}
                />
                <p className="text-xs text-muted-foreground mt-1">{t('page.schemaVersionHelp')}</p>
              </div>
              <div>
                <Input
                  label={t('page.donationVersion')}
                  value={v.donation_version || '1.0'}
                  onChange={() => {}} // No-op since it's readonly
                  disabled={true}
                />
                <p className="text-xs text-muted-foreground mt-1">{t('page.donationVersionHelp')}</p>
              </div>
            </div>
          </div>
          
          {/* Content fields - Editable */}
          <div>
            <Input
              label={t('page.description')}
              value={v.description || ''}
              onChange={(val) => set('description', val)}
              disabled={disabled}
              required
            />
            <p className="text-xs text-muted-foreground mt-1">{t('page.descriptionHelp')}</p>
          </div>
        </div>
      </Section>

      <Section title={t('page.methods')} badge={<Badge variant="info">{t('page.methodsBadge', { count: v.method_donations?.length || 0 })}</Badge>}>

        <div className="space-y-4">
          {(v.method_donations?.map((method, idx) => {
            const isExpanded = isMethodExpanded(idx);
            const methodName = method.method_name || t('page.methodFallback', { index: idx + 1 });
            
            return (
              <div key={idx} className="border border-border rounded-xl bg-card">
                {/* Collapsible Header */}
                <div className="flex items-center justify-between p-4 border-b border-border">
                  <button
                    onClick={() => toggleMethodExpansion(idx)}
                    className="flex items-center space-x-2 text-left flex-1 hover:bg-muted/60 -m-2 p-2 rounded-lg transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    disabled={disabled}
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    )}
                    <div>
                      <h4 className="text-sm font-medium text-foreground">{methodName}</h4>
                      {method.description && (
                        <p className="text-xs text-muted-foreground mt-0.5">{method.description}</p>
                      )}
                    </div>
                  </button>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive"
                        onClick={() => {
                          const newMethods = v.method_donations.filter((_, i) => i !== idx);
                          set('method_donations', newMethods);
                        }}
                        disabled={disabled}
                        aria-label={t('page.removeMethod')}
                      >
                        <Trash2 />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>{t('page.removeMethod')}</TooltipContent>
                  </Tooltip>
                </div>

                {/* Collapsible Content */}
                {isExpanded && (
                  <div className="p-4">
                    {/* Method Structure - Read only */}
                    <div className="p-3 bg-muted rounded-lg border border-border mb-4">
                      <h5 className="text-xs font-medium text-muted-foreground mb-2">{t('page.methodStructure')}</h5>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                          <Input
                            label={t('page.methodName')}
                            value={method.method_name || ''}
                            onChange={() => {}} // No-op since it's readonly
                            disabled={true}
                            required
                          />
                          <p className="text-xs text-muted-foreground mt-1">{t('page.methodNameHelp')}</p>
                        </div>
                        <div>
                          <Input
                            label={t('page.intentSuffix')}
                            value={method.intent_suffix || ''}
                            onChange={() => {}} // No-op since it's readonly
                            disabled={true}
                          />
                          <p className="text-xs text-muted-foreground mt-1">{t('page.intentSuffixHelp')}</p>
                        </div>
                      </div>
                    </div>
                    
                    {/* Method Content - Editable */}
                    <div className="mb-4">
                      <Input
                        label={t('page.methodDescription')}
                        value={method.description || ''}
                        onChange={(val) => {
                          const newMethods = [...(v.method_donations || [])];
                          newMethods[idx] = { ...method, description: val };
                          set('method_donations', newMethods);
                        }}
                        disabled={disabled}
                        placeholder={t('page.methodDescriptionPlaceholder')}
                      />
                      <p className="text-xs text-muted-foreground mt-1">{t('page.methodDescriptionHelp')}</p>
                    </div>

                    {/* Method-specific editors */}
                    <div className="space-y-4">
                      <ArrayOfStringsEditor
                        label={t('page.globalParameters')}
                        value={method.global_params || []}
                        onChange={(val) => {
                          const newMethods = [...(v.method_donations || [])];
                          newMethods[idx] = { ...method, global_params: val };
                          set('method_donations', newMethods);
                        }}
                        disabled={disabled}
                      />
                      
                      <LemmasEditor
                        value={method.lemmas || []}
                        onChange={(val) => {
                          const newMethods = [...(v.method_donations || [])];
                          newMethods[idx] = { ...method, lemmas: val };
                          set('method_donations', newMethods);
                        }}
                        disabled={disabled}
                      />

                      {/* UI-3: card-based "ways of saying it" (replaces the raw TokenPatternsEditor) */}
                      <div>
                        <div className="text-sm font-medium mb-1">{t('page.whatMightUserSay')}</div>
                        <CardPatternsEditor
                          value={method.token_patterns || []}
                          onChange={(val) => {
                            const newMethods = [...(v.method_donations || [])];
                            newMethods[idx] = { ...method, token_patterns: val };
                            set('method_donations', newMethods);
                          }}
                          disabled={disabled}
                          itemLabel={t('page.wayOfSayingIt')}
                        />
                      </div>

                      {/* UI-3: card-based shared value slots (replaces the raw SlotPatternsEditor).
                          Per-parameter extraction reference these by label (see "How to find each value" below). */}
                      <div>
                        <div className="text-sm font-medium mb-1">{t('page.sharedValueSlots')}</div>
                        <SlotCardPatternsEditor
                          value={method.slot_patterns || {}}
                          onChange={(val) => {
                            const newMethods = [...(v.method_donations || [])];
                            newMethods[idx] = { ...method, slot_patterns: val };
                            set('method_donations', newMethods);
                          }}
                          disabled={disabled}
                        />
                      </div>

                      {/* UI-3 §6: validate a phrasing by example against the real recognizer */}
                      <div>
                        <div className="text-sm font-medium mb-1">{t('page.doesThisWork')}</div>
                        <PatternTester expectedIntent={`${v.handler_domain}.${method.intent_suffix}`} />
                      </div>

                      <ExamplesEditor
                        value={method.examples || []}
                        onChange={(val) => {
                          const newMethods = [...(v.method_donations || [])];
                          newMethods[idx] = { ...method, examples: val };
                          set('method_donations', newMethods);
                        }}
                        globalParams={globalParamNames}
                        disabled={disabled}
                      />

                      {/* UI-3 §3.4: per-parameter value extraction + (for choice/entity) spoken surface forms.
                          Parameters come from the contract; phrasing fields are upserted by name. */}
                      {(() => {
                        const cMethod = contract?.method_donations.find(
                          m => m.method_name === method.method_name && m.intent_suffix === method.intent_suffix
                        );
                        const cParams = cMethod?.parameters ?? [];
                        if (cParams.length === 0) return null;
                        const phrasingParams = (method.parameters ?? []) as PhrasingParam[];

                        const upsertParam = (name: string, patch: Partial<PhrasingParam>): void => {
                          const params: PhrasingParam[] = [...phrasingParams];
                          const pi = params.findIndex(p => p.name === name);
                          if (pi >= 0) params[pi] = { ...params[pi], ...patch };
                          else params.push({ name, ...patch });
                          const newMethods = [...(v.method_donations || [])];
                          newMethods[idx] = { ...method, parameters: params };
                          set('method_donations', newMethods);
                        };

                        return (
                          <div>
                            <div className="text-sm font-medium mb-1">{t('page.howToFindEachValue')}</div>
                            <div className="space-y-3">
                              {cParams.map((cp) => {
                                const pParam = phrasingParams.find(p => p.name === cp.name);
                                const isChoice = (cp.type === 'choice' || cp.type === 'entity') && (cp.choices?.length ?? 0) > 0;
                                return (
                                  <div key={cp.name} className="border border-border rounded-xl p-3">
                                    <div className="text-sm font-medium mb-2">
                                      {t('page.parameterLabel', { name: cp.name })} <span className="text-xs text-muted-foreground">{t('page.parameterType', { type: cp.type })}</span>
                                    </div>
                                    <ExtractionFillersEditor
                                      value={pParam?.extraction_patterns ?? []}
                                      disabled={disabled}
                                      onChange={(eps) => upsertParam(cp.name, { extraction_patterns: eps })}
                                    />
                                    {isChoice && (
                                      <div className="mt-3">
                                        <ChoiceSurfacesEditor
                                          canonicalChoices={cp.choices ?? []}
                                          value={pParam?.choice_surfaces ?? {}}
                                          disabled={disabled}
                                          onChange={(surfaces) => upsertParam(cp.name, { choice_surfaces: surfaces })}
                                        />
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                )}
              </div>
            );
          }) || [])}
          
          <Button
            variant="outline"
            onClick={() => {
              const newMethods = [...(v.method_donations || []), { method_name: '', intent_suffix: '', description: '', phrases: [], parameters: [], token_patterns: [], slot_patterns: {}, examples: [] }];
              set('method_donations', newMethods);
            }}
            className="w-full h-auto p-4 border-2 border-dashed rounded-xl text-muted-foreground hover:text-foreground"
            disabled={disabled}
          >
            {t('page.addMethod')}
          </Button>
        </div>
      </Section>

      {/* Smart Suggestions Panel */}
      {conflicts.length > 0 && (
        <SuggestionPanel 
          conflicts={conflicts}
          onApplySuggestion={(conflictId, suggestion) => {
            console.log('Apply suggestion:', conflictId, suggestion);
            // TODO: Implement suggestion application logic
          }}
          onDismissConflict={(conflictId) => {
            console.log('Dismiss conflict:', conflictId);
            // TODO: Implement conflict dismissal logic
          }}
        />
      )}
    </div>
  );
}

const DonationsPage: React.FC = () => {
  const { t } = useTranslation(['donations', 'common']);
  // Helper function to extract lemmas from token patterns and slot patterns
  // Core state - Updated for language-aware architecture
  const [handlersList, setHandlersList] = useState<HandlerLanguageInfo[]>([]);
  const [donations, setDonations] = useState<Record<string, DonationData>>({});
  const [originalDonations, setOriginalDonations] = useState<Record<string, DonationData>>({});
  const [schema, setSchema] = useState<JsonSchema | null>(null);
  const [selectedHandler, setSelectedHandler] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState<Record<string, boolean>>({});

  // Loading and error states
  const [loadingHandlers, setLoadingHandlers] = useState(true);
  const [, setLoadingSchema] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  // UI state
  const [searchQuery, setSearchQuery] = useState('');
  const [showRawJson, setShowRawJson] = useState(false);
  
  // Method collapsible state - track expanded methods by handler:methodIndex
  const [expandedMethods, setExpandedMethods] = useState<Record<string, Set<number>>>({});

  // Validation state
  const [validationResults, setValidationResults] = useState<Record<string, ValidationResult>>({});

  // Language support state  
  const [selectedLanguage, setSelectedLanguage] = useState<string>('en');
  const [languageCountFilter, setLanguageCountFilter] = useState<'all' | 'single' | 'multiple'>('all');
  
  // Phase 4: Cross-language validation state
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const [completenessReport, setCompletenessReport] = useState<CompletenessReport | null>(null);

  // UI-5: language-neutral contract editing (per handler), separate from per-language phrasing.
  const [contract, setContract] = useState<DonationContract | null>(null);
  const [contractOriginal, setContractOriginal] = useState<string>('');
  const [contractStatus, setContractStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const contractChanged = contract != null && JSON.stringify(contract) !== contractOriginal;

  const loadContract = useCallback(async (handlerName: string) => {
    try {
      const res = await apiClient.getDonationContract(handlerName);
      setContract(res.contract as DonationContract);
      setContractOriginal(JSON.stringify(res.contract));
      setContractStatus('idle');
    } catch {
      setContract(null);
      setContractOriginal('');
    }
  }, []);

  const handleSaveContract = useCallback(async () => {
    if (!selectedHandler || !contract) return;
    try {
      setContractStatus('saving');
      await apiClient.updateDonationContract(selectedHandler, contract);
      setContractOriginal(JSON.stringify(contract));
      setContractStatus('saved');
      setTimeout(() => setContractStatus('idle'), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save contract');
      setContractStatus('error');
    }
  }, [selectedHandler, contract]);

  // Helper functions for language management
  const getAvailableLanguagesForHandler = (handlerName: string): LanguageInfo[] => {
    const handler = handlersList.find(h => h.handler_name === handlerName);
    if (!handler) return [];
    
    return handler.languages.map(lang => {
      const donationKey = `${handlerName}:${lang}`;
      const donation = donations[donationKey];
      const methodCount = donation?.method_donations?.length || 0;
      const hasValidationErrors = validationResults[donationKey] && !validationResults[donationKey].valid;
      
      return {
        code: lang,
        label: lang.toUpperCase(),
        status: hasValidationErrors ? 'error' as const : 'loaded' as const,
        methodCount,
        lastModified: new Date().toISOString(),
        validationErrors: hasValidationErrors ? validationResults[donationKey].errors.length : 0
      };
    });
  };

  const getSupportedLanguages = (): string[] => {
    const handler = handlersList.find(h => h.handler_name === selectedHandler);
    return handler?.supported_languages || ['en', 'ru'];
  };

  const convertToNestedHasChanges = (flatChanges: Record<string, boolean>): Record<string, Record<string, boolean>> => {
    const nested: Record<string, Record<string, boolean>> = {};
    
    for (const [key, hasChanged] of Object.entries(flatChanges)) {
      if (key.includes(':')) {
        const [handlerName, language] = key.split(':');
        if (!nested[handlerName]) {
          nested[handlerName] = {};
        }
        nested[handlerName][language] = hasChanged;
      }
    }
    
    return nested;
  };

  const handleCreateLanguage = async (language: string, templateFrom?: string) => {
    if (!selectedHandler) return;
    
    try {
      await apiClient.createLanguage(selectedHandler, language, { 
        copyFrom: templateFrom,
        useTemplate: !templateFrom 
      });
      
      // Reload handlers to get updated language list
      await loadHandlers();
      
      // Switch to the new language
      setSelectedLanguage(language);
    } catch (err) {
      console.error('Failed to create language:', err);
      setError(err instanceof Error ? err.message : 'Failed to create language');
    }
  };

  const handleDeleteLanguage = async (language: string) => {
    if (!selectedHandler) return;
    
    try {
      await apiClient.deleteLanguage(selectedHandler, language);
      
      // Reload handlers to get updated language list
      await loadHandlers();
      
      // Switch to default language if current language was deleted
      if (selectedLanguage === language) {
        const handler = handlersList.find(h => h.handler_name === selectedHandler);
        if (handler && handler.languages.length > 0) {
          setSelectedLanguage(handler.default_language || handler.languages[0]);
        }
      }
    } catch (err) {
      console.error('Failed to delete language:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete language');
    }
  };

  // Helper function for method expansion state
  const toggleMethodExpansion = (handlerName: string, methodIndex: number): void => {
    setExpandedMethods(prev => {
      const handlerExpanded = prev[handlerName] || new Set();
      const newExpanded = new Set(handlerExpanded);
      
      if (newExpanded.has(methodIndex)) {
        newExpanded.delete(methodIndex);
      } else {
        newExpanded.add(methodIndex);
      }
      
      return {
        ...prev,
        [handlerName]: newExpanded
      };
    });
  };

  // Phase 4: Cross-language validation functions
  const loadCrossLanguageValidation = async (handlerName: string) => {
    if (!handlerName) return;
    
    try {
      const response: CrossLanguageValidationResponse = await apiClient.getCrossLanguageValidation(handlerName);
      
      setValidationReport(response.parameter_report || null);
      setCompletenessReport(response.completeness_report || null);
    } catch (err) {
      // Gracefully handle 404 - the cross-language validation API might not be implemented yet
      if (err instanceof Error && err.message.includes('404')) {
        console.warn('Cross-language validation API not implemented yet - feature will be hidden');
        setValidationReport(null);
        setCompletenessReport(null);
        return;
      }
      
      console.error('Failed to load cross-language validation:', err);
      setValidationReport(null);
      setCompletenessReport(null);
    }
  };

  const handleRefreshValidation = useCallback(() => {
    if (selectedHandler) {
      void loadCrossLanguageValidation(selectedHandler);
    }
  }, [selectedHandler]);

  // Load initial data
  useEffect(() => {
    void Promise.all([
      loadHandlers(),
      loadSchema()
    ]);
  // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional scoped/mount load (load fns are not memoized)
  }, []);

  // Load selected donation when handler or language changes
  useEffect(() => {
    if (selectedHandler && selectedLanguage) {
      const donationKey = `${selectedHandler}:${selectedLanguage}`;
      if (!donations[donationKey]) {
        void loadDonation(selectedHandler, selectedLanguage);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional scoped/mount load (load fns are not memoized)
  }, [selectedHandler, selectedLanguage, donations]);

  // Load the language-neutral contract when the handler changes (UI-5).
  useEffect(() => {
    if (selectedHandler) {
      void loadContract(selectedHandler);
    } else {
      setContract(null);
      setContractOriginal('');
    }
  }, [selectedHandler, loadContract]);

  // Load cross-language validation when handler changes and has multiple languages
  useEffect(() => {
    if (selectedHandler) {
      const handler = handlersList.find(h => h.handler_name === selectedHandler);
      if (handler && handler.languages.length > 1) {
        void loadCrossLanguageValidation(selectedHandler);
      } else {
        // Clear validation for single-language handlers
        setValidationReport(null);
        setCompletenessReport(null);
      }
    }
  }, [selectedHandler, handlersList]);

  const loadHandlers = async (): Promise<void> => {
    try {
      setLoadingHandlers(true);
      setError(null);

      const response: DonationHandlerListResponse = await apiClient.getDonationHandlers();
      setHandlersList(response.handlers || []);

      // Auto-select first handler if none selected
      if (response.handlers && response.handlers.length > 0 && !selectedHandler) {
        setSelectedHandler(response.handlers[0].handler_name);
        // Also set default language for the first handler
        const firstHandler = response.handlers[0];
        if (firstHandler.languages.length > 0) {
          setSelectedLanguage(firstHandler.default_language || firstHandler.languages[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load handlers:', err);
      setError(err instanceof Error ? err.message : 'Failed to load handlers');
    } finally {
      setLoadingHandlers(false);
    }
  };

  const loadSchema = async (): Promise<void> => {
    try {
      setLoadingSchema(true);
      const response = await apiClient.getDonationSchema();
      setSchema(response.json_schema as JsonSchema);
    } catch (err) {
      console.error('Failed to load schema:', err);
      // Schema loading failure is not critical, continue without it
    } finally {
      setLoadingSchema(false);
    }
  };

  const loadDonation = async (handlerName: string, language?: string): Promise<void> => {
    const targetLanguage = language || selectedLanguage;
    if (!targetLanguage) {
      console.warn('No language selected for loading donation');
      return;
    }
    // BUG-8: key by `${handler}:${language}` in BOTH the success and 404-fallback branches — the
    // load effect (and the editor) read this composite key, so storing the fallback under the bare
    // handler name left the key permanently absent → the effect re-fired forever (infinite reload).
    const donationKey = `${handlerName}:${targetLanguage}`;

    try {
      const response: LanguageDonationContentResponse = await apiClient.getLanguageDonation(handlerName, targetLanguage);

      setDonations(prev => ({
        ...prev,
        [donationKey]: response.donation_data
      }));
      setOriginalDonations(prev => ({
        ...prev,
        [donationKey]: structuredClone(response.donation_data)
      }));
    } catch (err) {
      // Handle 404 errors gracefully - some handlers might not have donation files yet
      if (err instanceof Error && err.message.includes('404')) {
        console.warn(`No donation file found for handler ${handlerName} - this is normal for handlers without donations`);
        // Create empty donation structure for handlers without donation files
        const emptyDonation: DonationData = {
          description: `Donation configuration for ${handlerName}`,
          handler_domain: handlerName.split('_')[0] || 'general', // Try to infer domain from handler name
          method_donations: []
        };
        setDonations(prev => ({
          ...prev,
          [donationKey]: emptyDonation
        }));
        setOriginalDonations(prev => ({
          ...prev,
          [donationKey]: structuredClone(emptyDonation)
        }));
      } else {
        console.error(`Failed to load donation ${handlerName}:`, err);
        setError(err instanceof Error ? err.message : `Failed to load donation ${handlerName}`);
      }
    }
  };

  const handleDonationChange = useCallback((handlerName: string, newDonation: DonationData): void => {
    setDonations(prev => ({
      ...prev,
      [handlerName]: newDonation
    }));

    // Check if changed
    const original = originalDonations[handlerName];
    const isChanged = JSON.stringify(newDonation) !== JSON.stringify(original);
    
    setHasChanges(prev => ({
      ...prev,
      [handlerName]: isChanged
    }));
  }, [originalDonations]);


  // Get global parameter names for the current donation
  const globalParamNames = useMemo(() => {
    if (!selectedHandler || !selectedLanguage) return [];
    const donationKey = `${selectedHandler}:${selectedLanguage}`;
    if (!donations[donationKey]) return [];
    const donation = donations[donationKey];
    const allParams = new Set<string>();
    
    donation.method_donations?.forEach(method => {
      method.global_params?.forEach(param => allParams.add(param));
    });
    
    return Array.from(allParams).sort();
    // BUG-8: depend on selectedLanguage too — the memo reads it, so a switch to an already-cached
    // language (which doesn't change `donations`) must still recompute, else ExamplesEditor gets the
    // previous language's global param names.
  }, [donations, selectedHandler, selectedLanguage]);

  // BUG-8: the selected handler can be absent from handlersList (e.g. after a reload that removed or
  // renamed it), so resolve it safely instead of asserting non-null at the CrossLanguageValidation
  // render — which derefs handlerInfo.languages and would crash.
  const selectedHandlerInfo = selectedHandler
    ? handlersList.find(h => h.handler_name === selectedHandler)
    : undefined;

  const handleSave = async (): Promise<void> => {
    if (!selectedHandler || !selectedLanguage) return;

    try {
      setSaveStatus('saving');
      setError(null);

      const donationKey = `${selectedHandler}:${selectedLanguage}`;
      const donationData = donations[donationKey];
      
      if (!donationData) {
        throw new Error(t('page.noDonationData'));
      }

      await apiClient.updateLanguageDonation(selectedHandler, selectedLanguage, donationData);

      // Update original to mark as saved
      setOriginalDonations(prev => ({
        ...prev,
        [donationKey]: structuredClone(donationData)
      }));

      setHasChanges(prev => ({
        ...prev,
        [donationKey]: false
      }));

      setSaveStatus('saved');
      
      // Reset save status after 2 seconds
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (err) {
      console.error('Failed to save donation:', err);
      setError(err instanceof Error ? err.message : 'Failed to save donation');
      setSaveStatus('error');
    }
  };

  const handleValidate = async (): Promise<ValidationResult> => {
    if (!selectedHandler || !selectedLanguage) {
      return { valid: false, errors: ['No handler or language selected'], warnings: [] };
    }
    // BUG-8: the language tab's error indicator reads validationResults[`${handler}:${lang}`], so the
    // catch must store under the same composite key (not the bare handler) or the failure stays hidden.
    const donationKey = `${selectedHandler}:${selectedLanguage}`;

    try {
      const donationData = donations[donationKey];
      
      if (!donationData) {
        return { valid: false, errors: ['No donation data to validate'], warnings: [] };
      }
      
      const response = await apiClient.validateLanguageDonation(selectedHandler, selectedLanguage, donationData);
      
      // Convert new API response structure to legacy ValidationResult format
      const validationResult: ValidationResult = {
        valid: response.is_valid,
        errors: response.errors?.map((err: any) => err.message) || [],
        warnings: response.warnings?.map((warn: any) => warn.message) || [],
        details: response
      };

      setValidationResults(prev => ({
        ...prev,
        [donationKey]: validationResult
      }));

      return validationResult;
    } catch (err: any) {
      console.error('Validation failed:', err);
      const errorResult: ValidationResult = {
        valid: false,
        errors: [err instanceof Error ? err.message : 'Validation failed'],
        warnings: []
      };
      
      setValidationResults(prev => ({
        ...prev,
        [donationKey]: errorResult
      }));

      return errorResult;
    }
  };

  const handleCancel = (): void => {
    if (!selectedHandler || !selectedLanguage) return;

    const donationKey = `${selectedHandler}:${selectedLanguage}`;
    const original = originalDonations[donationKey];
    if (original) {
      setDonations(prev => ({
        ...prev,
        [donationKey]: structuredClone(original)
      }));
      
      setHasChanges(prev => ({
        ...prev,
        [donationKey]: false
      }));
    }
  };

  // No need for filtering logic here - it's handled by HandlerList component

  if (loadingHandlers) {
    return (
      <div className="p-6">
        <Skeleton className="h-8 rounded mb-4" />
        <div className="grid grid-cols-4 gap-4">
          <Skeleton className="h-96 rounded" />
          <Skeleton className="col-span-3 h-96 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive" className="rounded-lg p-4">
          <AlertCircle />
          <div>
            <AlertTitle>{t('page.failedToLoad')}</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => {
                setError(null);
                void loadHandlers();
              }}
            >
              {t('common:actions.retry')}
            </Button>
          </div>
        </Alert>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Main Content Area with Sidebar */}
      <div className="flex-1 flex">
        {/* Handler List */}
        <HandlerList
          handlers={handlersList}
          selectedHandler={selectedHandler}
          selectedLanguage={selectedLanguage}
          onSelect={setSelectedHandler}
          onLanguageSelect={(handlerName, language) => {
            setSelectedHandler(handlerName);
            setSelectedLanguage(language);
          }}
          onCreateLanguage={(language, templateFrom) => void handleCreateLanguage(language, templateFrom)}
          onDeleteLanguage={(language) => void handleDeleteLanguage(language)}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          filterLanguageCount={languageCountFilter}
          onFilterLanguageCountChange={setLanguageCountFilter}
          hasChanges={convertToNestedHasChanges(hasChanges)}
          loading={loadingHandlers}
          error={error}
        />

      {/* Main Editor Area */}
      <div className="flex-1 flex flex-col">
        {selectedHandler ? (
          <>
            {/* Language Tabs */}
            <LanguageTabs
              activeLanguage={selectedLanguage}
              availableLanguages={getAvailableLanguagesForHandler(selectedHandler)}
              supportedLanguages={getSupportedLanguages()}
              onLanguageChange={setSelectedLanguage}
              onCreateLanguage={(language, templateFrom) => void handleCreateLanguage(language, templateFrom)}
              onDeleteLanguage={(language) => void handleDeleteLanguage(language)}
              disabled={saveStatus === 'saving'}
              // Phase 4: Cross-language validation props
              handlerName={selectedHandler}
              validationReport={validationReport}
              completenessReport={completenessReport}
              onRefreshValidation={handleRefreshValidation}
            />

            {/* Cross-Language Validation Panel */}
            {selectedHandler && selectedHandlerInfo && (
              <div className="border-b border-border p-4 bg-muted">
                <CrossLanguageValidation
                  handlerName={selectedHandler}
                  handlerInfo={selectedHandlerInfo}
                  activeLanguage={selectedLanguage}
                  validationReport={validationReport}
                  completenessReport={completenessReport}
                  onRefreshValidation={handleRefreshValidation}
                  isLoading={saveStatus === 'saving'}
                  disabled={saveStatus === 'saving'}
                />
              </div>
            )}

            {/* QUAL-42: wiring report + LLM translation validation/drafting */}
            <div className="border-b border-border p-4 bg-muted">
              <DonationValidationPanel
                handlerName={selectedHandler}
                sourceLanguage={selectedLanguage}
                availableLanguages={getAvailableLanguagesForHandler(selectedHandler).map(l => l.code)}
                disabled={saveStatus === 'saving' || contractStatus === 'saving'}
              />
            </div>

            {/* Header */}
            <div className="border-b border-border p-6 bg-card">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-foreground">{selectedHandler}</h1>
                  {selectedLanguage && donations[`${selectedHandler}:${selectedLanguage}`] && (
                    <p className="text-muted-foreground mt-1">
                      {donations[`${selectedHandler}:${selectedLanguage}`].description || t('page.noDescription')}
                    </p>
                  )}
                </div>
                {selectedHandler && selectedLanguage && hasChanges[`${selectedHandler}:${selectedLanguage}`] && (
                  <Badge variant="warning">{t('page.unsavedChanges')}</Badge>
                )}
              </div>
            </div>

            {/* Editor Content */}
            <div className="flex-1 overflow-auto p-6">
              {/* UI-5: language-neutral contract (structural) — edited once per handler */}
              {contract && (
                <div className="mb-6">
                  <ContractEditor
                    contract={contract}
                    onChange={setContract}
                    disabled={contractStatus === 'saving'}
                  />
                  <div className="flex items-center gap-2 mt-3">
                    <Button
                      onClick={() => void handleSaveContract()}
                      disabled={!contractChanged || contractStatus === 'saving'}
                    >
                      {contractStatus === 'saving' ? t('page.savingContract') : t('page.saveContract')}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setContract(JSON.parse(contractOriginal) as DonationContract)}
                      disabled={!contractChanged || contractStatus === 'saving'}
                    >
                      {t('page.revert')}
                    </Button>
                    {contractStatus === 'saved' && <Badge variant="success">{t('page.contractSaved')}</Badge>}
                    {contractChanged && <Badge variant="warning">{t('page.unsavedContractChanges')}</Badge>}
                  </div>
                </div>
              )}

              <div className="text-lg font-semibold text-foreground mb-3">
                {t('page.phrasing', { language: selectedLanguage?.toUpperCase() })}
              </div>
              {selectedLanguage && donations[`${selectedHandler}:${selectedLanguage}`] ? (
                <div>
                  {/* Show notice for empty donations */}
                  {donations[`${selectedHandler}:${selectedLanguage}`].method_donations?.length === 0 && (
                    <Alert variant="accent" className="mb-4 rounded-lg p-4">
                      <AlertCircle />
                      <div>
                        <AlertTitle>{t('page.newDonationTitle')}</AlertTitle>
                        <AlertDescription>
                          {t('page.newDonationText')}
                        </AlertDescription>
                      </div>
                    </Alert>
                  )}
                  
                  <MethodDonationEditor
                    value={donations[`${selectedHandler}:${selectedLanguage}`]}
                    onChange={(newDonation) => handleDonationChange(`${selectedHandler}:${selectedLanguage}`, newDonation)}
                    globalParamNames={globalParamNames}
                    schema={schema || undefined}
                    validationResult={selectedLanguage ? validationResults[`${selectedHandler}:${selectedLanguage}`] : undefined}
                    disabled={saveStatus === 'saving'}
                    showRawJson={showRawJson}
                    onToggleRawJson={() => setShowRawJson(!showRawJson)}
                    selectedHandler={selectedHandler}
                    expandedMethods={expandedMethods}
                    onToggleMethodExpansion={toggleMethodExpansion}
                    currentLanguage={selectedLanguage}
                    contract={contract}
                  />
                </div>
              ) : (
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                  <span className="ml-2 text-muted-foreground">{t('page.loadingDonation')}</span>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full bg-muted">
            <div className="text-center">
              <FileText className="w-16 h-16 text-muted-foreground/60 mx-auto mb-4" />
              <h3 className="text-xl font-medium text-foreground mb-2">{t('page.selectHandlerTitle')}</h3>
              <p className="text-muted-foreground">
                {t('page.selectHandlerText')}
              </p>
            </div>
          </div>
        )}
      </div>
      </div>

      {/* Apply Changes Bar - Positioned at bottom of entire page */}
      <ApplyChangesBar
        visible={!!(selectedHandler && selectedLanguage && hasChanges[`${selectedHandler}:${selectedLanguage}`])}
        selectedHandler={selectedHandler || undefined}
        hasUnsavedChanges={selectedHandler && selectedLanguage ? hasChanges[`${selectedHandler}:${selectedLanguage}`] || false : false}
        onSave={handleSave}
        onValidate={handleValidate}
        onCancel={handleCancel}
        loading={saveStatus === 'saving'}
        lastSaved={saveStatus === 'saved' ? new Date() : undefined}
        nluContext={{
          language: selectedLanguage || undefined,
          donationData: selectedHandler && selectedLanguage ? donations[`${selectedHandler}:${selectedLanguage}`] : undefined,
          enableEnhancedValidation: true
        }}
      />
    </div>
  );
};

export default DonationsPage;
