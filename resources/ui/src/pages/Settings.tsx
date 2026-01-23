import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api, GlobalSetting, getApiKey, formatDateTime } from '@/lib';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { ThemeToggle } from '@/components/ThemeToggle';
import { DatabaseConfigSection } from '@/components/database';
import { ProviderList } from '@/components/providers';
import {
  Settings as SettingsIcon,
  Key,
  Info,
  Moon,
  Sun,
  Database,
  Server,
  FileText,
  Copy,
  Check,
  Save,
  Eye,
  EyeOff,
  History,
  RefreshCw,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

export default function Settings() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const defaultTab = searchParams.get('tab') || 'general';

  // General tab state
  const [copied, setCopied] = useState(false);
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
  });

  const apiKey = getApiKey();
  const maskedKey = apiKey ? `${apiKey.substring(0, 8)}...${apiKey.substring(apiKey.length - 4)}` : 'Not set';

  const handleCopyApiKey = async () => {
    if (!apiKey) return;
    try {
      await navigator.clipboard.writeText(apiKey);
      setCopied(true);
      toast.success('API key copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy API key');
    }
  };

  // System tab state
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [historyKey, setHistoryKey] = useState<string | null>(null);

  // Fetch all settings
  const { data: settings, isLoading: settingsLoading } = useQuery({
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
    mutationFn: ({ key, value }: { key: string; value: string }) => api.settings.update(key, { value }),
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
    const displayValue =
      setting.is_secret && !showSecrets[setting.key] ? maskSecret(setting.value) : setting.value || '';

    if (isEditing) {
      return (
        <div className="flex items-center gap-2 flex-1">
          <Input
            type={setting.is_secret && !showSecrets[setting.key] ? 'password' : 'text'}
            value={editValues[setting.key] || ''}
            onChange={(e) => setEditValues({ ...editValues, [setting.key]: e.target.value })}
            className="flex-1 font-mono text-sm"
          />
          <Button size="sm" variant="outline" onClick={() => handleSave(setting)} disabled={updateMutation.isPending}>
            <Save className="h-4 w-4 mr-1" />
            Save
          </Button>
          <Button size="sm" variant="ghost" onClick={handleCancel}>
            Cancel
          </Button>
        </div>
      );
    }

    return (
      <div className="flex items-center gap-2 flex-1 justify-between">
        <code className="text-sm text-muted-foreground font-mono">{displayValue}</code>
        <div className="flex items-center gap-1">
          {setting.is_secret && (
            <Button size="sm" variant="ghost" onClick={() => toggleSecret(setting.key)}>
              {showSecrets[setting.key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
          )}
          {!setting.is_required && (
            <Button size="sm" variant="outline" onClick={() => handleEdit(setting)}>
              Edit
            </Button>
          )}
          {setting.is_required && (
            <Badge variant="secondary" className="text-xs">
              Required
            </Badge>
          )}
        </div>
      </div>
    );
  };

  // Group settings by category
  const groupedSettings = settings?.reduce(
    (acc, setting: GlobalSetting) => {
      const category = setting.category || 'general';
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(setting);
      return acc;
    },
    {} as Record<string, GlobalSetting[]>,
  );

  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value });
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="Settings"
          subtitle="Configure your Omni instance"
          icon={<SettingsIcon className="h-6 w-6 text-primary" />}
          actions={
            <Button variant="outline" asChild>
              <a href="/api/v1/docs" target="_blank" rel="noopener noreferrer">
                <FileText className="h-4 w-4 mr-2" />
                API Docs
              </a>
            </Button>
          }
        />

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 animate-fade-in max-w-6xl">
            <Tabs value={defaultTab} onValueChange={handleTabChange} className="space-y-6">
              <TabsList className="grid w-full grid-cols-3 max-w-md">
                <TabsTrigger value="general" className="flex items-center gap-2">
                  <Key className="h-4 w-4" />
                  General
                </TabsTrigger>
                <TabsTrigger value="providers" className="flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  Providers
                </TabsTrigger>
                <TabsTrigger value="system" className="flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  System
                </TabsTrigger>
              </TabsList>

              {/* General Tab */}
              <TabsContent value="general" className="space-y-6">
                {/* API Configuration */}
                <Card className="border-border elevation-md">
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Key className="h-5 w-5 text-primary" />
                      <CardTitle>API Configuration</CardTitle>
                    </div>
                    <CardDescription>Your Omni API connection settings</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                      <span className="text-sm font-medium text-foreground">API URL</span>
                      <code className="text-sm text-muted-foreground">
                        {import.meta.env.VITE_API_URL || 'http://localhost:8882'}
                      </code>
                    </div>

                    <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                      <span className="text-sm font-medium text-foreground">API Key</span>
                      <div className="flex items-center gap-2">
                        <code className="text-sm text-muted-foreground font-mono">{maskedKey}</code>
                        {apiKey && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={handleCopyApiKey}
                            title="Copy API key"
                          >
                            {copied ? (
                              <Check className="h-3.5 w-3.5 text-green-500" />
                            ) : (
                              <Copy className="h-3.5 w-3.5" />
                            )}
                          </Button>
                        )}
                      </div>
                    </div>

                    <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                      <span className="text-sm font-medium text-foreground">API Status</span>
                      {health ? (
                        <Badge
                          className={health.status === 'up' ? 'gradient-success border-0' : 'bg-destructive border-0'}
                        >
                          {health.status === 'up' ? 'Connected' : health.status}
                        </Badge>
                      ) : (
                        <Badge variant="outline">Checking...</Badge>
                      )}
                    </div>

                    {health?.version && (
                      <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                        <span className="text-sm font-medium text-foreground">API Version</span>
                        <code className="text-sm text-muted-foreground">{health.version}</code>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Theme Settings */}
                <Card className="border-border elevation-md">
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Moon className="h-5 w-5 text-primary dark:hidden" />
                      <Sun className="h-5 w-5 text-primary hidden dark:block" />
                      <CardTitle>Appearance</CardTitle>
                    </div>
                    <CardDescription>Customize the look and feel of the interface</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                      <div>
                        <span className="text-sm font-medium text-foreground block">Theme</span>
                        <span className="text-xs text-muted-foreground">Toggle between light and dark mode</span>
                      </div>
                      <ThemeToggle />
                    </div>

                    <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                      <span className="text-sm font-medium text-foreground">Primary Color</span>
                      <div className="flex items-center gap-2">
                        <div className="h-6 w-6 rounded-full gradient-primary border-2 border-border"></div>
                        <code className="text-sm text-muted-foreground">Purple</code>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* About */}
                <Card className="border-border elevation-md">
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <Info className="h-5 w-5 text-primary" />
                      <CardTitle>About</CardTitle>
                    </div>
                    <CardDescription>Information about Omni</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                      <span className="text-sm font-medium text-foreground">Application</span>
                      <span className="text-sm text-muted-foreground">Omni</span>
                    </div>

                    {health?.timestamp && (
                      <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                        <span className="text-sm font-medium text-foreground">Last API Check</span>
                        <span className="text-sm text-muted-foreground">{formatDateTime(health.timestamp)}</span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Providers Tab */}
              <TabsContent value="providers" className="space-y-6">
                <ProviderList />
              </TabsContent>

              {/* System Tab */}
              <TabsContent value="system" className="space-y-6">
                {/* Database Configuration Section */}
                <DatabaseConfigSection />

                {settingsLoading ? (
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
                            {category === 'security' && 'Security and authentication settings'}
                          </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          {categorySettings.map((setting: GlobalSetting) => (
                            <div key={setting.key} className="p-4 bg-muted rounded-lg border border-border space-y-2">
                              <div className="flex items-start justify-between gap-4">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <Label className="text-sm font-semibold">{setting.key}</Label>
                                    <Badge variant="outline" className="text-xs">
                                      {setting.value_type}
                                    </Badge>
                                    {setting.is_secret && (
                                      <Badge className="text-xs gradient-primary border-0">Secret</Badge>
                                    )}
                                  </div>
                                  {setting.description && (
                                    <p className="text-xs text-muted-foreground mb-2">{setting.description}</p>
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
                                                {history.map((entry) => (
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
                    System settings are stored in the database and synchronized across all instances.
                    <br />
                    Changes to required settings may require application restart.
                  </p>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
