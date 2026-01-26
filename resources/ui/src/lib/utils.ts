import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow, parseISO, isToday, isYesterday } from 'date-fns';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDateTime(dateString: string | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const date = parseISO(dateString);
    return format(date, 'MMM d, yyyy, h:mm a');
  } catch {
    return 'Invalid date';
  }
}

export function formatRelativeTime(dateString: string | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const date = parseISO(dateString);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return 'Invalid date';
  }
}

export function formatDate(dateString: string | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const date = parseISO(dateString);
    return format(date, 'MMM d, yyyy');
  } catch {
    return 'Invalid date';
  }
}

export function formatTime(dateString: string | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const date = parseISO(dateString);
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
    const date = new Date(timestamp);
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
