import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { api } from '@/lib';
import type { AccessRule, AccessRuleType, InstanceConfig } from '@/lib';
import { Shield, Plus, Trash2, Loader2, Phone, Globe, Filter } from 'lucide-react';

export default function AccessRules() {
  const queryClient = useQueryClient();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [filterType, setFilterType] = useState<AccessRuleType | 'all'>('all');
  const [filterInstance, setFilterInstance] = useState<string>('all');

  // Form state
  const [newRule, setNewRule] = useState({
    phone_number: '',
    rule_type: 'allow' as AccessRuleType,
    instance_name: '',
  });

  // Fetch rules
  const {
    data: rules,
    isLoading: rulesLoading,
    error: rulesError,
  } = useQuery({
    queryKey: ['access-rules', filterType, filterInstance],
    queryFn: () =>
      api.accessRules.list({
        rule_type: filterType === 'all' ? undefined : filterType,
        instance_name: filterInstance === 'all' ? undefined : filterInstance,
      }),
  });

  // Fetch instances for dropdown
  const { data: instances } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list(),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: api.accessRules.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['access-rules'] });
      toast.success('Access rule created');
      setIsCreateDialogOpen(false);
      setNewRule({ phone_number: '', rule_type: 'allow', instance_name: '' });
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to create rule');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: api.accessRules.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['access-rules'] });
      toast.success('Access rule deleted');
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to delete rule');
    },
  });

  const handleCreateRule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRule.phone_number.trim()) {
      toast.error('Phone number is required');
      return;
    }
    createMutation.mutate({
      phone_number: newRule.phone_number.trim(),
      rule_type: newRule.rule_type,
      instance_name: newRule.instance_name || undefined,
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="Access Rules"
          subtitle="Manage allow and block rules for phone numbers"
          icon={<Shield className="h-6 w-6 text-primary" />}
          actions={
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Rule
                </Button>
              </DialogTrigger>
              <DialogContent>
                <form onSubmit={handleCreateRule}>
                  <DialogHeader>
                    <DialogTitle>Create Access Rule</DialogTitle>
                    <DialogDescription>
                      Add a new allow or block rule for a phone number
                    </DialogDescription>
                  </DialogHeader>

                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="phone_number">Phone Number</Label>
                      <Input
                        id="phone_number"
                        value={newRule.phone_number}
                        onChange={(e) => setNewRule({ ...newRule, phone_number: e.target.value })}
                        placeholder="+1234567890 or +1* for prefix"
                        disabled={createMutation.isPending}
                      />
                      <p className="text-xs text-muted-foreground">
                        E.164 format. Use trailing * for prefix matching (e.g., +1* matches all US numbers)
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="rule_type">Rule Type</Label>
                      <Select
                        value={newRule.rule_type}
                        onValueChange={(value: AccessRuleType) =>
                          setNewRule({ ...newRule, rule_type: value })
                        }
                        disabled={createMutation.isPending}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="allow">Allow</SelectItem>
                          <SelectItem value="block">Block</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="instance_name">Scope</Label>
                      <Select
                        value={newRule.instance_name || 'global'}
                        onValueChange={(value) =>
                          setNewRule({ ...newRule, instance_name: value === 'global' ? '' : value })
                        }
                        disabled={createMutation.isPending}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="global">
                            <div className="flex items-center gap-2">
                              <Globe className="h-4 w-4" />
                              Global (all instances)
                            </div>
                          </SelectItem>
                          {instances?.map((instance: InstanceConfig) => (
                            <SelectItem key={instance.name} value={instance.name}>
                              {instance.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground">
                        Global rules apply to all instances. Instance-specific rules override global rules.
                      </p>
                    </div>
                  </div>

                  <DialogFooter>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setIsCreateDialogOpen(false)}
                      disabled={createMutation.isPending}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" disabled={createMutation.isPending}>
                      {createMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Creating...
                        </>
                      ) : (
                        'Create Rule'
                      )}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          }
        />

        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 space-y-6 animate-fade-in">
            {/* Filters */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <CardTitle className="text-sm font-medium">Filters</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4">
                  <div className="w-40">
                    <Label className="text-xs text-muted-foreground mb-1 block">Rule Type</Label>
                    <Select
                      value={filterType}
                      onValueChange={(value) => setFilterType(value as AccessRuleType | 'all')}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Types</SelectItem>
                        <SelectItem value="allow">Allow</SelectItem>
                        <SelectItem value="block">Block</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="w-48">
                    <Label className="text-xs text-muted-foreground mb-1 block">Instance</Label>
                    <Select value={filterInstance} onValueChange={setFilterInstance}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Instances</SelectItem>
                        {instances?.map((instance: InstanceConfig) => (
                          <SelectItem key={instance.name} value={instance.name}>
                            {instance.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Rules Table */}
            <Card>
              <CardHeader>
                <CardTitle>Access Rules</CardTitle>
                <CardDescription>
                  {rules?.length ?? 0} rule{rules?.length !== 1 ? 's' : ''} configured
                </CardDescription>
              </CardHeader>
              <CardContent>
                {rulesLoading ? (
                  <div className="space-y-3">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                ) : rulesError ? (
                  <div className="text-center py-8 text-destructive">
                    Failed to load rules: {rulesError instanceof Error ? rulesError.message : 'Unknown error'}
                  </div>
                ) : rules?.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Shield className="h-12 w-12 mx-auto mb-3 opacity-30" />
                    <p>No access rules configured</p>
                    <p className="text-sm mt-1">Click "Add Rule" to create your first rule</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Phone Number</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Scope</TableHead>
                        <TableHead>Created</TableHead>
                        <TableHead className="w-16"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rules?.map((rule: AccessRule) => (
                        <TableRow key={rule.id}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Phone className="h-4 w-4 text-muted-foreground" />
                              <code className="text-sm">{rule.phone_number}</code>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge
                              className={
                                rule.rule_type === 'allow'
                                  ? 'gradient-success border-0'
                                  : 'bg-destructive border-0'
                              }
                            >
                              {rule.rule_type}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {rule.instance_name ? (
                              <Badge variant="outline">{rule.instance_name}</Badge>
                            ) : (
                              <div className="flex items-center gap-1 text-muted-foreground">
                                <Globe className="h-3 w-3" />
                                <span className="text-xs">Global</span>
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm">
                            {formatDate(rule.created_at)}
                          </TableCell>
                          <TableCell>
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Delete Access Rule</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Are you sure you want to delete the {rule.rule_type} rule for{' '}
                                    <code className="bg-muted px-1 rounded">{rule.phone_number}</code>?
                                    This action cannot be undone.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => deleteMutation.mutate(rule.id)}
                                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                  >
                                    Delete
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
