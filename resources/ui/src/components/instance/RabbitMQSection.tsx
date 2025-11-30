import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Server, Loader2, Save, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { EventSelector } from './EventSelector';
import { api } from '@/lib';

interface RabbitMQSectionProps {
  instanceName: string;
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

export function RabbitMQSection({ instanceName }: RabbitMQSectionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [form, setForm] = useState<RabbitMQForm>(defaultForm);
  const [hasChanges, setHasChanges] = useState(false);
  const queryClient = useQueryClient();

  const { data: rabbitmq, isLoading } = useQuery({
    queryKey: ['rabbitmq', instanceName],
    queryFn: () => api.evolution.getRabbitMQ(instanceName),
    enabled: isOpen,
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
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Card>
        <CollapsibleTrigger asChild>
          <CardHeader className="pb-3 cursor-pointer hover:bg-muted/50 rounded-t-lg">
            <CardTitle className="text-sm font-medium flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Server className="h-4 w-4" />
                RabbitMQ
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
                    <div className="space-y-1.5">
                      <Label htmlFor="rmq-uri" className="text-xs text-muted-foreground">
                        Connection URI
                      </Label>
                      <Input
                        id="rmq-uri"
                        type="url"
                        placeholder="amqp://user:pass@localhost:5672"
                        value={form.uri}
                        onChange={(e) => updateForm('uri', e.target.value)}
                        className="h-8 text-sm"
                      />
                    </div>

                    {/* Exchange */}
                    <div className="space-y-1.5">
                      <Label htmlFor="rmq-exchange" className="text-xs text-muted-foreground">
                        Exchange Name
                      </Label>
                      <Input
                        id="rmq-exchange"
                        placeholder="evolution_exchange"
                        value={form.exchange}
                        onChange={(e) => updateForm('exchange', e.target.value)}
                        className="h-8 text-sm"
                      />
                    </div>

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
                    Save RabbitMQ
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
