# Chat Details Panel Enhancement - Implementation Summary

## Completed Backend Work

### 1. Message Schemas (`src/api/schemas/omni.py`)
✅ Added `OmniMessageType` enum with all message types (text, image, video, audio, document, sticker, contact, location, reaction, system, unknown)
✅ Added `OmniMessage` model with comprehensive fields for cross-channel messages
✅ Added `OmniMessagesResponse` for paginated message responses

### 2. Base Handler Interface (`src/channels/omni_base.py`)
✅ Added `get_messages()` abstract method to `OmniChannelHandler` base class
✅ Supports pagination with page/page_size and cursor-based pagination with before_message_id

### 3. Evolution API Client (`src/channels/whatsapp/omni_evolution_client.py`)
✅ Added `fetch_messages()` method to fetch messages from Evolution API
✅ Endpoint: `GET /chat/findMessages/{instance}/{chat_id}?limit=X`
✅ Includes client-side pagination support

### 4. Message Transformers (`src/services/omni_transformers.py`)
✅ Added `WhatsAppTransformer.message_to_omni()` - transforms WhatsApp messages
   - Parses all media types (image, video, audio, document, sticker)
   - Extracts media URLs, mime types, sizes, captions, thumbnails
   - Handles replies, forwards, reactions
✅ Added `DiscordTransformer.message_to_omni()` - transforms Discord messages
   - Parses attachments (images, videos, audio, documents)
   - Handles stickers, embeds, mentions, reactions
   - Preserves reply chains

### 5. WhatsApp Handler (`src/channels/handlers/whatsapp_chat_handler.py`)
✅ Implemented `get_messages()` method
✅ Fetches messages via Evolution API
✅ Transforms messages to Omni format
✅ Returns paginated results with total count

### 6. Discord Handler (`src/channels/handlers/discord_chat_handler.py`)
✅ Implemented `get_messages()` method
✅ Uses Discord.py `channel.history()` API
✅ Transforms messages to Omni format
✅ Supports cursor pagination with before parameter

### 7. API Endpoint (`src/api/routes/omni.py`)
✅ Added `/api/v1/omni/{instance_name}/chats/{chat_id}/messages` endpoint
✅ Query params: page, page_size, before_message_id
✅ Returns `OmniMessagesResponse` with messages, pagination info, errors

### 8. Frontend Schema (`ui/lib/conveyor/schemas/omni-schema.ts`)
✅ Updated `MessageSchema` to match backend `OmniMessage` model
✅ Added `MessagesResponseSchema` for API responses
✅ Full TypeScript types generated

## Remaining Frontend Work

### 9. API Client Method (PENDING)
**File:** `ui/lib/conveyor/api/omni-api.ts` or `ui/lib/main/omni-api-client.ts`

Add method:
```typescript
async getChatMessages(
  instanceName: string,
  chatId: string,
  options?: {
    page?: number
    pageSize?: number
    beforeMessageId?: string
  }
): Promise<MessagesResponse> {
  const params = new URLSearchParams()
  if (options?.page) params.set('page', options.page.toString())
  if (options?.pageSize) params.set('page_size', options.pageSize.toString())
  if (options?.beforeMessageId) params.set('before_message_id', options.beforeMessageId)

  const response = await fetch(
    `/api/v1/omni/${instanceName}/chats/${chatId}/messages?${params}`,
    { headers: { 'x-api-key': this.apiKey } }
  )
  return MessagesResponseSchema.parse(await response.json())
}
```

### 10. Enhanced ChatDetailsPanel Component (PENDING)
**File:** `ui/app/components/chats/ChatDetailsPanel.tsx`

**Required Changes:**
1. **State Management**
   - Add `messages` state for message list
   - Add `loading` state for fetch operations
   - Add `page` state for pagination
   - Add `hasMore` state for infinite scroll

2. **Message Fetching**
   ```typescript
   const fetchMessages = async () => {
     setLoading(true)
     try {
       const response = await omniApi.getChatMessages(
         chat.instance_name,
         chat.id,
         { page: 1, pageSize: 50 }
       )
       setMessages(response.messages)
       setHasMore(response.has_more)
     } catch (error) {
       console.error('Failed to fetch messages:', error)
     } finally {
       setLoading(false)
     }
   }

   useEffect(() => {
     if (chat) {
       fetchMessages()
     }
   }, [chat?.id])
   ```

3. **Message List UI**
   ```tsx
   <div className="flex-1 overflow-y-auto space-y-2">
     {loading && <div className="text-center text-zinc-400">Loading...</div>}
     {messages.length === 0 && !loading && (
       <div className="text-center text-zinc-500">No messages</div>
     )}
     {messages.map((message) => (
       <MessageItem key={message.id} message={message} />
     ))}
   </div>
   ```

