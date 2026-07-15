/**
 * SuggestionPanel Component - Smart fix suggestions for conflicts
 * 
 * Displays actionable suggestions for resolving detected conflicts
 * with the ability to apply suggestions directly to the donation data.
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Lightbulb, CheckCircle, ArrowRight, X } from 'lucide-react';
import { Button, Tooltip, TooltipTrigger, TooltipContent } from 'locveil-ui-kit';
import Badge from '@/components/ui/Badge';
import type { ConflictReport } from '@/types';

interface SuggestionPanelProps {
  conflicts: ConflictReport[];
  onApplySuggestion?: (conflictId: string, suggestion: string) => void;
  onDismissConflict?: (conflictId: string) => void;
  className?: string;
}

const SuggestionPanel: React.FC<SuggestionPanelProps> = ({
  conflicts,
  onApplySuggestion,
  onDismissConflict,
  className = ''
}) => {
  const { t } = useTranslation('common');
  const [expandedConflicts, setExpandedConflicts] = useState<Set<string>>(new Set());
  const [appliedSuggestions, setAppliedSuggestions] = useState<Set<string>>(new Set());

  // Filter to only show conflicts with suggestions
  const conflictsWithSuggestions = conflicts.filter(c => c.suggestions.length > 0);

  if (conflictsWithSuggestions.length === 0) {
    return null;
  }

  const getConflictId = (conflict: ConflictReport): string => {
    return `${conflict.intent_a}-${conflict.intent_b}-${conflict.conflict_type}`;
  };

  const toggleExpanded = (conflictId: string) => {
    setExpandedConflicts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(conflictId)) {
        newSet.delete(conflictId);
      } else {
        newSet.add(conflictId);
      }
      return newSet;
    });
  };

  const handleApplySuggestion = (conflict: ConflictReport, suggestion: string) => {
    const conflictId = getConflictId(conflict);
    const suggestionId = `${conflictId}-${suggestion}`;
    
    if (onApplySuggestion) {
      onApplySuggestion(conflictId, suggestion);
      setAppliedSuggestions(prev => new Set([...prev, suggestionId]));
    }
  };

  const handleDismissConflict = (conflict: ConflictReport) => {
    const conflictId = getConflictId(conflict);
    if (onDismissConflict) {
      onDismissConflict(conflictId);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'blocker':
        return 'bg-[hsl(var(--lv-status-conflict)_70%_96%)] dark:bg-[hsl(var(--lv-status-conflict)_45%_22%_/_0.45)]';
      case 'warning':
        return 'bg-[hsl(var(--lv-status-edited)_70%_96%)] dark:bg-[hsl(var(--lv-status-edited)_45%_22%_/_0.45)]';
      case 'info':
        return 'bg-[hsl(var(--lv-status-tested)_70%_96%)] dark:bg-[hsl(var(--lv-status-tested)_45%_22%_/_0.45)]';
      default:
        return 'bg-muted/40';
    }
  };

  return (
    <div className={`border border-border rounded-lg bg-card ${className}`}>
      <div className="flex items-center space-x-2 p-3 border-b border-border bg-muted">
        <Lightbulb className="w-4 h-4 text-primary" />
        <h3 className="text-sm font-medium text-foreground">
          {t('conflicts.smartSuggestions', { count: conflictsWithSuggestions.length })}
        </h3>
      </div>

      <div className="divide-y divide-border">
        {conflictsWithSuggestions.map((conflict) => {
          const conflictId = getConflictId(conflict);
          const isExpanded = expandedConflicts.has(conflictId);

          return (
            <div key={conflictId} className={`p-3 ${getSeverityColor(conflict.severity)}`}>
              {/* Conflict Header */}
              <div className="flex items-center justify-between">
                <button
                  onClick={() => toggleExpanded(conflictId)}
                  className="flex items-center space-x-2 text-left flex-1 hover:bg-muted/60 -m-1 p-1 rounded transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <div className="flex-1">
                    <div className="text-sm font-medium text-foreground">
                      {conflict.intent_a} ↔ {conflict.intent_b}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {conflict.conflict_type.replace(/_/g, ' ')} • {t('conflicts.suggestionCount', { count: conflict.suggestions.length })}
                    </div>
                  </div>
                  <ArrowRight className={`w-4 h-4 text-muted-foreground transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                </button>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => handleDismissConflict(conflict)}
                      aria-label={t('conflicts.dismissConflict')}
                    >
                      <X />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{t('conflicts.dismissConflict')}</TooltipContent>
                </Tooltip>
              </div>

              {/* Expanded Suggestions */}
              {isExpanded && (
                <div className="mt-3 space-y-2">
                  {conflict.suggestions.map((suggestion, index) => {
                    const suggestionId = `${conflictId}-${suggestion}`;
                    const isApplied = appliedSuggestions.has(suggestionId);

                    return (
                      <div key={index} className="bg-card/70 border border-border rounded p-3">
                        <div className="text-sm text-muted-foreground mb-2">
                          {suggestion}
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="text-xs text-muted-foreground">
                            {t('conflicts.suggestionIndex', { index: index + 1, total: conflict.suggestions.length })}
                          </div>

                          {isApplied ? (
                            <Badge variant="success" className="text-xs">
                              <CheckCircle className="w-3 h-3 mr-1" />
                              {t('conflicts.applied')}
                            </Badge>
                          ) : (
                            <Button
                              size="sm"
                              onClick={() => handleApplySuggestion(conflict, suggestion)}
                              disabled={!onApplySuggestion}
                            >
                              {t('actions.apply')}
                            </Button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default SuggestionPanel;
