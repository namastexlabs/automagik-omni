import { useState, useEffect } from 'react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import { useInstanceStore } from '@/lib/store/instance-store'
import { Button } from '@/app/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/app/components/ui/card'
import { Input } from '@/app/components/ui/input'
import { Label } from '@/app/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/app/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs'
import { TextMessageForm } from '@/app/components/messages/TextMessageForm'
import { MediaMessageForm } from '@/app/components/messages/MediaMessageForm'
import { AudioMessageForm } from '@/app/components/messages/AudioMessageForm'
import { ReactionForm } from '@/app/components/messages/ReactionForm'
import { RecentMessagesList } from '@/app/components/messages/RecentMessagesList'
import { getErrorMessage, isBackendError } from '@/lib/utils/error'
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
      const errorMessage = getErrorMessage(err)
      setError(errorMessage)
      console.error('Failed to load instances:', err)
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
      const errorMessage = getErrorMessage(err)
      setError(errorMessage)
      console.error('Failed to send message:', err)
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
      const errorMessage = getErrorMessage(err)
      setError(errorMessage)
      console.error('Failed to send media:', err)
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
      const errorMessage = getErrorMessage(err)
      setError(errorMessage)
      console.error('Failed to send audio:', err)
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
      const errorMessage = getErrorMessage(err)
      setError(errorMessage)
      console.error('Failed to send reaction:', err)
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
          <Card className="border-red-500 bg-red-900/20 mb-6">
            <CardHeader>
              <CardTitle className="text-red-400 text-xl flex items-center gap-2">
                <span className="text-2xl">⚠️</span>
                Operation Failed
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-red-200">{useInstanceStore.getState().error}</p>
              <div className="flex items-center gap-3">
                <Button onClick={loadInstances} variant="outline" size="sm">
                  Retry Loading Instances
                </Button>
                <Button onClick={() => setError(null)} variant="ghost" size="sm">
                  Dismiss
                </Button>
              </div>
              {isBackendError(new Error(useInstanceStore.getState().error || '')) && (
                <p className="text-sm text-zinc-400 mt-2">
                  💡 <strong>Tip:</strong> Go to Dashboard and start the backend service
                </p>
              )}
            </CardContent>
          </Card>
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
