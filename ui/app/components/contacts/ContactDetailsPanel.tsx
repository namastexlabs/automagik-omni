import { Badge } from '@/app/components/ui/badge'
import type { Contact } from '@/lib/main/omni-api-client'

interface ContactDetailsPanelProps {
  contact: Contact | null
  onClose: () => void
}

export function ContactDetailsPanel({ contact, onClose }: ContactDetailsPanelProps) {
  if (!contact) return null

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-zinc-950 border-l border-zinc-800 p-6 overflow-auto z-50">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-white">Contact Details</h2>
        <button
          onClick={onClose}
          className="text-zinc-400 hover:text-white text-2xl leading-none"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      <div className="space-y-6">
        {/* Profile Picture */}
        {contact.avatar_url ? (
          <div className="flex justify-center">
            <img
              src={contact.avatar_url}
              alt={contact.name || 'Contact'}
              className="w-24 h-24 rounded-full object-cover"
            />
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-24 h-24 rounded-full bg-zinc-800 flex items-center justify-center text-4xl text-zinc-400">
              {contact.name?.charAt(0).toUpperCase() || '?'}
            </div>
          </div>
        )}

        {/* Name */}
        <div>
          <label className="text-sm text-zinc-400 block mb-1">Name</label>
          <p className="text-white">{contact.name || 'Unknown'}</p>
        </div>

        {/* Phone Number */}
        {(contact.channel_data?.phone || contact.channel_data?.jid) && (
          <div>
            <label className="text-sm text-zinc-400 block mb-1">Phone Number</label>
            <p className="text-white font-mono">
              {contact.channel_data?.phone || contact.channel_data?.jid}
            </p>
          </div>
        )}

        {/* Status */}
        {contact.status && (
          <div>
            <label className="text-sm text-zinc-400 block mb-1">Status</label>
            <p className="text-white">{contact.status}</p>
          </div>
        )}

        {/* Channel Type */}
        <div>
          <label className="text-sm text-zinc-400 block mb-1">Channel</label>
          <Badge variant="default">{contact.channel_type}</Badge>
        </div>

        {/* Contact ID */}
        <div>
          <label className="text-sm text-zinc-400 block mb-1">ID</label>
          <p className="text-xs text-zinc-500 font-mono break-all">{contact.id}</p>
        </div>
      </div>
    </div>
  )
}
