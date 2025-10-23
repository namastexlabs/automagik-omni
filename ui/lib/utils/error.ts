/**
 * Error handling utilities for user-facing error messages
 * Converts technical errors into friendly, actionable messages
 */

/**
 * Detects if an error is a backend connection failure
 */
export function isBackendError(error: unknown): boolean {
  if (!(error instanceof Error)) return false

  const message = error.message.toLowerCase()
  const cause = (error as any).cause

  // Check for common backend connection errors
  const backendErrorPatterns = [
    'fetch failed',
    'econnrefused',
    'network error',
    'failed to fetch',
    'connection refused',
    'connect_timeout',
    'socket hang up',
    'enotfound',
    'etimedout'
  ]

  // Check error message
  if (backendErrorPatterns.some(pattern => message.includes(pattern))) {
    return true
  }

  // Check error cause
  if (cause && typeof cause === 'object') {
    const causeStr = String(cause).toLowerCase()
    if (backendErrorPatterns.some(pattern => causeStr.includes(pattern))) {
      return true
    }
  }

  return false
}

/**
 * Converts errors to user-friendly messages
 */
export function getErrorMessage(error: unknown): string {
  // Handle non-Error objects
  if (!error) {
    return 'An unknown error occurred'
  }

  if (typeof error === 'string') {
    return error
  }

  if (!(error instanceof Error)) {
    return 'An unexpected error occurred'
  }

  const message = error.message

  // Backend connection errors
  if (isBackendError(error)) {
    return 'Cannot connect to backend service. Please check if the backend is running from the Dashboard.'
  }

  // API-specific error patterns
  if (message.includes('does not exist')) {
    return message // Already user-friendly from API
  }

  if (message.includes('unauthorized') || message.includes('401')) {
    return 'Authentication failed. Please check your API credentials.'
  }

  if (message.includes('forbidden') || message.includes('403')) {
    return 'Access denied. You do not have permission to perform this action.'
  }

  if (message.includes('not found') || message.includes('404')) {
    return 'The requested resource was not found.'
  }

  if (message.includes('timeout')) {
    return 'Request timed out. The server took too long to respond.'
  }

  if (message.includes('rate limit')) {
    return 'Too many requests. Please wait a moment and try again.'
  }

  if (message.includes('server error') || message.includes('500')) {
    return 'Server error. Please try again later or contact support.'
  }

  if (message.includes('bad request') || message.includes('400')) {
    return 'Invalid request. Please check your input and try again.'
  }

  // If error message is already user-friendly (no technical jargon)
  const technicalPatterns = ['TypeError:', 'ReferenceError:', 'AggregateError', 'at Object.']
  if (!technicalPatterns.some(pattern => message.includes(pattern))) {
    return message
  }

  // Fallback for technical errors
  return 'An error occurred. Please try again or restart the backend from the Dashboard.'
}

/**
 * Error message mapping for common scenarios
 */
export const ErrorMessages = {
  BACKEND_DOWN: 'Cannot connect to backend service. Please check if the backend is running from the Dashboard.',
  INSTANCE_NOT_FOUND: 'Instance not found. It may have been deleted or is not available.',
  LOAD_FAILED: 'Failed to load data. Please try again.',
  NETWORK_ERROR: 'Network error. Please check your connection and try again.',
  UNKNOWN: 'An unexpected error occurred. Please try again.',
} as const
