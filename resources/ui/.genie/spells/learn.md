# Project Learnings

This file captures critical project-specific learnings to prevent repeated mistakes.

## Package Management

### PNPM Only - Never Use npm

**Rule:** This project uses `pnpm` exclusively for package management. NEVER use `npm` commands.

**Why:**
- pnpm is configured in the project (pnpm-workspace.yaml)
- pnpm handles monorepo workspaces correctly
- npm creates incompatible lock files (package-lock.json vs pnpm-lock.yaml)
- npm installs cause peer dependency conflicts with React 19

**Correct Commands:**
```bash
pnpm install           # Install dependencies
pnpm add <package>     # Add new dependency
pnpm remove <package>  # Remove dependency
pnpm exec <command>    # Execute package binaries
```

**Incorrect Commands (NEVER USE):**
```bash
npm install     # ❌ WRONG
npm ci          # ❌ WRONG
npm run         # ❌ WRONG
npx             # ❌ WRONG
```

**Recovery from npm Mistakes:**
If npm was accidentally used:
```bash
# Delete npm artifacts
rm -rf node_modules package-lock.json

# Clean install with pnpm
pnpm install
```

**Evidence:** Issue encountered 2025-11-27 when attempting to use `npm install` for Playwright setup, causing peer dependency conflicts and corrupted node_modules.
