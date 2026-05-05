# JobHunter Developer Checklist

Quick reference for developers working with the JobHunter platform.

## Pre-Launch Checklist

### Code Quality
- [ ] No console errors in DevTools
- [ ] No console warnings on critical paths
- [ ] ESLint passes without warnings
- [ ] TypeScript compiles without errors
- [ ] All imports are correct
- [ ] No unused variables or imports

### Mobile Testing
- [ ] Test on Android device (Chrome)
- [ ] Test on iOS device (Safari)
- [ ] Test on tablet (landscape)
- [ ] Test on desktop (all breakpoints)
- [ ] Test with slow 3G network (DevTools)
- [ ] Test in offline mode (DevTools)

### Touch & Interaction
- [ ] All buttons respond to single tap
- [ ] No double-tap zoom issues
- [ ] Navigation tabs are easy to tap
- [ ] Forms are easy to use on mobile
- [ ] Keyboard dismisses properly
- [ ] No accidental scrolls/selections

### Performance
- [ ] Lighthouse score > 90
- [ ] First Contentful Paint < 2s
- [ ] Largest Contentful Paint < 2.5s
- [ ] Cumulative Layout Shift < 0.1
- [ ] No jank during scrolling/animations
- [ ] App is responsive at 60fps

### Responsive Design
- [ ] Looks good at 375px (mobile)
- [ ] Looks good at 768px (tablet)
- [ ] Looks good at 1024px (desktop)
- [ ] Looks good at 1440px (wide)
- [ ] No horizontal scrolling
- [ ] Text is readable at all sizes

### Accessibility
- [ ] Color contrast > 4.5:1
- [ ] Touch targets ≥ 48x48px
- [ ] Tab navigation works
- [ ] Screen reader compatible
- [ ] Error messages clear
- [ ] Focus indicators visible

### Browser Compatibility
- [ ] Chrome 80+ (Android)
- [ ] Firefox 75+ (Android)
- [ ] Samsung Internet 12+ (Android)
- [ ] Safari 12+ (iOS)
- [ ] Chrome 80+ (Desktop)
- [ ] Firefox 75+ (Desktop)

---

## Development Workflow

### Starting Development
```bash
# 1. Clone and install
git clone <repo>
cd /vercel/share/v0-project
pnpm install

# 2. Start dev server
pnpm dev

# 3. Open browser
# Desktop: http://localhost:3000
# Mobile: http://<your-ip>:3000
```

### Creating New Features
1. **Plan**: Consider mobile constraints first
2. **Design**: Mobile-first responsive design
3. **Code**: Use existing component patterns
4. **Test**: Desktop, tablet, mobile
5. **Optimize**: Check performance metrics
6. **Document**: Update relevant docs

### Component Template
```tsx
"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface MyComponentProps {
  className?: string;
}

export function MyComponent({ className }: MyComponentProps) {
  // Mobile-first responsive classes
  return (
    <div className={cn(
      // Base (mobile) styles
      "px-3 py-4 text-sm",
      // Tablet+ enhancements
      "sm:px-4 sm:py-6 sm:text-base",
      // Desktop enhancements
      "lg:px-6 lg:py-8 lg:text-lg",
      // Custom styles
      className
    )}>
      {/* Content */}
    </div>
  );
}
```

### Key Patterns to Follow
- **Mobile-first**: Smallest screen first, enhance for larger
- **Touch targets**: Minimum 48x48px all interactive elements
- **Spacing**: Use px-3/px-4/px-6 for horizontal, py-4/py-6/py-8 for vertical
- **Responsive**: sm:, md:, lg: prefixes for breakpoint-specific styles
- **Safe areas**: Apply to fixed elements (header, nav, modals)
- **Accessibility**: ARIA labels, semantic HTML, proper heading hierarchy

---

## Styling Guidelines

