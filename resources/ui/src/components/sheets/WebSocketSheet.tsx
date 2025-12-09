import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Radio, Loader2, Save } from 'lucide-react';
import { toast } from 'sonner';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { EventSelector } from '@/components/instance/EventSelector';
import { api } from '@/lib';

interface WebSocketSheetProps {
  instanceName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface WebSocketForm {
  enabled: boolean;
  events: string[];
}

const defaultForm: WebSocketForm = {
  enabled: false,
  events: [],
};

export function WebSocketSheet({ instanceName, open, onOpenChange }: WebSocketSheetProps) {
  const [form, setForm] = useState<WebSocketForm>(defaultForm);
  const [hasChanges, setHasChanges] = useState(false);
  const queryClient = useQueryClient();

  const { data: websocket, isLoading } = useQuery({
    queryKey: ['websocket', instanceName],
    queryFn: () => api.evolution.getWebSocket(instanceName),
    enabled: open,
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
    setForm((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Radio className="h-5 w-5" />
            WebSocket - {instanceName}
            {form.enabled && (
              <Badge variant="secondary" className="bg-green-500/20 text-green-600">
                Active
              </Badge>
            )}
          </SheetTitle>
          <SheetDescription>Configure WebSocket for real-time event delivery</SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-120px)] mt-6">
          <div className="space-y-6 pr-4">
            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                {/* Enable Toggle */}
                <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
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
                    {/* Info */}
                    <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                      <p className="text-sm text-blue-600 dark:text-blue-400">
                        Connect via Socket.io to receive real-time events. The WebSocket endpoint is available at the
                        Evolution API base URL.
                      </p>
                    </div>

                    {/* Events */}
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">Events ({form.events.length} selected)</Label>
                      <div className="p-4 rounded-lg bg-muted/50">
                        <EventSelector
                          selectedEvents={form.events}
                          onChange={(events) => updateForm('events', events)}
                        />
                      </div>
                    </div>
                  </>
                )}

                {/* Save Button */}
                {hasChanges && (
                  <Button
                    className="w-full"
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
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
