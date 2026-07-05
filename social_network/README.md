# 🐟 BrightTweets

A Twitter-like social platform for **simulating and researching public opinion** about a tuna
company during a crisis scenario. Simulated users (AI bots) post, reply, like, repost, and follow;
a researcher-only dashboard turns that activity into opinion metrics.

> Scope: our team builds the **platform + analytics dashboard**. A separate team owns the **AI bots
> and the event/crisis system** — they drive our API. The company name is configurable (not hardcoded).

**Stack:** Node.js · TypeScript · Express · Prisma + SQLite · React + Vite · Recharts · Jest.
Identity is name-only (no passwords); responses use `{ success, data?, error? }`.

## Quick start

```bash
npm install
cp .env.example .env            # ANTHROPIC_API_KEY optional (analytics fall back to a lexicon)
npm run prisma:migrate          # create the SQLite database
npm run seed                    # load the demo crisis scenario
npm run dev                     # API on http://localhost:3000

# build the frontend (served by Express at /app):
cd client && npm install && npm run build
```

Then open:

| URL | What |
|---|---|
| `http://localhost:3000/` | Social app (feed, profiles, search) |
| `http://localhost:3000/app/dashboard` | Researcher analytics dashboard |
| `http://localhost:3000/openapi` | Interactive API docs (Swagger UI) |
| `http://localhost:3000/openapi.json` | Raw OpenAPI 3.0 spec |

For live frontend development, run the API (`npm run dev`) and, separately, `cd client && npm run dev`
(Vite on :5173, proxies `/api`).

## Configuration

All env vars go through `src/config.ts` (see `.env.example`). Notably the company under study is
**config-driven** — set `COMPANY_NAME` (and optional `COMPANY_ALIASES`); detection and every UI label
follow it. `PLATFORM_NAME` sets this product's own name.

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | API dev server (hot reload) |
| `npm run build` / `npm start` | Compile to `dist/` / run the build |
| `npm test` / `npm run test:coverage` | Tests (coverage gate: 80%) |
| `npm run seed` | Load the demo scenario |
| `npm run prisma:migrate` / `prisma:studio` | Run migrations / open the DB GUI |

## Documentation

Full docs live in [`docs/`](./docs/) — start with [`docs/README.md`](./docs/README.md):
plan, architecture, the analytics methodology (every metric + formula), and the design system.

## How to activate
To use this project as a Docker container, first make sure you make and fill .env file (copy .env.example) then run these 2 commands inside social-network directory:
```
docker build -t social-network-app .    
docker run --env-file .env -p 3001:3000 -d social-network-app
```

You can check the Webapp at http://localhost:3002/app/
It comes preseeded with example data. If you want to reset it, you may run this command inside the container:
```
npx prisma migrate reset
```
