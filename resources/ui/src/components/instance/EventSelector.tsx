import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { EVOLUTION_EVENTS } from '@/lib';

interface EventSelectorProps {
  selectedEvents: string[];
  onChange: (events: string[]) => void;
}

export function EventSelector({ selectedEvents, onChange }: EventSelectorProps) {
  const handleToggle = (event: string, checked: boolean) => {
    if (checked) {
      onChange([...selectedEvents, event]);
    } else {
      onChange(selectedEvents.filter((e) => e !== event));
    }
  };

  const handleSelectAll = () => {
    if (selectedEvents.length === EVOLUTION_EVENTS.length) {
      onChange([]);
    } else {
      onChange([...EVOLUTION_EVENTS]);
    }
  };

  const allSelected = selectedEvents.length === EVOLUTION_EVENTS.length;
  const someSelected = selectedEvents.length > 0 && selectedEvents.length < EVOLUTION_EVENTS.length;

  return (
    <div className="space-y-4">
      {/* Select All */}
      <div className="flex items-center space-x-2 pb-2 border-b">
        <Checkbox
          id="select-all"
          checked={allSelected}
          onCheckedChange={handleSelectAll}
          className={someSelected ? 'data-[state=checked]:bg-primary/50' : ''}
        />
        <Label htmlFor="select-all" className="text-sm font-medium cursor-pointer">
          {allSelected ? 'Deselect All' : 'Select All'}
        </Label>
      </div>

      {/* Event List */}
      <div className="grid grid-cols-1 gap-2 max-h-[300px] overflow-y-auto">
        {EVOLUTION_EVENTS.map((event) => (
          <div key={event} className="flex items-center space-x-2">
            <Checkbox
              id={event}
              checked={selectedEvents.includes(event)}
              onCheckedChange={(checked) => handleToggle(event, checked as boolean)}
            />
            <Label htmlFor={event} className="text-sm cursor-pointer font-mono">
              {event}
            </Label>
          </div>
        ))}
      </div>
    </div>
  );
}
