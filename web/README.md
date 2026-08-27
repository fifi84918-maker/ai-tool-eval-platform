# AI Skill Benchmark Platform - Web Frontend

Next.js 14 + TypeScript + Tailwind CSS frontend for the AI Skill Benchmark Platform.

## Prerequisites

- Node.js 18+ and pnpm
- Backend API running on `http://localhost:8000`

## Installation

```bash
# Install pnpm if not already installed
npm install -g pnpm

# Install dependencies
pnpm install
```

## Environment Variables

Create `.env.local` file:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Development

```bash
# Start development server
pnpm dev

# Open http://localhost:3000
```

## Build

```bash
# Build for production
pnpm build

# Start production server
pnpm start
```

## Linting

```bash
pnpm lint
```

## Project Structure

```
web/
├── src/
│   └── app/
│       ├── api/
│       │   └── skills/
│       │       └── route.ts       # API proxy to backend
│       ├── skills/
│       │   └── [skill_id]/
│       │       └── page.tsx       # Skill detail page
│       ├── admin/
│       │   └── page.tsx           # Admin dashboard (Phase 2)
│       ├── layout.tsx             # Root layout with navigation
│       ├── page.tsx               # Home page (search + list)
│       └── globals.css            # Global styles (Tailwind)
├── tailwind.config.ts
├── tsconfig.json
└── next.config.js
```

## Features

### Phase 1 (Current)

- ✅ Skill search and listing
- ✅ Skill detail page with JSON-LD
- ✅ Status badges and evidence grades
- ✅ API proxy for backend integration
- ✅ Responsive Tailwind UI

### Phase 2 (Planned)

- Manual skill approval workflow
- Benchmark test case management
- Real-time evaluation monitoring
- Admin dashboard with statistics
- Evidence storage integration

## API Integration

Frontend communicates with FastAPI backend through Next.js API routes:

- `GET /api/skills?query=&limit=20` → proxies to backend `/api/v1/skills`
- `GET /api/v1/skills/{skill_id}` → direct fetch to backend

This approach avoids CORS issues and allows server-side rendering.
