/**
 * PromptsPage Component - Main prompts management interface
 * 
 * Integrates handler list, prompt editor, and apply changes workflow
 * with full API integration for real-time prompt management.
 * Follows the exact same pattern as TemplatesPage for consistency.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, MessageSquare, Code } from 'lucide-react';

// Import reusable components from donations
import HandlerList from '@/components/donations/HandlerList';
import LanguageTabs, { LanguageInfo } from '@/components/donations/LanguageTabs';
import ApplyChangesBar from '@/components/common/ApplyChangesBar';

// Import prompt-specific components
import PromptEditor from '@/components/editors/PromptEditor';

// Import UI components
import Badge from '@/components/ui/Badge';

import apiClient from '@/utils/apiClient';
import type { 
  HandlerLanguageInfo,
  PromptDefinition
} from '@/types';

interface PromptData {
  [key: string]: PromptDefinition;
}

interface PromptValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

const PromptsPage: React.FC = () => {
  const { t } = useTranslation(['prompts', 'common']);
  // Core state management
  const [handlers, setHandlers] = useState<HandlerLanguageInfo[]>([]);
  const [selectedHandler, setSelectedHandler] = useState<string | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string | null>(null);
  const [promptData, setPromptData] = useState<PromptData>({});
  const [originalPromptData, setOriginalPromptData] = useState<PromptData>({});
  
  // UI state
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [, setValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Prompt management state
  const [, setValidationResult] = useState<PromptValidationResult>({
    isValid: true,
    errors: [],
    warnings: []
  });
  // UI-14 (E1): derive hasChanges instead of syncing it via an effect (which lagged a render and
  // forced an extra one). Every former imperative setHasChanges(false) coincided with data===original
  // (save sets original=data; select/discard/delete make them equal), so the derived value is equivalent.
  const hasChanges = useMemo(
    () => !!(selectedHandler && selectedLanguage) &&
      JSON.stringify(promptData) !== JSON.stringify(originalPromptData),
    [promptData, originalPromptData, selectedHandler, selectedLanguage]);
  
  // Language management state  
  const [languageInfos, setLanguageInfos] = useState<Record<string, LanguageInfo>>({});
  
  // Handler list UI state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterLanguageCount, setFilterLanguageCount] = useState<'all' | 'single' | 'multiple'>('all');

  // Load handlers on component mount
  useEffect(() => {
    void loadHandlers();
  // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional scoped/mount load (load fns are not memoized)
  }, []);

  // Update language info when handlers change
  useEffect(() => {
    const newLanguageInfos: Record<string, LanguageInfo> = {};
    
    handlers.forEach(handler => {
      handler.languages.forEach(language => {
        const key = `${handler.handler_name}:${language}`;
        newLanguageInfos[key] = {
          code: language,
          label: language.toUpperCase(),
          status: 'loaded',
          validationErrors: 0,
          lastModified: new Date().toISOString()
        };
      });
    });
    
    setLanguageInfos(newLanguageInfos);
  }, [handlers]);

  // Load prompt data when handler or language selection changes
  useEffect(() => {
    if (selectedHandler && selectedLanguage) {
      void loadPromptData(selectedHandler, selectedLanguage);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional scoped/mount load (load fns are not memoized)
  }, [selectedHandler, selectedLanguage]);

  const loadHandlers = async () => {
    try {
      setError(null);
      setLoading(true);
      const response = await apiClient.getPromptHandlers();
      setHandlers(response.handlers);

      // Auto-select first handler if none selected
      if (response.handlers && response.handlers.length > 0 && !selectedHandler) {
        const firstHandler = response.handlers[0];
        setSelectedHandler(firstHandler.handler_name);
        
        // Auto-select first language for the first handler
        if (firstHandler.languages.length > 0) {
          setSelectedLanguage(firstHandler.default_language || firstHandler.languages[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load prompt handlers:', err);
      setError(err instanceof Error ? err.message : t('page.errors.loadHandlers'));
      setHandlers([]);
    } finally {
      setLoading(false);
    }
  };

  const loadPromptData = async (handlerName: string, language: string) => {
    try {
      setError(null);
      const response = await apiClient.getLanguagePrompt(handlerName, language);
      setPromptData(response.prompt_data);
      setOriginalPromptData(response.prompt_data);
    } catch (err) {
      console.error('Failed to load prompt data:', err);
      setError(err instanceof Error ? err.message : t('page.errors.loadData'));
      setPromptData({});
      setOriginalPromptData({});
    }
  };

  const handleHandlerSelect = useCallback((handlerName: string) => {
    if (handlerName === selectedHandler) return;
    
    setSelectedHandler(handlerName);
    
    // Auto-select first available language for the new handler
    const handler = handlers.find(h => h.handler_name === handlerName);
    if (handler && handler.languages.length > 0) {
      setSelectedLanguage(handler.languages[0]);
    } else {
      setSelectedLanguage(null);
    }
    
    setPromptData({});
    setOriginalPromptData({});
    setError(null);
  }, [selectedHandler, handlers]);

  const handleLanguageSelect = useCallback((language: string) => {
    if (language === selectedLanguage) return;
    setSelectedLanguage(language);
  }, [selectedLanguage]);

  const handlePromptDataChange = useCallback((newData: PromptData) => {
    setPromptData(newData);
  }, []);

  const handleValidationChange = useCallback((isValid: boolean, errors: string[]) => {
    setValidationResult({
      isValid,
      errors,
      warnings: []
    });
  }, []);

  const handleSave = async () => {
    if (!selectedHandler || !selectedLanguage) return;

    try {
      setSaving(true);
      setError(null);

      const response = await apiClient.updateLanguagePrompt(
        selectedHandler,
        selectedLanguage,
        promptData
      );

      if (response.success) {
        setOriginalPromptData(promptData);
        
        // Show success message briefly
        setTimeout(() => {
          // Success feedback could go here
        }, 1000);
      } else {
        throw new Error(t('page.errors.saveFailed'));
      }
    } catch (err) {
      console.error('Failed to save prompt data:', err);
      setError(err instanceof Error ? err.message : t('page.errors.save'));
    } finally {
      setSaving(false);
    }
  };

  const handleValidate = async () => {
    if (!selectedHandler || !selectedLanguage) {
      return {
        valid: false,
        errors: [t('page.errors.noSelection')],
        warnings: []
      };
    }

    try {
      setValidating(true);
      setError(null);

      const response = await apiClient.validateLanguagePrompt(
        selectedHandler,
        selectedLanguage,
        promptData
      );

      const result = {
        valid: response.is_valid,
        errors: response.errors.map(e =>
          typeof e === 'string' ? e : (e as any).message || t('page.errors.validationError')
        ),
        warnings: response.warnings.map(w =>
          typeof w === 'string' ? w : w.message || t('page.errors.validationWarning')
        )
      };

      setValidationResult({
        isValid: result.valid,
        errors: result.errors,
        warnings: result.warnings
      });

      return result;
    } catch (err) {
      console.error('Failed to validate prompt data:', err);
      setError(err instanceof Error ? err.message : t('page.errors.validate'));
      return {
        valid: false,
        errors: [err instanceof Error ? err.message : t('page.errors.validateShort')],
        warnings: []
      };
    } finally {
      setValidating(false);
    }
  };

  const handleCreateLanguage = async (handlerName: string, language: string, copyFrom?: string) => {
    try {
      setError(null);
      await apiClient.createPromptLanguage(handlerName, language, {
        copyFrom,
        useTemplate: !copyFrom
      });
      
      // Reload handlers to show new language
      await loadHandlers();
      
      // If this is for the currently selected handler, select the new language
      if (handlerName === selectedHandler) {
        setSelectedLanguage(language);
        await loadPromptData(handlerName, language);
      }
    } catch (err) {
      console.error('Failed to create language:', err);
      setError(err instanceof Error ? err.message : t('page.errors.createLanguage'));
    }
  };

  const handleDeleteLanguage = async (handlerName: string, language: string) => {
    try {
      setError(null);
      await apiClient.deletePromptLanguage(handlerName, language);
      
      // Reload handlers
      await loadHandlers();
      
      // If we deleted the currently selected language, clear selection
      if (handlerName === selectedHandler && language === selectedLanguage) {
        setSelectedLanguage(null);
        setPromptData({});
        setOriginalPromptData({});
      }
    } catch (err) {
      console.error('Failed to delete language:', err);
      setError(err instanceof Error ? err.message : t('page.errors.deleteLanguage'));
    }
  };

  const handleRevert = () => {
    setPromptData(originalPromptData);
  };

  // Filter handlers based on search query and language count
  const filteredHandlers = useMemo(() => {
    let filtered = handlers;

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(handler =>
        handler.handler_name.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply language count filter
    if (filterLanguageCount !== 'all') {
      filtered = filtered.filter(handler => {
        const langCount = handler.total_languages;
        return filterLanguageCount === 'single' ? langCount === 1 : langCount > 1;
      });
    }

    return filtered;
  }, [handlers, searchQuery, filterLanguageCount]);

  // Get current handler data
  const currentHandler = handlers.find(h => h.handler_name === selectedHandler);
  const availableLanguages = currentHandler?.languages || [];

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">{t('page.loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('page.title')}</h1>
          <p className="text-gray-600">{t('page.subtitle')}</p>
        </div>
        <div className="flex items-center space-x-2 mt-1">
          <Badge variant="info">
            <MessageSquare className="w-3 h-3 mr-1" />
            {t('page.badge')}
          </Badge>
          {hasChanges && (
            <Badge variant="warning">
              {t('page.unsavedChanges')}
            </Badge>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">{t('common:status.error')}</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      <div className="h-full flex">
        {/* Handler List */}
        <HandlerList
          handlers={filteredHandlers}
          selectedHandler={selectedHandler}
          selectedLanguage={selectedLanguage}
          onSelect={handleHandlerSelect}
          onLanguageSelect={() => {}} // Not used in this pattern
          onCreateLanguage={() => {}} // Not used in this pattern  
          onDeleteLanguage={() => {}} // Not used in this pattern
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          filterLanguageCount={filterLanguageCount}
          onFilterLanguageCountChange={setFilterLanguageCount}
          loading={loading}
        />

        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {selectedHandler ? (
            <div className="space-y-6">
              {/* Language Tabs */}
              <LanguageTabs
                activeLanguage={selectedLanguage || ''}
                availableLanguages={availableLanguages.map(lang => languageInfos[`${selectedHandler}:${lang}`] || {
                  code: lang,
                  label: lang.toUpperCase(),
                  status: 'loaded' as const,
                  validationErrors: 0
                })}
                supportedLanguages={currentHandler?.supported_languages || []}
                onLanguageChange={handleLanguageSelect}
                onCreateLanguage={(lang: string, templateFrom?: string) => 
                  void handleCreateLanguage(selectedHandler, lang, templateFrom)
                }
                onDeleteLanguage={(lang: string) => 
                  void handleDeleteLanguage(selectedHandler, lang)
                }
                handlerName={selectedHandler}
              />

              {selectedLanguage ? (
                <>
                  {/* Prompt Editor */}
                  <PromptEditor
                    value={promptData}
                    onChange={handlePromptDataChange}
                    onValidationChange={handleValidationChange}
                  />

                  {/* Apply Changes Bar */}
                  {hasChanges && (
                    <ApplyChangesBar
                      visible={hasChanges}
                      selectedHandler={`${selectedHandler}/${selectedLanguage}`}
                      hasUnsavedChanges={hasChanges}
                      onSave={handleSave}
                      onValidate={handleValidate}
                      onCancel={handleRevert}
                      loading={saving}
                    />
                  )}
                </>
              ) : (
                <div className="text-center py-12">
                  <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">{t('page.noLanguage.title')}</h3>
                  <p className="text-gray-600">{t('page.noLanguage.subtitle')}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <Code className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">{t('page.noHandler.title')}</h3>
              <p className="text-gray-600">{t('page.noHandler.subtitle')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PromptsPage;
