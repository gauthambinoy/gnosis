# Gnosis Frontend

Next.js 16 dashboard for the Gnosis AI Agent Automation Platform.

## Local development

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Open http://localhost:3000. The frontend expects the FastAPI backend at `NEXT_PUBLIC_API_URL` and WebSocket server at `NEXT_PUBLIC_WS_URL`.

## Scripts

```bash
npm run typecheck
npm run lint
npx vitest run
npm run build
```

## Deploy

For a portfolio demo, deploy this directory as a Vercel project with:

```bash
NEXT_PUBLIC_API_URL=https://<your-backend-host>
NEXT_PUBLIC_WS_URL=wss://<your-backend-host>
```

See `../docs/PORTFOLIO_DEPLOY.md` for the full frontend + backend deployment checklist.
