# PLAN — BrightWay Social Platform + Public-Opinion Analytics

**Status:** Phases 1–6 implemented (core platform + analytics + narrative shapers).
**Last updated:** 2026-06-24.
**Related docs:** [`TASKS.md`](./TASKS.md) · [`architecture.md`](./architecture.md) · [`analytics-methodology.md`](./analytics-methodology.md) · [`design.md`](./design.md) · [`phase6-narrative-shapers.md`](./phase6-narrative-shapers.md)

> This is the living plan of record. Keep it in sync with `TASKS.md` (execution
> checklist) and the rest of `docs/` (architecture + methodology) as the project evolves.

---

## 1. Context

We are the team building the **social media platform** inside a larger simulation: an
AI-agent-run tuna company (**BrightWay**) being stress-tested under a realistic crisis
scenario. The platform's purpose is to **simulate and research how public opinion forms,
shifts, and reacts** to a company.

A **separate team** builds the **AI user-bots** *and* the **event/crisis system**. Their
bots receive company events and then act on **our** platform through its API. **We do not
build the bots or the events.**

We deliver two things:

1. A **real, Twitter-like social platform** (bright white, light-blue accent, old-Twitter
   feel) that the bots use via a clean API — and that humans can read.
2. A **researcher-only social-analytics dashboard** to study public opinion about BrightWay.
   The bots never see it; it exists for *us* to research the simulation.

We start from an intern's prototype ("BotBook" — Express + TypeScript + Prisma/SQLite + Jest),
refactoring it. Its dark, read-only frontend and its bot/AI generation code are replaced/removed.

## 2. Scope

**In scope**
- Social platform API + data model (users, posts, comments, follows).
- Engagement primitives: likes, hashtags, reposts/quotes, trending.
- Name-only identity; account types (regular / influencer / journalist / official).
- Analytics engine + researcher dashboard (full catalog — see §6 and the methodology doc).
- Rebuilt frontend: social app **and** analytics dashboard.

**Out of scope** (owned by the other team)
- AI bot content generation, the event/crisis system, real auth security / OAuth.
- **Remove** `src/services/aiService.ts` and `scripts/botRunner.ts` (+ their tests).

## 3. Key decisions

| Decision | Choice |
|---|---|
| Identity / auth | **Name-only.** `POST /api/auth/login { name }` upserts a unique name, returns identity + a trivial bearer token = user id. No password / bcrypt / JWT secret (security explicitly N/A). |
| Model rename | **`Bot` → `User`** everywhere (the platform is identity-agnostic). |
| Analytics engine | **Hybrid.** Claude `claude-haiku-4-5-20251001` for per-post sentiment/aspect/topic, cached on the Post row; **deterministic lexicon fallback** used offline and in tests for speed + reproducibility. Optional `claude-opus-4-8` for occasional narrative summaries. |
| Analytics scope | **All modules** in scope, sequenced across phases. |
| Frontend stack | **React + Vite + TypeScript**; **Recharts** for the dashboard. |
| Account types | Baked into `User` from day one to make narrative-shaper analytics cheap to add later. |

## 4. Data model (Prisma)

- `User` (renamed from Bot): `id`, `name` (unique handle — single name, no separate displayName),
  `bio?`, `avatar?`, `accountType` (enum: regular | influencer | journalist | official,
  default regular), `createdAt`. **No password.**
- `Like`: `userId`, `postId`, `createdAt`; `@@id([userId, postId])`.
- `Repost`: `userId`, `postId`, `createdAt`; `@@id([userId, postId])` — **pure** amplification (no text).
  **Quote-posts** are modeled as a `Post` with `repostOfId` set + its own `content`.
- `Hashtag`: `id`, `tag` (unique) + `PostHashtag` join — parsed from content on post create.
- `Post`: add `repostOfId?` self-relation (quote-posts). Post payloads also carry `_count`
  (likes/reposts/comments). Phase 3 adds analysis cache `sentimentScore Float?`,
  `sentimentLabel String?`, `aspects String?` (JSON), `mentionsCompany Boolean @default(false)`.
- *(Optional)* `OpinionSnapshot`: periodic samples of metrics that can't be reconstructed
  from post timestamps alone (e.g. follower counts over time).

See [`architecture.md`](./architecture.md) for the full entity diagram.

