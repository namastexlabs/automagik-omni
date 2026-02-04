import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib';
import { Eye, EyeOff, Save, Loader2, CheckCircle2, XCircle, Image, Mic, Sparkles, Volume2 } from 'lucide-react';

interface ApiKeyFieldProps {
  label: string;
  description: string;
  settingKey: string;
  currentValue: string | null;
  icon: React.ReactNode;
  placeholder?: string;
}

function ApiKeyField({ label, description, settingKey, currentValue, icon, placeholder }: ApiKeyFieldProps) {
  const queryClient = useQueryClient();
  const [value, setValue] = useState('');
  const [showValue, setShowValue] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const updateMutation = useMutation({
    mutationFn: (newValue: string) => api.settings.update(settingKey, { value: newValue }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      toast.success(`${label} updated successfully`);
      setIsEditing(false);
      setValue('');
    },
    onError: (err: Error) => {
      toast.error(`Failed to update ${label}: ${err.message}`);
    },
  });

  const handleSave = () => {
    if (!value.trim()) {
      toast.error('Please enter a value');
      return;
    }
    updateMutation.mutate(value);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setValue('');
  };

  const maskedValue = currentValue ? `${currentValue.substring(0, 8)}...${currentValue.slice(-4)}` : null;

  return (
    <div className="p-4 bg-muted rounded-lg border border-border space-y-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          {icon}
          <div>
            <Label className="text-sm font-medium">{label}</Label>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
        </div>
        {currentValue ? (
          <Badge variant="default" className="bg-green-500/10 text-green-600 border-green-500/20">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Configured
          </Badge>
        ) : (
          <Badge variant="outline" className="text-muted-foreground">
            <XCircle className="h-3 w-3 mr-1" />
            Not Set
          </Badge>
        )}
      </div>

      {isEditing ? (
        <div className="space-y-2">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                type={showValue ? 'text' : 'password'}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={placeholder || `Enter ${label}`}
                className="pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                onClick={() => setShowValue(!showValue)}
              >
                {showValue ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
            <Button onClick={handleSave} disabled={updateMutation.isPending} size="sm">
              {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            </Button>
            <Button variant="outline" onClick={handleCancel} size="sm">
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between">
          <code className="text-sm text-muted-foreground font-mono">
            {maskedValue || <span className="italic">Not configured</span>}
          </code>
          <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
            {currentValue ? 'Update' : 'Configure'}
          </Button>
        </div>
      )}
    </div>
  );
}

export function MediaProcessingSettings() {
  // Fetch settings
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.settings.list(),
  });

  const getSetting = (key: string): string | null => {
    const setting = settings?.find((s) => s.key === key);
    return setting?.value as string | null;
  };

  if (isLoading) {
    return (
      <Card className="border-border elevation-md">
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Image/Video Processing */}
      <Card className="border-border elevation-md">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Image className="h-5 w-5 text-primary" />
            <CardTitle>Image & Video Processing</CardTitle>
          </div>
          <CardDescription>Configure API keys for image description and video analysis</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ApiKeyField
            label="Google Gemini API Key"
            description="Primary provider for image/video description (gemini-2.5-flash)"
            settingKey="gemini_api_key"
            currentValue={getSetting('gemini_api_key')}
            icon={<Sparkles className="h-4 w-4 text-blue-500" />}
            placeholder="AIza..."
          />

          <ApiKeyField
            label="OpenAI API Key"
            description="Fallback for images when Gemini is unavailable (gpt-5-nano)"
            settingKey="openai_api_key"
            currentValue={getSetting('openai_api_key')}
            icon={<Sparkles className="h-4 w-4 text-green-500" />}
            placeholder="sk-..."
          />
        </CardContent>
      </Card>

      {/* Audio Processing */}
      <Card className="border-border elevation-md">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Mic className="h-5 w-5 text-primary" />
            <CardTitle>Audio Transcription</CardTitle>
          </div>
          <CardDescription>Configure API keys for audio transcription services</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ApiKeyField
            label="Groq API Key"
            description="Primary provider for audio transcription (whisper-large-v3-turbo, 216x real-time)"
            settingKey="groq_api_key"
            currentValue={getSetting('groq_api_key')}
            icon={<Mic className="h-4 w-4 text-orange-500" />}
            placeholder="gsk_..."
          />

          <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <p className="text-sm text-blue-600 dark:text-blue-400">
              <strong>Fallback:</strong> If Groq is unavailable, the system automatically falls back to OpenAI Whisper
              using the OpenAI API key configured above.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Audio Generation / Text-to-Speech */}
      <Card className="border-border elevation-md">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Volume2 className="h-5 w-5 text-primary" />
            <CardTitle>Audio Generation</CardTitle>
          </div>
          <CardDescription>Configure API keys for text-to-speech and audio generation</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ApiKeyField
            label="ElevenLabs API Key"
            description="Text-to-speech voice message generation for WhatsApp"
            settingKey="XI_API_KEY"
            currentValue={getSetting('XI_API_KEY')}
            icon={<Volume2 className="h-4 w-4 text-purple-500" />}
            placeholder="sk_..."
          />
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="border-border bg-muted/50">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">How Media Processing Works</p>
              <p className="text-xs text-muted-foreground">
                Process media attachments to extract text and generate audio. These are then available to your AI agents
                as context or for sending voice messages.
              </p>
              <ul className="text-xs text-muted-foreground mt-2 space-y-1">
                <li>
                  <strong>Images:</strong> Gemini → OpenAI fallback
                </li>
                <li>
                  <strong>Audio Transcription:</strong> Groq Whisper → OpenAI Whisper fallback
                </li>
                <li>
                  <strong>Audio Generation:</strong> ElevenLabs TTS for voice messages
                </li>
                <li>
                  <strong>Video:</strong> Gemini (extracts frames and audio)
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
