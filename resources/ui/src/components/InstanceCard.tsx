import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { QrCode, Eye, Settings as SettingsIcon, Trash2, Loader2, AlertTriangle } from 'lucide-react';
import type { InstanceConfig } from '@/lib/types';

interface InstanceCardProps {
  instance: InstanceConfig;
  onShowQR?: (instanceName: string) => void;
  onEdit?: (instance: InstanceConfig) => void;
  onDelete?: (instanceName: string) => void;
  isDeleting?: boolean;
}

export function InstanceCard({
  instance,
  onShowQR,
  onEdit,
  onDelete,
  isDeleting
}: InstanceCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const handleDeleteClick = () => {
    setShowDeleteDialog(true);
  };

  const handleConfirmDelete = () => {
    if (onDelete) {
      onDelete(instance.name);
    }
    setShowDeleteDialog(false);
  };

  const getStatusBadge = () => {
    // For WhatsApp, check evolution_status
    if (instance.channel_type === 'whatsapp') {
      const state = instance.evolution_status?.state?.toLowerCase();

      // Check evolution_status.state or evolution_status.status
      const statusStr = instance.evolution_status?.status?.toLowerCase();

      // Also check if evolution_status has raw data indicating connection
      const evolutionData: any = instance.evolution_status;
      const isOpen = state === 'open' ||
                     statusStr === 'connected' ||
                     evolutionData?.instance?.state === 'open';

      if (isOpen) {
        return <Badge className="gradient-success border-0">Connected</Badge>;
      } else if (state === 'close' || state === 'disconnected' || statusStr === 'disconnected') {
        return <Badge className="gradient-danger border-0">Disconnected</Badge>;
      } else if (state === 'connecting' || statusStr === 'connecting') {
        return <Badge className="gradient-warning border-0">Connecting</Badge>;
      } else if (instance.is_active && !instance.evolution_status) {
        // Active but status not fetched yet - show as pending
        return <Badge className="gradient-warning border-0">Checking...</Badge>;
      } else {
        // New instance or not connected yet
        return <Badge className="gradient-warning border-0">Not Connected</Badge>;
      }
    }

    // For Discord or other channels
    if (instance.is_active) {
      return <Badge className="gradient-success border-0">Active</Badge>;
    } else {
      return <Badge variant="outline">Inactive</Badge>;
    }
  };

  const isWhatsAppConnected = () => {
    const state = instance.evolution_status?.state?.toLowerCase();
    const statusStr = (instance.evolution_status as any)?.status?.toLowerCase();
    const evolutionData: any = instance.evolution_status;

    return state === 'open' ||
           statusStr === 'connected' ||
           evolutionData?.instance?.state === 'open';
  };

  return (
    <Card className="group border-border elevation-md hover:elevation-lg transition-all hover-lift overflow-hidden bg-card">
      <CardHeader className="relative">
        <div className="flex justify-between items-start">
          <div className="flex-1 space-y-1">
            <CardTitle className="text-xl flex items-center gap-2 text-foreground">
              {instance.name}
              {instance.is_default && (
                <Badge className="gradient-primary text-xs border-0">Default</Badge>
              )}
            </CardTitle>
            <CardDescription className="capitalize flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary"></span>
              {instance.channel_type}
            </CardDescription>
          </div>
          {getStatusBadge()}
        </div>
      </CardHeader>

      <CardContent className="relative space-y-4">
        <div className="space-y-2 text-sm">
          {instance.profile_name && (
            <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
              <span className="text-muted-foreground">Profile</span>
              <span className="font-medium text-foreground">{instance.profile_name}</span>
            </div>
          )}
          {instance.automagik_instance_name && (
            <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
              <span className="text-muted-foreground">Agent</span>
              <span className="font-medium text-foreground">{instance.automagik_instance_name}</span>
            </div>
          )}
          <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
            <span className="text-muted-foreground">Status</span>
            <span className="font-medium text-foreground">
              {instance.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>

        <div className="flex gap-2 pt-2">
          {/* WhatsApp QR/View buttons */}
          {instance.channel_type === 'whatsapp' && onShowQR && (
            <>
              {/* Show Scan QR if not connected */}
              {!isWhatsAppConnected() && (
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 hover:bg-success/10 hover:text-success hover:border-success transition-colors"
                  onClick={() => onShowQR(instance.name)}
                >
                  <QrCode className="h-4 w-4 mr-1" />
                  Scan QR
                </Button>
              )}
              {/* Show View when connected */}
              {isWhatsAppConnected() && (
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 hover:bg-primary/10 hover:text-primary hover:border-primary transition-colors"
                  onClick={() => onShowQR(instance.name)}
                >
                  <Eye className="h-4 w-4 mr-1" />
                  View
                </Button>
              )}
            </>
          )}

          {/* Manage button */}
          {onEdit && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1 hover:bg-primary/10 hover:text-primary hover:border-primary transition-colors"
              onClick={() => onEdit(instance)}
            >
              <SettingsIcon className="h-4 w-4 mr-1" />
              Manage
            </Button>
          )}

          {/* Delete button */}
          {onDelete && (
            <Button
              variant="outline"
              size="sm"
              className="hover:bg-destructive/10 hover:text-destructive hover:border-destructive transition-colors"
              onClick={handleDeleteClick}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>
      </CardContent>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Delete Instance
            </AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <span className="font-semibold text-foreground">"{instance.name}"</span>?
              <br /><br />
              This action cannot be undone. All instance data, configurations, and settings will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete Instance
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
