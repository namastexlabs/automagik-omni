# Blanka Font Installation

## Download the Font

1. Visit: https://befonts.com/blanka-font.html
2. Click the "Download" button
3. Extract the downloaded ZIP file
4. Copy the font file (either `Blanka-Regular.otf` or `Blanka-Regular.ttf`) to this directory

OR

1. Visit: https://www.dafontfree.co/blanka-font/
2. Download the font
3. Extract and copy to this directory

## Usage in the App

Once the font file is in this directory, it will be automatically loaded via `@font-face` in `app/styles/globals.css`.

You can use it in your components with the Tailwind class: `font-blanka`

Example:
```tsx
<h1 className="font-blanka text-4xl">Omni</h1>
```

Or directly with CSS:
```css
.my-element {
  font-family: var(--font-family-blanka);
}
```

## License

Blanka font is free for both personal and commercial use.
Designer: Emmeran Richard
