# Phase 3 — Redefining the product for its actual purpose

The old system tried to be a B2B SaaS for SMSF trustees at A$29/month. The real intent was always a personal investment intelligence OS for one user: James. This phase describes what the new system should actually be, given that fact. It is opinionated. One recommendation per question, not five.

## The fundamental reframe

The new system has one user. There is no signup flow, no login, no password reset, no email verification, no subscription, no billing, no admin panel, no support inbox, no marketing site, no AFSL or CAR posture, no compliance review, no general-advice disclaimer, no terms of service, no privacy policy modal, no cookie banner, no analytics tracking, no onboarding wizard, no demo account, no role-based access control, no multi-tenancy, no row-level security, no organisations, no teams, no invites, no rate limiting against external abuse (rate limit EODHD calls from the application side, but no need to defend against unauthenticated traffic), no JWT, no token revocation, no `user_id` column on anything.

Every line of code in the old repo that exists to manage these concerns is dead weight in the new one. The cost of removing them isn't just the code itself — it's every architectural decision they shaped. Tables don't need a `user_id`. Endpoints don't need an auth chain. Migrations don't need RLS policies. The schema gets dramatically simpler. The route layer collapses.

The right framing for the new system is "a piece of software James runs to think better about his own money." It is closer to a personal Jupyter notebook with persistence than it is to a web app.

## What the system is for

Three concrete uses, in priority order:

1. **Daily decision support**: every weekday morning, James wants to know which of his holdings has changed signal, what the broader market regime looks like, what tax actions are pending (CGT discount eligibility dates, Div 296 exposure, franking events coming up), and whether any regulatory release in the last day affects his positions. He should be able to consume this in under five minutes over coffee.

2. **Periodic deep work**: weekly or monthly, James wants to investigate specific decisions in more depth — does the model still like BHP, what changed since last month, what are the top three SHAP features driving the current signal, what would the tax cost be of selling 200 shares of CBA today versus in three months. This is interactive analysis, not a fixed dashboard view.

3. **Strategy evolution journal**: across quarters, James wants to record decisions, revisit them, and learn from them. What did the model think? What did he do? What was the outcome? This is the most valuable long-term feature and the one most often skipped in tooling like this. It is not a feature, it is a habit, and the system should make it cheap.

Notice what's not in this list: no "user growth", no "engagement", no "retention", no notifications that nag, no email drip campaigns, no streaks. The system exists to help James make better decisions about his own capital. Anything that distracts from that is wrong.

## Asset class scope

ASX equities first. The Model A pipeline, SHAP explanations, regime classifier, and screening engine all already work on this asset class and the data source (EODHD) is solid. Don't try to broaden the asset universe before the equities loop is genuinely useful.

Tax alpha is a cross-cutting layer over positions, not a feature. Whether James holds BHP or CBA or a CHESS-sponsored ETF, the tax math (CGT discount tier, franking gross-up, Division 296 exposure) is the same shape. The new repo should treat positions as the primitive and produce tax-adjusted views as a deterministic computation over them.

Property is a future module. Not in the first three months. The data sources are different (CoreLogic, council records, RPData), the modelling is qualitatively different (one or two assets, not 500), and the value of building it badly is much lower than the cost of getting distracted from the equities loop. When it appears, it appears as a separate module with its own ingestion, valuation, and tax treatment, and it shares only the journal and the tax alpha layer with the equities side.

Regulatory monitoring is a single scheduled job, not a feature module. Pull ASIC media releases, RBA monetary policy decisions, ATO ruling updates, ASX listing changes once a day. Store anything new in a `regulatory_events` table. Surface in the morning brief if there's anything to surface. Don't build a regulatory dashboard.

## What survives from the old vision

- ML signals on the Model A pipeline. Carried forward exactly.
- SHAP explanations per signal, persisted alongside the signal row. The "why is BHP a Buy today" answer is the differentiator and the one feature with no off-the-shelf substitute.
- Screening as a personal tool — define a rule, see which stocks match today, optionally backtest. The walk-forward methodology survives; the published-screen catalogue and archetype clustering UI do not need to.
- Tax alpha — CGT discount tier tracking, Division 296 exposure, franking gross-up, foreign holdings lots with RBA FX. The math is correct; the API surface around it should collapse to a few pure functions taking position lists and returning tax-adjusted views.
- Regime detection as ambient context. One value per day. Used to tighten signal thresholds in neutral / bear regimes. No regime dashboard.
- Strategy evolution as a personal journal. Markdown files in the repo or rows in a `decisions` table. Each row records what the model thought, what James did, why, and (later) what happened. The lowest-tech version is enough.
- Regulatory awareness as a daily-ingest job and a section in the morning brief.

## What deliberately gets dropped

