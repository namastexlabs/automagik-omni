import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/app/components/ui/dialog'
import { Button } from '@/app/components/ui/button'
import { Input } from '@/app/components/ui/input'
import { Label } from '@/app/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/app/components/ui/select'
import { Switch } from '@/app/components/ui/switch'
import { MessageSquareText } from 'lucide-react'
import { useConveyor } from '@/app/hooks/use-conveyor'

const createInstanceSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  channel_type: z.enum(['whatsapp', 'discord']),
  evolution_url: z.string().url('Must be a valid URL').optional().or(z.literal('')),
  evolution_key: z.string().optional(),
  discord_bot_token: z.string().optional(),
  discord_guild_id: z.string().optional(),
  agent_api_url: z.string().url('Must be a valid URL'),
  agent_api_key: z.string().optional(),
  agent_timeout: z.number().min(1000).max(300000).optional(),
  default_agent: z.string().optional(),
  enable_auto_split: z.boolean().optional(),
})

type CreateInstanceFormData = z.infer<typeof createInstanceSchema>

interface CreateInstanceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: () => void
}

export function CreateInstanceDialog({ open, onOpenChange, onCreated }: CreateInstanceDialogProps) {
  const { omni } = useConveyor()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [channelType, setChannelType] = useState<'whatsapp' | 'discord'>('whatsapp')

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<CreateInstanceFormData>({
    resolver: zodResolver(createInstanceSchema),
    defaultValues: {
      channel_type: 'whatsapp',
      evolution_url: 'http://localhost:8080',
      evolution_key: 'namastex888',
      agent_api_url: 'http://localhost:8886',
      agent_api_key: 'hive_key_placeholder',
      default_agent: 'template-agent',
      agent_timeout: 30000,
      enable_auto_split: true,
    },
  })

  const onSubmit = async (data: CreateInstanceFormData) => {
    try {
      setLoading(true)
      setError(null)

      const payload: any = {
        name: data.name,
        channel_type: data.channel_type,
        agent_api_url: data.agent_api_url,
        agent_api_key: data.agent_api_key || '',
        agent_timeout: data.agent_timeout || 30000,
        is_default: false,
        enable_auto_split: data.enable_auto_split ?? true,
      }

      if (data.default_agent) {
        payload.default_agent = data.default_agent
      }

      if (data.channel_type === 'whatsapp') {
        if (data.evolution_url) payload.evolution_url = data.evolution_url
        if (data.evolution_key) payload.evolution_key = data.evolution_key
        payload.whatsapp_instance = data.name
      } else if (data.channel_type === 'discord') {
        if (data.discord_bot_token) payload.discord_bot_token = data.discord_bot_token
        if (data.discord_guild_id) payload.discord_guild_id = data.discord_guild_id
      }

      await omni.createInstance(payload)
      reset()
      onCreated()
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create instance')
    } finally {
      setLoading(false)
    }
  }

  const handleChannelTypeChange = (value: string) => {
    setChannelType(value as 'whatsapp' | 'discord')
    setValue('channel_type', value as 'whatsapp' | 'discord')
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Instance</DialogTitle>
          <DialogDescription>
            Configure a new messaging instance for WhatsApp or Discord
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {error && (
            <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="name">Instance Name *</Label>
            <Input
              id="name"
              placeholder="my-instance"
              {...register('name')}
              className="bg-zinc-800 border-zinc-700 text-white"
            />
            {errors.name && <p className="text-sm text-red-400">{errors.name.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="channel_type">Channel Type *</Label>
            <Select value={channelType} onValueChange={handleChannelTypeChange}>
              <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
                <SelectValue placeholder="Select channel type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="whatsapp">WhatsApp</SelectItem>
                <SelectItem value="discord">Discord</SelectItem>
              </SelectContent>
            </Select>
            {errors.channel_type && (
              <p className="text-sm text-red-400">{errors.channel_type.message}</p>
            )}
          </div>

          {channelType === 'whatsapp' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="evolution_url">Evolution API URL</Label>
                <Input
                  id="evolution_url"
                  placeholder="https://evolution-api.example.com"
                  {...register('evolution_url')}
                  className="bg-zinc-800 border-zinc-700 text-white"
                />
                {errors.evolution_url && (
                  <p className="text-sm text-red-400">{errors.evolution_url.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="evolution_key">Evolution API Key</Label>
                <Input
                  id="evolution_key"
                  type="password"
                  placeholder="API Key"
                  {...register('evolution_key')}
                  className="bg-zinc-800 border-zinc-700 text-white"
                />
              </div>
            </>
          )}

          {channelType === 'discord' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="discord_bot_token">Discord Bot Token</Label>
                <Input
                  id="discord_bot_token"
                  type="password"
                  placeholder="Bot Token"
                  {...register('discord_bot_token')}
                  className="bg-zinc-800 border-zinc-700 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="discord_guild_id">Discord Guild ID</Label>
                <Input
                  id="discord_guild_id"
                  placeholder="Guild ID"
                  {...register('discord_guild_id')}
                  className="bg-zinc-800 border-zinc-700 text-white"
                />
              </div>
            </>
          )}

          <div className="space-y-2">
            <Label htmlFor="agent_api_url">Agent API URL *</Label>
            <Input
              id="agent_api_url"
              placeholder="https://agent-api.example.com"
              {...register('agent_api_url')}
              className="bg-zinc-800 border-zinc-700 text-white"
            />
            {errors.agent_api_url && (
              <p className="text-sm text-red-400">{errors.agent_api_url.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="agent_api_key">Agent API Key</Label>
            <Input
              id="agent_api_key"
              type="password"
              placeholder="API Key"
              {...register('agent_api_key')}
              className="bg-zinc-800 border-zinc-700 text-white"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="default_agent">Default Agent</Label>
            <Input
              id="default_agent"
              placeholder="agent-name"
              {...register('default_agent')}
              className="bg-zinc-800 border-zinc-700 text-white"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="agent_timeout">Agent Timeout (ms)</Label>
            <Input
              id="agent_timeout"
              type="number"
              placeholder="30000"
              {...register('agent_timeout', { valueAsNumber: true })}
              className="bg-zinc-800 border-zinc-700 text-white"
            />
            {errors.agent_timeout && (
              <p className="text-sm text-red-400">{errors.agent_timeout.message}</p>
            )}
          </div>

          <div className="space-y-3 border border-zinc-700 rounded-lg p-4 bg-zinc-800/50">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <MessageSquareText className="h-4 w-4 text-zinc-400" />
                <Label htmlFor="enable_auto_split" className="text-sm font-medium cursor-pointer">
                  Auto-split messages
                </Label>
              </div>
              <Switch
                id="enable_auto_split"
                checked={watch('enable_auto_split') ?? true}
                onCheckedChange={(checked) => setValue('enable_auto_split', checked)}
              />
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Split long messages at paragraph breaks (double newline).
              <br />
              <span className="text-zinc-500">
                WhatsApp: Controls splitting behavior. Discord: Preferred split point (2000-char limit always applies).
              </span>
            </p>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Instance'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
