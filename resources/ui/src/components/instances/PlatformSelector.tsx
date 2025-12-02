import { Card, CardContent } from '@/components/ui/card';
import { MessageCircle } from 'lucide-react';

// Discord icon as SVG (lucide doesn't have Discord)
const DiscordIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
  </svg>
);

export type Platform = 'whatsapp' | 'discord';

interface PlatformSelectorProps {
  onSelect: (platform: Platform) => void;
}

export function PlatformSelector({ onSelect }: PlatformSelectorProps) {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl font-semibold text-foreground">Choose Your Platform</h2>
        <p className="text-sm text-muted-foreground">
          Select the messaging platform you want to connect
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* WhatsApp Card */}
        <Card
          className="cursor-pointer border-2 border-border hover:border-[#25D366] hover:bg-[#25D366]/5 transition-all duration-200 group"
          onClick={() => onSelect('whatsapp')}
          data-testid="platform-whatsapp"
        >
          <CardContent className="pt-6 pb-6 flex flex-col items-center text-center space-y-4">
            <div className="h-16 w-16 rounded-2xl bg-[#25D366] flex items-center justify-center group-hover:scale-110 transition-transform">
              <MessageCircle className="h-8 w-8 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">WhatsApp</h3>
              <p className="text-xs text-muted-foreground mt-1">
                Connect via QR code scan
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Discord Card */}
        <Card
          className="cursor-pointer border-2 border-border hover:border-[#5865F2] hover:bg-[#5865F2]/5 transition-all duration-200 group"
          onClick={() => onSelect('discord')}
          data-testid="platform-discord"
        >
          <CardContent className="pt-6 pb-6 flex flex-col items-center text-center space-y-4">
            <div className="h-16 w-16 rounded-2xl bg-[#5865F2] flex items-center justify-center group-hover:scale-110 transition-transform">
              <DiscordIcon className="h-8 w-8 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Discord</h3>
              <p className="text-xs text-muted-foreground mt-1">
                Connect with bot token
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
