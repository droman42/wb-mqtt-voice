/**
 * Irene API Client - Centralized API communication for donations management
 * 
 * Provides type-safe API calls to the Irene backend with proper error handling,
 * response validation, and consistent request formatting.
 */

import type {
  BaseApiResponse,
  ApiError,
  SchemaResponse,
  IntentStatusResponse,
  IntentHandlersResponse,
  ReloadResponse,
  // Language-aware donation types
  DonationHandlerListResponse,
  LanguageDonationContentResponse,
  LanguageDonationUpdateResponse,
  LanguageDonationValidationResponse,
  CreateLanguageResponse,
  DeleteLanguageResponse,
  ReloadDonationResponse,
  // Phase 4: Cross-language validation types
  CrossLanguageValidationResponse,
  // v1.1 donation contract + QUAL-42 validation/translation types (UI-5)
  DonationContract,
  DonationContractResponse,
  DonationContractUpdateResponse,
  ContractValidationResponse,
  TranslationValidationResponse,
  TranslateRequest,
  TranslateResponse,
  // UI-3: real-recognizer test
  RecognizeResponse,
  // Phase 6: Template management types
  TemplateHandlerListResponse,
  TemplateContentResponse,
  TemplateUpdateResponse,
  TemplateValidationResponse,
  CreateTemplateLanguageResponse,
  DeleteTemplateLanguageResponse,
  // Prompt management types (Phase 7)
  PromptHandlerListResponse,
  PromptContentResponse,
  PromptDefinition,
  PromptUpdateResponse,
  PromptValidationResponse,
  CreatePromptLanguageResponse,
  DeletePromptLanguageResponse,
  // Localization types
  LocalizationDomainListResponse,
  LocalizationContentResponse,
  LocalizationUpdateResponse,
  LocalizationValidationResponse,
  CreateLocalizationLanguageResponse,
  DeleteLocalizationLanguageResponse,
  // Configuration management types
  CoreConfig,
  TTSConfig,
  ASRConfig,
  AudioConfig,
  LLMConfig,
  NLUConfig,
  VoiceTriggerConfig,
  TextProcessorConfig,
  IntentSystemConfig,
  ConfigSchemaResponse,
  ConfigSectionOrderResponse,
  ConfigUpdateResponse,
  ConfigValidationResponse,
  ConfigStatusResponse,
  ProvidersResponse,
  AudioDevicesResponse,
  // Raw TOML types (Phase 5)
  RawTomlRequest,
  RawTomlResponse,
  RawTomlSaveResponse,
  RawTomlValidationRequest,
  RawTomlValidationResponse,
  SectionToTomlRequest,
  SectionToTomlResponse,
  // NLU Analysis types (Phase 3 - comprehensive implementation)
  AnalyzeDonationRequest,
  AnalyzeChangesRequest,
  NLUValidationResult,
  NLUAnalysisResult,
  ChangeImpactAnalysisResponse,
  BatchAnalysisResponse,
  SystemHealthResponse,
  ConflictReport,
  // Phase 4: Configure Response Types
  TTSConfigureResponse,
  ASRConfigureResponse,
  AudioConfigureResponse,
  LLMConfigureResponse,
  NLUConfigureResponse,
  VoiceTriggerConfigureResponse,
  TextProcessorConfigureResponse,
  IntentSystemConfigureResponse
} from '@/types';

interface RequestOptions extends RequestInit {
  headers?: Record<string, string>;
}

declare global {
  interface Window {
    /** Manual API-base override (dev escape hatch; the nginx runtime-config.js that
     *  used to inject this retired with the standalone app at UI-17). */
    __IRENE_API_BASE__?: string;
  }
}

/** FALLBACK base-URL resolution — the real source is the Workbench shell's per-plugin
 *  `PageProps.backends.api` (IMPL-6), applied via `setBaseUrl` in plugin.tsx before any
 *  page renders. This chain only covers a shell with no backends configured: manual
 *  window override, else same-hostname:8080 (under the shell that is the SHELL origin
 *  host — right only when the backend runs on the same machine). */
function defaultApiBase(): string {
  const injected = typeof window !== 'undefined' ? window.__IRENE_API_BASE__ : undefined;
  if (injected) return injected;
  const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  return `http://${hostname}:8080`;
}

class IreneApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = defaultApiBase()) {
    this.baseUrl = baseUrl;
  }

  /** Re-point the singleton at the shell-declared backend origin (UI-23 / IMPL-6:
   *  `PageProps.backends.api` — deployment facts live in the owner-edited shell
   *  config, never in build artifacts). Idempotent. */
  setBaseUrl(baseUrl: string): void {
    this.baseUrl = baseUrl;
  }

  /**
   * Make a generic API request with error handling
   */
  async request<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const defaultOptions: RequestOptions = {
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const finalOptions: RequestOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, finalOptions);

      // Handle non-OK responses
      if (!response.ok) {
        let errorMessage = `API Error: ${response.status} ${response.statusText}`;
        
        try {
          const errorData: ApiError = await response.json();
          if (errorData.error) {
            errorMessage = errorData.error;
          }
        } catch {
          // If we can't parse error JSON, use the status text
        }
        
        throw new Error(errorMessage);
      }

      // Parse and return JSON response
      const data: T = await response.json();
      return data;
    } catch (error) {
      // Re-throw with context if it's a fetch error
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Failed to connect to Irene API at ${this.baseUrl}: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Make a GET request
   */
  async get<T = any>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  /**
   * Make a POST request
   */
  async post<T = any>(endpoint: string, data: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Make a PUT request
   */
  async put<T = any>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /**
   * Make a DELETE request
   */
  async delete<T = any>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
    });
  }

  // ============================================================
  // Shared per-language resource CRUD (UI-12 / C1)
  // ------------------------------------------------------------
  // donations / templates / prompts / localizations differ only by URL prefix, the request body key
  // (`donation_data` / `template_data` / …), and the create-path suffix (donations posts to
  // `…/{lang}/create`; the others to `…/{lang}`). These private helpers centralise the URL + body
  // assembly; the public methods below stay thin typed wrappers, so call sites and request shapes are
  // unchanged. (`key` is the handler name or, for localizations, the domain.)
  // ============================================================
  private resourceLanguages(prefix: string, key: string): Promise<string[]> {
    return this.get<string[]>(`${prefix}/${encodeURIComponent(key)}/languages`);
  }

  private getLanguageResource<T>(prefix: string, key: string, language: string): Promise<T> {
    return this.get<T>(`${prefix}/${encodeURIComponent(key)}/${encodeURIComponent(language)}`);
  }

  private updateLanguageResource<T>(
    prefix: string, key: string, language: string, dataKey: string, data: any,
    options: { validateBeforeSave?: boolean; triggerReload?: boolean } = {}
  ): Promise<T> {
    return this.put<T>(`${prefix}/${encodeURIComponent(key)}/${encodeURIComponent(language)}`, {
      [dataKey]: data,
      validate_before_save: options.validateBeforeSave ?? true,
      trigger_reload: options.triggerReload ?? true,
    });
  }

  private validateLanguageResource<T>(prefix: string, key: string, language: string, dataKey: string, data: any): Promise<T> {
    return this.post<T>(`${prefix}/${encodeURIComponent(key)}/${encodeURIComponent(language)}/validate`, { [dataKey]: data });
  }

  private deleteLanguageResource<T>(prefix: string, key: string, language: string): Promise<T> {
    return this.delete<T>(`${prefix}/${encodeURIComponent(key)}/${encodeURIComponent(language)}`);
  }

  private createLanguageResource<T>(
    prefix: string, key: string, language: string, createSuffix: string,
    options: { copyFrom?: string; useTemplate?: boolean } = {}
  ): Promise<T> {
    return this.post<T>(`${prefix}/${encodeURIComponent(key)}/${encodeURIComponent(language)}${createSuffix}`, {
      copy_from: options.copyFrom,
      use_template: options.useTemplate ?? false,
    });
  }

  // ============================================================
  // SYSTEM METHODS
  // ============================================================

  /**
   * Get donation JSON schema for validation
   */
  async getDonationSchema(): Promise<SchemaResponse> {
    return this.get<SchemaResponse>('/intents/schema');
  }

  /**
   * Trigger intent system reload
   */
  async reloadIntentSystem(): Promise<ReloadResponse> {
    return this.post<ReloadResponse>('/intents/reload', {});
  }

  // ============================================================
  // LANGUAGE-AWARE DONATION METHODS
  // ============================================================

  /**
   * List all handlers with language information
   */
  async getDonationHandlers(): Promise<DonationHandlerListResponse> {
    return this.get<DonationHandlerListResponse>('/intents/donations');
  }

  /**
   * Get available languages for a handler
   */
  async getHandlerLanguages(handlerName: string): Promise<string[]> {
    return this.resourceLanguages('/intents/donations', handlerName);
  }

  /**
   * Get language-specific donation content for editing
   */
  async getLanguageDonation(handlerName: string, language: string): Promise<LanguageDonationContentResponse> {
    return this.getLanguageResource<LanguageDonationContentResponse>('/intents/donations', handlerName, language);
  }

  /**
   * Update language-specific donation
   */
  async updateLanguageDonation(
    handlerName: string,
    language: string,
    donationData: any,
    options: { validateBeforeSave?: boolean; triggerReload?: boolean } = {}
  ): Promise<LanguageDonationUpdateResponse> {
    return this.updateLanguageResource<LanguageDonationUpdateResponse>(
      '/intents/donations', handlerName, language, 'donation_data', donationData, options);
  }

  /**
   * Validate language-specific donation without saving
   */
  async validateLanguageDonation(
    handlerName: string,
    language: string,
    donationData: any
  ): Promise<LanguageDonationValidationResponse> {
    return this.validateLanguageResource<LanguageDonationValidationResponse>(
      '/intents/donations', handlerName, language, 'donation_data', donationData);
  }

  /**
   * Create a new language file for a handler
   */
  async createLanguage(
    handlerName: string,
    language: string,
    options: { copyFrom?: string; useTemplate?: boolean } = {}
  ): Promise<CreateLanguageResponse> {
    return this.createLanguageResource<CreateLanguageResponse>(
      '/intents/donations', handlerName, language, '/create', options);
  }

  /**
   * Delete a language file for a handler
   */
  async deleteLanguage(handlerName: string, language: string): Promise<DeleteLanguageResponse> {
    return this.deleteLanguageResource<DeleteLanguageResponse>('/intents/donations', handlerName, language);
  }

  /**
   * Trigger unified donation reload for a handler
   */
  async reloadHandlerDonation(handlerName: string): Promise<ReloadDonationResponse> {
    return this.post<ReloadDonationResponse>(
      `/intents/donations/${encodeURIComponent(handlerName)}/reload`,
      {}
    );
  }

  // ============================================================
  // v1.1 CONTRACT METHODS (UI-5)
  // ============================================================

  /**
   * Get the language-neutral contract for a handler (methods + ParameterSpec core + room_context).
   */
  async getDonationContract(handlerName: string): Promise<DonationContractResponse> {
    return this.get<DonationContractResponse>(
      `/intents/donations/${encodeURIComponent(handlerName)}/contract`
    );
  }

  /**
   * Validate + save the language-neutral contract, then reload the unified donation.
   */
  async updateDonationContract(
    handlerName: string,
    contract: DonationContract,
    options: { validateBeforeSave?: boolean; triggerReload?: boolean } = {}
  ): Promise<DonationContractUpdateResponse> {
    return this.put<DonationContractUpdateResponse>(
      `/intents/donations/${encodeURIComponent(handlerName)}/contract`,
      {
        contract,
        validate_before_save: options.validateBeforeSave ?? true,
        trigger_reload: options.triggerReload ?? true,
      }
    );
  }

  // ============================================================
  // QUAL-42: CONTRACT↔CODE WIRING + LLM TRANSLATION (UI-5)
  // ============================================================

  /**
   * Get the system-wide contract↔code wiring report (computed at startup).
   */
  async getContractValidation(): Promise<ContractValidationResponse> {
    return this.get<ContractValidationResponse>('/intents/donations/validation');
  }

  /**
   * LLM-validate a handler's translations for meaning/consistency. Returns llm_available=false (with a
   * manual-validation message) when no API-keyed LLM is configured.
   */
  async validateTranslation(handlerName: string, provider?: string): Promise<TranslationValidationResponse> {
    return this.post<TranslationValidationResponse>(
      `/intents/donations/${encodeURIComponent(handlerName)}/validate-translation`,
      { provider }
    );
  }

  /**
   * LLM translation service: suggest target-language phrases for a handler's methods. Returns
   * llm_available=false (with a manual message) when no API-keyed LLM is configured.
   */
  async translateDonation(
    handlerName: string,
    request: { sourceLanguage: string; targetLanguage: string; methodKeys?: string[]; provider?: string }
  ): Promise<TranslateResponse> {
    const body: TranslateRequest = {
      source_language: request.sourceLanguage,
      target_language: request.targetLanguage,
      method_keys: request.methodKeys ?? null,
      provider: request.provider ?? null,
    };
    return this.post<TranslateResponse>(
      `/intents/donations/${encodeURIComponent(handlerName)}/translate`,
      body
    );
  }

  /**
   * UI-3: run text through the REAL recognizer (the same path production uses), to test a phrasing by example.
   */
  async recognizeText(text: string, sessionId = 'donation_editor_test'): Promise<RecognizeResponse> {
    return this.post<RecognizeResponse>('/nlu/recognize', { text, context: { session_id: sessionId } });
  }

  // ============================================================
  // PHASE 4: CROSS-LANGUAGE VALIDATION METHODS
  // ============================================================

  /**
   * Get cross-language validation report for a handler
   */
  async getCrossLanguageValidation(handlerName: string): Promise<CrossLanguageValidationResponse> {
    return this.get<CrossLanguageValidationResponse>(
      `/intents/donations/${encodeURIComponent(handlerName)}/cross-validation`
    );
  }

  // UI-5: syncParameters + suggestTranslations removed — sync-parameters is gone from the backend
  // (params are single-source in the contract under v1.1), and rule-based suggest-translations is superseded
  // by the LLM `translateDonation` service (QUAL-42). Backend endpoint cleanup tracked in QUAL-43.

  // ============================================================
  // SYSTEM STATUS METHODS
  // ============================================================

  /**
   * Get intent system status
   */
  async getIntentStatus(): Promise<IntentStatusResponse> {
    return this.get<IntentStatusResponse>('/intents/status');
  }

  /**
   * Get available intent handlers
   */
  async getIntentHandlers(): Promise<IntentHandlersResponse> {
    return this.get<IntentHandlersResponse>('/intents/handlers');
  }

  /**
   * Check if API is reachable and system is healthy
   */
  async checkConnection(): Promise<boolean> {
    try {
      await this.getIntentStatus();
      return true;
    } catch (error) {
      console.warn('API connection check failed:', error instanceof Error ? error.message : String(error));
      return false;
    }
  }

  // ============================================================
  // TEMPLATE MANAGEMENT API (Phase 6)
  // ============================================================

  /**
   * Get all handlers with template language info
   */
  async getTemplateHandlers(): Promise<TemplateHandlerListResponse> {
    return this.get<TemplateHandlerListResponse>('/intents/templates');
  }

  /**
   * Get available languages for a handler's templates
   */
  async getTemplateHandlerLanguages(handlerName: string): Promise<string[]> {
    return this.resourceLanguages('/intents/templates', handlerName);
  }

  /**
   * Get language-specific template content
   */
  async getLanguageTemplate(handlerName: string, language: string): Promise<TemplateContentResponse> {
    return this.getLanguageResource<TemplateContentResponse>('/intents/templates', handlerName, language);
  }

  /**
   * Update language-specific template
   */
  async updateLanguageTemplate(
    handlerName: string,
    language: string,
    templateData: Record<string, any>,
    options: { validateBeforeSave?: boolean; triggerReload?: boolean } = {}
  ): Promise<TemplateUpdateResponse> {
    return this.updateLanguageResource<TemplateUpdateResponse>(
      '/intents/templates', handlerName, language, 'template_data', templateData, options);
  }

  /**
   * Validate language-specific template without saving
   */
  async validateLanguageTemplate(
    handlerName: string,
    language: string,
    templateData: Record<string, any>
  ): Promise<TemplateValidationResponse> {
    return this.validateLanguageResource<TemplateValidationResponse>(
      '/intents/templates', handlerName, language, 'template_data', templateData);
  }

  /**
   * Delete language-specific template file
   */
  async deleteTemplateLanguage(handlerName: string, language: string): Promise<DeleteTemplateLanguageResponse> {
    return this.deleteLanguageResource<DeleteTemplateLanguageResponse>('/intents/templates', handlerName, language);
  }

  /**
   * Create new language file for template
   */
  async createTemplateLanguage(
    handlerName: string,
    language: string,
    options: { copyFrom?: string; useTemplate?: boolean } = {}
  ): Promise<CreateTemplateLanguageResponse> {
    return this.createLanguageResource<CreateTemplateLanguageResponse>(
      '/intents/templates', handlerName, language, '', options);
  }

  // ============================================================
  // PROMPT MANAGEMENT API (Phase 7)
  // ============================================================

  /**
   * Get all handlers with prompt language info
   */
  async getPromptHandlers(): Promise<PromptHandlerListResponse> {
    return this.get<PromptHandlerListResponse>('/intents/prompts');
  }

  /**
   * Get available languages for a handler's prompts
   */
  async getPromptHandlerLanguages(handlerName: string): Promise<string[]> {
    return this.resourceLanguages('/intents/prompts', handlerName);
  }

  /**
   * Get language-specific prompt content
   */
  async getLanguagePrompt(handlerName: string, language: string): Promise<PromptContentResponse> {
    return this.getLanguageResource<PromptContentResponse>('/intents/prompts', handlerName, language);
  }

  /**
   * Update language-specific prompt
   */
  async updateLanguagePrompt(
    handlerName: string,
    language: string,
    promptData: Record<string, PromptDefinition>,
    options: { validateBeforeSave?: boolean; triggerReload?: boolean } = {}
  ): Promise<PromptUpdateResponse> {
    return this.updateLanguageResource<PromptUpdateResponse>(
      '/intents/prompts', handlerName, language, 'prompt_data', promptData, options);
  }

  /**
   * Validate language-specific prompt without saving
   */
  async validateLanguagePrompt(
    handlerName: string,
    language: string,
    promptData: Record<string, PromptDefinition>
  ): Promise<PromptValidationResponse> {
    return this.validateLanguageResource<PromptValidationResponse>(
      '/intents/prompts', handlerName, language, 'prompt_data', promptData);
  }

  /**
   * Delete language-specific prompt file
   */
  async deletePromptLanguage(handlerName: string, language: string): Promise<DeletePromptLanguageResponse> {
    return this.deleteLanguageResource<DeletePromptLanguageResponse>('/intents/prompts', handlerName, language);
  }

  /**
   * Create new language file for prompt
   */
  async createPromptLanguage(
    handlerName: string,
    language: string,
    options: { copyFrom?: string; useTemplate?: boolean } = {}
  ): Promise<CreatePromptLanguageResponse> {
    return this.createLanguageResource<CreatePromptLanguageResponse>(
      '/intents/prompts', handlerName, language, '', options);
  }

  // ============================================================
  // CONFIGURATION MANAGEMENT API 
  // ============================================================

  /**
   * Get complete TOML configuration
   */
  async getConfig(): Promise<CoreConfig> {
    return this.get<CoreConfig>('/configuration/config');
  }

  /**
   * Get configuration schema for all sections
   */
  async getConfigSchema(): Promise<ConfigSchemaResponse> {
    return this.get<ConfigSchemaResponse>('/configuration/config/schema');
  }

  /**
   * Get specific section schema
   */
  async getSectionSchema(sectionName: string): Promise<ConfigSchemaResponse> {
    return this.get<ConfigSchemaResponse>(`/configuration/config/schema/${encodeURIComponent(sectionName)}`);
  }

  /**
   * Update specific configuration section
   */
  async updateConfigSection(sectionName: string, data: any): Promise<ConfigUpdateResponse> {
    return this.put<ConfigUpdateResponse>(`/configuration/config/sections/${encodeURIComponent(sectionName)}`, data);
  }

  /**
   * Validate configuration section without saving
   */
  async validateConfigSection(sectionName: string, data: any): Promise<ConfigValidationResponse> {
    return this.post<ConfigValidationResponse>(`/configuration/config/sections/${encodeURIComponent(sectionName)}/validate`, data);
  }

  /**
   * Get available providers for a component
   */
  async getAvailableProviders(componentName: string): Promise<ProvidersResponse> {
    return this.get<ProvidersResponse>(`/configuration/config/providers/${encodeURIComponent(componentName)}`);
  }

  /**
   * Get available audio input devices for microphone configuration
   */
  async getAvailableAudioDevices(): Promise<AudioDevicesResponse> {
    return this.get<AudioDevicesResponse>('/configuration/config/audio/devices');
  }

  /**
   * Get available audio output devices for audio provider configuration
   */
  async getAvailableAudioOutputDevices(): Promise<AudioDevicesResponse> {
    return this.get<AudioDevicesResponse>('/configuration/config/audio/output-devices');
  }

  /**
   * Get configuration system status
   */
  async getConfigStatus(): Promise<ConfigStatusResponse> {
    return this.get<ConfigStatusResponse>('/configuration/config/status');
  }

  /**
   * Get section order and titles for frontend auto-generation
   */
  async getConfigSectionOrder(): Promise<ConfigSectionOrderResponse> {
    return this.get<ConfigSectionOrderResponse>('/configuration/config/schema/sections');
  }

  // ============================================================
  // RUNTIME CONFIGURATION TESTING API (Phase 4)
  // ============================================================

  /**
   * Configure TTS settings for live testing (no TOML persistence)
   */
  async configureTTS(config: TTSConfig): Promise<TTSConfigureResponse> {
    return this.post<TTSConfigureResponse>('/tts/configure', config);
  }

  /**
   * Configure ASR settings for live testing (no TOML persistence)
   */
  async configureASR(config: ASRConfig): Promise<ASRConfigureResponse> {
    return this.post<ASRConfigureResponse>('/asr/configure', config);
  }

  /**
   * Configure Audio settings for live testing (no TOML persistence)
   */
  async configureAudio(config: AudioConfig): Promise<AudioConfigureResponse> {
    return this.post<AudioConfigureResponse>('/audio/configure', config);
  }

  /**
   * Configure LLM settings for live testing (no TOML persistence)
   */
  async configureLLM(config: LLMConfig): Promise<LLMConfigureResponse> {
    return this.post<LLMConfigureResponse>('/llm/configure', config);
  }

  /**
   * Configure NLU settings for live testing (no TOML persistence)
   */
  async configureNLU(config: NLUConfig): Promise<NLUConfigureResponse> {
    return this.post<NLUConfigureResponse>('/nlu/configure', config);
  }

  /**
   * Configure Voice Trigger settings for live testing (no TOML persistence)
   */
  async configureVoiceTrigger(config: VoiceTriggerConfig): Promise<VoiceTriggerConfigureResponse> {
    return this.post<VoiceTriggerConfigureResponse>('/voice_trigger/configure', config);
  }

  /**
   * Configure Text Processor settings for live testing (no TOML persistence)
   */
  async configureTextProcessor(config: TextProcessorConfig): Promise<TextProcessorConfigureResponse> {
    return this.post<TextProcessorConfigureResponse>('/text_processing/configure', config);
  }

  /**
   * Configure Intent System settings for live testing (no TOML persistence)
   */
  async configureIntentSystem(config: IntentSystemConfig): Promise<IntentSystemConfigureResponse> {
    // The intent component mounts under the '/intents' prefix, so its live-config route is '/intents/configure'
    // (not '/intent_system/configure', which 404s). Surfaced by the UI-5 openapi codegen coverage check.
    return this.post<IntentSystemConfigureResponse>('/intents/configure', config);
  }

  // ============================================================
  // RAW TOML CONFIGURATION METHODS (Phase 5)
  // ============================================================

  /**
   * Get raw TOML configuration content with comments preserved
   */
  async getRawToml(): Promise<RawTomlResponse> {
    try {
      return await this.get<RawTomlResponse>('/configuration/config/raw');
    } catch (error) {
      console.error('Failed to fetch raw TOML content:', error);
      throw new Error('Unable to load TOML configuration. Please check your connection and try again.');
    }
  }

  /**
   * Save raw TOML content with comment preservation
   */
  async saveRawToml(tomlContent: string, validateBeforeSave: boolean = true): Promise<RawTomlSaveResponse> {
    try {
      const requestData: RawTomlRequest = {
        toml_content: tomlContent,
        validate_before_save: validateBeforeSave
      };
      return await this.put<RawTomlSaveResponse>('/configuration/config/raw', requestData);
    } catch (error) {
      console.error('Failed to save TOML content:', error);
      // Try to extract validation errors from response
      if (error instanceof Error && error.message.includes('validation failed')) {
        throw new Error('Configuration validation failed. Please check your settings and try again.');
      }
      throw new Error('Unable to save TOML configuration. Please check your settings and try again.');
    }
  }

  /**
   * Validate raw TOML content without saving
   */
  async validateRawToml(tomlContent: string): Promise<RawTomlValidationResponse> {
    try {
      const requestData: RawTomlValidationRequest = {
        toml_content: tomlContent
      };
      return await this.post<RawTomlValidationResponse>('/configuration/config/raw/validate', requestData);
    } catch (error) {
      console.error('Failed to validate TOML content:', error);
      // Return a failed validation response instead of throwing
      return {
        success: false,
        timestamp: Date.now(),
        valid: false,
        errors: [{ 
          msg: error instanceof Error ? error.message : 'Validation service unavailable', 
          type: 'network_error' 
        }]
      };
    }
  }

  /**
   * Apply section changes to raw TOML while preserving comments
   */
  async applySectionToToml(sectionName: string, sectionData: any): Promise<SectionToTomlResponse> {
    try {
      const requestData: SectionToTomlRequest = {
        section_data: sectionData
      };
      return await this.post<SectionToTomlResponse>(
        `/configuration/config/sections/${encodeURIComponent(sectionName)}/toml`, 
        requestData
      );
    } catch (error) {
      console.error(`Failed to apply section '${sectionName}' to TOML:`, error);
      throw new Error(`Unable to update section '${sectionName}' with comment preservation. Falling back to standard update.`);
    }
  }

  // ========================================
  // LOCALIZATION MANAGEMENT METHODS (Phase 8)
  // ========================================

  /**
   * Get all domains with their available languages
   */
  async getLocalizationDomains(): Promise<LocalizationDomainListResponse> {
    return this.get<LocalizationDomainListResponse>('/intents/localizations');
  }

  /**
   * Get available languages for a domain
   */
  async getLocalizationDomainLanguages(domain: string): Promise<string[]> {
    return this.resourceLanguages('/intents/localizations', domain);
  }

  /**
   * Get language-specific localization content
   */
  async getLanguageLocalization(domain: string, language: string): Promise<LocalizationContentResponse> {
    return this.getLanguageResource<LocalizationContentResponse>('/intents/localizations', domain, language);
  }

  /**
   * Update language-specific localization
   */
  async updateLanguageLocalization(
    domain: string,
    language: string,
    localizationData: Record<string, any>,
    options: { validateBeforeSave?: boolean; triggerReload?: boolean } = {}
  ): Promise<LocalizationUpdateResponse> {
    return this.updateLanguageResource<LocalizationUpdateResponse>(
      '/intents/localizations', domain, language, 'localization_data', localizationData, options);
  }

  /**
   * Validate language-specific localization without saving
   */
  async validateLanguageLocalization(
    domain: string,
    language: string,
    localizationData: Record<string, any>
  ): Promise<LocalizationValidationResponse> {
    return this.validateLanguageResource<LocalizationValidationResponse>(
      '/intents/localizations', domain, language, 'localization_data', localizationData);
  }

  /**
   * Delete language-specific localization file
   */
  async deleteLocalizationLanguage(domain: string, language: string): Promise<DeleteLocalizationLanguageResponse> {
    return this.deleteLanguageResource<DeleteLocalizationLanguageResponse>('/intents/localizations', domain, language);
  }

  /**
   * Create new language file for localization
   */
  async createLocalizationLanguage(
    domain: string,
    language: string,
    options: { copyFrom?: string; useTemplate?: boolean } = {}
  ): Promise<CreateLocalizationLanguageResponse> {
    return this.createLanguageResource<CreateLocalizationLanguageResponse>(
      '/intents/localizations', domain, language, '', options);
  }

  // ============================================================
  // NLU ANALYSIS API METHODS (Phase 3 - Comprehensive Implementation)
  // ============================================================

  /**
   * Real-time analysis of donation for conflicts and issues
   */
  async analyzeDonation(
    handlerName: string,
    language: string,
    donationData: Record<string, any>,
    signal?: AbortSignal
  ): Promise<NLUAnalysisResult> {
    const requestData: AnalyzeDonationRequest = {
      handler_name: handlerName,
      language: language,
      donation_data: donationData
    };
    // BUG-9: forward an AbortSignal so a superseded real-time analysis actually cancels its network
    // request (not just flips a flag) — the caller debounces and races these on every keystroke.
    return this.post<NLUAnalysisResult>('/nlu_analysis/analyze/donation', requestData, { signal });
  }

  /**
   * Pre-save validation with blocking/warning classification
   */
  async validateDonation(
    handlerName: string, 
    language: string, 
    donationData: Record<string, any>
  ): Promise<NLUValidationResult> {
    const requestData: AnalyzeDonationRequest = {
      handler_name: handlerName,
      language: language,
      donation_data: donationData
    };
    return this.post<NLUValidationResult>('/nlu_analysis/validate/save', requestData);
  }

  /**
   * Analyze impact of proposed changes
   */
  async analyzeChanges(
    changes: Record<string, Record<string, any>>,
    language?: string
  ): Promise<ChangeImpactAnalysisResponse> {
    const requestData: AnalyzeChangesRequest = {
      changes: changes,
      language: language
    };
    return this.post<ChangeImpactAnalysisResponse>('/nlu_analysis/analyze/changes', requestData);
  }

  /**
   * Get conflicts for specific handler with optional language filtering
   */
  async getHandlerConflicts(
    handlerName: string, 
    language?: string
  ): Promise<ConflictReport[]> {
    const params = language ? `?language=${language}` : '';
    const response = await this.get<BatchAnalysisResponse>(`/nlu_analysis/conflicts/${encodeURIComponent(handlerName)}${params}`);
    return response.conflicts || [];
  }

  /**
   * Full system analysis for dashboard/CI integration
   */
  async getSystemAnalysis(language?: string): Promise<BatchAnalysisResponse> {
    const params = language ? `?language=${language}` : '';
    return this.get<BatchAnalysisResponse>(`/nlu_analysis/analysis/batch${params}`);
  }

  /**
   * Get NLU system health status
   */
  async getSystemHealth(): Promise<SystemHealthResponse> {
    return this.get<SystemHealthResponse>('/nlu_analysis/health');
  }

  /**
   * Get conflicts by severity level with optional language filtering
   * Note: This endpoint is not implemented in the backend yet
   */
  async getConflictsBySeverity(
    severity: 'blocker' | 'warning' | 'info', 
    language?: string
  ): Promise<BatchAnalysisResponse> {
    // TODO: Implement severity-based filtering in backend
    console.warn(`getConflictsBySeverity not implemented in backend - ignoring severity '${severity}' and using full batch analysis`);
    return this.getSystemAnalysis(language);
  }

  /**
   * Clear analysis cache
   * Note: This endpoint is not implemented in the backend yet
   */
  async clearAnalysisCache(): Promise<BaseApiResponse> {
    // TODO: Implement cache clearing in backend
    console.warn('clearAnalysisCache not implemented in backend');
    return Promise.resolve({ success: true, timestamp: Date.now() });
  }

  // Legacy method for backward compatibility during transition
  async validateDonationForSaving(
    handlerName: string, 
    language: string, 
    donationData: Record<string, any>
  ): Promise<NLUValidationResult> {
    return this.validateDonation(handlerName, language, donationData);
  }

  // Legacy method for backward compatibility during transition  
  async getNLUSystemHealth(): Promise<SystemHealthResponse> {
    return this.getSystemHealth();
  }
}

// Create and export a default instance
const apiClient = new IreneApiClient();
export default apiClient;

// Also export the class for custom instances
export { IreneApiClient };
