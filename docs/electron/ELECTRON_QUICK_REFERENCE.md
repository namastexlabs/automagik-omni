# Electron Boilerplate Quick Reference

## TL;DR

**Use: electron-react-app (ERA)**
- Conveyor IPC for FastAPI = type-safe backend calls
- Shadcn UI = 100+ components ready to use
- Vite = blazing fast hot reload
- 4-5 days to production

---

## Why ERA Wins

| Feature | ERA | vite-eb | ERB |
|---------|-----|---------|-----|
| **Conveyor IPC** | ✓ Built-in | ✗ Manual | ✗ Basic |
| **Shadcn UI** | ✓ Yes | ✗ No | ✗ No |
| **Vite Hot Reload** | ✓ Excellent | ✓ Good | ✗ Slow (Webpack) |
| **Recent Updates** | ✓ 48 commits | ✓ 48 commits | ✗ 0 commits |
| **GitHub Actions** | ✗ Copy from vite-eb | ✓ 5 workflows | ~ 3 workflows |
| **Auto-updates** | ✗ Copy from vite-eb | ✓ Ready | ✓ Ready (Mac only) |

---

## Getting Started

```bash
# 1. Clone
git clone https://github.com/guasam/electron-react-app my-desktop-app
cd my-desktop-app

# 2. Install & run
npm install
npm run dev

# 3. Explore
# Read: /lib/conveyor/README.md
# Check: /lib/conveyor/schemas/
# Review: /lib/conveyor/api/
```

---

## FastAPI Integration Flow

```
React Component
    ↓
useConveyor('backend').sendMessage()
    ↓
IPC Channel (type-safe with Zod)
    ↓
Main Process Handler
    ↓
HTTP fetch to http://localhost:8000/api/messages
    ↓
FastAPI Backend (your Python code)
```

---

## 4-Day Implementation Plan

**Day 1: Setup**
- Clone ERA
- npm install
- npm run dev
- Explore Conveyor system

**Days 2-3: Backend Integration**
- Create `lib/conveyor/schemas/backend-schema.ts`
- Create `lib/conveyor/api/backend-api.ts`
- Create `lib/conveyor/handlers/backend-handler.ts`
- Create `lib/main/backend-launcher.ts` (start FastAPI)
- Register handlers

**Day 4: UI + CI/CD**
- Build Shadcn UI components
- Copy GitHub Actions from vite-electron-builder
- Test builds locally
- Test on all platforms

---

## Key Code Pattern

```typescript
// Step 1: Define what FastAPI endpoints look like
export const backendIpcSchema = {
  'send-message': {
    args: z.tuple([z.object({ text: z.string() })]),
    return: z.object({ success: z.boolean(), id: z.string() }),
  },
}

// Step 2: Create type-safe API class
export class BackendApi extends ConveyorApi {
  sendMessage = (text: string) => this.invoke('send-message', { text })
}

// Step 3: Implement in main process
handle('send-message', async ({ text }) => {
  const res = await fetch('http://localhost:8000/api/messages', {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
  return await res.json()
})

// Step 4: Use in React
const { sendMessage } = useConveyor('backend')
await sendMessage('Hello!')
```

That's it!

---

## GitHub Actions (Copy These)

From: `https://github.com/cawa-93/vite-electron-builder/.github/workflows/`

Copy:
- `compile-and-test.yml` → Builds on Windows/Mac/Linux
- `deploy.yml` → Release management
- `codeql.yml` → Security scanning

Adapt for ERA:
- Change `npm run compile` to `npm run build`
- Change `npm run test` to `npm run test` (same)

---

## Auto-Updates (Copy This)

From: `https://github.com/cawa-93/vite-electron-builder/packages/main/src/modules/AutoUpdater.ts`

Copy this file and integrate into ERA's main process.

---

## Pre-built Components Ready to Use

ERA comes with Shadcn UI, so you get:

```
Button, Input, Dialog, Form, Select, Checkbox, 
Radio, Switch, Tabs, Accordion, Alerts, Cards,
Dropdown Menu, Pagination, Table, Breadcrumb, etc.
```

No need to build UI from scratch!

---

## Troubleshooting

**IPC channel not found?**
- Check handler is registered in main process
- Verify schema is imported correctly
- Restart npm run dev

**Backend won't start?**
- Check Python path in backend-launcher.ts
- Verify FastAPI is runnable: `python main.py`
- Check logs in Electron console

**Hot reload not working?**
- Restart `npm run dev`
- Check file was actually saved
- Clear browser cache

**GitHub Actions failing?**
- Check node version (use 18+)
- Verify npm install passes
- Check build command syntax

---

## What to Avoid

1. Don't use ERB (0 commits in 3 months, Webpack is slow)
2. Don't hand-build UI components (Shadcn UI already exists)
3. Don't create GitHub Actions from scratch (copy vite-eb's)
4. Don't hardcode FastAPI URL (use env vars)

---

## Files You'll Create/Modify

**Create:**
- `lib/conveyor/schemas/backend-schema.ts`
- `lib/conveyor/api/backend-api.ts`
- `lib/conveyor/handlers/backend-handler.ts`
- `lib/main/backend-launcher.ts`
- `.github/workflows/compile-and-test.yml` (copy + adapt)
- `.github/workflows/deploy.yml` (copy + adapt)
- `app/components/chat/` (your UI)

**Modify:**
- `lib/main/app.ts` (add handler registration + backend start)

**Copy:**
- `lib/main/src/modules/AutoUpdater.ts` (from vite-eb)

---

## Production Checklist

- [ ] Local dev works (npm run dev)
- [ ] Backend starts automatically
- [ ] Messages send/receive
- [ ] UI looks good
- [ ] Built app works (npm run build:win/mac/linux)
- [ ] GitHub Actions passes
- [ ] Auto-updates configured
- [ ] Error handling added
- [ ] Logging configured
- [ ] Icons/branding applied

---

## Expected Result

After 4-5 days:

✓ Desktop app with React UI
✓ Shadcn UI components
✓ Type-safe FastAPI integration
✓ Multi-platform GitHub Actions
✓ Auto-updates working
✓ Production-ready

---

## Learn More

Read these in order:
1. `/lib/conveyor/README.md` (ERA's own docs)
2. `ELECTRON_BOILERPLATE_COMPARISON.md` (detailed analysis)
3. `ELECTRON_IMPLEMENTATION_GUIDE.md` (step-by-step code)

---

## Need Help?

- ERA docs: https://github.com/guasam/electron-react-app
- vite-eb workflows: https://github.com/cawa-93/vite-electron-builder/.github/workflows/
- Shadcn UI: https://ui.shadcn.com/

That's it! You're ready to go.
