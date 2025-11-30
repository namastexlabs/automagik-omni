import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { api, GlobalSetting, formatDateTime } from '@/lib';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { DatabaseConfigSection } from '@/components/database';
import { Settings as SettingsIcon, Save, Eye, EyeOff, History, RefreshCw } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export default function GlobalSettings() {
  const queryClient = useQueryClient();
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [historyKey, setHistoryKey] = useState<string | null>(null);

  // Fetch all settings
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.settings.list(),
  });

  // Fetch history for specific setting
  const { data: history } = useQuery({
    queryKey: ['settings-history', historyKey],
    queryFn: () => api.settings.getHistory(historyKey!),
    enabled: !!historyKey,
  });

  // Update setting mutation
  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      api.settings.update(key, { value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      setEditingKey(null);
      setEditValues({});
    },
  });

  const handleEdit = (setting: GlobalSetting) => {
    setEditingKey(setting.key);
    setEditValues({ ...editValues, [setting.key]: setting.value || '' });
  };

  const handleSave = (setting: GlobalSetting) => {
    const newValue = editValues[setting.key];
    if (newValue !== undefined) {
      updateMutation.mutate({ key: setting.key, value: newValue });
    }
  };

  const handleCancel = () => {
    setEditingKey(null);
    setEditValues({});
  };

  const toggleSecret = (key: string) => {
    setShowSecrets({ ...showSecrets, [key]: !showSecrets[key] });
  };

  const maskSecret = (value: string | null) => {
    if (!value) return '***';
    if (value.length <= 8) return '***';
    return `${value.substring(0, 4)}***${value.substring(value.length - 4)}`;
  };

  const renderValue = (setting: GlobalSetting) => {
    const isEditing = editingKey === setting.key;
    const displayValue = setting.is_secret && !showSecrets[setting.key]
      ? maskSecret(setting.value)
      : setting.value || '';

    if (isEditing) {
      return (
        <div className="flex items-center gap-2 flex-1">
          <Input
            type={setting.is_secret && !showSecrets[setting.key] ? 'password' : 'text'}
            value={editValues[setting.key] || ''}
            onChange={(e) => setEditValues({ ...editValues, [setting.key]: e.target.value })}
            className="flex-1 font-mono text-sm"
          />
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleSave(setting)}
            disabled={updateMutation.isPending}
          >
            <Save className="h-4 w-4 mr-1" />
            Save
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleCancel}
          >
            Cancel
          </Button>
        </div>
      );
    }

    return (
      <div className="flex items-center gap-2 flex-1 justify-between">
        <code className="text-sm text-muted-foreground font-mono">
          {displayValue}
        </code>
        <div className="flex items-center gap-1">
          {setting.is_secret && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => toggleSecret(setting.key)}
            >
              {showSecrets[setting.key] ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </Button>
          )}
          {!setting.is_required && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleEdit(setting)}
            >
              Edit
            </Button>
          )}
          {setting.is_required && (
            <Badge variant="secondary" className="text-xs">Required</Badge>
          )}
        </div>
      </div>
    );
  };

  // Group settings by category
  const groupedSettings = settings?.reduce((acc, setting: GlobalSetting) => {
    const category = setting.category || 'general';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(setting);
    return acc;
  }, {} as Record<string, GlobalSetting[]>);

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="Global Settings"
          subtitle="Manage system-wide configuration"
          icon={<SettingsIcon className="h-6 w-6 text-primary" />}
        />

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 space-y-6 animate-fade-in max-w-6xl">
            {/* Database Configuration Section */}
            <DatabaseConfigSection />

            {isLoading ? (
              <div className="flex items-center justify-center p-12">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                {Object.entries(groupedSettings || {}).map(([category, categorySettings]) => (
                  <Card key={category} className="border-border elevation-md">
                    <CardHeader>
                      <CardTitle className="capitalize">{category}</CardTitle>
                      <CardDescription>
                        {category === 'integration' && 'External service configuration'}
                        {category === 'limits' && 'System limits and quotas'}
                        {category === 'features' && 'Feature toggles'}
                        {category === 'general' && 'General system settings'}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {categorySettings.map((setting: GlobalSetting) => (
                        <div
                          key={setting.key}
                          className="p-4 bg-muted rounded-lg border border-border space-y-2"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <Label className="text-sm font-semibold">
                                  {setting.key}
                                </Label>
                                <Badge variant="outline" className="text-xs">
                                  {setting.value_type}
                                </Badge>
                                {setting.is_secret && (
                                  <Badge className="text-xs gradient-primary border-0">
                                    Secret
                                  </Badge>
                                )}
                              </div>
                              {setting.description && (
                                <p className="text-xs text-muted-foreground mb-2">
                                  {setting.description}
                                </p>
                              )}
                              {renderValue(setting)}
                              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                                <span>Updated: {formatDateTime(setting.updated_at)}</span>
                                {setting.updated_by && <span>By: {setting.updated_by}</span>}
                                <Dialog>
                                  <DialogTrigger asChild>
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      className="h-6 px-2 text-xs"
                                      onClick={() => setHistoryKey(setting.key)}
                                    >
                                      <History className="h-3 w-3 mr-1" />
                                      History
                                    </Button>
                                  </DialogTrigger>
                                  <DialogContent className="max-w-3xl max-h-[80vh] overflow-auto">
                                    <DialogHeader>
                                      <DialogTitle>Change History: {setting.key}</DialogTitle>
                                      <DialogDescription>
                                        Audit trail of all changes to this setting
                                      </DialogDescription>
                                    </DialogHeader>
                                    <div className="mt-4">
                                      {history && history.length > 0 ? (
                                        <Table>
                                          <TableHeader>
                                            <TableRow>
                                              <TableHead>Date</TableHead>
                                              <TableHead>Changed By</TableHead>
                                              <TableHead>Old Value</TableHead>
                                              <TableHead>New Value</TableHead>
                                              <TableHead>Reason</TableHead>
                                            </TableRow>
                                          </TableHeader>
                                          <TableBody>
                                            {history.map((entry: any) => (
                                              <TableRow key={entry.id}>
                                                <TableCell className="text-xs">
                                                  {formatDateTime(entry.changed_at)}
                                                </TableCell>
                                                <TableCell className="text-xs">
                                                  {entry.changed_by || 'system'}
                                                </TableCell>
                                                <TableCell className="text-xs font-mono">
                                                  {setting.is_secret
                                                    ? maskSecret(entry.old_value)
                                                    : entry.old_value || '(empty)'}
                                                </TableCell>
                                                <TableCell className="text-xs font-mono">
                                                  {setting.is_secret
                                                    ? maskSecret(entry.new_value)
                                                    : entry.new_value || '(empty)'}
                                                </TableCell>
                                                <TableCell className="text-xs">
                                                  {entry.change_reason || '-'}
                                                </TableCell>
                                              </TableRow>
                                            ))}
                                          </TableBody>
                                        </Table>
                                      ) : (
                                        <p className="text-sm text-muted-foreground text-center py-8">
                                          No change history available
                                        </p>
                                      )}
                                    </div>
                                  </DialogContent>
                                </Dialog>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                ))}
              </>
            )}

            {/* Footer */}
            <div className="pt-6 pb-4">
              <Separator className="mb-4" />
              <p className="text-xs text-center text-muted-foreground">
                Global settings are stored in the database and synchronized across all instances.
                <br />
                Changes to required settings may require application restart.
              </p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
