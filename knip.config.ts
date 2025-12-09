import type { KnipConfig } from 'knip';

const config: KnipConfig = {
  workspaces: {
    '.': {
      entry: ['bin/*.js'],
      project: ['bin/**/*.js'],
    },
    'gateway': {
      entry: ['src/index.ts'],
      project: ['src/**/*.ts'],
    },
    'resources/ui': {
      entry: ['src/main.tsx'],
      project: ['src/**/*.{ts,tsx}'],
    },
  },
  ignore: [
    '**/node_modules/**',
    '**/dist/**',
    '**/.venv/**',
    '**/build/**',
    // Ignore Evolution API (has its own config)
    'resources/omni-whatsapp-core/**',
    // Ignore Python files (not TypeScript)
    'src/**',
    'tests/**',
    // Ignore generated files
    '**/*.generated.*',
  ],
  ignoreDependencies: [
    // These are used dynamically or via CLI
    'tsx',
    'playwright',
    '@playwright/test',
    'forge-inspector',
  ],
  rules: {
    files: 'error',
    dependencies: 'error',
    devDependencies: 'warn',
    unlisted: 'error',
    unresolved: 'error',
    exports: 'warn',
    types: 'warn',
    duplicates: 'warn',
    enumMembers: 'off',
    classMembers: 'off',
  },
};

export default config;
