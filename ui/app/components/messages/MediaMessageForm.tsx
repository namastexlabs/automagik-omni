import { useState } from 'react'
import { Button } from '@/app/components/ui/button'
import { Input } from '@/app/components/ui/input'
import { Textarea } from '@/app/components/ui/textarea'
import { Label } from '@/app/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/app/components/ui/select'

interface MediaMessageFormProps {
  onSend: (mediaUrl: string, mediaType: 'image' | 'video' | 'document', caption?: string) => Promise<void>
  loading: boolean
}

export function MediaMessageForm({ onSend, loading }: MediaMessageFormProps) {
  const [mediaUrl, setMediaUrl] = useState('')
  const [mediaType, setMediaType] = useState<'image' | 'video' | 'document'>('image')
  const [caption, setCaption] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!mediaUrl.trim()) return

    await onSend(mediaUrl, mediaType, caption || undefined)
    setMediaUrl('')
    setCaption('')
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="mediaType">Media Type</Label>
        <Select value={mediaType} onValueChange={(value) => setMediaType(value as 'image' | 'video' | 'document')}>
          <SelectTrigger>
            <SelectValue placeholder="Select media type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="image">Image</SelectItem>
            <SelectItem value="video">Video</SelectItem>
            <SelectItem value="document">Document</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="mediaUrl">Media URL</Label>
        <Input
          id="mediaUrl"
          placeholder="https://example.com/media.jpg"
          value={mediaUrl}
          onChange={(e) => setMediaUrl(e.target.value)}
          disabled={loading}
          required
          type="url"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="caption">Caption (Optional)</Label>
        <Textarea
          id="caption"
          placeholder="Add a caption..."
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          disabled={loading}
        />
      </div>

      <Button type="submit" disabled={loading || !mediaUrl.trim()}>
        {loading ? 'Sending...' : 'Send Media'}
      </Button>
    </form>
  )
}
