# BrightWay Social Platform — Documentation

All project documentation lives in this `docs/` folder. It covers the social media platform +
public-opinion analytics we build for the BrightWay tuna-company crisis simulation.

## Index

- [**PLAN.md**](./PLAN.md) — plan of record: scope, key decisions, data model, API, phasing.
- [**TASKS.md**](./TASKS.md) — execution checklist, maintained throughout the project.
- [**architecture.md**](./architecture.md) — system components, boundaries (what we own vs the
  bot/event team), data model, request flows, auth model, tech stack, directory layout.
- [**analytics-methodology.md**](./analytics-methodology.md) — how every metric is computed: the
  hybrid sentiment engine, the Opinion Index, Crisis Meter, aspect-based sentiment, trending,
  spike/event-footprint detection, influence & polarization, narrative-shaper analytics, plus
  the company-keyword and tuna-aspect lexicons.
- [**design.md**](./design.md) — the BrightTweets design system: palette, type, 3-column layout,
  the "waterline" signature, and account-type identity styling.
- [**phase6-narrative-shapers.md**](./phase6-narrative-shapers.md) — what was decided and built for
  the influencer/journalist "narrative shaper" analytics (weighted index, cohort split, narrative
  provenance), with the demo crisis arc and verification.

## Live API docs

- **`/openapi`** — interactive Swagger UI (browse + try every endpoint).
- **`/openapi.json`** — the raw OpenAPI 3.0 spec (`public/openapi.json`). Every operation has an
  `operationId` and typed schemas, so it also drives client codegen and agent/MCP tooling.

## Related (repo root)

- [`../CLAUDE.md`](../CLAUDE.md) — coding standards, testing requirements, and house rules.
- [`../README.md`](../README.md) — short project overview + quick start.

## How to keep docs current

These docs are **living artifacts**, not a one-time write-up:

- Changing a component or the data model → update [`architecture.md`](./architecture.md).
- Adding or changing a metric → update [`analytics-methodology.md`](./analytics-methodology.md).
- Changing scope, decisions, or phases → update [`PLAN.md`](./PLAN.md) and [`TASKS.md`](./TASKS.md).
