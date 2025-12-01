/**
 * Progressive test visualization component.
 * Shows step-by-step test progress with detailed feedback and troubleshooting.
 */

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import {
  CheckCircle2,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
} from 'lucide-react';
import type { TestResult } from '@/lib';

interface TestProgressProps {
  tests: Record<string, TestResult>;
  totalLatency: number;
  isPending?: boolean;
  testType?: 'postgresql' | 'redis';
}

// Test step configuration
const TEST_STEPS = {
  postgresql: [
    { key: 'tcp', label: 'TCP Connection', description: 'Checking network connectivity' },
    { key: 'database', label: 'Database', description: 'Creating database if needed' },
    { key: 'auth', label: 'Authentication', description: 'Verifying credentials' },
    { key: 'permissions', label: 'Permissions', description: 'Testing CREATE TABLE permission' },
    { key: 'write_read', label: 'Read/Write', description: 'Testing data operations' },
  ],
  redis: [
    { key: 'tcp', label: 'TCP Connection', description: 'Checking network connectivity' },
    { key: 'auth', label: 'Authentication', description: 'Testing PING command' },
    { key: 'write_read', label: 'Read/Write', description: 'Testing SET/GET/DEL operations' },
  ],
};

// Troubleshooting suggestions for common errors
const TROUBLESHOOTING: Record<string, string[]> = {
  // TCP errors
  'connection refused': [
    'Verify the database server is running',
    'Check that the host and port are correct',
    'Ensure firewall allows connections to the port',
  ],
  'dns resolution failed': [
    'Check that the hostname is spelled correctly',
    'Try using an IP address instead of hostname',
    'Verify DNS is configured correctly',
  ],
  'timed out': [
    'Check network connectivity to the server',
    'Verify firewall settings allow the connection',
    'Ensure the server is not overloaded',
  ],

  // Auth errors
  'authentication failed': [
    'Verify the username and password are correct',
    'Check that the user exists in the database',
    'Ensure the user has remote connection permissions',
  ],
  'password': [
    'Double-check the password for typos',
    'Verify special characters are entered correctly',
    'Check if password authentication is enabled',
  ],

  // Database errors
  'does not exist': [
    'The wizard will try to create the database automatically',
    'Verify the database name is spelled correctly',
    'Check that you have access to the database',
  ],
  'cannot create database': [
    'Verify the user has CREATEDB permission',
    'Ask your database administrator to create the database',
    'Or grant CREATEDB permission: ALTER USER username CREATEDB;',
  ],
  'permission denied': [
    'The user does not have permission to create databases',
    'Ask your database administrator to create the database',
    'Or grant appropriate permissions to the user',
  ],

  // Permission errors
  'insufficient permissions': [
    'Grant CREATE TABLE permission to the user',
    'Verify the user has write access to the database',
    'Check database-level permissions',
  ],
};

function getSuggestionsForError(errorMessage: string): string[] {
  const lowerError = errorMessage.toLowerCase();
  for (const [keyword, suggestions] of Object.entries(TROUBLESHOOTING)) {
    if (lowerError.includes(keyword)) {
      return suggestions;
    }
  }
  return ['Check server logs for more details', 'Verify all connection parameters are correct'];
}

