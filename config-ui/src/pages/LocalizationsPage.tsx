/**
 * LocalizationsPage - Main page for managing localization data
 * 
 * Provides domain-based localization editing following the same patterns
 * as DonationsPage but adapted for domain structure instead of handlers.
 */

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, Loader, AlertCircle, Filter, RefreshCw } from 'lucide-react';
import {
  ActionBar,
  Button, Alert, AlertTitle, AlertDescription,
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem
} from 'locveil-ui-kit';
import { 
  DomainLanguageInfo, 
  LocalizationContentResponse
} from '@/types/api';

import HandlerList from '@/components/donations/HandlerList';
import LanguageTabs from '@/components/donations/LanguageTabs';
import LocalizationEditor from '@/components/editors/LocalizationEditor';
import Section from '@/components/ui/Section';
import Badge from '@/components/ui/Badge';
import apiClient from '@/utils/apiClient';

interface LocalizationChanges {
  [domainLanguageKey: string]: {
    domain: string;
    language: string;
    data: Record<string, any>;
    hasChanges: boolean;
  };
}

const LocalizationsPage: React.FC = () => {
  const { t } = useTranslation(['localizations', 'common']);
  const [domains, setDomains] = useState<DomainLanguageInfo[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('en');
  const [localizationData, setLocalizationData] = useState<Record<string, any>>({});
  const [changes, setChanges] = useState<LocalizationChanges>({});
  const [metadata, setMetadata] = useState<LocalizationContentResponse['metadata'] | null>(null);
  
  // UI state
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isValid, setIsValid] = useState(true);
  
  // Filters
  const [languageFilter, setLanguageFilter] = useState<'all' | 'single' | 'multiple'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const currentKey = selectedDomain ? `${selectedDomain}:${selectedLanguage}` : '';

  // Load domains on mount
  useEffect(() => {
    void loadDomains();
  // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional scoped/mount load (load fns are not memoized)
  }, []);

  // Load localization data when domain/language changes
  useEffect(() => {
    if (selectedDomain && selectedLanguage) {
      void loadLocalizationData(selectedDomain, selectedLanguage);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional scoped/mount load (load fns are not memoized)
  }, [selectedDomain, selectedLanguage]);

  const loadDomains = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.getLocalizationDomains();
      setDomains(response.domains);
      
      // Auto-select first domain if none selected
      if (!selectedDomain && response.domains.length > 0) {
        setSelectedDomain(response.domains[0].domain);
      }
    } catch (err) {
      console.error('Failed to load domains:', err);
      setError(t('page.errors.loadDomains'));
    } finally {
      setLoading(false);
    }
  };

  const loadLocalizationData = async (domain: string, language: string) => {
    try {
      setError(null);
      
      const response = await apiClient.getLanguageLocalization(domain, language);
      setLocalizationData(response.localization_data);
      setMetadata(response.metadata);
      
      // Clear changes for this key since we're loading fresh data
      const newChanges = { ...changes };
      delete newChanges[`${domain}:${language}`];
      setChanges(newChanges);
      
    } catch (err) {
      console.error('Failed to load localization data:', err);
      setError(t('page.errors.loadData', { language, domain }));
    }
  };

  const handleLocalizationChange = useCallback((newData: Record<string, any>) => {
    setLocalizationData(newData);
    
    // Track changes
    if (selectedDomain) {
      setChanges(prev => ({
        ...prev,
        [currentKey]: {
          domain: selectedDomain,
          language: selectedLanguage,
          data: newData,
          hasChanges: true
        }
      }));
    }
  }, [selectedDomain, selectedLanguage, currentKey]);

  const handleValidationChange = useCallback((valid: boolean, errors: string[]) => {
    setIsValid(valid);
    setValidationErrors(errors);
  }, []);

  const handleSaveChanges = async () => {
    try {
      setSaving(true);
      setError(null);
      
      const changesToSave = Object.values(changes).filter(change => change.hasChanges);
      
      for (const change of changesToSave) {
        await apiClient.updateLanguageLocalization(
          change.domain,
          change.language,
          change.data,
          { validateBeforeSave: true, triggerReload: true }
        );
      }
      
      // Clear changes after successful save
      setChanges({});
      
      // Reload current data
      if (selectedDomain) {
        await loadLocalizationData(selectedDomain, selectedLanguage);
      }
      
      console.log('All localization changes saved successfully');
      
    } catch (err) {
      console.error('Failed to save changes:', err);
      setError(t('page.errors.save'));
    } finally {
      setSaving(false);
    }
  };

  const handleDiscardChanges = () => {
    setChanges({});
    
    // Reload current data
    if (selectedDomain) {
      void loadLocalizationData(selectedDomain, selectedLanguage);
    }
  };

  const handleDomainSelect = (domain: string) => {
    setSelectedDomain(domain);
    
    // Auto-select first available language for new domain
    const domainInfo = domains.find(d => d.domain === domain);
    if (domainInfo && domainInfo.languages.length > 0) {
      const preferredLang = domainInfo.languages.includes('en') ? 'en' : domainInfo.languages[0];
      setSelectedLanguage(preferredLang);
    }
  };

  const filteredDomains = domains.filter(domain => {
    switch (languageFilter) {
      case 'single':
        return domain.total_languages === 1;
      case 'multiple':
        return domain.total_languages > 1;
      default:
        return true;
    }
  });

  const selectedDomainInfo = domains.find(d => d.domain === selectedDomain);
  const hasChanges = Object.values(changes).some(change => change.hasChanges);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="w-8 h-8 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">{t('page.loading')}</span>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('page.title')}</h1>
          <p className="text-muted-foreground">{t('page.subtitle')}</p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            onClick={() => void loadDomains()}
            className="text-muted-foreground hover:text-foreground"
          >
            <RefreshCw />
            {t('common:actions.refresh')}
          </Button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive" className="rounded-lg p-4">
          <AlertCircle />
          <div>
            <AlertTitle>{t('common:status.error')}</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </div>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Domain List */}
        <div className="lg:col-span-1">
          <Section title={t('page.domains')} className="h-fit">
            {/* Filter Controls */}
            <div className="mb-4 flex items-center gap-2">
              <Filter className="w-4 h-4 text-muted-foreground" />
              <Select
                value={languageFilter}
                onValueChange={(value) => setLanguageFilter(value as 'all' | 'single' | 'multiple')}
              >
                <SelectTrigger className="h-8 w-auto text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('page.filterAll')}</SelectItem>
                  <SelectItem value="single">{t('page.filterSingle')}</SelectItem>
                  <SelectItem value="multiple">{t('page.filterMultiple')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Domain List */}
            <HandlerList
              handlers={filteredDomains.map(domain => ({
                handler_name: domain.domain,
                languages: domain.languages,
                supported_languages: domain.supported_languages,
                total_languages: domain.total_languages,
                default_language: domain.default_language,
                total_methods: 0
              }))}
              selectedHandler={selectedDomain}
              selectedLanguage={selectedLanguage}
              onSelect={handleDomainSelect}
              onLanguageSelect={() => {}} // Not used for domain-based navigation
              onCreateLanguage={() => {}} // Not used here
              onDeleteLanguage={() => {}} // Not used here
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              filterLanguageCount={languageFilter}
              onFilterLanguageCountChange={setLanguageFilter}
              hasChanges={{}}
              loading={loading}
              error={error}
            />
          </Section>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3 space-y-6">
          {selectedDomain ? (
            <>
              {/* Language Tabs */}
              {selectedDomainInfo && (
                <LanguageTabs
                  activeLanguage={selectedLanguage}
                  availableLanguages={selectedDomainInfo.languages.map(lang => ({
                    code: lang,
                    label: lang.toUpperCase(),
                    status: 'loaded' as const,
                    validationErrors: lang === selectedLanguage ? validationErrors.length : 0
                  }))}
                  supportedLanguages={selectedDomainInfo.supported_languages}
                  onLanguageChange={setSelectedLanguage}
                  onCreateLanguage={(lang, templateFrom) => {
                    console.log('Create language:', lang, 'from:', templateFrom);
                    // TODO: Implement language creation
                  }}
                  onDeleteLanguage={(lang) => {
                    console.log('Delete language:', lang);
                    // TODO: Implement language deletion
                  }}
                />
              )}

              {/* Localization Editor */}
              <Section title={`${selectedDomain} - ${selectedLanguage.toUpperCase()}`}>
                <div className="space-y-4">
                  {/* Metadata */}
                  {metadata && (
                    <div className="flex items-center gap-4 text-sm text-muted-foreground bg-muted p-3 rounded">
                      <Badge variant="default">
                        {t('page.metadata.entries', { count: metadata.entry_count })}
                      </Badge>
                      <span>
                        {t('page.metadata.file', { path: metadata.file_path })}
                      </span>
                      <span>
                        {t('page.metadata.size', { size: (metadata.file_size / 1024).toFixed(1) })}
                      </span>
                    </div>
                  )}

                  {/* Validation Status */}
                  {!isValid && validationErrors.length > 0 && (
                    <Alert>
                      <AlertTitle className="text-sm">{t('page.validationIssues')}</AlertTitle>
                      <AlertDescription className="text-muted-foreground">
                        <ul className="space-y-1">
                          {validationErrors.map((error, index) => (
                            <li key={index}>• {error}</li>
                          ))}
                        </ul>
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Editor */}
                  <LocalizationEditor
                    value={localizationData}
                    onChange={handleLocalizationChange}
                    domain={selectedDomain}
                    onValidationChange={handleValidationChange}
                  />
                </div>
              </Section>
            </>
          ) : (
            <Section title={t('page.selectDomain')}>
              <div className="text-center py-12 text-muted-foreground">
                <Globe className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <h3 className="text-lg font-medium mb-2">{t('page.noDomain.title')}</h3>
                <p>{t('page.noDomain.subtitle')}</p>
              </div>
            </Section>
          )}
        </div>
      </div>

      {/* Simple Save Controls — rendered through the shell's bottom slot (UI-22) */}
      {hasChanges && (
        <ActionBar>
          <div className="flex w-full items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">
                {t('page.unsavedChanges', { count: Object.values(changes).filter(c => c.hasChanges).length })}
              </span>
              {!isValid && (
                <span className="text-sm text-destructive">
                  {t('page.validationErrorsPresent')}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                onClick={handleDiscardChanges}
                className="text-muted-foreground hover:text-foreground"
                disabled={saving}
              >
                {t('page.discard')}
              </Button>
              <Button
                onClick={() => void handleSaveChanges()}
                disabled={saving || !isValid}
              >
                {saving ? (
                  <>
                    <Loader className="animate-spin" />
                    {t('common:status.saving')}
                  </>
                ) : (
                  t('page.saveAll')
                )}
              </Button>
            </div>
          </div>
        </ActionBar>
      )}
    </div>
  );
};

export default LocalizationsPage;
