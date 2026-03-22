

## Plan: Move Game to /game & Add Hero Section on Home Page

### Problem with the Provided Component
The hero component uses **WebGPU** (`three/webgpu`, `three/tsl`) which is experimental and unsupported in most browsers. Additionally, the JSX in the provided code is stripped/empty (all return statements contain empty tags). This component **cannot be used as-is**.

**Proposed alternative**: Create a hero section inspired by the same aesthetic (dark futuristic, glitch text reveal, scroll-to-explore prompt) using standard CSS animations and Framer Motion — matching the existing game's visual language. A "Play Now" button will link to the game.

### Changes

**1. Move game to `/game` route**
- Update `App.tsx`: add `/game` route pointing to the game page
- Move game rendering from Index to a new `src/pages/Game.tsx`

**2. Create hero landing page (`src/pages/Index.tsx`)**
- Full-screen dark hero with animated title text ("Zen Rhythm") using word-by-word glitch reveal (ported from the provided component's `Html` logic)
- Subtitle with fade-in delay
- Animated breathing orb as visual centerpiece (reuse existing `BreathOrb` or a simplified version)
- "Play Now" button linking to `/game`
- "Scroll to explore" indicator with animated chevron
- Matches existing color tokens (teal/cyan glow, deep navy background)

**3. Install dependencies**
- No new dependencies needed — Framer Motion and existing CSS handle everything

### Files to Create/Modify
| File | Action |
|------|--------|
| `src/pages/Game.tsx` | Create — wraps `ZenRhythmGame` |
| `src/pages/Index.tsx` | Rewrite — hero landing page |
| `src/App.tsx` | Add `/game` route |