### Tailwind Classes (Mobile-First)
```tsx
// Good: Mobile-first, scales up
<div className="px-3 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8">

// Bad: Desktop-first, breaks on mobile
<div className="px-8 py-8">

// Bad: Mixing space-* and gap
<div className="space-y-4 gap-4"> {/* Don't do this */}
```

### Color System
```tsx
// Use design tokens (defined in globals.css)
// Light mode
bg-white           // Card backgrounds
text-gray-900      // Primary text
text-gray-600      // Secondary text
bg-blue-600        // Primary action
bg-gray-100        // Secondary action

// Dark mode (handled automatically)
// Use same classes, CSS handles dark mode
```

### Responsive Images
```tsx
<img
  src="/image.jpg"
  alt="Description"
  className="w-12 h-12 sm:w-14 sm:h-14 lg:w-16 lg:h-16"
/>
```

### Buttons
```tsx
// Primary button
<button className="bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold py-3 sm:py-2.5 rounded-lg transition touch-target">
  Button Text
</button>

// Secondary button
<button className="bg-gray-100 hover:bg-gray-200 active:bg-gray-300 text-gray-900 font-semibold py-2.5 rounded-lg transition touch-target">
  Button Text
</button>
```

### Cards
```tsx
<div className="bg-white rounded-lg border border-gray-200 p-4 sm:p-6 hover:shadow-md transition">
  {/* Card content */}
</div>
```

### Inputs
```tsx
<input
  type="text"
  placeholder="Placeholder text"
  className="w-full px-4 py-3 rounded-lg bg-gray-100 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition text-base"
/>
```

---

## Performance Checklist

### Assets
- [ ] Images are optimized (< 100KB each)
- [ ] No unused CSS in bundles
- [ ] JavaScript is minified
- [ ] No render-blocking resources
- [ ] Fonts are optimized (subset + loading strategy)

### Network
- [ ] API responses are minimal
- [ ] Caching headers are set
- [ ] Compression is enabled (gzip/brotli)
- [ ] CDN is configured for static assets
- [ ] No unnecessary API calls

### Rendering
- [ ] No layout shifts during load
- [ ] Animations use transform/opacity only
- [ ] No forced synchronous layouts
- [ ] Efficient re-renders (proper React deps)
- [ ] Images have intrinsic dimensions

### Code
- [ ] Components are memoized where needed
- [ ] useCallback/useMemo used appropriately
- [ ] No infinite loops or recursion
- [ ] Event listeners are cleaned up
- [ ] No memory leaks

---

## Debugging on Mobile

### Using Chrome DevTools
1. Open Chrome on Android device
2. Enable USB Debugging
3. Connect via USB
4. Open chrome://inspect on desktop
5. Click "inspect" on your device

### Remote Debugging
```bash
# Start dev server
pnpm dev

# Access from mobile
# Replace <your-ip> with your computer's IP
http://<your-ip>:3000
```

### Common Issues
| Issue | Solution |
|-------|----------|
| Text too small | Check font-size in responsive classes |
| Buttons not tapping | Check min-height: 48px and padding |
| Layout shifts | Check images have explicit dimensions |
| Slow performance | Run DevTools Lighthouse audit |
| Offline not working | Check localStorage implementation |

---

## Version Control

### Commit Message Format
```
feat: add new feature (mobile-optimized)
fix: fix touch target on buttons
docs: update mobile optimization guide
style: improve spacing on mobile
refactor: simplify responsive classes
```

### Before Pushing
```bash
# Check for errors
pnpm lint
pnpm type-check
pnpm build

# Format code
pnpm format

# Test mobile
# Open on actual device and test key flows
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] No console errors
- [ ] Lighthouse > 90
- [ ] Tested on mobile devices
- [ ] HTTPS enabled (required for PWA)
- [ ] Environment variables set

### Deployment Commands
```bash
# Vercel
vercel deploy --prod

# Docker
docker build -t jobhunter .
docker run -p 3000:3000 jobhunter