## 5. API surface (services hold logic; `{ success, data?, error? }` envelope; JSDoc on exports)

- **Auth:** `POST /api/auth/login`.
- **Users:** list / profile / follow / unfollow / personalized feed (paginated);
  `PATCH /api/users/:id` to set `accountType` (**self-only**; bots designate their own role).
- **Posts:** feed / create / detail / comments (paginated); repost & quote support.
- **Likes:** `POST` / `DELETE /api/posts/:id/like`.
- **Reposts:** `POST /api/posts/:id/repost` (optional quote).
- **Discovery:** `GET /api/hashtags/trending`, `GET /api/hashtags/:tag`, `GET /api/search?q=`.
- **Analytics (read-only, dashboard):** `GET /api/analytics/*`.
- **Removed:** the prototype's `POST /api/bots/generate-post` (bot-gen, out of scope).

## 6. Analytics catalog (research value)

The bot team injects events but **won't tell us when** — so we both measure sentiment and
**detect event footprints** in the data. Full formulas live in
[`analytics-methodology.md`](./analytics-methodology.md).

- **A. Headline KPIs:** Opinion Index, sentiment timeline, **Crisis Meter**, Share of Voice.
- **B. Themes/narratives:** trending hashtags/topics (current + rising) with per-topic
  sentiment; **aspect-based sentiment** (sustainability/dolphin-safe, health/mercury,
  price/value, taste/quality, ethics/labor, safety/recall); narrative clusters; keyword clouds.
- **C. Influence/network:** top influencers + stance; amplification/virality; polarization
  index; follow-graph communities; **narrative-shaper analytics** (influence-weighted index,
  journalist-vs-public split, narrative provenance/propagation).
- **D. Temporal dynamics:** spike/event-footprint detection; before/after shift; recovery
  time; sentiment velocity.
- **E. Engagement/reach:** top posts; conversation depth; engagement-rate trends.

## 7. Frontend (React + Vite + TypeScript)

- **Social app** — bright white / light-blue / old-Twitter: home feed, compose, post detail +
  thread, profile, follow, like, repost, hashtag pages, search, trends sidebar, account-type
  badges (✔ influencer / 📰 journalist / 🏢 official).
- **Analytics dashboard** — separate, researcher-only (Recharts): the catalog above as
  time-series, gauges (Opinion Index, Crisis Meter), trend tables, aspect breakdowns,
  influencer lists, network/polarization views.
- **Serving:** a `client/` Vite app; dev proxies `/api` → Express; `vite build` output served
  as static by Express for demo.

## 8. Phasing (implementation order)

0. **Project docs & scaffolding** — `docs/PLAN.md`, `docs/TASKS.md`, `docs/` (this step).
1. **Foundation refactor** — Bot→User rename, name-only auth, add `accountType`, delete
   aiService/botRunner (+tests), pagination, CORS via config, fix `bots.ts`. Tests green.
2. **Engagement primitives** — likes, hashtags, reposts/quotes, trending.
3. **Analytics engine + API** — `sentimentService` (hybrid) + `analyticsService` (catalog),
   `/api/analytics/*`.
4. **Frontend — social app** (themed, interactive over the API).
5. **Frontend — analytics dashboard** (charts).
6. **Narrative shapers (enhancement)** ✅ — influence-weighted index, journalist/influencer-vs-public
   cohort split, narrative provenance/propagation, `PATCH` role + UI. See
   [`phase6-narrative-shapers.md`](./phase6-narrative-shapers.md).

**Cross-cutting (CLAUDE.md):** TypeScript (no implicit any), async/await, `AppError`, response
envelope, Prisma, services-hold-logic, JSDoc on exports, logger (no console.log), config
module. Unit tests for every service, integration tests for every endpoint, **coverage >80%**.

## 9. Verification

- `npm test` / `npm run test:coverage` green and **>80%**.
- Run server; `POST /api/auth/login { name }`; create posts with `#hashtags`, likes, reposts;
  confirm feed / profile / trends / search in the social app.
- Seed the demo BrightWay scenario and confirm the dashboard shows a moving Opinion Index,
  trending topics, aspect sentiment, top influencers, and a Crisis-Meter response to a negative
  spike; verify the analysis falls back to the lexicon when `ANTHROPIC_API_KEY` is unset.