- Onboarding wizards. James knows how to use the system; he built it.
- Marketing surface. The repo has no public face.
- Signup flow, login, password reset, email verification, multi-factor auth, session management. Single user means no auth.
- AFSL / CAR consumer-facing compliance posture. Personal capital, no licence required.
- General advice / personal advice distinction in copy. Irrelevant when audience is self.
- Subscription gating, Stripe, feature flags by tier, usage limits. None applicable.
- Multi-channel notification dispatch (Slack, SMS, Discord). Email to self is enough; one channel.
- Admin dashboards, manual job triggers in a UI, user impersonation tools. Run jobs from the command line.
- Compliance review, audit trails for advice generation, REP 798 explainability wrappers. Keep the explainability discipline; drop the regulatory framing.
- The entire Next.js frontend, until the backend has something worth surfacing visually. CLI + email + Jupyter is enough for at least three months.

## What "done" looks like

The first version of "done" is not a polished product. It is:

- A `make morning-brief` command (or equivalent) on James's laptop or a small server that prints a 200-word summary to the terminal and sends the same content as an email to himself.
- A `make daily` cron that refreshes prices, regenerates signals, computes SHAP factors, updates tax-adjusted views for current holdings, and ingests the day's regulatory events.
- A retraining job he can run manually (`make retrain-model-a`) that produces a new versioned artefact under `models/`, validates it against the gates, and either deploys or rejects with a printed reason.
- A small CLI for ad-hoc questions: `asxos signal BHP.AU`, `asxos shap BHP.AU`, `asxos tax-action`, `asxos screen 'mom_6 >= 0.04 and pe_ratio <= 25'`.
- A `decisions/` directory (or table) where James appends a record any time he places a trade, with the model state and his reasoning at the time.

There is no web UI in this version. There is also no public surface — the entire system runs on James's machine or on a single private server reachable only by him.

A future version might add a single Streamlit or htmx page for the morning brief, served only on the local network. But that's earned, not assumed.

## Where the system runs

Local-first is the right default. Postgres in Docker on James's laptop, plus a Mac mini or a tiny always-on machine at home or a $5/month Hetzner box for the daily cron. No cloud platform until there is a reason for one.

Specific recommendation: a single Hetzner Cloud CPX11 (€4.51/month) running Ubuntu, Docker Compose with Postgres and the FastAPI service, jobs via systemd timers, model artefacts on the same disk, daily backup of the Postgres dump to a personal S3 bucket or rsync target. Total monthly cost under €10. Reachable over Tailscale or via SSH; not exposed to the public internet at all.

Why not Render: drift between checked-in YAML and dashboard reality, the cron-creation problem this repo just lived through, the cold-start penalty, and the cost of an always-on service to avoid cold starts is higher than a Hetzner VPS. Render is fine for a SaaS; it's overkill for one user.

Why not Vercel: there's no frontend, and even when there is, Vercel exists for public traffic and edge functions. A personal tool doesn't need either.

Why not stay on Supabase: Supabase is a fine managed Postgres, but it adds a dependency, an admin surface, RLS policies that no longer apply, and a billing relationship. A vanilla Postgres in Docker on the same machine as the application is simpler and more debuggable. The types-gen workflow that justified Supabase in the old repo only matters if there's a frontend consuming the types. There won't be for a while.

Why not Modal or Fly: both are good products for different problems. Modal is overkill for a daily retraining job on a few thousand rows; the LightGBM model takes minutes, not hours. Fly is a closer match to Render and would solve the cron drift, but a VPS is cheaper and more general.

Why not run on James's laptop alone: morning brief should arrive at 7am whether the laptop is open or not. An always-on small server costs €5/month and removes that constraint.

## The "synthesis gap" question

In the old SaaS framing, the question was "what do we surface that nobody else does." For a personal tool the question is different: "what helps me make better decisions about my own capital." The answers are:

- A model that's mine, with explanations I trust, run on data I have control over.
- A tax view that reflects my actual situation (account type, account balances for Div 296, holding lots, franking history).
- A regulatory feed filtered to my universe.
- A journal that makes it cheap to record decisions.

None of this depends on being differentiated from a competitor. It depends only on being useful to one person, accurately, every day.

## The compliance question

Compliance was a major drag on the old project: AFSL considerations, REP 798 wrappers, general-advice language, audit trails, the LAWYER_BRIEF in memory. None of it applies to a personal tool. The new system is not advice, it is software for thinking. James is not licensed and does not need to be, because he is not providing a service to anyone else.

Keep the underlying discipline (every signal has an explanation; every decision gets recorded). Drop the regulatory framing entirely.

## Summary

The product is: a personal investment intelligence OS for James, running on a tiny VPS, with a Postgres database, a FastAPI backend that James talks to via CLI and a daily email, an ML pipeline that retrains weekly or monthly, a tax alpha layer over current holdings, and a decisions journal. No frontend, no auth, no multi-tenancy, no compliance posture, no marketing. The morning brief is the primary UX. The CLI is the secondary UX. Everything else is plumbing.

The system is done when James opens his email at 7am, reads what changed overnight in his portfolio and the wider market, sees the tax actions he should consider today, and is in a position to act on any of them by lunchtime. Nothing more. Nothing less.

Ready for Phase 4?
