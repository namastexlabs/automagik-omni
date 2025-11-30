import { Lock, Info } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface LockedDatabaseTypeBadgeProps {
  dbType: string;
  isLocked: boolean;
}

/**
 * Badge component showing the database type with lock indicator.
 * When locked, displays tooltip explaining why changes are restricted.
 */
export function LockedDatabaseTypeBadge({
  dbType,
  isLocked,
}: LockedDatabaseTypeBadgeProps) {
  const formattedType = dbType === 'postgresql' ? 'PostgreSQL' :
                        dbType === 'sqlite' ? 'SQLite' : dbType;

  if (!isLocked) {
    return (
      <Badge variant="secondary" className="capitalize">
        {formattedType}
      </Badge>
    );
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="secondary"
            className="flex items-center gap-1.5 cursor-help bg-muted border border-border"
          >
            <Lock className="h-3 w-3" />
            {formattedType}
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium mb-1">Database type is locked</p>
              <p className="text-muted-foreground">
                Database type cannot be changed after initial setup because instances exist.
                Contact support if migration is required.
              </p>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
