import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow, parseISO, isToday, isYesterday } from 'date-fns';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Normalize a timestamp string to include UTC timezone if missing.
 * Backend stores UTC but SQLAlchemy returns naive timestamps without 'Z'.
 * This ensures date-fns parseISO treats them as UTC, not local time.
 */
function normalizeUtcTimestamp(dateString: string): string {
  // If already has timezone info (+00:00, Z, etc), return as-is
  if (/[+-]\d{2}:\d{2}$/.test(dateString) || dateString.endsWith('Z')) {
    return dateString;
  }
  // Append Z to treat as UTC
  return dateString + 'Z';
}

export function formatDateTime(dateString: string | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const date = parseISO(normalizeUtcTimestamp(dateString));
    return format(date, 'MMM d, yyyy, h:mm a');
  } catch {
    return 'Invalid date';
  }
}

export function formatRelativeTime(dateString: string | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const date = parseISO(normalizeUtcTimestamp(dateString));
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return 'Invalid date';
  }
}

export function formatDate(dateString: string | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const date = parseISO(normalizeUtcTimestamp(dateString));
    return format(date, 'MMM d, yyyy');
  } catch {
    return 'Invalid date';
  }
}

export function formatTime(dateString: string | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const date = parseISO(normalizeUtcTimestamp(dateString));
    return format(date, 'h:mm a');
  } catch {
    return 'Invalid date';
  }
}

export function formatTimeFromTimestamp(timestamp: number | undefined): string {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp * 1000);
    return format(date, 'h:mm a');
  } catch {
    return '';
  }
}

export function formatTimestampForChat(timestamp: number | string | undefined): string {
  if (!timestamp || timestamp === 0 || timestamp === '0') return '';

  try {
    // Convert to milliseconds if it looks like a Unix timestamp in seconds
    const numericTs = typeof timestamp === 'number' ? timestamp : Number(timestamp);
    const ms = numericTs > 1e12 ? numericTs : numericTs * 1000;
    const date = new Date(ms);

    // Check for invalid date
    if (isNaN(date.getTime())) return '';

    // Today - show time
    if (isToday(date)) {
      return format(date, 'h:mm a');
    }

    // Yesterday
    if (isYesterday(date)) {
      return 'Yesterday';
    }

    // This week - show day name (within 7 days)
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    if (diffMs < 604800000) {
      return format(date, 'EEEE');
    }

    // Older - show date
    return format(date, 'MM/dd/yyyy');
  } catch {
    return '';
  }
}

export function formatLogTimestamp(timestamp: string | undefined): string {
  if (!timestamp) return '';
  try {
    // Normalize UTC timestamp if it's an ISO string without timezone
    const normalized = normalizeUtcTimestamp(timestamp);
    const date = parseISO(normalized);
    return format(date, 'h:mm:ss a');
  } catch {
    return '';
  }
}

export function truncate(str: string | undefined, length: number): string {
  if (!str) return '';
  if (str.length <= length) return str;
  return str.substring(0, length) + '...';
}
