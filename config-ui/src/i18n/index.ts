/**
 * i18n bootstrap (UI-7) — react-i18next with `en`/`ru` bundles, one namespace per app area.
 *
 * Imported once for its side effect (in `main.tsx`, before <App/>). The UI language is the persisted choice or the
 * Russian-first default; `fallbackLng: 'en'` covers any key not yet translated. This axis is independent of the
 * donation *content* language (LanguageTabs).
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { en } from './locales/en';
import { ru } from './locales/ru';
import { DEFAULT_LNG, FALLBACK_LNG, SUPPORTED_LNGS, initialLang } from './config';

export const NAMESPACES = Object.keys(en) as (keyof typeof en)[];

void i18n.use(initReactI18next).init({
  resources: { en, ru },
  lng: initialLang(),
  fallbackLng: FALLBACK_LNG,
  supportedLngs: SUPPORTED_LNGS,
  defaultNS: 'common',
  ns: NAMESPACES,
  interpolation: { escapeValue: false }, // React already escapes
  returnNull: false,
  react: { useSuspense: false },
});

// Keep <html lang> in sync for a11y / browser features.
const applyHtmlLang = (lng: string): void => {
  if (typeof document !== 'undefined') document.documentElement.lang = lng;
};
applyHtmlLang(i18n.language || DEFAULT_LNG);
i18n.on('languageChanged', applyHtmlLang);

export default i18n;
