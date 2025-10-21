import { useState } from 'react'
import { Button } from '@/app/components/ui/button'
import { Input } from '@/app/components/ui/input'
import { Label } from '@/app/components/ui/label'

interface AudioMessageFormProps {
  onSend: (audioUrl: string) => Promise<void>
  loading: boolean
}

export function AudioMessageForm({ onSend, loading }: AudioMessageFormProps) {
  const [audioUrl, setAudioUrl] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!audioUrl.trim()) return

    await onSend(audioUrl)
    setAudioUrl('')
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="audioUrl">Audio URL</Label>
        <Input
          id="audioUrl"
          placeholder="https://example.com/audio.mp3"
          value={audioUrl}
          onChange={(e) => setAudioUrl(e.target.value)}
          disabled={loading}
          required
          type="url"
        />
      </div>

      <Button type="submit" disabled={loading || !audioUrl.trim()}>
        {loading ? 'Sending...' : 'Send Audio'}
      </Button>
    </form>
  )
}
