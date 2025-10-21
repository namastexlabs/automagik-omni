import { useState } from 'react'
import { Button } from '@/app/components/ui/button'
import { Input } from '@/app/components/ui/input'
import { Label } from '@/app/components/ui/label'

interface ReactionFormProps {
  onSend: (messageId: string, emoji: string) => Promise<void>
  loading: boolean
}

export function ReactionForm({ onSend, loading }: ReactionFormProps) {
  const [messageId, setMessageId] = useState('')
  const [emoji, setEmoji] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!messageId.trim() || !emoji.trim()) return

    await onSend(messageId, emoji)
    setMessageId('')
    setEmoji('')
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="messageId">Message ID</Label>
        <Input
          id="messageId"
          placeholder="Message ID to react to"
          value={messageId}
          onChange={(e) => setMessageId(e.target.value)}
          disabled={loading}
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="emoji">Emoji</Label>
        <Input
          id="emoji"
          placeholder="👍"
          value={emoji}
          onChange={(e) => setEmoji(e.target.value)}
          disabled={loading}
          required
          maxLength={2}
        />
        <p className="text-xs text-zinc-500">Enter a single emoji character</p>
      </div>

      <Button type="submit" disabled={loading || !messageId.trim() || !emoji.trim()}>
        {loading ? 'Sending...' : 'Send Reaction'}
      </Button>
    </form>
  )
}
