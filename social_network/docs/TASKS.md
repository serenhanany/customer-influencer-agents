# TASKS — BrightWay Social Platform + Analytics

**Maintained throughout the project.** Update status as work proceeds.
See [`PLAN.md`](./PLAN.md) for the why and the design.

**Last updated:** 2026-06-24.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked

---

## Phase 0 — Project docs & scaffolding
- [x] Write `docs/PLAN.md` (plan of record)
- [x] Replace `tasks.md` → `docs/TASKS.md` (this file)
- [x] `docs/architecture.md` (system architecture)
- [x] `docs/analytics-methodology.md` (analytics formulas & methodology)
- [x] `docs/README.md` (docs index)
- [x] Refresh root `README.md` (concise BrightTweets overview + quick start)

## Phase 1 — Foundation refactor  ✅ done (2026-06-23)
- [x] Rename `Bot` → `User` across schema, services, routes, tests
- [x] Schema: drop `passwordHash`/`username`/`llmTag`; `name` is the unique handle; add `accountType` (string: regular/influencer/journalist/official)
- [x] Auth → name-only: `POST /api/auth/login { name }` upsert; token = user id
- [x] Rewrite `src/middleware/auth.ts` (token = id lookup, no JWT verify)
- [x] Delete `src/services/aiService.ts` + its test
- [x] Delete `scripts/botRunner.ts` + `scripts/seedBots.ts` (scripts/ removed) + tests
- [x] Remove `POST /api/bots/generate-post`; rename `routes/bots.ts` → `users.ts`, `botService` → `userService`
- [x] Add pagination (`src/utils/pagination.ts`) to global feed, user feed, user list
- [x] CORS configured via `src/config.ts` (`corsOrigin`); dropped `JWT_SECRET`/`BOT_*`; kept `ANTHROPIC_API_KEY` for analytics
- [x] `prisma/seed.ts` → BrightWay demo scenario (official/journalist/influencer/regular accounts, tuna-aspect posts)
- [x] Fresh `init` migration for the new schema (dev.db + test.db); `public/openapi.json` rewritten (name-only `User` API)
- [x] Tests updated/green — 53 passing; coverage 93% stmts / 84% branches / 97% funcs (> 80% gate)

> Note: `package.json#prisma` seed config triggers a Prisma 7 deprecation warning. Harmless on
> Prisma 6; migrate to `prisma.config.ts` when we bump to Prisma 7.

## Phase 2 — Engagement primitives  ✅ done (2026-06-24)
- [x] `Like` model + `POST`/`DELETE /api/posts/:id/like` (`engagementService`) + tests
- [x] `Repost` model (pure amplification) + `POST`/`DELETE /api/posts/:id/repost` + tests
- [x] Quote-posts: `Post.repostOfId` + `POST /api/posts { content, repostOfId }`; payloads include `repostOf` + `_count`
- [x] `Hashtag` + `PostHashtag`; parse `#tags` on post create (`utils/text.ts`); `GET /api/hashtags/:tag` + tests
- [x] Trending: `GET /api/hashtags/trending` (count-based; rising-rate deferred to Phase 3 analytics) + tests
- [x] Search: `GET /api/search?q=` (users/posts/hashtags) + tests
- [x] Seed enriched with hashtags, likes, reposts; `openapi.json` updated; 81 tests green, coverage ~94%/86%

## Phase 3 — Analytics engine + API  ✅ done (2026-06-24)
- [x] `src/analytics/lexicon.ts` (company keywords + tuna aspect lexicons + deterministic scorer)
- [x] `src/services/sentimentService.ts` — hybrid (Claude Haiku + lexicon fallback), caches on Post
- [x] **On-demand** analysis (`POST /api/analytics/analyze`, `reanalyze` option) — not on post-create
- [x] **Runtime AI on/off toggle** (`src/analytics/settings.ts`, `GET`/`PUT /api/analytics/config`)
- [x] Post analysis cache fields (`sentimentScore`, `sentimentLabel`, `aspects`, `mentionsCompany`, `analyzedAt`, `analyzedBy`) + migration
- [x] `src/services/analyticsService.ts` — overview, sentiment timeline, aspects, trends, influencers, spikes, top-posts
- [x] `src/routes/analytics.ts` — `GET /api/analytics/*`
- [x] Tests use the deterministic lexicon; Claude path covered via mocked SDK + fallback. 99 tests green, coverage ~95%/81%
- [x] `openapi.json`, `.env.example`, methodology doc updated

