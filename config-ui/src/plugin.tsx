/**
 * The Voice Workbench plugin (UI-17) — config-ui's public face.
 *
 * Default-exports the WorkbenchPlugin the shell loads at runtime (native ESM +
 * import map, HK-11). The standalone app is retired: no router, no Layout/Header —
 * the shell owns chrome, navigation, locale and theme. Pages follow the shell's
 * locale signal through the plugin-local i18next instance (bundled — i18n is
 * deliberately NOT a shared singleton).
 */

import { useEffect } from 'react';
import type { ComponentType } from 'react';
import type {
  PageProps,
  PluginStatus,
  ReportContext,
  WorkbenchPlugin,
} from 'locveil-workbench/contract';

import { TooltipProvider } from 'locveil-ui-kit';
import i18n from '@/i18n';
import apiClient from '@/utils/apiClient';
import DonationsPage from '@/pages/DonationsPage';
import TemplatesPage from '@/pages/TemplatesPage';
import PromptsPage from '@/pages/PromptsPage';
import LocalizationsPage from '@/pages/LocalizationsPage';
import MonitoringPage from '@/pages/MonitoringPage';
import ConfigurationPage from '@/pages/ConfigurationPage';
import './index.css';

/** Sync the plugin-local i18next instance to the shell's locale signal; provide the
 *  plugin-wide Tooltip context (UI-21 — kit tooltips replace bare `title=`). */
function page(Page: ComponentType): ComponentType<PageProps> {
  return function VoicePage({ locale }: PageProps) {
    useEffect(() => {
      if (i18n.language !== locale) void i18n.changeLanguage(locale);
    }, [locale]);
    return (
      <TooltipProvider delayDuration={300}>
        <Page />
      </TooltipProvider>
    );
  };
}

const status = async (): Promise<PluginStatus> => {
  try {
    const connected = await apiClient.checkConnection();
    if (!connected) return { level: 'error', text: { ru: 'нет связи', en: 'disconnected' } };
    try {
      const s = await apiClient.getIntentStatus();
      const n = s.handlers_count ?? 0;
      return { level: 'ok', text: { ru: `подключено · ${n} обработчиков`, en: `connected · ${n} handlers` } };
    } catch {
      return { level: 'ok', text: { ru: 'подключено', en: 'connected' } };
    }
  } catch {
    return { level: 'error', text: { ru: 'нет связи', en: 'disconnected' } };
  }
};

/* Voice has no REST report-write surface by design — problem intake is the spoken
   dialog (ARCH-30); a UI write endpoint would be a new PROD-4-auth-gated backend
   surface. The hook delegates honestly: it tells the user the voice-first path. */
const reportHook = (ctx: ReportContext): void => {
  window.alert(
    ctx.locale === 'ru'
      ? 'Голосовой ассистент принимает отчёты о проблемах голосом: скажите «сообщить о проблеме». Экран: ' + ctx.route
      : 'The voice assistant takes problem reports by voice: say the report command. Screen: ' + ctx.route
  );
};

const plugin: WorkbenchPlugin = {
  id: 'voice',
  title: { ru: 'Голос', en: 'Voice' },
  pages: () => [
    { route: 'donations', title: { ru: 'Доноры', en: 'Donations' }, render: page(DonationsPage) },
    { route: 'templates', title: { ru: 'Шаблоны', en: 'Templates' }, render: page(TemplatesPage) },
    { route: 'prompts', title: { ru: 'Промпты', en: 'Prompts' }, render: page(PromptsPage) },
    { route: 'localizations', title: { ru: 'Локализации', en: 'Localizations' }, render: page(LocalizationsPage) },
    { route: 'monitoring', title: { ru: 'Мониторинг', en: 'Monitoring' }, render: page(MonitoringPage) },
    { route: 'configuration', title: { ru: 'Конфигурация', en: 'Configuration' }, render: page(ConfigurationPage) },
  ],
  status,
  reportHook,
};

export default plugin;
