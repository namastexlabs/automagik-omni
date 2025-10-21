import { useState } from 'react'
import { Button } from '@/app/components/ui/button'
import { Input } from '@/app/components/ui/input'
import { Textarea } from '@/app/components/ui/textarea'
import { Label } from '@/app/components/ui/label'

interface TextMessageFormProps {
  onSend: (message: string, quotedMessageId?: string) => Promise<void>
  loading: boolean
}

export function TextMessageForm({ onSend, loading }: TextMessageFormProps) {
  const [message, setMessage] = useState('')
  const [quotedMessageId, setQuotedMessageId] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim()) return

    await onSend(message, quotedMessageId || undefined)
    setMessage('')
    setQuotedMessageId('')
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="message">Message</Label>
        <Textarea
          id="message"
          placeholder="Type your message here..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="min-h-[120px]"
          disabled={loading}
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="quotedMessageId">Reply to Message ID (Optional)</Label>
        <Input
          id="quotedMessageId"
          placeholder="Message ID to reply to"
          value={quotedMessageId}
          onChange={(e) => setQuotedMessageId(e.target.value)}
          disabled={loading}
        />
      </div>

      <Button type="submit" disabled={loading || !message.trim()}>
        {loading ? 'Sending...' : 'Send Message'}
      </Button>
    </form>
  )
}