## Phase 4 — Frontend: social app  ✅ done (2026-06-24)
- [x] Scaffold `client/` (React + Vite + TypeScript); dev proxy `/api` → Express; build → `public/app`, served by Express (`/app`, SPA fallback, root redirect)
- [x] Theme per `docs/design.md`: bright white + light-blue (oceanic), old-Twitter 3-column, Space Grotesk × Hanken Grotesque, "waterline" signature
- [x] Screens: home (Latest/Following + compose), post detail + thread, profile, explore/search, hashtag page, trends + who-to-follow rail, login dialog
- [x] Interactions: name login (token in localStorage), post, reply, like, repost, quote-post, follow/unfollow; account-type badges (official/journalist/influencer)
- [x] Supporting API added: `GET /api/users/:id/posts`, `GET /api/users/:id/following` (+ tests, openapi)
- [x] Retired the interim `public/` viewer; 101 backend tests green; client builds clean; verified via headless screenshots
- [x] Dev workflow: terminal 1 `npm run dev` (API :3000), terminal 2 `cd client && npm run dev` (Vite :5173, proxies /api). Demo build: `cd client && npm run build`, then open `http://localhost:3000/`

## Phase 5 — Frontend: analytics dashboard  ✅ done (2026-06-24)
- [x] Separate full-width dashboard route (`/dashboard`, own layout, lazy-loaded; Recharts split into its own chunk — social app stays ~190 kB)
- [x] Control bar: **AI on/off toggle** (PUT /config), **Run analysis** (POST /analyze, reanalyze), coverage + engine pill
- [x] Headline KPIs: Opinion Index meter, Crisis Meter (banded), Share of Voice, sentiment donut
- [x] Opinion-over-time area chart; aspect-sentiment bars (6 tuna facets)
- [x] Trending table (count/rising/sentiment); Top influencers + stance; Detected events (spikes); Top posts by engagement
- [~] Polarization, follow-graph communities, conversation-depth widgets — deferred (catalog items for a later pass)

> Verified live: ran analysis (9 posts, lexicon) and screenshotted the dashboard — Opinion Index +30.2,
> Crisis Meter 22.2 (Calm), all panels populated. AI toggle flips engine (lexicon ⇄ claude when key present).

## Phase 6 — Narrative shapers (enhancement)  ✅ done (2026-06-24)
- [x] Shared `src/utils/accountTypes.ts` — allowed types, shaper set, `typeBoost` (single source)
- [x] `PATCH /api/users/:id` to set `accountType` (self-only; `AccountType` validation) + tests
- [x] Influence-weighted Opinion Index (`/overview.weightedOpinionIndex`: author boost × amplification)
- [x] Journalist/influencer-vs-public **cohort split** + gap (`GET /api/analytics/cohorts`)
- [x] **Narrative provenance & propagation** (`GET /api/analytics/narratives`): originator +
      shaper/official/grassroots origin + per-type propagation footprint
- [x] Seed enriched into a staggered **crisis narrative arc** (journalist breaks → shapers amplify →
      public spike → company responds) so the metrics have movement to show
- [x] Dashboard: "Narrative shapers" section (Cohort panel + Narrative origins panel), weighted-index
      ghost marker; social app: self-service **Account role** picker on own profile
- [x] `openapi.json` → v2.2.0 (PATCH user, /cohorts, /narratives, weightedOpinionIndex); docs +
      [`phase6-narrative-shapers.md`](./phase6-narrative-shapers.md)
- [x] Tests: 114 passing, 19 suites; coverage 94% stmts / 80.5% branch (> 80% gate); client builds clean
- [x] Usability: split the cohort bar into Journalists + Influencers; dashboard **Help** modal
      (every metric in formal plain English + formulas, team credit) + per-panel **ⓘ tooltips**
      (`InfoDot`, single popup); Opinion Index **Raw / Influence-weighted** toggle; charts render
      instantly (animations off)
- [x] **Config-driven company identity** — `COMPANY_NAME`/`COMPANY_ALIASES`/`PLATFORM_NAME` drive
      detection (`companyKeywords()`), the demo **seed** (all company refs templated), and every UI
      label via `GET /api/meta` + `MetaProvider`; no company name hardcoded anywhere. Default is now
      `HappyTuna`; tests pin `COMPANY_NAME=BrightWay` in `test-setup.ts`. openapi → v2.3.0
- [x] **Interactive API docs + agent-ready spec** — `operationId` on all 34 operations + typed
      `components/schemas` for analytics responses; **Swagger UI** at `/openapi` (`swagger-ui-express`),
      raw spec at `/openapi.json`; title → "BrightTweets API". openapi → v2.4.0. Lays the groundwork
      for generating an MCP server / agent tools later.
- [~] Polarization, follow-graph communities, conversation-depth widgets — still deferred (catalog items)

> Verified live: reseeded the arc, ran analysis (16 posts, lexicon), screenshotted `/app/dashboard` —
> Opinion Index −10.1 (weighted −9.3), Crisis Meter 100, a detected spike (z=3.32), #brightwaymercury
> shaper-led by `maria_chen` (−45.8), cohort gap shapers −12.4 vs public −20.

## Continuous
- [ ] Keep `PLAN.md`, `TASKS.md`, and the rest of `docs/` in sync with reality
- [ ] Maintain test coverage > 80% on every change
- [ ] Update `architecture.md` when components/data model change
- [ ] Update `analytics-methodology.md` when a metric is added/changed
