import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Settings, Loader2, Save, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { api } from '@/lib/api';

interface SettingsSectionProps {
  instanceName: string;
}

interface SettingsForm {
  rejectCall: boolean;
  msgCall: string;
  groupsIgnore: boolean;
  alwaysOnline: boolean;
  readMessages: boolean;
  readStatus: boolean;
  syncFullHistory: boolean;
}

const defaultSettings: SettingsForm = {
  rejectCall: false,
  msgCall: '',
  groupsIgnore: false,
  alwaysOnline: false,
  readMessages: false,
  readStatus: false,
  syncFullHistory: false,
};

export function SettingsSection({ instanceName }: SettingsSectionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [form, setForm] = useState<SettingsForm>(defaultSettings);
  const [hasChanges, setHasChanges] = useState(false);
  const queryClient = useQueryClient();

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings', instanceName],
    queryFn: () => api.evolution.getSettings(instanceName),
    enabled: isOpen,
  });

  useEffect(() => {
    if (settings) {
      setForm({
        rejectCall: settings.rejectCall ?? false,
        msgCall: settings.msgCall ?? '',
        groupsIgnore: settings.groupsIgnore ?? false,
        alwaysOnline: settings.alwaysOnline ?? false,
        readMessages: settings.readMessages ?? false,
        readStatus: settings.readStatus ?? false,
        syncFullHistory: settings.syncFullHistory ?? false,
      });
      setHasChanges(false);
    }
  }, [settings]);

  const saveMutation = useMutation({
    mutationFn: (data: SettingsForm) => api.evolution.setSettings(instanceName, data),
    onSuccess: () => {
      toast.success('Settings saved');
      setHasChanges(false);
      queryClient.invalidateQueries({ queryKey: ['settings', instanceName] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to save: ${error.message}`);
    },
  });

  const updateForm = (key: keyof SettingsForm, value: boolean | string) => {
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
                <Settings className="h-4 w-4" />
                Settings
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
                {/* Call Settings */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="rejectCall" className="text-sm">
                      Auto-reject calls
                    </Label>
                    <Switch
                      id="rejectCall"
                      checked={form.rejectCall}
                      onCheckedChange={(checked) => updateForm('rejectCall', checked)}
                    />
                  </div>

                  {form.rejectCall && (
                    <div className="space-y-1.5 pl-4 border-l-2">
                      <Label htmlFor="msgCall" className="text-xs text-muted-foreground">
                        Rejection message
                      </Label>
                      <Input
                        id="msgCall"
                        placeholder="Sorry, I can't take calls right now"
                        value={form.msgCall}
                        onChange={(e) => updateForm('msgCall', e.target.value)}
                        className="h-8 text-sm"
                      />
                    </div>
                  )}
                </div>

                {/* Presence Settings */}
                <div className="flex items-center justify-between">
                  <Label htmlFor="alwaysOnline" className="text-sm">
                    Always online
                  </Label>
                  <Switch
                    id="alwaysOnline"
                    checked={form.alwaysOnline}
                    onCheckedChange={(checked) => updateForm('alwaysOnline', checked)}
                  />
                </div>

                {/* Message Settings */}
                <div className="flex items-center justify-between">
                  <Label htmlFor="readMessages" className="text-sm">
                    Auto-read messages
                  </Label>
                  <Switch
                    id="readMessages"
                    checked={form.readMessages}
                    onCheckedChange={(checked) => updateForm('readMessages', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <Label htmlFor="readStatus" className="text-sm">
                    Auto-read status
                  </Label>
                  <Switch
                    id="readStatus"
                    checked={form.readStatus}
                    onCheckedChange={(checked) => updateForm('readStatus', checked)}
                  />
                </div>

                {/* Group Settings */}
                <div className="flex items-center justify-between">
                  <Label htmlFor="groupsIgnore" className="text-sm">
                    Ignore group messages
                  </Label>
                  <Switch
                    id="groupsIgnore"
                    checked={form.groupsIgnore}
                    onCheckedChange={(checked) => updateForm('groupsIgnore', checked)}
                  />
                </div>

                {/* Sync Settings */}
                <div className="flex items-center justify-between">
                  <Label htmlFor="syncFullHistory" className="text-sm">
                    Sync full history
                  </Label>
                  <Switch
                    id="syncFullHistory"
                    checked={form.syncFullHistory}
                    onCheckedChange={(checked) => updateForm('syncFullHistory', checked)}
                  />
                </div>

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
                    Save Settings
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
