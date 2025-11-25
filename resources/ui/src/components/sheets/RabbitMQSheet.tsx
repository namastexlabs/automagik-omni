import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Server, Loader2, Save } from 'lucide-react';
import { toast } from 'sonner';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { EventSelector } from '@/components/instance/EventSelector';
import { api } from '@/lib/api';

interface RabbitMQSheetProps {
  instanceName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface RabbitMQForm {
  enabled: boolean;
  uri: string;
  exchange: string;
  events: string[];
}

const defaultForm: RabbitMQForm = {
  enabled: false,
  uri: '',
  exchange: '',
  events: [],
};

export function RabbitMQSheet({ instanceName, open, onOpenChange }: RabbitMQSheetProps) {
  const [form, setForm] = useState<RabbitMQForm>(defaultForm);
  const [hasChanges, setHasChanges] = useState(false);
  const queryClient = useQueryClient();

  const { data: rabbitmq, isLoading } = useQuery({
    queryKey: ['rabbitmq', instanceName],
    queryFn: () => api.evolution.getRabbitMQ(instanceName),
    enabled: open,
  });

  useEffect(() => {
    if (rabbitmq && typeof rabbitmq === 'object') {
      setForm({
        enabled: rabbitmq.enabled ?? false,
        uri: rabbitmq.uri ?? '',
        exchange: rabbitmq.exchange ?? '',
        events: Array.isArray(rabbitmq.events) ? rabbitmq.events : [],
      });
      setHasChanges(false);
    }
  }, [rabbitmq]);

  const saveMutation = useMutation({
    mutationFn: (data: RabbitMQForm) => api.evolution.setRabbitMQ(instanceName, data),
    onSuccess: () => {
      toast.success('RabbitMQ settings saved');
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['rabbitmq', instanceName] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to save: ${error.message}`);
    },
  });

  const updateForm = <K extends keyof RabbitMQForm>(key: K, value: RabbitMQForm[K]) => {
    setForm(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            RabbitMQ - {instanceName}
            {form.enabled && <Badge variant="secondary" className="bg-green-500/20 text-green-600">Active</Badge>}
          </SheetTitle>
          <SheetDescription>
            Configure RabbitMQ for message queue event delivery
          </SheetDescription>
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
                  <Label htmlFor="rmq-enabled" className="text-sm font-medium">
                    Enable RabbitMQ
                  </Label>
                  <Switch
                    id="rmq-enabled"
                    checked={form.enabled}
                    onCheckedChange={(checked) => updateForm('enabled', checked)}
                  />
                </div>

                {form.enabled && (
                  <>
                    {/* URI */}
                    <div className="space-y-2">
                      <Label htmlFor="rmq-uri" className="text-sm font-medium">
                        Connection URI
                      </Label>
                      <Input
                        id="rmq-uri"
                        type="url"
                        placeholder="amqp://user:pass@localhost:5672"
                        value={form.uri}
                        onChange={(e) => updateForm('uri', e.target.value)}
                      />
                    </div>

                    {/* Exchange */}
                    <div className="space-y-2">
                      <Label htmlFor="rmq-exchange" className="text-sm font-medium">
                        Exchange Name
                      </Label>
                      <Input
                        id="rmq-exchange"
                        placeholder="evolution_exchange"
                        value={form.exchange}
                        onChange={(e) => updateForm('exchange', e.target.value)}
                      />
                    </div>

                    {/* Events */}
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Events ({form.events.length} selected)
                      </Label>
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
                    Save RabbitMQ
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
