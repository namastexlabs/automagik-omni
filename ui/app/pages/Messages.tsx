import { useState, useEffect } from 'react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import { useInstanceStore } from '@/lib/store/instance-store'
import { Button } from '@/app/components/ui/button'
import { Input } from '@/app/components/ui/input'
import { Label } from '@/app/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/app/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs'
import { TextMessageForm } from '@/app/components/messages/TextMessageForm'
import { MediaMessageForm } from '@/app/components/messages/MediaMessageForm'
import { AudioMessageForm } from '@/app/components/messages/AudioMessageForm'
import { ReactionForm } from '@/app/components/messages/ReactionForm'
import { RecentMessagesList } from '@/app/components/messages/RecentMessagesList'
import type { Message } from '@/lib/conveyor/schemas/omni-schema'

export default function Messages() {
  const { omni } = useConveyor()
  const { instances, selectedInstance, setInstances, setSelectedInstance, setLoading, setError } = useInstanceStore()
  
  const [phone, setPhone] = useState('')
  const [phoneError, setPhoneError] = useState('')
  const [sending, setSending] = useState(false)
  const [recentMessages, setRecentMessages] = useState<Message[]>([])
  const [successMessage, setSuccessMessage] = useState('')

  // Load instances on mount
  useEffect(() => {
    loadInstances()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadInstances = async () => {
    try {
      setLoading(true)
      setError(null)
      const instancesList = await omni.listInstances()
      setInstances(instancesList)
      
      // Auto-select first instance if none selected
      if (!selectedInstance && instancesList.length > 0) {
        setSelectedInstance(instancesList[0])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load instances')
    } finally {
      setLoading(false)
    }
  }

  const validatePhone = (phoneNumber: string): boolean => {
    // Simple phone validation: +[country code][number]
    const phoneRegex = /^\+?[1-9]\d{1,14}$/
    if (!phoneRegex.test(phoneNumber)) {
      setPhoneError('Invalid phone number format (e.g., +1234567890)')
      return false
    }
    setPhoneError('')
    return true
  }

  const showSuccess = (message: string) => {
    setSuccessMessage(message)
    setTimeout(() => setSuccessMessage(''), 3000)
  }

  const addToRecentMessages = (message: Message) => {
    setRecentMessages((prev) => [message, ...prev].slice(0, 10))
  }

  const handleSendText = async (message: string, quotedMessageId?: string) => {
    if (!selectedInstance) {
      setError('Please select an instance')
      return
    }
    if (!validatePhone(phone)) return

    try {
      setSending(true)
      const result = await omni.sendTextMessage(
        selectedInstance.name,
        phone,
        message,
        quotedMessageId
      )
      addToRecentMessages(result)
      showSuccess('Text message sent successfully!')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  const handleSendMedia = async (
    mediaUrl: string,
    mediaType: 'image' | 'video' | 'document',
    caption?: string
  ) => {
    if (!selectedInstance) {
      setError('Please select an instance')
      return
    }
    if (!validatePhone(phone)) return

    try {
      setSending(true)
      const result = await omni.sendMediaMessage(
        selectedInstance.name,
        phone,
        mediaUrl,
        mediaType,
        caption
      )
      addToRecentMessages(result)
      showSuccess('Media message sent successfully!')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send media')
    } finally {
      setSending(false)
    }
  }

  const handleSendAudio = async (audioUrl: string) => {
    if (!selectedInstance) {
      setError('Please select an instance')
      return
    }
    if (!validatePhone(phone)) return

    try {
      setSending(true)
      const result = await omni.sendAudioMessage(selectedInstance.name, phone, audioUrl)
      addToRecentMessages(result)
      showSuccess('Audio message sent successfully!')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send audio')
    } finally {
      setSending(false)
    }
  }

  const handleSendReaction = async (messageId: string, emoji: string) => {
    if (!selectedInstance) {
      setError('Please select an instance')
      return
    }
    if (!validatePhone(phone)) return

    try {
      setSending(true)
      const result = await omni.sendReaction(selectedInstance.name, phone, messageId, emoji)
      addToRecentMessages(result)
      showSuccess('Reaction sent successfully!')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reaction')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="h-screen bg-black text-white overflow-auto">
      <div className="max-w-6xl mx-auto p-8">
        <h1 className="text-4xl font-bold mb-8">Messages</h1>

        {/* Success Message */}
        {successMessage && (
          <div className="bg-green-900/50 border border-green-500 text-green-200 px-4 py-3 rounded mb-4">
            {successMessage}
          </div>
        )}

        {/* Error Message */}
        {useInstanceStore.getState().error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-4">
            <div className="flex justify-between items-start">
              <span>{useInstanceStore.getState().error}</span>
              <button
                onClick={() => setError(null)}
                className="text-red-200 hover:text-red-100"
              >
                ×
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Message Composer */}
          <div className="lg:col-span-2">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Compose Message</h2>

              {/* Instance Selector */}
              <div className="space-y-2 mb-4">
                <Label htmlFor="instance">Instance</Label>
                <Select
                  value={selectedInstance?.name || ''}
                  onValueChange={(name) => {
                    const instance = instances.find((i) => i.name === name)
                    setSelectedInstance(instance || null)
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select an instance" />
                  </SelectTrigger>
                  <SelectContent>
                    {instances.length === 0 ? (
                      <div className="p-2 text-sm text-zinc-500">No instances available</div>
                    ) : (
                      instances.map((instance) => (
                        <SelectItem key={instance.id} value={instance.name}>
                          {instance.name} ({instance.channel_type})
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
                {instances.length === 0 && (
                  <Button onClick={loadInstances} variant="outline" className="w-full mt-2">
                    Refresh Instances
                  </Button>
                )}
              </div>

              {/* Recipient Phone */}
              <div className="space-y-2 mb-6">
                <Label htmlFor="phone">Recipient Phone Number</Label>
                <Input
                  id="phone"
                  placeholder="+1234567890"
                  value={phone}
                  onChange={(e) => {
                    setPhone(e.target.value)
                    setPhoneError('')
                  }}
                  disabled={sending}
                />
                {phoneError && (
                  <p className="text-xs text-red-400">{phoneError}</p>
                )}
                <p className="text-xs text-zinc-500">
                  Enter phone number with country code (e.g., +1234567890)
                </p>
              </div>

              {/* Message Type Tabs */}
              <Tabs defaultValue="text" className="w-full">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="text">Text</TabsTrigger>
                  <TabsTrigger value="media">Media</TabsTrigger>
                  <TabsTrigger value="audio">Audio</TabsTrigger>
                  <TabsTrigger value="reaction">Reaction</TabsTrigger>
                </TabsList>

                <TabsContent value="text">
                  <TextMessageForm onSend={handleSendText} loading={sending} />
                </TabsContent>

                <TabsContent value="media">
                  <MediaMessageForm onSend={handleSendMedia} loading={sending} />
                </TabsContent>

                <TabsContent value="audio">
                  <AudioMessageForm onSend={handleSendAudio} loading={sending} />
                </TabsContent>

                <TabsContent value="reaction">
                  <ReactionForm onSend={handleSendReaction} loading={sending} />
                </TabsContent>
              </Tabs>
            </div>
          </div>

          {/* Recent Messages */}
          <div className="lg:col-span-1">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Recent Messages</h2>
              <div className="max-h-[600px] overflow-y-auto">
                <RecentMessagesList messages={recentMessages} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
