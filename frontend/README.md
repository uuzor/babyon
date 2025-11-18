# Babylon Genesis Analytics - Frontend Dashboard

Modern, professional analytics dashboard for Babylon Genesis Chain built with Next.js 15, React 19, and TailwindCSS.

## Features

✅ **Dashboard Overview** - Real-time blockchain statistics
✅ **Blockchain Metrics** - Detailed network health indicators
✅ **Smart Money Leaderboard** - Top addresses ranked by AI-powered scoring
✅ **Address Lookup** - Search and analyze any Babylon address
✅ **Network Metrics** - Transaction and address activity analytics

## Tech Stack

- **Next.js 15.5** - React framework with App Router
- **React 19** - Latest React with concurrent features
- **TypeScript** - Type-safe development
- **TailwindCSS** - Utility-first CSS framework
- **shadcn/ui** - High-quality React components
- **Lucide Icons** - Beautiful icon set
- **Recharts** - Chart library for data visualization

## Design

- Clean Vercel-style UI with modern aesthetics
- Fully responsive layout
- Dark/light mode support (via CSS variables)
- Professional sidebar navigation
- Real-time data updates

## Getting Started

### Prerequisites

- Node.js 20+ (v22.21.1 recommended)
- npm 10+ (v10.9.4 recommended)
- Backend API running at `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Open browser
open http://localhost:3000
```

### Build for Production

```bash
# Create production build
npm run build

# Start production server
npm start
```

## Configuration

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

For production:

```env
NEXT_PUBLIC_API_URL=https://your-api-domain.com
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js app router pages
│   │   ├── address/           # Address lookup page
│   │   ├── blockchain/        # Blockchain metrics page
│   │   ├── metrics/           # Network metrics page
│   │   ├── smart-money/       # Smart money leaderboard
│   │   ├── layout.tsx         # Root layout with sidebar
│   │   └── page.tsx           # Dashboard homepage
│   │
│   ├── components/
│   │   ├── ui/                # shadcn/ui components
│   │   │   ├── badge.tsx
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   └── input.tsx
│   │   └── sidebar.tsx        # Navigation sidebar
│   │
│   └── lib/
│       ├── api.ts             # API client for backend
│       └── utils.ts           # Utility functions
│
├── public/                     # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.ts
```

## Pages

### Dashboard (/)
- Real-time blockchain overview
- Key metrics cards
- Quick navigation links
- Auto-refresh every 30s

### Blockchain (/blockchain)
- Current block height
- Transaction statistics
- Network activity metrics
- Data synchronization status

### Smart Money (/smart-money)
- Top 50 addresses ranked by smart money score
- Podium display for top 3
- Detailed scoring breakdown
- Rating system (Elite, Smart, Above Average, Average)

### Address Lookup (/address)
- Search any Babylon address
- Address overview with transaction count
- Smart money analysis
- Token holdings display

### Metrics (/metrics)
- Transaction activity over last 7 days
- Address growth metrics
- Network health indicators
- Engagement rate analytics

## API Integration

The dashboard connects to the backend API with the following endpoints:

- `GET /blockchain/overview` - Overall blockchain stats
- `GET /smart-money/top` - Smart money leaderboard
- `GET /addresses/{address}` - Address information
- `GET /addresses/{address}/holdings` - Token holdings
- `GET /smart-money/{address}` - Smart money score
- `GET /metrics/transactions` - Transaction metrics
- `GET /metrics/addresses` - Address metrics

## Development

### Code Quality

```bash
# Run ESLint
npm run lint

# Type checking
npm run build  # TypeScript errors will be shown
```

### Adding New Pages

1. Create page in `src/app/[page-name]/page.tsx`
2. Add route to sidebar in `src/components/sidebar.tsx`
3. Create API functions in `src/lib/api.ts` if needed

### Adding New Components

```bash
# Add shadcn/ui component (example)
npx shadcn-ui@latest add [component-name]
```

## Performance

- **Build Time:** ~8-10 seconds
- **First Load JS:** ~102-114 KB
- **Static Generation:** All pages pre-rendered
- **Real-time Updates:** Automatic polling for fresh data

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Docker

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
RUN npm ci --only=production
EXPOSE 3000
CMD ["npm", "start"]
```

## Troubleshooting

### API Connection Issues

If you see "Error Loading Data" messages:

1. Ensure backend is running at `http://localhost:8000`
2. Check CORS settings on backend
3. Verify `.env.local` has correct API URL

### Build Failures

```bash
# Clear Next.js cache
rm -rf .next

# Clear node_modules
rm -rf node_modules
npm install

# Rebuild
npm run build
```

## Contributing

This project is part of the Babylon Genesis Analytics platform.

## License

AWS Global Vibe: AI Coding Hackathon 2025 submission

## Links

- [Babylon Labs](https://babylonlabs.io)
- [Babylon Documentation](https://docs.babylonlabs.io)
- [Backend API Repository](../backend)
