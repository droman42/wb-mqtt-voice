/**
 * ConflictBadge Component - Inline conflict markers for donation editing
 * 
 * Displays individual conflict indicators with severity-based styling
 * and tooltip information for detailed conflict information.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import Badge from '@/components/ui/Badge';
import type { BadgeProps, ConflictReport } from '@/types';

interface ConflictBadgeProps {
  conflict: ConflictReport;
  className?: string;
  onClick?: () => void;
}

const ConflictBadge: React.FC<ConflictBadgeProps> = ({
  conflict,
  className = '',
  onClick
}) => {
  const { t } = useTranslation('common');
  const getSeverityConfig = (): { icon: typeof Info; variant: BadgeProps['variant']; label: string } => {
    switch (conflict.severity) {
      case 'blocker':
        return {
          icon: AlertCircle,
          variant: 'error',
          label: 'Blocker'
        };
      case 'warning':
        return {
          icon: AlertTriangle,
          variant: 'warning',
          label: 'Warning'
        };
      case 'info':
        return {
          icon: Info,
          variant: 'info',
          label: 'Info'
        };
      default:
        return {
          icon: Info,
          variant: 'default',
          label: 'Unknown'
        };
    }
  };

  const config = getSeverityConfig();
  const Icon = config.icon;

  const formatConflictType = (type: string): string => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getTooltipContent = (): string => {
    const lines: string[] = [
      t('conflicts.tooltip.conflict', { a: conflict.intent_a, b: conflict.intent_b }),
      t('conflicts.tooltip.type', { type: formatConflictType(conflict.conflict_type) }),
      t('conflicts.tooltip.score', { score: (conflict.score * 100).toFixed(1) }),
      t('conflicts.tooltip.language', { language: conflict.language.toUpperCase() })
    ];

    if (conflict.suggestions.length > 0) {
      lines.push('', t('conflicts.suggestionsLabel'));
      conflict.suggestions.slice(0, 2).forEach(suggestion => {
        lines.push(`• ${suggestion}`);
      });
      if (conflict.suggestions.length > 2) {
        lines.push(`• ${t('conflicts.andMore', { count: conflict.suggestions.length - 2 })}`);
      }
    }

    return lines.join('\n');
  };

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className={`inline-flex items-center cursor-help ${className}`}
          onClick={onClick}
        >
          <Badge
            variant={config.variant}
            className="cursor-pointer transition-colors duration-200 text-xs"
          >
            <Icon className="w-3 h-3 mr-1" />
            {formatConflictType(conflict.conflict_type)}
          </Badge>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        <span className="whitespace-pre-line">{getTooltipContent()}</span>
      </TooltipContent>
    </Tooltip>
  );
};

export default ConflictBadge;
