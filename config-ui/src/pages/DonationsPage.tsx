/**
 * DonationsPage Component - Main donations management interface
 * 
 * Integrates handler list, donation editor, and apply changes workflow
 * with full API integration for real-time donation management.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { AlertCircle, Trash2, FileText, ChevronDown, ChevronRight } from 'lucide-react';

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
      
      <Section title="Basic Information" defaultCollapsed={false}>
        <div className="space-y-4">
          {/* Structural/Metadata fields - Read only */}
          <div className="p-4 bg-gray-50 rounded-lg border">
            <h4 className="text-sm font-medium text-gray-700 mb-3">Structure & Metadata (Read-only)</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <Input
                  label="Handler Domain"
                  value={v.handler_domain || ''}
                  onChange={() => {}} // No-op since it's readonly
                  disabled={true}
                  required
                />
                <p className="text-xs text-gray-500 mt-1">Defines which handler this donation belongs to</p>
              </div>
              <div>
                <Input
                  label="Language"
                  value={currentLanguage || 'Unknown'}
                  onChange={() => {}} // No-op since it's readonly
                  disabled={true}
                />
                <p className="text-xs text-gray-500 mt-1">Language code for this donation file</p>
              </div>
              <div>
                <Input
                  label="Schema Version"
                  value={v.schema_version || '1.0'}
                  onChange={() => {}} // No-op since it's readonly
                  disabled={true}
                />
                <p className="text-xs text-gray-500 mt-1">JSON schema version used</p>
              </div>
              <div>
                <Input
                  label="Donation Version"
                  value={v.donation_version || '1.0'}
                  onChange={() => {}} // No-op since it's readonly
                  disabled={true}
                />
                <p className="text-xs text-gray-500 mt-1">Content version for caching</p>
              </div>
            </div>
          </div>
          
          {/* Content fields - Editable */}
          <div>
            <Input
              label="Description"
              value={v.description || ''}
              onChange={(val) => set('description', val)}
              disabled={disabled}
              required
            />
            <p className="text-xs text-gray-500 mt-1">Human-readable description of this handler's functionality</p>
          </div>
        </div>
      </Section>

      <Section title="Methods" badge={<Badge variant="info">{v.method_donations?.length || 0} methods</Badge>}>

        <div className="space-y-4">
          {(v.method_donations?.map((method, idx) => {
            const isExpanded = isMethodExpanded(idx);
            const methodName = method.method_name || `Method ${idx + 1}`;
            
            return (
              <div key={idx} className="border rounded-xl bg-white">
                {/* Collapsible Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-100">
                  <button
                    onClick={() => toggleMethodExpansion(idx)}
                    className="flex items-center space-x-2 text-left flex-1 hover:bg-gray-50 -m-2 p-2 rounded-lg transition-colors"
                    disabled={disabled}
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    )}
                    <div>
                      <h4 className="text-sm font-medium text-gray-900">{methodName}</h4>
                      {method.description && (
                        <p className="text-xs text-gray-500 mt-0.5">{method.description}</p>
                      )}
                    </div>
                  </button>
                  <button
                    onClick={() => {
                      const newMethods = v.method_donations.filter((_, i) => i !== idx);
                      set('method_donations', newMethods);
                    }}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                    disabled={disabled}
                    title="Remove method"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                {/* Collapsible Content */}
                {isExpanded && (
                  <div className="p-4">
                    {/* Method Structure - Read only */}
                    <div className="p-3 bg-gray-50 rounded-lg border mb-4">
                      <h5 className="text-xs font-medium text-gray-600 mb-2">Method Structure (Read-only)</h5>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                          <Input
                            label="Method name"
                            value={method.method_name || ''}
                            onChange={() => {}} // No-op since it's readonly
                            disabled={true}
                            required
                          />
                          <p className="text-xs text-gray-500 mt-1">Python method name - must match handler code</p>
                        </div>
                        <div>
                          <Input
                            label="Intent suffix"
                            value={method.intent_suffix || ''}
                            onChange={() => {}} // No-op since it's readonly
                            disabled={true}
                          />
                          <p className="text-xs text-gray-500 mt-1">Defines intent routing structure</p>
                        </div>
                      </div>
                    </div>
                    
                    {/* Method Content - Editable */}
                    <div className="mb-4">
                      <Input
                        label="Description"
                        value={method.description || ''}
                        onChange={(val) => {
                          const newMethods = [...(v.method_donations || [])];
                          newMethods[idx] = { ...method, description: val };
                          set('method_donations', newMethods);
                        }}
                        disabled={disabled}
                        placeholder="Describe what this method does"
                      />
                      <p className="text-xs text-gray-500 mt-1">Human-readable description of method functionality</p>
                    </div>

                    {/* Method-specific editors */}
                    <div className="space-y-4">
                      <ArrayOfStringsEditor
                        label="Global Parameters"
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
                        <div className="text-sm font-medium mb-1">What might the user say?</div>
                        <CardPatternsEditor
                          value={method.token_patterns || []}
                          onChange={(val) => {
                            const newMethods = [...(v.method_donations || [])];
                            newMethods[idx] = { ...method, token_patterns: val };
                            set('method_donations', newMethods);
                          }}
                          disabled={disabled}
                          itemLabel="way of saying it"
                        />
                      </div>

                      {/* UI-3: card-based shared value slots (replaces the raw SlotPatternsEditor).
                          Per-parameter extraction reference these by label (see "How to find each value" below). */}
                      <div>
                        <div className="text-sm font-medium mb-1">Shared value slots</div>
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
                        <div className="text-sm font-medium mb-1">Does this work?</div>
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
                            <div className="text-sm font-medium mb-1">How to find each value</div>
                            <div className="space-y-3">
                              {cParams.map((cp) => {
                                const pParam = phrasingParams.find(p => p.name === cp.name);
                                const isChoice = (cp.type === 'choice' || cp.type === 'entity') && (cp.choices?.length ?? 0) > 0;
                                return (
                                  <div key={cp.name} className="border rounded-xl p-3">
                                    <div className="text-sm font-medium mb-2">
                                      Parameter “{cp.name}” <span className="text-xs text-gray-500">({cp.type})</span>
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
          
          <button
            onClick={() => {
              const newMethods = [...(v.method_donations || []), { method_name: '', intent_suffix: '', description: '', phrases: [], parameters: [], token_patterns: [], slot_patterns: {}, examples: [] }];
              set('method_donations', newMethods);
            }}
            className="w-full p-4 border-2 border-dashed border-gray-300 rounded-xl text-gray-600 hover:border-gray-400 hover:text-gray-700 transition-colors"
            disabled={disabled}
          >
            + Add Method
          </button>
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
    
    try {
      const response: LanguageDonationContentResponse = await apiClient.getLanguageDonation(handlerName, targetLanguage);
      const donationKey = `${handlerName}:${targetLanguage}`;
      
      setDonations(prev => ({
        ...prev,
        [donationKey]: response.donation_data
      }));
      setOriginalDonations(prev => ({
        ...prev,
        [donationKey]: JSON.parse(JSON.stringify(response.donation_data))
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
          [handlerName]: emptyDonation
        }));
        setOriginalDonations(prev => ({
          ...prev,
          [handlerName]: JSON.parse(JSON.stringify(emptyDonation))
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
  // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional scoped/mount load (load fns are not memoized)
  }, [donations, selectedHandler]);

  const handleSave = async (): Promise<void> => {
    if (!selectedHandler || !selectedLanguage) return;

    try {
      setSaveStatus('saving');
      setError(null);

      const donationKey = `${selectedHandler}:${selectedLanguage}`;
      const donationData = donations[donationKey];
      
      if (!donationData) {
        throw new Error('No donation data to save');
      }

      await apiClient.updateLanguageDonation(selectedHandler, selectedLanguage, donationData);

      // Update original to mark as saved
      setOriginalDonations(prev => ({
        ...prev,
        [donationKey]: JSON.parse(JSON.stringify(donationData))
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

    try {
      const donationKey = `${selectedHandler}:${selectedLanguage}`;
      const donationData = donations[donationKey];
      
      if (!donationData) {
        return { valid: false, errors: ['No donation data to validate'], warnings: [] };
      }
      
      const response = await apiClient.validateLanguageDonation(selectedHandler, selectedLanguage, donationData);
      
      // Convert new API response structure to legacy ValidationResult format
      const validationResult: ValidationResult = {
        valid: response.is_valid,
        errors: response.errors?.map((err: any) => err.msg) || [],
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
        [selectedHandler]: errorResult
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
        [donationKey]: JSON.parse(JSON.stringify(original))
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
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4"></div>
          <div className="grid grid-cols-4 gap-4">
            <div className="h-96 bg-gray-200 rounded"></div>
            <div className="col-span-3 h-96 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start">
            <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 mr-3 flex-shrink-0" />
            <div>
              <h3 className="text-red-800 font-medium">Failed to load donations</h3>
              <p className="text-red-700 text-sm mt-1">{error}</p>
              <button
                onClick={() => {
                  setError(null);
                  void loadHandlers();
                }}
                className="mt-3 px-3 py-1 bg-red-100 text-red-800 rounded text-sm hover:bg-red-200 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
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
      <div className="flex-1 flex flex-col pb-20">
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
            {selectedHandler && (
              <div className="border-b border-gray-200 p-4 bg-gray-50">
                <CrossLanguageValidation
                  handlerName={selectedHandler}
                  handlerInfo={handlersList.find(h => h.handler_name === selectedHandler)!}
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
            <div className="border-b border-gray-200 p-4 bg-gray-50">
              <DonationValidationPanel
                handlerName={selectedHandler}
                sourceLanguage={selectedLanguage}
                availableLanguages={getAvailableLanguagesForHandler(selectedHandler).map(l => l.code)}
                disabled={saveStatus === 'saving' || contractStatus === 'saving'}
              />
            </div>

            {/* Header */}
            <div className="border-b border-gray-200 p-6 bg-white">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">{selectedHandler}</h1>
                  {selectedLanguage && donations[`${selectedHandler}:${selectedLanguage}`] && (
                    <p className="text-gray-600 mt-1">
                      {donations[`${selectedHandler}:${selectedLanguage}`].description || 'No description'}
                    </p>
                  )}
                </div>
                {selectedHandler && selectedLanguage && hasChanges[`${selectedHandler}:${selectedLanguage}`] && (
                  <Badge variant="warning">Unsaved Changes</Badge>
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
                    <button
                      onClick={() => void handleSaveContract()}
                      disabled={!contractChanged || contractStatus === 'saving'}
                      className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    >
                      {contractStatus === 'saving' ? 'Saving…' : 'Save contract'}
                    </button>
                    <button
                      onClick={() => setContract(JSON.parse(contractOriginal) as DonationContract)}
                      disabled={!contractChanged || contractStatus === 'saving'}
                      className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50"
                    >
                      Revert
                    </button>
                    {contractStatus === 'saved' && <span className="text-sm text-green-700">Contract saved</span>}
                    {contractChanged && <Badge variant="warning">Unsaved contract changes</Badge>}
                  </div>
                </div>
              )}

              <div className="text-lg font-semibold text-gray-900 mb-3">
                Phrasing — {selectedLanguage?.toUpperCase()}
              </div>
              {selectedLanguage && donations[`${selectedHandler}:${selectedLanguage}`] ? (
                <div>
                  {/* Show notice for empty donations */}
                  {donations[`${selectedHandler}:${selectedLanguage}`].method_donations?.length === 0 && (
                    <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-start">
                        <AlertCircle className="w-5 h-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" />
                        <div>
                          <h3 className="text-blue-800 font-medium">New Donation Configuration</h3>
                          <p className="text-blue-700 text-sm mt-1">
                            This handler doesn't have a donation file yet. You can create one by adding methods below.
                          </p>
                        </div>
                      </div>
                    </div>
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
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <span className="ml-2 text-gray-600">Loading donation...</span>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full bg-gray-50">
            <div className="text-center">
              <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-medium text-gray-900 mb-2">Select a handler</h3>
              <p className="text-gray-500">
                Choose a handler from the list to edit its donation configuration
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