4. **Media Rendering Component**
   Create `MessageItem` component with media support:
   ```tsx
   function MessageItem({ message }: { message: Message }) {
     const renderMedia = () => {
       switch (message.message_type) {
         case 'image':
           return (
             <img
               src={message.media_url}
               alt={message.caption || 'Image'}
               className="max-w-sm rounded"
             />
           )
         case 'video':
           return (
             <video controls className="max-w-sm rounded">
               <source src={message.media_url} type={message.media_mime_type} />
             </video>
           )
         case 'audio':
           return (
             <audio controls className="w-full max-w-sm">
               <source src={message.media_url} type={message.media_mime_type} />
             </audio>
           )
         case 'document':
           return (
             <a
               href={message.media_url}
               target="_blank"
               rel="noopener noreferrer"
               className="flex items-center space-x-2 text-blue-400 hover:text-blue-300"
             >
               <FileIcon className="w-5 h-5" />
               <span>{message.caption || 'Download'}</span>
             </a>
           )
         default:
           return null
       }
     }

     return (
       <div className={`flex ${message.is_from_me ? 'justify-end' : 'justify-start'}`}>
         <div className={`max-w-[70%] rounded-lg p-3 ${
           message.is_from_me ? 'bg-blue-600' : 'bg-zinc-800'
         }`}>
           {!message.is_from_me && message.sender_name && (
             <div className="text-xs text-zinc-400 mb-1">{message.sender_name}</div>
           )}
           {renderMedia()}
           {message.text && <div className="text-white">{message.text}</div>}
           <div className="text-xs text-zinc-400 mt-1">
             {new Date(message.timestamp).toLocaleTimeString()}
           </div>
         </div>
       </div>
     )
   }
   ```

5. **Layout Updates**
   - Make panel wider when showing messages (e.g., `w-2/3` or full-screen modal)
   - Add sticky header with chat name and close button
   - Add scrollable message container with proper height
   - Optional: Add message input at bottom for sending messages

### 11. Testing Checklist (PENDING)
- [ ] Test WhatsApp text messages display correctly
- [ ] Test WhatsApp image messages with inline rendering
- [ ] Test WhatsApp video messages with player controls
- [ ] Test WhatsApp audio messages with playback
- [ ] Test WhatsApp document messages with download links
- [ ] Test Discord messages (if Discord instance available)
- [ ] Test pagination - load more messages
- [ ] Test empty state when no messages
- [ ] Test loading states
- [ ] Test error handling
- [ ] Test mobile responsiveness
- [ ] Test dark theme consistency

## API Endpoint Reference

```
GET /api/v1/omni/{instance_name}/chats/{chat_id}/messages
```

**Query Parameters:**
- `page` (int, default: 1) - Page number (1-based)
- `page_size` (int, default: 50, max: 200) - Items per page
- `before_message_id` (string, optional) - Cursor for pagination

**Response:**
```json
{
  "messages": [
    {
      "id": "string",
      "chat_id": "string",
      "sender_id": "string",
      "sender_name": "string",
      "message_type": "text|image|video|audio|document|...",
      "text": "string",
      "media_url": "string",
      "media_mime_type": "string",
      "media_size": 12345,
      "caption": "string",
      "thumbnail_url": "string",
      "is_from_me": false,
      "is_forwarded": false,
      "is_reply": false,
      "reply_to_message_id": "string",
      "timestamp": "2025-10-22T...",
      "edited_at": null,
      "channel_type": "whatsapp",
      "instance_name": "my-instance",
      "channel_data": {}
    }
  ],
  "total_count": 150,
  "page": 1,
  "page_size": 50,
  "has_more": true,
  "instance_name": "my-instance",
  "chat_id": "123@c.us",
  "channel_type": "whatsapp",
  "partial_errors": []
}
```

## Files Modified

### Backend:
1. `/home/cezar/automagik/automagik-omni/src/api/schemas/omni.py` - Added message models
2. `/home/cezar/automagik/automagik-omni/src/channels/omni_base.py` - Added get_messages interface
3. `/home/cezar/automagik/automagik-omni/src/channels/whatsapp/omni_evolution_client.py` - Added fetch_messages
4. `/home/cezar/automagik/automagik-omni/src/services/omni_transformers.py` - Added message transformers
5. `/home/cezar/automagik/automagik-omni/src/channels/handlers/whatsapp_chat_handler.py` - Implemented WhatsApp messages
6. `/home/cezar/automagik/automagik-omni/src/channels/handlers/discord_chat_handler.py` - Implemented Discord messages
7. `/home/cezar/automagik/automagik-omni/src/api/routes/omni.py` - Added messages endpoint

### Frontend:
8. `/home/cezar/automagik/automagik-omni/ui/lib/conveyor/schemas/omni-schema.ts` - Updated message schema

### Pending Frontend:
9. `ui/lib/conveyor/api/omni-api.ts` - Add getChatMessages method
10. `ui/app/components/chats/ChatDetailsPanel.tsx` - Enhance with message history and media rendering

## Next Steps

1. **Add API Client Method** - Implement `getChatMessages()` in the API client
2. **Update ChatDetailsPanel** - Add message fetching, display, and media rendering
3. **Test End-to-End** - Verify all message types render correctly
4. **Polish UI** - Add pagination, infinite scroll, better mobile support
5. **Add Send Message** - Optional: Add ability to send messages from panel

## Notes

- Backend is fully implemented and ready to use
- Frontend schemas are updated and type-safe
- Media rendering uses native HTML5 elements (img, video, audio)
- Pagination is supported but infinite scroll could be added
- The implementation is channel-agnostic (works for WhatsApp and Discord)