# Self-hosted
npm run build
npm run start
```

### Post-Deployment
- [ ] Website loads on mobile
- [ ] API calls work
- [ ] Offline mode works
- [ ] Monitor errors (Sentry/logs)
- [ ] Check performance (Web Vitals)
- [ ] Gather user feedback

---

## Responsive Design Breakpoints

### Mobile First Approach
```
Mobile (default)     < 640px
  └─ Phone (375-425px)
  └─ Large phone (425-540px)

Tablet (sm: 640px)   640px - 1023px
  └─ Tablet (768-1024px)
  └─ Large tablet (1024+)

Desktop (lg: 1024px) 1024px+
  └─ Desktop (1024-1440px)
  └─ Large desktop (1440px+)
```

### Typical Device Dimensions
```
iPhone SE:       375px (mobile)
iPhone 12:       390px (mobile)
iPad:            768px (tablet)
iPad Pro:        1024px (tablet)
Desktop:         1440px+ (desktop)
```

---

## Common Patterns

### Responsive Container
```tsx
<div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-8">
  {/* Content */}
</div>
```

### Responsive Grid
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
  {/* Cards */}
</div>
```

### Responsive Text
```tsx
<h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold">
  Heading
</h1>
```

### Responsive Padding
```tsx
<div className="p-4 sm:p-6 lg:p-8">
  {/* Content with responsive padding */}
</div>
```

### Safe Area Aware
```tsx
<header className="sticky top-0 safe-area-inset-left safe-area-inset-right">
  {/* Header that respects notches */}
</header>
```

---

## Testing Commands

```bash
# Build and test
pnpm build
pnpm start

# Type check
pnpm type-check

# Run linter
pnpm lint

# Format code
pnpm format

# Run tests (if configured)
pnpm test

# Lighthouse audit
# Use Chrome DevTools → Lighthouse
```

---

## Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Quick start guide |
| `MOBILE_OPTIMIZATION.md` | Detailed optimization guide |
| `ANDROID_WEB_OPTIMIZATION.md` | Cross-platform summary |
| `ANDROID_DEPLOYMENT_GUIDE.md` | Deployment instructions |
| `OPTIMIZATION_SUMMARY.md` | Complete implementation summary |
| `DEVELOPER_CHECKLIST.md` | This document |

---

## Resources

### Official Documentation
- [Next.js](https://nextjs.org/)
- [React](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [TypeScript](https://www.typescriptlang.org/)

### Mobile Development
- [MDN Mobile Guide](https://developer.mozilla.org/en-US/docs/Web/Guide/Mobile)
- [Google Mobile Optimization](https://developers.google.com/search/mobile-sites)
- [Web.dev](https://web.dev/) - Performance & accessibility

### Tools
- Chrome DevTools
- Lighthouse
- WebPageTest
- GTmetrix

---

## Quick Reference

### File Structure
```
app/
  layout.tsx           - Main layout
  globals.css          - Global styles
  page.tsx             - Dashboard
  jobs/page.tsx        - Jobs feed
  saved/page.tsx       - Saved jobs
  profile/page.tsx     - Profile
  new-today/page.tsx   - New jobs

components/
  Header.tsx           - Top navigation
  Navigation.tsx       - Bottom tabs
  JobCard.tsx          - Job listing card
  FilterSidebar.tsx    - Filter panel
  MatchScoreBadge.tsx   - Match score display
  screens/             - Screen components

lib/
  types.ts             - TypeScript types
  api.ts               - API client
  mock-data.ts         - Demo data
  utils.ts             - Utility functions
```

### Key Imports
```tsx
import { cn } from "@/lib/utils";              // Class merger
import { Job } from "@/lib/types";             // Type definitions
import { api } from "@/lib/api";               // API client
import { MOCK_JOBS } from "@/lib/mock-data";   // Demo data
```

---

## Contact & Support

For questions or issues:
1. Check documentation files
2. Search existing code for patterns
3. Review GitHub issues
4. Consult team documentation

---

**Version**: 1.0
**Last Updated**: May 3, 2026
**Status**: Complete ✅
