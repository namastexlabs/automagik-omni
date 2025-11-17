# Automagik Omni UI

Web dashboard for managing Automagik Omni instances across multiple messaging channels (WhatsApp, Discord, Slack, etc.).

## Quick Start

### Prerequisites

- Node.js 20+ (npm or pnpm)
- Automagik Omni API running on http://localhost:8882

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Update .env with your API key (must match AUTOMAGIK_OMNI_API_KEY in the API)
# VITE_API_URL=http://localhost:8882
# VITE_API_KEY=your-secret-api-key-here
```

### Development

```bash
# Start dev server (runs on http://localhost:9882)
npm run dev
```

### Build for Production

```bash
# Build static files
npm run build

# Preview production build
npm run preview
```

## Features

- API key authentication
- Instance management (create, view, update, delete)
- Real-time connection status monitoring
- WhatsApp QR code display
- Multi-channel support (WhatsApp, Discord)
- Responsive design with dark mode support

## Tech Stack

- **Framework**: React 19 + Vite
- **UI Components**: shadcn/ui (Radix UI + Tailwind CSS)
- **Routing**: React Router v7
- **State Management**: Tanstack Query (React Query)
- **Styling**: Tailwind CSS
- **TypeScript**: Full type safety

## Configuration

The UI connects to the Omni API via:
- Default URL: `http://localhost:8882`
- Authentication: API key via `x-api-key` header
- Port: 9882 (configurable in vite.config.ts)

## Project Structure

```
src/
├── components/ui/     # shadcn/ui components (Button, Card, Input)
├── lib/              # Utilities and API client
│   ├── api.ts        # API client with authentication
│   ├── types.ts      # TypeScript types from API schemas
│   └── utils.ts      # Helper functions
├── pages/            # Page components
│   ├── Login.tsx     # API key authentication
│   └── Dashboard.tsx # Main dashboard
├── App.tsx           # Router and app setup
└── main.tsx          # Entry point
```

## API Integration

The UI communicates with the Omni API endpoints:

- `GET /health` - API health check
- `GET /api/v1/instances` - List instances
- `POST /api/v1/instances` - Create instance
- `GET /api/v1/instances/{name}/qr` - Get QR code
- `GET /api/v1/instances/{name}/status` - Connection status
- And more...

See `src/lib/api.ts` for full API client implementation.

## Development Notes

- Vite dev server includes API proxy to avoid CORS issues
- API key is stored in localStorage (client-side only)
- Dark mode support via Tailwind CSS
- Type-safe API calls with TypeScript
