import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Settings, Loader2, Save } from 'lucide-react';
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
import { api } from '@/lib/api';

interface SettingsSheetProps {
  instanceName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
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

export function SettingsSheet({ instanceName, open, onOpenChange }: SettingsSheetProps) {
  const [form, setForm] = useState<SettingsForm>(defaultSettings);
  const [hasChanges, setHasChanges] = useState(false);
  const queryClient = useQueryClient();

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings', instanceName],
    queryFn: () => api.evolution.getSettings(instanceName),
    enabled: open,
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
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Settings - {instanceName}
          </SheetTitle>
          <SheetDescription>
            Configure instance behavior and preferences
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
                {/* Call Settings */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">Call Settings</h3>
                  <div className="space-y-3 pl-4">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="rejectCall" className="text-sm">
                        Auto-reject incoming calls
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
                          className="h-9"
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* Presence Settings */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">Presence</h3>
                  <div className="space-y-3 pl-4">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="alwaysOnline" className="text-sm">
                        Always show as online
                      </Label>
                      <Switch
                        id="alwaysOnline"
                        checked={form.alwaysOnline}
                        onCheckedChange={(checked) => updateForm('alwaysOnline', checked)}
                      />
                    </div>
                  </div>
                </div>

                {/* Message Settings */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">Messages</h3>
                  <div className="space-y-3 pl-4">
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
                        Auto-read status updates
                      </Label>
                      <Switch
                        id="readStatus"
                        checked={form.readStatus}
                        onCheckedChange={(checked) => updateForm('readStatus', checked)}
                      />
                    </div>
                  </div>
                </div>

                {/* Group Settings */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">Groups</h3>
                  <div className="space-y-3 pl-4">
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
                  </div>
                </div>

                {/* Sync Settings */}
                <div className="space-y-4">
                  <h3 className="text-sm font-medium">Sync</h3>
                  <div className="space-y-3 pl-4">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="syncFullHistory" className="text-sm">
                        Sync full message history
                      </Label>
                      <Switch
                        id="syncFullHistory"
                        checked={form.syncFullHistory}
                        onCheckedChange={(checked) => updateForm('syncFullHistory', checked)}
                      />
                    </div>
                  </div>
                </div>

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
                    Save Settings
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
