# Omni UI Design System

Professional, consistent design system based on shadcn/ui best practices with a purple theme.

## Color System

### Semantic Tokens

Our design uses **semantic color tokens** that automatically adapt to light/dark mode:

```tsx
// Use semantic tokens, NOT hardcoded colors
<div className="bg-card text-card-foreground">     // ✅ Correct
<div className="bg-white text-black">              // ❌ Wrong - won't adapt to dark mode
```

### Available Tokens

| Token | Usage | Example |
|-------|-------|---------|
| `background` | Page background | `bg-background` |
| `foreground` | Main text | `text-foreground` |
| `card` | Card/surface backgrounds | `bg-card` |
| `card-foreground` | Text on cards | `text-card-foreground` |
| `primary` | Brand color (purple) | `bg-primary text-primary-foreground` |
| `secondary` | Secondary elements | `bg-secondary` |
| `muted` | Less prominent | `bg-muted text-muted-foreground` |
| `accent` | Highlights | `bg-accent` |
| `destructive` | Errors/delete | `bg-destructive` |
| `border` | Borders | `border-border` |
| `input` | Input fields | `border-input` |
| `ring` | Focus rings | `ring-ring` |

### Custom Semantic Colors

```tsx
// Success (green)
<span className="text-success">Connected</span>
<div className="bg-success/10 border border-success/20">Status</div>

// Warning (amber)
<span className="text-warning">Pending</span>

// Info (cyan)
<span className="text-info">Information</span>
```

## Gradients

Predefined gradients that work in light/dark mode:

```tsx
// Primary purple gradient
<button className="gradient-primary">Button</button>

// Success gradient
<div className="gradient-success">Success state</div>

// Warning gradient
<div className="gradient-warning">Warning state</div>

// Danger gradient
<div className="gradient-danger">Error state</div>

// Info gradient
<div className="gradient-info">Info state</div>
```

## Elevation (Shadows)

Consistent depth using our elevation system:

```tsx
<Card className="elevation-sm">  // Subtle shadow
<Card className="elevation-md">  // Medium shadow (default for cards)
<Card className="elevation-lg">  // Large shadow (elevated)
<Card className="elevation-xl">  // Extra large (modals, popovers)
```

**Best Practice**: Combine with hover effects:
```tsx
<Card className="elevation-md hover:elevation-lg hover-lift">
```

## Animations

### Entrance Animations

```tsx
<div className="animate-fade-in">    // Fade in
<div className="animate-slide-in">   // Slide up + fade
```

### Hover Effects

```tsx
<Card className="hover-lift">  // Lifts up on hover
```

### Loading States

```tsx
<div className="animate-shimmer">  // Shimmer effect
<div className="animate-pulse">    // Pulse effect
```

## Component Patterns

### Cards

```tsx
// Standard card
<Card className="border-border elevation-md hover:elevation-lg hover-lift">
  <CardHeader>
    <CardTitle className="text-foreground">Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>Content</CardContent>
</Card>
```

### Buttons

```tsx
// Primary action
<Button className="gradient-primary elevation-md hover:elevation-lg hover-lift">
  Primary Action
</Button>

// Secondary action
<Button variant="outline" className="elevation-sm hover:elevation-md">
  Secondary
</Button>

// Destructive action
<Button variant="destructive">Delete</Button>
```

### Status Badges

```tsx
<Badge className="gradient-success border-0">Connected</Badge>
<Badge className="gradient-warning border-0">Pending</Badge>
<Badge className="gradient-danger border-0">Error</Badge>
<Badge variant="outline">Unknown</Badge>
```

### Input Fields

```tsx
<Input
  className="focus-ring"
  placeholder="Enter text..."
/>
```

## Spacing Scale

Consistent spacing using Tailwind's scale:

- `space-y-1` (4px) - Tight spacing
- `space-y-2` (8px) - Default tight
- `space-y-4` (16px) - Default comfortable
- `space-y-6` (24px) - Section spacing
- `space-y-8` (32px) - Large sections

## Border Radius

```tsx
<div className="rounded-sm">   // Small (4px)
<div className="rounded-md">   // Medium (6px)
<div className="rounded-lg">   // Large (8px)
<div className="rounded-xl">   // Extra large (12px)
<div className="rounded-2xl">  // 2X large (16px)
```

## Typography

### Hierarchy

```tsx
// Page title
<h1 className="text-3xl font-bold text-foreground">Dashboard</h1>

// Section title
<h2 className="text-2xl font-bold text-foreground">Active Instances</h2>

// Card title
<CardTitle className="text-xl text-foreground">Instance Name</CardTitle>

// Body text
<p className="text-sm text-muted-foreground">Description text</p>

// Label
<label className="text-sm font-medium text-foreground">Field Label</label>
```

## Accessibility

### Focus States

Always use the focus-ring utility:
```tsx
<button className="focus-ring">...</button>
```

### Color Contrast

Our semantic tokens ensure WCAG AA compliance:
- `foreground` on `background` - ✅ AAA
- `card-foreground` on `card` - ✅ AAA
- `primary-foreground` on `primary` - ✅ AAA

### Screen Readers

```tsx
<button aria-label="Close dialog">
  <X className="h-4 w-4" />
</button>
```

## Dark Mode

**Automatic**: Our design system automatically adapts based on system preference.

All components use semantic tokens, so they work in both modes without changes:

```tsx
// This works in light AND dark mode automatically
<div className="bg-card text-card-foreground border-border">
  <h1 className="text-foreground">Title</h1>
  <p className="text-muted-foreground">Description</p>
</div>
```

## DO's and DON'Ts

### ✅ DO

- Use semantic color tokens (`bg-card`, `text-foreground`)
- Use elevation classes (`elevation-md`)
- Combine hover effects (`hover:elevation-lg hover-lift`)
- Use gradients for CTAs (`gradient-primary`)
- Use focus-ring for accessibility

### ❌ DON'T

- Hardcode colors (`bg-white`, `text-gray-900`)
- Use arbitrary shadow values (`shadow-lg`)
- Mix gradients with semantic colors inconsistently
- Forget hover states on interactive elements
- Skip focus states

## Examples

### Instance Card (Complete)

```tsx
<Card className="border-border elevation-md hover:elevation-lg hover-lift bg-card">
  <CardHeader>
    <div className="flex justify-between items-start">
      <div className="flex-1 space-y-1">
        <CardTitle className="text-xl text-foreground">
          Instance Name
          <Badge className="gradient-primary text-xs border-0 ml-2">Default</Badge>
        </CardTitle>
        <CardDescription className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-primary"></span>
          whatsapp
        </CardDescription>
      </div>
      <Badge className="gradient-success border-0">Connected</Badge>
    </div>
  </CardHeader>
  <CardContent className="space-y-4">
    <div className="space-y-2 text-sm">
      <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
        <span className="text-muted-foreground">Profile</span>
        <span className="font-medium text-foreground">John Doe</span>
      </div>
    </div>
    <div className="flex gap-2">
      <Button variant="outline" size="sm" className="flex-1 hover:bg-primary/10 hover:text-primary">
        View
      </Button>
      <Button variant="outline" size="sm" className="flex-1 hover:bg-primary/10 hover:text-primary">
        Manage
      </Button>
    </div>
  </CardContent>
</Card>
```

## Future Enhancements

- [ ] Theme switcher component (manual light/dark toggle)
- [ ] Additional color schemes (blue, green, orange variants)
- [ ] More gradient combinations
- [ ] Animation presets for page transitions
