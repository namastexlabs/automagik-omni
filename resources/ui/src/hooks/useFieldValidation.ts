/**
 * Field validation hook with debounced validation and visual feedback.
 * Provides real-time validation for database configuration fields.
 */

import { useState, useEffect } from 'react';

export type ValidationState = 'idle' | 'typing' | 'valid' | 'invalid';

export interface ValidationResult {
  state: ValidationState;
  error: string | null;
}

export interface ValidationRule {
  required?: boolean;
  pattern?: RegExp;
  min?: number;
  max?: number;
  custom?: (value: string) => { valid: boolean; error?: string };
}

/**
 * Hook for field validation with debouncing.
 *
 * @param value - Current field value
 * @param rule - Validation rule to apply
 * @param debounceMs - Debounce delay in milliseconds (default: 500ms)
 * @returns ValidationResult with state and error message
 */
export function useFieldValidation(value: string, rule: ValidationRule, debounceMs: number = 500): ValidationResult {
  const [state, setState] = useState<ValidationState>('idle');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Skip validation if field is empty and not required
    if (!value && !rule.required) {
      setState('idle');
      setError(null);
      return;
    }

    // Set typing state immediately
    setState('typing');

    // Debounced validation
    const timer = setTimeout(() => {
      const result = validateField(value, rule);

      if (result.valid) {
        setState('valid');
        setError(null);
      } else {
        setState('invalid');
        setError(result.error || 'Invalid value');
      }
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [value, rule, debounceMs]);

  return { state, error };
}

/**
 * Validate a field value against a rule.
 */
function validateField(value: string, rule: ValidationRule): { valid: boolean; error?: string } {
  // Required check
  if (rule.required && !value.trim()) {
    return { valid: false, error: 'This field is required' };
  }

  // Skip further validation if empty and not required
  if (!value.trim() && !rule.required) {
    return { valid: true };
  }

  // Pattern check
  if (rule.pattern && !rule.pattern.test(value)) {
    return { valid: false, error: 'Invalid format' };
  }

  // Numeric range check
  if (rule.min !== undefined || rule.max !== undefined) {
    const num = parseInt(value, 10);
    if (isNaN(num)) {
      return { valid: false, error: 'Must be a number' };
    }
    if (rule.min !== undefined && num < rule.min) {
      return { valid: false, error: `Must be at least ${rule.min}` };
    }
    if (rule.max !== undefined && num > rule.max) {
      return { valid: false, error: `Must be at most ${rule.max}` };
    }
  }

  // Custom validation
  if (rule.custom) {
    return rule.custom(value);
  }

  return { valid: true };
}

/**
 * Predefined validation rules for common field types.
 */
export const validationRules = {
  // PostgreSQL fields
  pgHost: {
    required: true,
    custom: (value: string) => {
      // Allow localhost, IP addresses, and hostnames
      const hostnamePattern = /^([a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+$|^localhost$|^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;
      if (!hostnamePattern.test(value)) {
        return { valid: false, error: 'Invalid hostname or IP address' };
      }
      return { valid: true };
    },
  } as ValidationRule,

  pgPort: {
    required: true,
    min: 1,
    max: 65535,
  } as ValidationRule,

  pgUsername: {
    required: true,
    custom: (value: string) => {
      if (value.trim().length === 0) {
        return { valid: false, error: 'Username is required' };
      }
      return { valid: true };
    },
  } as ValidationRule,

  pgPassword: {
    required: true,
    custom: (value: string) => {
      if (value.length === 0) {
        return { valid: false, error: 'Password is required' };
      }
      return { valid: true };
    },
  } as ValidationRule,

  pgDatabase: {
    required: true,
    custom: (value: string) => {
      if (value.trim().length === 0) {
        return { valid: false, error: 'Database name is required' };
      }
      // Basic database name validation (alphanumeric, underscores, hyphens)
      const dbPattern = /^[a-zA-Z0-9_-]+$/;
      if (!dbPattern.test(value)) {
        return { valid: false, error: 'Database name can only contain letters, numbers, underscores, and hyphens' };
      }
      return { valid: true };
    },
  } as ValidationRule,

  // Redis fields
  redisHost: {
    required: true,
    custom: (value: string) => {
      const hostnamePattern = /^([a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+$|^localhost$|^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;
      if (!hostnamePattern.test(value)) {
        return { valid: false, error: 'Invalid hostname or IP address' };
      }
      return { valid: true };
    },
  } as ValidationRule,

  redisPort: {
    required: true,
    min: 1,
    max: 65535,
  } as ValidationRule,

  redisPassword: {
    required: false, // Optional for Redis
  } as ValidationRule,

  redisDbNumber: {
    required: true,
    min: 0,
    max: 15,
  } as ValidationRule,
};
