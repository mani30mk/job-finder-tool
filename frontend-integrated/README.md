# JobHunter - Professional Job Aggregation Platform

A modern, professional job aggregation platform built with Next.js 16, React 19, and Tailwind CSS. Inspired by LinkedIn, Naukri, and Unstop, JobHunter helps users find and manage job opportunities with intelligent matching scores.

## Features

✨ **Professional UI Design**
- Clean, minimalist interface matching industry-standard job platforms
- Card-based layouts with subtle shadows and borders
- Responsive design (mobile, tablet, desktop)
- Professional blue (#0066cc) accent color with supporting palette

📊 **Dashboard**
- Quick stats overview (Available Jobs, High Match, New Today, Saved Jobs)
- Featured job opportunities section
- Welcome message and call-to-action

🔍 **Job Feed**
- Browse all available job opportunities
- Advanced filtering sidebar (employment type, location, match score)
- Search functionality across job titles, companies, and skills
- Large job cards with company logos, match scores, and key details

⭐ **New Today**
- Jobs posted in the last 24 hours
- Fresh opportunities discovery
- "New" badges on recently posted jobs

💾 **Saved Jobs**
- Bookmark interesting opportunities
- View saved jobs offline (localStorage support)
- Quick access to job collection

👤 **Profile & Settings**
- Edit user profile information
- Manage skills and experience
- Configure email notifications
- Custom API URL configuration

## Architecture

### Tech Stack
- **Framework**: Next.js 16 with App Router
- **UI Components**: shadcn/ui + custom components
- **Styling**: Tailwind CSS v4
- **State Management**: React Hooks + localStorage
- **Icons**: Lucide React
- **API Integration**: Fetch API with fallback to mock data

### Project Structure
```
app/
├── layout.tsx           # Root layout with header/nav
├── page.tsx             # Dashboard screen
├── jobs/page.tsx        # Jobs feed
├── new-today/page.tsx   # New jobs today
├── saved/page.tsx       # Saved jobs
└── profile/page.tsx     # User profile & settings

components/
├── Header.tsx           # Top navigation bar
├── Navigation.tsx       # Bottom/side navigation
├── FilterSidebar.tsx    # Advanced filters
├── JobCard.tsx          # Individual job card
├── MatchScoreBadge.tsx  # Match score display
├── StatCard.tsx         # Dashboard stat card
└── screens/
    ├── DashboardScreen.tsx
    ├── JobsFeedScreen.tsx
    ├── SavedJobsScreen.tsx
    └── ProfileScreen.tsx

lib/
├── types.ts             # TypeScript interfaces
├── api.ts               # API client with mock fallback
└── mock-data.ts         # Sample job data

app/globals.css          # Design tokens & theme
```

## Design System

### Color Palette
- **Primary**: #0066cc (Professional Blue)
- **Backgrounds**: #ffffff (white), #f8fafc (subtle gray)
- **Text**: #0f172a (dark), #64748b (secondary)
- **Borders**: #e5e7eb (light gray)
- **Status Colors**:
  - Green (#059669) - High match (≥70%)
  - Amber (#d97706) - Medium match (40-69%)
  - Red (#dc2626) - Low match (<40%)

### Typography
- **Font Family**: Geist (sans-serif)
- **Headings**: Bold, 24-32px
- **Body**: 16px, 1.5 line-height
- **Secondary**: 14px gray text

### Spacing & Layout
- **Grid System**: 8px base unit
- **Card Padding**: 16-24px
- **Section Gaps**: 24-32px
- **Border Radius**: 8px (modern, professional)
- **Shadows**: Subtle (0 1px 3px rgba(0,0,0,0.1))

## Getting Started

### Prerequisites
- Node.js 18+
- pnpm (or npm/yarn)

### Installation
```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Open browser
# http://localhost:3000
```

## Configuration

### Environment Variables
Create a `.env.local` file:
```env
# Optional: Connect to backend API
NEXT_PUBLIC_API_URL=http://your-api.com

# Without NEXT_PUBLIC_API_URL, mock data is used by default
```

### Backend Integration (Optional)
The app includes fallback mock data but can connect to a FastAPI backend:

**Expected API Endpoints:**
- `GET /api/v1/recommendations/default?limit=50&min_score=0.1`
- `GET /api/v1/jobs/new?since_hours=24&limit=30`

Example response format:
```json
{
  "id": "1",
  "title": "Senior React Developer",
  "company": "TechCorp",
  "location": "San Francisco, CA",
  "matchScore": 0.85,
  "description": "...",
  "requiredSkills": ["React", "TypeScript"],
  "employmentType": "full-time",
  "remote": "hybrid",
  "salary": {
    "min": 120000,
    "max": 160000,
    "currency": "USD"
  },
  "link": "https://...",
  "isNew": true
}
```

## Data Persistence

### LocalStorage
- **savedJobs**: Bookmarked jobs (offline access)
- **userProfile**: User profile information

### Mock Data
When no backend is configured, the app uses sample data from `lib/mock-data.ts` with realistic job postings.

## Features Breakdown

### Job Matching
- Match score displayed as percentage (0-100%)
- Color-coded badges for quick identification
- Filter by minimum match score
- Sorted by relevance

### Responsive Navigation
- **Mobile**: Bottom tab navigation (fixed)
- **Desktop**: Top header + sidebar navigation
- Active state indicators
- Smooth transitions

### Search & Filter
- Real-time search across titles, companies, skills
- Multi-select employment type filter
- Remote-only toggle
- Match score range filter
- Clear filters button

### User Experience
- Loading skeletons while data fetches
- Empty states with helpful CTAs
- Hover effects and transitions
- One-click job apply (external link)
- Save/unsave jobs with heart icon toggle

## Browser Support
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Performance
- Next.js 16 with Turbopack for fast builds
- React Server Components where possible
- Client-side filtering for responsive UX
- Lazy loading with Suspense boundaries
- Optimized images with next/image

## Accessibility
- Semantic HTML elements
- ARIA labels on interactive elements
- Focus states for keyboard navigation
- Color contrast compliance
- Screen reader friendly

## Future Enhancements
- [ ] User authentication
- [ ] Email notifications
- [ ] Job application tracking
- [ ] Resume upload & matching
- [ ] Saved searches
- [ ] Job alerts/subscriptions
- [ ] Social sharing
- [ ] Dark mode toggle
- [ ] Multiple language support

## License
MIT

## Support
For issues or questions, please create an issue in the repository.
