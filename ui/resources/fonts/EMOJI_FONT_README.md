# Emoji Font Setup

## Problem

Emojis were displaying as squares (▢) in the Electron app due to:

1. **System emoji fonts not accessible**: When Electron runs with GPU acceleration disabled (required for WSL2 compatibility), Chromium cannot access system emoji fonts like "Segoe UI Emoji" or "Apple Color Emoji"

2. **Software rendering limitations**: Chromium's software renderer does not properly support color emoji font rendering

3. **Font fallback issues**: System fonts report they can handle emoji but render them as squares instead

## Solution

We bundle **Noto Color Emoji** font directly with the application to ensure consistent emoji rendering across all platforms and environments.

### Font Details

- **Font Name**: Noto Color Emoji
- **Source**: [Google Noto Emoji](https://github.com/googlefonts/noto-emoji)
- **File**: `NotoColorEmoji.ttf` (~10.6 MB)
- **License**: SIL Open Font License 1.1
- **Download**: Automated via `scripts/download-emoji-font.sh`

### Why Not Commit the Font?

The emoji font file is ~10.6 MB, which is too large for git. Instead:

1. The font is downloaded automatically during `pnpm install` (postinstall hook)
2. It's also downloaded before builds via `prebuild` hook
3. The font file is gitignored to keep the repository clean

### Manual Download

If automatic download fails, run:

```bash
cd ui
bash scripts/download-emoji-font.sh
```

Or download manually:

```bash
curl -L -o ui/resources/fonts/NotoColorEmoji.ttf \
  https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoColorEmoji.ttf
```

## Implementation

### CSS Setup

The font is declared in `app/styles/globals.css`:

```css
@font-face {
  font-family: 'Noto Color Emoji';
  src: url('@/resources/fonts/NotoColorEmoji.ttf') format('truetype');
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}
```

### Font Stack

In `app/styles/app.css`, the bundled font is included in the fallback chain:

```css
body {
  font-family:
    system-ui,
    -apple-system,
    "Segoe UI",
    Arial,
    Helvetica,
    sans-serif,
    "Noto Color Emoji",
    "Apple Color Emoji",
    "Segoe UI Emoji";
}
```

### Electron Configuration

Additional Chromium flags in `lib/main/main.ts` for Windows:

```typescript
if (process.platform === 'win32') {
  app.commandLine.appendSwitch('enable-features', 'DirectWriteFontCache')
  app.commandLine.appendSwitch('font-render-hinting', 'none')
}
```

## Testing

To verify emoji rendering:

1. Build the app: `pnpm run vite:build:app`
2. Start the app: `pnpm run dev` or `pnpm start`
3. Check that emojis (😀 🎉 👍 ❤️ 🚀) display correctly, not as squares

## Troubleshooting

### Emojis still showing as squares?

1. **Check font file exists**:
   ```bash
   ls -lh ui/resources/fonts/NotoColorEmoji.ttf
   ```

2. **Verify font was bundled**:
   ```bash
   ls -lh ui/out/renderer/assets/NotoColorEmoji*.ttf
   ```

3. **Check CSS includes font**:
   ```bash
   grep "Noto Color Emoji" ui/out/renderer/assets/*.css
   ```

4. **Clear Electron cache**:
   - Close the app completely
   - Delete cache folder (location varies by OS)
   - Rebuild and restart

### Font download fails?

- Check internet connection
- Verify GitHub is accessible
- Try downloading manually (see above)
- Check firewall/proxy settings

## Alternative Solutions (Not Used)

We considered but did not implement:

1. **Git LFS**: Adds complexity for all contributors
2. **CDN hosting**: Requires internet connection
3. **Twemoji**: Image-based, larger bundle size
4. **System font only**: Doesn't work with GPU disabled

## References

- [Electron Font Rendering Issues](https://github.com/electron/electron/issues/7334)
- [Noto Emoji GitHub](https://github.com/googlefonts/noto-emoji)
- [WSL2 + Electron Rendering](https://github.com/microsoft/WSL/issues/590)
