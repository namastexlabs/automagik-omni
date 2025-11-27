import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Radio, Loader2, Save, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { EventSelector } from './EventSelector';
import { api } from '@/lib';

interface WebSocketSectionProps {
  instanceName: string;
}

interface WebSocketForm {
  enabled: boolean;
  events: string[];
}

const defaultForm: WebSocketForm = {
  enabled: false,
  events: [],
};

export function WebSocketSection({ instanceName }: WebSocketSectionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [form, setForm] = useState<WebSocketForm>(defaultForm);
  const [hasChanges, setHasChanges] = useState(false);
  const queryClient = useQueryClient();

  const { data: websocket, isLoading } = useQuery({
    queryKey: ['websocket', instanceName],
    queryFn: () => api.evolution.getWebSocket(instanceName),
    enabled: isOpen,
  });

  useEffect(() => {
    if (websocket && typeof websocket === 'object') {
      setForm({
        enabled: websocket.enabled ?? false,
        events: Array.isArray(websocket.events) ? websocket.events : [],
      });
      setHasChanges(false);
    }
  }, [websocket]);

  const saveMutation = useMutation({
    mutationFn: (data: WebSocketForm) => api.evolution.setWebSocket(instanceName, data),
    onSuccess: () => {
      toast.success('WebSocket settings saved');
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['websocket', instanceName] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to save: ${error.message}`);
    },
  });

  const updateForm = <K extends keyof WebSocketForm>(key: K, value: WebSocketForm[K]) => {
    setForm(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Card>
        <CollapsibleTrigger asChild>
          <CardHeader className="pb-3 cursor-pointer hover:bg-muted/50 rounded-t-lg">
            <CardTitle className="text-sm font-medium flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Radio className="h-4 w-4" />
                WebSocket
                {form.enabled && <Badge variant="secondary" className="bg-green-500/20 text-green-600">Active</Badge>}
              </span>
              <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </CardTitle>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="space-y-4 pt-0">
            {isLoading ? (
              <div className="flex justify-center py-4">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : (
              <>
                {/* Enable Toggle */}
                <div className="flex items-center justify-between">
                  <Label htmlFor="ws-enabled" className="text-sm font-medium">
                    Enable WebSocket
                  </Label>
                  <Switch
                    id="ws-enabled"
                    checked={form.enabled}
                    onCheckedChange={(checked) => updateForm('enabled', checked)}
                  />
                </div>

                {form.enabled && (
                  <>
                    <p className="text-xs text-muted-foreground">
                      Connect via Socket.io to receive real-time events
                    </p>

                    {/* Events */}
                    <div className="space-y-2">
                      <Label className="text-xs text-muted-foreground">
                        Events ({form.events.length} selected)
                      </Label>
                      <EventSelector
                        selectedEvents={form.events}
                        onChange={(events) => updateForm('events', events)}
                      />
                    </div>
                  </>
                )}

                {/* Save Button */}
                {hasChanges && (
                  <Button
                    className="w-full"
                    size="sm"
                    onClick={() => saveMutation.mutate(form)}
                    disabled={saveMutation.isPending}
                  >
                    {saveMutation.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-2" />
                    )}
                    Save WebSocket
                  </Button>
                )}
              </>
            )}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