export function TestProgress({ tests, totalLatency, isPending = false, testType = 'postgresql' }: TestProgressProps) {
  const [copiedError, setCopiedError] = useState<string | null>(null);
  const [expandedTests, setExpandedTests] = useState<Set<string>>(new Set());

  const steps = TEST_STEPS[testType];
  const allPassed = Object.values(tests).every((t) => t.ok);

  const toggleExpanded = (key: string) => {
    const newExpanded = new Set(expandedTests);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedTests(newExpanded);
  };

  const copyError = (stepLabel: string, errorMessage: string) => {
    const errorText = `${stepLabel} Failed: ${errorMessage}`;
    navigator.clipboard.writeText(errorText);
    setCopiedError(stepLabel);
    setTimeout(() => setCopiedError(null), 2000);
  };

  return (
    <div className="space-y-2 p-4 bg-muted rounded-lg">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="font-semibold">Connection Test Results</span>
        <Badge variant={allPassed ? 'default' : 'destructive'}>
          {isPending ? 'Testing...' : allPassed ? 'All Passed' : 'Failed'}
        </Badge>
      </div>

      {/* Progressive steps */}
      <div className="space-y-2">
        {steps.map((step, index) => {
          const testResult = tests[step.key];
          const isExpanded = expandedTests.has(step.key);

          // Determine step state
          let stepState: 'pending' | 'running' | 'passed' | 'failed' = 'pending';
          if (isPending && index === Object.keys(tests).length) {
            stepState = 'running';
          } else if (testResult) {
            stepState = testResult.ok ? 'passed' : 'failed';
          } else if (index < Object.keys(tests).length) {
            stepState = 'pending';
          }

          // Icon selection
          let Icon = Loader2;
          let iconClass = 'h-4 w-4 text-muted-foreground';

          if (stepState === 'running') {
            Icon = Loader2;
            iconClass = 'h-4 w-4 animate-spin text-blue-500';
          } else if (stepState === 'passed') {
            Icon = CheckCircle2;
            iconClass = 'h-4 w-4 text-green-500';
          } else if (stepState === 'failed') {
            Icon = XCircle;
            iconClass = 'h-4 w-4 text-red-500';
          }

          const suggestions = testResult && !testResult.ok ? getSuggestionsForError(testResult.message) : [];

          return (
            <div key={step.key} className={stepState === 'failed' ? 'border-l-2 border-red-500 pl-2' : ''}>
              {/* Step row */}
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 flex-1">
                  <Icon className={iconClass} />
                  <div className="flex-1">
                    <div className="font-medium">{step.label}</div>
                    {stepState === 'running' && (
                      <div className="text-xs text-muted-foreground">{step.description}</div>
                    )}
                  </div>
                </div>

                {/* Latency badge */}
                {testResult?.latency_ms && stepState === 'passed' && (
                  <Badge variant="outline" className="text-xs">
                    {testResult.latency_ms.toFixed(0)}ms
                  </Badge>
                )}

                {/* Expand button for failed tests */}
                {stepState === 'failed' && suggestions.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleExpanded(step.key)}
                    className="h-6 px-2"
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-3 w-3" />
                    ) : (
                      <ChevronRight className="h-3 w-3" />
                    )}
                  </Button>
                )}
              </div>

              {/* Error details and troubleshooting (collapsible) */}
              {stepState === 'failed' && testResult && (
                <Collapsible open={isExpanded}>
                  <CollapsibleContent className="mt-2 space-y-2">
                    {/* Error message */}
                    <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded p-2">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <p className="text-xs font-medium text-red-900 dark:text-red-100">Error:</p>
                          <p className="text-xs text-red-800 dark:text-red-200 font-mono mt-1">
                            {testResult.message}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyError(step.label, testResult.message)}
                          className="h-6 px-2 shrink-0"
                          title="Copy error message"
                        >
                          {copiedError === step.label ? (
                            <Check className="h-3 w-3 text-green-500" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </Button>
                      </div>
                    </div>

                    {/* Troubleshooting suggestions */}
                    {suggestions.length > 0 && (
                      <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded p-2">
                        <p className="text-xs font-medium text-blue-900 dark:text-blue-100 mb-1">
                          Troubleshooting:
                        </p>
                        <ul className="list-disc list-inside space-y-1">
                          {suggestions.map((suggestion, i) => (
                            <li key={i} className="text-xs text-blue-800 dark:text-blue-200">
                              {suggestion}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CollapsibleContent>
                </Collapsible>
              )}
            </div>
          );
        })}
      </div>

      {/* Total latency */}
      {!isPending && (
        <div className="text-xs text-muted-foreground pt-2 border-t">
          Total time: {totalLatency.toFixed(0)}ms
        </div>
      )}
    </div>
  );
}
