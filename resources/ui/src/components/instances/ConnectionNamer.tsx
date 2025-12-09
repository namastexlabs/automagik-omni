import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { MessageCircle, ArrowLeft, ArrowRight } from 'lucide-react';
import type { Platform } from './PlatformSelector';

// Discord icon as SVG
const DiscordIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
  </svg>
);

// Normalize instance name: remove spaces, convert to lowercase, replace with hyphens
function normalizeInstanceName(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-_]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

interface ConnectionNamerProps {
  platform: Platform;
  initialName?: string;
  onBack: () => void;
  onNext: (name: string) => void;
}

export function ConnectionNamer({ platform, initialName = '', onBack, onNext }: ConnectionNamerProps) {
  const [name, setName] = useState(initialName);
  const [normalizedName, setNormalizedName] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Generate default name based on platform
  useEffect(() => {
    if (!initialName) {
      const defaultName = platform === 'whatsapp' ? 'my-whatsapp' : 'my-discord';
      setName(defaultName);
      setNormalizedName(defaultName);
    }
  }, [platform, initialName]);

  const handleNameChange = (value: string) => {
    setName(value);
    const normalized = normalizeInstanceName(value);
    setNormalizedName(normalized);
    setError(null);
  };

  const handleNext = () => {
    if (!normalizedName) {
      setError('Please enter a valid connection name');
      return;
    }
    if (normalizedName.length < 2) {
      setError('Name must be at least 2 characters');
      return;
    }
    onNext(normalizedName);
  };

  const platformConfig = {
    whatsapp: {
      icon: <MessageCircle className="h-6 w-6 text-white" />,
      color: 'bg-[#25D366]',
      label: 'WhatsApp',
    },
    discord: {
      icon: <DiscordIcon className="h-6 w-6 text-white" />,
      color: 'bg-[#5865F2]',
      label: 'Discord',
    },
  };

  const config = platformConfig[platform];

  return (
    <div className="space-y-6">
      {/* Header with platform icon */}
      <div className="text-center space-y-4">
        <div className={`h-14 w-14 rounded-2xl ${config.color} flex items-center justify-center mx-auto`}>
          {config.icon}
        </div>
        <div>
          <h2 className="text-xl font-semibold text-foreground">Name Your {config.label} Connection</h2>
          <p className="text-sm text-muted-foreground mt-1">Give it a friendly name to identify it later</p>
        </div>
      </div>

      {/* Name Input */}
      <div className="space-y-3">
        <Label htmlFor="connection-name" className="text-sm font-medium">
          Connection Name
        </Label>
        <Input
          id="connection-name"
          value={name}
          onChange={(e) => handleNameChange(e.target.value)}
          placeholder={`my-${platform}`}
          className="text-center text-lg"
          data-testid="connection-name"
          autoFocus
          onKeyDown={(e) => e.key === 'Enter' && handleNext()}
        />
        {name !== normalizedName && normalizedName && (
          <p className="text-xs text-muted-foreground text-center">
            Will be saved as: <span className="font-mono font-medium">{normalizedName}</span>
          </p>
        )}
        {error && <p className="text-xs text-destructive text-center">{error}</p>}
      </div>

      {/* Navigation */}
      <div className="flex gap-3 pt-2">
        <Button variant="outline" onClick={onBack} className="flex-1">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <Button onClick={handleNext} className="flex-1 gradient-primary" data-testid="next-button">
          Next
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </div>
    </div>
  );
}
