import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Clock } from 'lucide-react';

export type TimeRange = '1h' | '24h' | '7d' | '15d' | '30d';

interface TimeRangeOption {
  value: TimeRange;
  label: string;
}

const TIME_RANGES: TimeRangeOption[] = [
  { value: '1h', label: 'Last hour' },
  { value: '24h', label: 'Last 24 hours' },
  { value: '7d', label: 'Last 7 days' },
  { value: '15d', label: 'Last 15 days' },
  { value: '30d', label: 'Last 30 days' },
];

export function getDateRangeFromTimeRange(range: TimeRange): { start_date: string; end_date: string } {
  const now = new Date();
  const end_date = now.toISOString();

  let start: Date;
  switch (range) {
    case '1h':
      start = new Date(now.getTime() - 60 * 60 * 1000);
      break;
    case '24h':
      start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      break;
    case '7d':
      start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      break;
    case '15d':
      start = new Date(now.getTime() - 15 * 24 * 60 * 60 * 1000);
      break;
    case '30d':
      start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      break;
    default:
      start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  }

  return {
    start_date: start.toISOString(),
    end_date,
  };
}

interface TimeRangeSelectorProps {
  className?: string;
}

export function TimeRangeSelector({ className }: TimeRangeSelectorProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentRange = (searchParams.get('range') as TimeRange) || '24h';

  const handleRangeChange = (value: TimeRange) => {
    setSearchParams({ range: value });
  };

  return (
    <Select value={currentRange} onValueChange={handleRangeChange}>
      <SelectTrigger className={`w-[160px] ${className || ''}`}>
        <Clock className="h-4 w-4 mr-2 text-muted-foreground" />
        <SelectValue placeholder="Select range" />
      </SelectTrigger>
      <SelectContent>
        {TIME_RANGES.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function useTimeRange(): { range: TimeRange; dateRange: { start_date: string; end_date: string } } {
  const [searchParams] = useSearchParams();
  const range = (searchParams.get('range') as TimeRange) || '24h';

  // Memoize the dateRange to prevent infinite re-renders
  // Only recalculate when the range changes
  const dateRange = React.useMemo(() => getDateRangeFromTimeRange(range), [range]);

  return { range, dateRange };
}
