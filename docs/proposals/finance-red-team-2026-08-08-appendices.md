# Finance red-team 2026-08-08 — verbatim appendices

Companion evidence record to `finance-red-team-2026-08-08.md`. Nothing here is edited or
summarized: each appendix is the exact artifact as frozen/delivered during the mission.
Repo baseline: origin/main `1b471b60cdaa176692cc5f987e8399acfdab03d9`. Firewall: nothing in
this record is a direction regarding any live position; all HUBS ESS/CGT facts are
UNKNOWN / NOT RELIABLE pending Division 83A facts and accountant review.

Contents:
- Appendix A — Frozen evidence packet (content-addressed JSON)
- Appendix B — Finance-rule manifest (Step -1 denominator freeze; NOT fully reconciled)
- Appendix C — Panel #1: finance adversary
- Appendix D — Panel #3: thesis-milestone-monitor (ladder audit, flags only)
- Appendix E — Panel #4: portfolio-coherence-reviewer (coherence read + self-inventory)
- Appendix F — Panel #5: benchmark-performance-analyst (identity/method, no return calc)
- Appendix G — Panel #6: macro-economist (regime-gate design audit)
- Appendix H — Panel #7: tax-spec-conformance (consequence-gap audit)
- Appendix I — Plan-level critique 1: arbi-red-team (PROCEED-WITH-CHANGES)
- Appendix J — Plan-level critique 2: completeness critic (12 gaps)
- Appendix K — Dissent pass over the draft synthesis (arbi-red-team)

---

## Appendix A — Frozen evidence packet

```json
{
 "meta": {
  "packet_id": "finance-red-team-evidence-2026-08-08",
  "built_at_utc": "2026-08-08T09:20:00Z",
  "repo_sha_origin_main": "1b471b60cdaa176692cc5f987e8399acfdab03d9",
  "working_tree": "identical to origin/main; only untracked file is docs/proposals/arbi-outcome-programme-convergence-sprint-2026-08-08.md (out of scope, must not be modified)",
  "db": "Supabase project via supabase-ro MCP (read-only role)",
  "purpose": "Frozen evidence packet for the finance red-team mission (rev 4, governor-corrected). Every panel agent cites entries by id+hash. Claims outside this packet must be re-queried into an addendum before use.",
  "corrected_hubs_frame": "Confirmed semantic/actionability defect; born-breached if intended as an immediate hard-exit trigger. Lock-at-authoring and intended trigger semantics remain unproven at authoring time; the row's tax_notes NOW documents the stop as ALERT/REVIEW-only while the ESS window is locked. All HUBS ESS/CGT dates and computations are UNKNOWN / NOT RELIABLE pending verified Division 83A facts and accountant review.",
  "governor_answers_2026_08_08": {
   "hubs_230_stop_at_authoring": "Placeholder / experiment (not firmed up)",
   "cba_42_45_band": "Error \u2014 wrong numbers from the start",
   "intended_trigger_semantics": "Immediate exit prompt \u2014 James expected a triggered condition to push an exit decision that day"
  },
  "unavailable_facts": [
   "ESS lock-window end date (plan administrator; tax_notes says 'confirm and record when known')",
   "Verified Division 83A acquisition date / cost base for the ESPP lot (accountant review pending)",
   "Brokerage-statement AUD/USD acquisition rate (lot carries 0.6450 flagged 'estimated'; vendor FX 0.7171 on 2026-05-31; AUD P&L SIGN depends on resolution)",
   "Cash-flow series for TWR/MWR (capital_aud alone is not a valid return method)",
   "Benchmark TR identity/licence verification (snapshots carry benchmark_tr_level; index identity to be confirmed from code, not assumed)",
   "HUBS Q2 FY26 actual results vs the falsifier metrics written in earnings_notes (print was 2026-08-05 AMC; no system surface evaluated it)",
   "macro_thesis_id=11 machine_conditions (NULL \u2014 tonight's scorer can evaluate only 2 of 3 approved macro theses)"
  ],
  "entry_hashes_sha256_16": {
   "E01_theses_active_watching": "21ff37f2719bfa9c",
   "E02_theses_research_summary": "16d71743c2b8ebd0",
   "E03_active_profile": "77859aad840e33de",
   "E04_model_versions": "417d7cfe045d6562",
   "E05_prices": "22e3234378dca4da",
   "E06_snapshots_lots_index": "028a9870ed255b9f",
   "E07_rules_infra": "e7a394d10cd377cb",
   "E08_fx_jobs_brief": "ac39a924b03043fe",
   "E09_hubs_news": "5870e314f2344d6c",
   "D01_derived_observations": "28d5d505457d0a37"
  },
  "packet_hash_note": "hash = sha256 over the canonical-JSON (sorted keys, compact) serialization of each entry; first 16 hex chars"
 },
 "entries": {
  "E01_theses_active_watching": {
   "queried_at": "2026-08-08 09:15:38.852374+00",
   "sql": "SELECT now() AS queried_at, jsonb_agg(to_jsonb(t) - 'thesis_text' - 'report_sections' ORDER BY t.thesis_id) AS rows FROM theses t WHERE t.status IN ('active','watching');",
   "units": "stop/target/band prices: native listing currency (CBA.AU=AUD, HUBS.NYSE=USD). Dates: UTC timestamps.",
   "result": [
    {
     "status": "watching",
     "symbol": "CBA.AU",
     "themes": [
      "big-4-banks"
     ],
     "closed_at": null,
     "opened_at": "2026-05-28T10:31:46.118213+00:00",
     "tax_notes": null,
     "thesis_id": 1,
     "stop_price": 38,
     "target_price": 60,
     "source_run_id": null,
     "timeline_days": 540,
     "actual_exit_at": null,
     "earnings_notes": "",
     "revisit_due_at": "2026-06-27T10:31:46.118213+00:00",
     "actual_entry_at": null,
     "conviction_level": null,
     "entry_band_lower": 42,
     "entry_band_upper": 45,
     "actual_exit_price": null,
     "analyst_buy_count": null,
     "governance_status": "approved",
     "last_revisited_at": "2026-05-28T10:31:46.118213+00:00",
     "actual_entry_price": null,
     "analyst_sell_count": null,
     "analyst_updated_at": null,
     "next_earnings_date": null,
     "analyst_neutral_count": null,
     "invalidation_conditions": [],
     "analyst_consensus_target": null
    },
    {
     "status": "active",
     "symbol": "HUBS.NYSE",
     "themes": [
      "us-saas-ai",
      "us-equities"
     ],
     "closed_at": null,
     "opened_at": "2026-05-31T00:00:00+00:00",
     "tax_notes": "ESPP acquisition (broker_ref ESPP-2026-05-31, 15% plan discount vs 2026-05-29 close). Shares are inside a LOCKED employee-share-scheme trading window \u2014 NON-DISPOSABLE until the window opens. While locked: the $230 stop and the triggered invalidation condition #1 operate as ALERT/REVIEW levels only, not executable sell triggers; discipline events during the lock are documented revisions, not exits. Confirm lock-window end date from the plan administrator and record it here when known. Acquisition FX rate on the lot (0.6450) is flagged estimated and disagrees with vendor FX (0.7171 on 2026-05-31) \u2014 resolve from the brokerage statement; the AUD P&L sign depends on it.",
     "thesis_id": 2,
     "stop_price": 230,
     "target_price": 318,
     "source_run_id": null,
     "timeline_days": 365,
     "actual_exit_at": null,
     "earnings_notes": "Q2 FY26 print expected Tue-Wed Aug 5 2026 AMC (aggregator-sourced, IR page unverified \u2014 recheck ~Jul 22). First full quarter of outcome-based Breeze pricing. Falsifier metrics to check in the print: net adds <10k/qtr, avg sub revenue/customer stalling <=$11,700 CC, NRR <103%, credit consumption decelerating sharply from +67% QoQ, revenue below $897M guide or FY26 cut. Analyst consensus ~31 Buy/4 Hold/1 Sell, PT range ~$272-305 (aggregators disagree; BofA $180 Underperform is the anchor bear). UNBOUND flagship event Sept 16-18.",
     "revisit_due_at": "2026-08-03T04:13:50.372298+00:00",
     "actual_entry_at": "2026-05-31T00:00:00+00:00",
     "conviction_level": null,
     "entry_band_lower": 185,
     "entry_band_upper": 190,
     "actual_exit_price": null,
     "analyst_buy_count": null,
     "governance_status": "approved",
     "last_revisited_at": "2026-07-04T04:13:50.372298+00:00",
     "actual_entry_price": 187.54,
     "analyst_sell_count": null,
     "analyst_updated_at": null,
     "next_earnings_date": "2026-08-05",
     "analyst_neutral_count": null,
     "invalidation_conditions": [
      {
       "note": "auto: close=192.120000 below 230 on 2026-07-03",
       "status": "triggered",
       "condition": "Price closes below $230 stop on volume"
      },
      {
       "status": "active",
       "condition": "50d MA ($243.61) not recaptured within 2 weeks of breach"
      },
      {
       "status": "active",
       "condition": "Macro regime shifts to risk_off_disorderly"
      },
      {
       "status": "active",
       "condition": "Three or more sell-side downgrades with consensus target below $220"
      }
     ],
     "analyst_consensus_target": null
    }
   ]
  },
  "E02_theses_research_summary": {
   "queried_at": "2026-08-08 09:15:40.818392+00",
   "sql": "SELECT now(), t.status, count(*), jsonb_agg(jsonb_build_object('thesis_id',t.thesis_id,'symbol',t.symbol,'stop',t.stop_price,'target',t.target_price,'band_lo',t.entry_band_lower,'band_hi',t.entry_band_upper,'gov',t.governance_status) ORDER BY t.thesis_id) FROM theses t WHERE t.status NOT IN ('active','watching') GROUP BY t.status;",
   "units": "AUD (all .AU symbols)",
   "note": "All 11 research theses have DEGENERATE POINT BANDS (band_lo == band_hi) \u2014 a systematic authoring artifact. All governance_status='approved' by default, stop/target NULL.",
   "result": {
    "status": "research",
    "n": 11,
    "summary": [
     {
      "gov": "approved",
      "stop": null,
      "symbol": "TPW.AU",
      "target": null,
      "band_hi": 5.67,
      "band_lo": 5.67,
      "thesis_id": 3
     },
     {
      "gov": "approved",
      "stop": null,
      "symbol": "ATR.AU",
      "target": null,
      "band_hi": 0.555,
      "band_lo": 0.555,
      "thesis_id": 4
     },
     {
      "gov": "approved",
      "stop": null,
      "symbol": "WTC.AU",
      "target": null,
      "band_hi": 36.88,
      "band_lo": 36.88,
      "thesis_id": 5
     },
     {
      "gov": "approved",
      "stop": null,
      "symbol": "BAP.AU",
      "target": null,
      "band_hi": 0.465,
      "band_lo": 0.465,
      "thesis_id": 6
     },
     {
      "gov": "approved",
      "stop": null,
      "symbol": "BLX.AU",
      "target": null,
      "band_hi": 1.72,
      "band_lo": 1.72,
      "thesis_id": 7
     },
     {
      "gov": "approved",
      "stop": null,
      "symbol": "WA1.AU",
      "target": null,
      "band_hi": 12.57,
      "band_lo": 12.57,
      "thesis_id": 8
     },
     {
      "gov": "approved",
      "stop": null,
      "symbol": "OCL.AU",
      "target": null,
      "band_hi": 10.2,
      "band_lo": 10.2,
      "thesis_id": 9
     },
     {
      "gov": "approved",
      "stop": null,
      "symbol": "NEC.AU",
      "target": null,
      "band_hi": 0.915,
      "band_lo": 0.915,
      "thesis_id": 10
     },
     {
      "gov": "approved",
      "stop": null,
      "symbol": "EBR.AU",
      "target": null,
      "band_hi": 0.38,
      "band_lo": 0.38,
      "thesis_id": 11
     },
     {
      "gov": "approved",
      "stop": null,
      "symbol": "LLC.AU",
      "target": null,
      "band_hi": 2.98,
      "band_lo": 2.98,
      "thesis_id": 12
     },
     {
      "gov": "approved",
      "stop": null,
      "symbol": "KPG.AU",
      "target": null,
      "band_hi": 3.57,
      "band_lo": 3.57,
      "thesis_id": 13
     }
    ]
   }
  },
  "E03_active_profile": {
   "queried_at": "2026-08-08 09:15:43.033487+00",
   "sql": "SELECT now(), jsonb_agg(to_jsonb(p)) FROM profiles p WHERE p.is_active;",
   "units": "capital_aud/min_position_aud: AUD. Caps: fractions (0.1 = 10%).",
   "note": "per_name_cap_pct=0.10 while the live portfolio is 100% one name (E06). cash_floor_pct=0. leverage_cap=1.",
   "result": {
    "name": "baseline",
    "is_active": true,
    "created_at": "2026-05-22T21:46:42.762642+00:00",
    "profile_id": 1,
    "updated_at": "2026-07-04T04:13:52.455813+00:00",
    "capital_aud": 6666.98,
    "account_type": "individual",
    "leverage_cap": 1,
    "horizon_years": 10,
    "cash_floor_pct": 0,
    "risk_tolerance": "balanced",
    "sector_cap_pct": 0.3,
    "excluded_sectors": [],
    "excluded_symbols": [],
    "min_position_aud": 1000,
    "per_name_cap_pct": 0.1,
    "score_weights_json": {
     "prob_up": "0.6",
     "expected_return": "0.4"
    },
    "risk_tolerance_scalar": 0.5,
    "defer_near_boundary_sells": true
   }
  },
  "E04_model_versions": {
   "queried_at": "2026-08-08 09:15:44.919213+00",
   "sql": "SELECT now(), jsonb_agg(jsonb_build_object('model',m.model,'version',m.version,'is_active',m.is_active,'approved',m.approved_for_allocation)) FROM model_versions m;",
   "result": [
    {
     "model": "model_a",
     "version": "v1_5",
     "approved": false,
     "is_active": true
    }
   ],
   "note": "Rule #11 quarantine mechanically in place: approved_for_allocation=false."
  },
  "E05_prices": {
   "queried_at": "2026-08-08 09:16:16.456123+00",
   "sql": "HUBS.NYSE daily closes dt>='2026-05-01' (USD); CBA.AU latest (AUD); AXJO.INDX latest (index points).",
   "units": "HUBS: USD. CBA: AUD. AXJO: index points (price index, not total return).",
   "hubs_closes_usd": [
    {
     "dt": "2026-05-27",
     "close": 200.72
    },
    {
     "dt": "2026-05-28",
     "close": 198.8
    },
    {
     "dt": "2026-05-29",
     "close": 220.63
    },
    {
     "dt": "2026-06-01",
     "close": 262.2
    },
    {
     "dt": "2026-06-02",
     "close": 240.16
    },
    {
     "dt": "2026-06-03",
     "close": 222.45
    },
    {
     "dt": "2026-06-04",
     "close": 220.37
    },
    {
     "dt": "2026-06-05",
     "close": 212.64
    },
    {
     "dt": "2026-06-08",
     "close": 208.12
    },
    {
     "dt": "2026-06-09",
     "close": 197.69
    },
    {
     "dt": "2026-06-10",
     "close": 192.79
    },
    {
     "dt": "2026-06-11",
     "close": 186.43
    },
    {
     "dt": "2026-06-12",
     "close": 187.98
    },
    {
     "dt": "2026-06-15",
     "close": 186.06
    },
    {
     "dt": "2026-06-16",
     "close": 182.85
    },
    {
     "dt": "2026-06-17",
     "close": 176.71
    },
    {
     "dt": "2026-06-18",
     "close": 176.03
    },
    {
     "dt": "2026-06-22",
     "close": 172.8
    },
    {
     "dt": "2026-06-23",
     "close": 173.29
    },
    {
     "dt": "2026-06-24",
     "close": 180.73
    },
    {
     "dt": "2026-06-25",
     "close": 170.28
    },
    {
     "dt": "2026-06-26",
     "close": 185.47
    },
    {
     "dt": "2026-06-29",
     "close": 184.47
    },
    {
     "dt": "2026-07-01",
     "close": 187.72
    },
    {
     "dt": "2026-07-02",
     "close": 192.12
    },
    {
     "dt": "2026-07-06",
     "close": 193.84
    },
    {
     "dt": "2026-07-07",
     "close": 205.2
    },
    {
     "dt": "2026-07-08",
     "close": 197.82
    },
    {
     "dt": "2026-07-09",
     "close": 205.95
    },
    {
     "dt": "2026-07-10",
     "close": 207.48
    },
    {
     "dt": "2026-07-13",
     "close": 217.59
    },
    {
     "dt": "2026-07-14",
     "close": 209.68
    },
    {
     "dt": "2026-07-15",
     "close": 215.33
    },
    {
     "dt": "2026-07-16",
     "close": 224.57
    },
    {
     "dt": "2026-07-17",
     "close": 224.26
    },
    {
     "dt": "2026-07-20",
     "close": 231.21
    },
    {
     "dt": "2026-07-21",
     "close": 218.578
    },
    {
     "dt": "2026-07-22",
     "close": 204.9
    },
    {
     "dt": "2026-07-23",
     "close": 190
    },
    {
     "dt": "2026-07-24",
     "close": 204.89
    },
    {
     "dt": "2026-07-27",
     "close": 223.01
    },
    {
     "dt": "2026-07-28",
     "close": 238.04
    },
    {
     "dt": "2026-07-29",
     "close": 251.12
    },
    {
     "dt": "2026-07-30",
     "close": 233.11
    },
    {
     "dt": "2026-07-31",
     "close": 237.36
    },
    {
     "dt": "2026-08-03",
     "close": 239.92
    },
    {
     "dt": "2026-08-04",
     "close": 248.89
    },
    {
     "dt": "2026-08-05",
     "close": 250.21
    },
    {
     "dt": "2026-08-06",
     "close": 202.43
    },
    {
     "dt": "2026-08-07",
     "close": 210.45
    }
   ],
   "cba_latest_aud": {
    "dt": "2026-08-07",
    "close": 178.01
   },
   "axjo_latest": {
    "dt": "2026-08-07",
    "close": 9263.6
   }
  },
  "E06_snapshots_lots_index": {
   "queried_at": "2026-08-08 09:16:56.244243+00",
   "sql": "portfolio_daily_snapshots columns + latest 5 rows; holding_lots all; universe index symbols.",
   "units": "snapshots *_aud: AUD. fx_rate_audusd: AUDUSD. holding_lots cost_base_usd: USD; cost_base_normal/cost_base_div296: AUD (CGT base at acquisition FX 0.6450 \u2014 DISPUTED, see meta.unavailable_facts).",
   "snapshot_columns": [
    "as_of",
    "capital_aud",
    "holdings_mv_aud",
    "cash_aud",
    "benchmark_xjo_close",
    "benchmark_tr_level",
    "trailing_div_yield_pct",
    "holdings_count",
    "ingested_at",
    "us_holdings_mv_aud",
    "us_holdings_cost_aud",
    "fx_rate_audusd",
    "unrealised_fx_pnl_aud"
   ],
   "snapshots_latest5": [
    {
     "as_of": "2026-08-07",
     "cash_aud": 0,
     "capital_aud": 7147.021367,
     "fx_rate_audusd": 0.7067,
     "holdings_count": 1,
     "holdings_mv_aud": 7147.021367,
     "benchmark_tr_level": 12001.803172,
     "us_holdings_mv_aud": 7147.021367,
     "benchmark_xjo_close": 9263.6,
     "us_holdings_cost_aud": 6978.23,
     "unrealised_fx_pnl_aud": 168.791367,
     "trailing_div_yield_pct": 4
    },
    {
     "as_of": "2026-08-05",
     "cash_aud": 0,
     "capital_aud": 8509.338246,
     "fx_rate_audusd": 0.7057,
     "holdings_count": 1,
     "holdings_mv_aud": 8509.338246,
     "benchmark_tr_level": 11952.852104,
     "us_holdings_mv_aud": 8509.338246,
     "benchmark_xjo_close": 9227.8,
     "us_holdings_cost_aud": 6978.23,
     "unrealised_fx_pnl_aud": 1531.108246,
     "trailing_div_yield_pct": 4
    },
    {
     "as_of": "2026-08-03",
     "cash_aud": 0,
     "capital_aud": 8224.653621,
     "fx_rate_audusd": 0.7001,
     "holdings_count": 1,
     "holdings_mv_aud": 8224.653621,
     "benchmark_tr_level": 11680.269731,
     "us_holdings_mv_aud": 8224.653621,
     "benchmark_xjo_close": 9019.3,
     "us_holdings_cost_aud": 6978.23,
     "unrealised_fx_pnl_aud": 1246.423621,
     "trailing_div_yield_pct": 4
    },
    {
     "as_of": "2026-07-31",
     "cash_aud": 0,
     "capital_aud": 8111.405382,
     "fx_rate_audusd": 0.7023,
     "holdings_count": 1,
     "holdings_mv_aud": 8111.405382,
     "benchmark_tr_level": 11621.484,
     "us_holdings_mv_aud": 8111.405382,
     "benchmark_xjo_close": 8976.8,
     "us_holdings_cost_aud": 6978.23,
     "unrealised_fx_pnl_aud": 1133.175382,
     "trailing_div_yield_pct": 4
    },
    {
     "as_of": "2026-07-30",
     "cash_aud": 0,
     "capital_aud": 7957.104253,
     "fx_rate_audusd": 0.7031,
     "holdings_count": 1,
     "holdings_mv_aud": 7957.104253,
     "benchmark_tr_level": 11608.455578,
     "us_holdings_mv_aud": 7957.104253,
     "benchmark_xjo_close": 8967.7,
     "us_holdings_cost_aud": 6978.23,
     "unrealised_fx_pnl_aud": 978.874253,
     "trailing_div_yield_pct": 4
    }
   ],
   "holding_lots": [
    {
     "id": 1,
     "notes": "ESPP lot \u2014 24 shares HubSpot Inc at USD 187.54/share. AUD/USD 0.6450 estimated \u2014 update from brokerage statement.",
     "symbol": "HUBS.NYSE",
     "quantity": 24,
     "broker_ref": "ESPP-2026-05-31",
     "created_at": "2026-06-03T09:37:46.160664+00:00",
     "updated_at": "2026-06-03T09:37:46.160664+00:00",
     "acquired_at": "2026-05-31",
     "disposed_at": null,
     "account_type": "individual",
     "cost_base_usd": 4500.96,
     "cost_base_div296": 6978.23,
     "cost_base_normal": 6978.23,
     "disposal_fx_rate": null,
     "disposal_proceeds": null,
     "acquisition_fx_rate": 0.645,
     "disposal_proceeds_usd": null
    }
   ],
   "index_symbols": [
    {
     "symbol": "AXJO.INDX",
     "is_active": false
    }
   ]
  },
  "E07_rules_infra": {
   "queried_at": "2026-08-08 09:16:59.623993+00",
   "sql": "fx tables list; screening_rules count; macro_theses summary; macro_thesis_outcomes count.",
   "result": {
    "fx_tables": [
     "fx_rates",
     "rs_corporate_actions"
    ],
    "screening_rules_count": 0,
    "macro_theses": [
     {
      "id": 7,
      "gov": "approved",
      "quadrant": "falling_growth_rising_inflation",
      "title_60": "Sticky ~5% AU long end: term-premium regime persists and kee",
      "has_machine_conditions": true
     },
     {
      "id": 6,
      "gov": "approved",
      "quadrant": "falling_growth_falling_inflation",
      "title_60": "Breadth-led catch-down: thin 200d breadth under a strong ind",
      "has_machine_conditions": true
     },
     {
      "id": 10,
      "gov": "rejected",
      "quadrant": "falling_growth_falling_inflation",
      "title_60": "ASX breadth deterioration without a volatility catalyst -- n",
      "has_machine_conditions": false
     },
     {
      "id": 11,
      "gov": "approved",
      "quadrant": "rising_growth_falling_inflation",
      "title_60": "Un-inverted US yield curve + benign AU credit backdrop -- no",
      "has_machine_conditions": false
     }
    ],
    "macro_outcomes_count": 0
   }
  },
  "E08_fx_jobs_brief": {
   "queried_at": "2026-08-08 09:17:23.699792+00",
   "sql": "fx_rates latest; job_runs for check_thesis_invalidations/score_macro_theses/compose_brief (latest 9); brief_runs latest section_runs.",
   "result": {
    "fx_latest": {
     "dt": "2026-08-07",
     "pair": "AUDUSD",
     "rate": 0.7067,
     "source": "eodhd"
    },
    "job_runs_recent": [
     {
      "err": "",
      "job": "compose_brief",
      "as_of": "2026-08-08",
      "status": "success"
     },
     {
      "err": "",
      "job": "compose_brief",
      "as_of": "2026-08-05",
      "status": "success"
     },
     {
      "err": "",
      "job": "check_thesis_invalidations",
      "as_of": "2026-08-05",
      "status": "success"
     },
     {
      "err": "",
      "job": "check_thesis_invalidations",
      "as_of": "2026-08-04",
      "status": "success"
     },
     {
      "err": "",
      "job": "compose_brief",
      "as_of": "2026-08-04",
      "status": "success"
     },
     {
      "err": "",
      "job": "compose_brief",
      "as_of": "2026-08-03",
      "status": "success"
     },
     {
      "err": "",
      "job": "check_thesis_invalidations",
      "as_of": "2026-08-03",
      "status": "success"
     },
     {
      "err": "",
      "job": "compose_brief",
      "as_of": "2026-08-02",
      "status": "success"
     },
     {
      "err": "",
      "job": "check_thesis_invalidations",
      "as_of": "2026-08-02",
      "status": "success"
     }
    ],
    "brief_latest": {
     "as_of": "2026-08-08",
     "composed_at": "2026-08-08T04:51:02.888613+00:00",
     "section_runs": {
      "new_ideas": {
       "error": "regime=risk_off_orderly",
       "status": "suppressed",
       "elapsed_ms": 0,
       "item_count": 0
      },
      "watchlist": {
       "error": null,
       "status": "ok",
       "elapsed_ms": 502,
       "item_count": 1
      },
      "wealth_state": {
       "error": null,
       "status": "ok",
       "elapsed_ms": 1010,
       "item_count": 3
      },
      "active_theses": {
       "error": null,
       "status": "ok",
       "elapsed_ms": 2305,
       "item_count": 1
      },
      "market_context": {
       "error": null,
       "status": "ok",
       "elapsed_ms": 510,
       "item_count": 2
      },
      "section_health": {
       "error": null,
       "status": "ok",
       "elapsed_ms": 0,
       "item_count": 2
      },
      "tax_operational": {
       "error": null,
       "status": "ok",
       "elapsed_ms": 1011,
       "item_count": 0
      },
      "theme_dashboard": {
       "error": null,
       "status": "ok",
       "elapsed_ms": 1594,
       "item_count": 1
      },
      "opportunity_cost": {
       "error": "no opportunity cost scenarios computed for this date",
       "status": "no_data",
       "elapsed_ms": 1544,
       "item_count": 0
      },
      "underlying_drivers": {
       "error": null,
       "status": "ok",
       "elapsed_ms": 1853,
       "item_count": 2
      }
     }
    }
   },
   "note": "NO check_thesis_invalidations run for as_of 2026-08-06/07/08 \u2014 the 2026-08-06 earnings crash and stop re-breach have NEVER been evaluated by the invalidation job."
  },
  "E09_hubs_news": {
   "queried_at": "2026-08-08 09:18:05.624989+00",
   "sql": "holding_news WHERE symbols @> '[\"HUBS.NYSE\"]' latest 5.",
   "result": [
    {
     "url": "https://finance.yahoo.com/markets/stocks/articles/hubspot-hubs-could-39-undervalued-141510",
     "title": "HubSpot (HUBS) Could Be 39% Undervalued Following Its Guidance Cut",
     "polarity": 0.997,
     "published": "2026-08-07"
    },
    {
     "url": "https://finance.yahoo.com/technology/ai/articles/cloud-ai-fortude-revolutionizes-erp-12403",
     "title": "Cloud AI Update - Fortude Revolutionizes ERP with AI-Driven Delivery Model",
     "polarity": 0.954,
     "published": "2026-08-07"
    }
   ],
   "note": "A 'guidance cut' headline scored 0.997 positive polarity. Guidance cut corroborates that a written falsifier in E01 earnings_notes ('revenue below $897M guide or FY26 cut') may have fired \u2014 unevaluated by any system surface."
  },
  "D01_derived_observations": {
   "derived_by": "packet builder (main loop), from E01/E05/E08 \u2014 DERIVED, not raw; agents must re-verify against the raw entries before relying on these",
   "observations": [
    "Authoring context: last close before thesis open (2026-05-29) was 220.63 \u2014 below the 230 stop. The next close (2026-06-01) was 262.20 \u2014 above it. 'Born-breached' holds only on the latest-close-at-authoring reading.",
    "Breach/recapture timeline (closing basis, vs 230): breach 06-03..07-17; single-day recapture 07-20 (231.21); re-breach 07-21..07-27; recapture 07-28..08-05 (7 consecutive closes, high 251.12 on 07-29... 250.21 on 08-05); re-breach 08-06 (202.43, \u221219.1% day, Q2 FY26 print 08-05 AMC) and 08-07 (210.45).",
    "The invalidation condition #1 status='triggered' (note dated 2026-07-03, close 192.12 \u2014 that close is dt 2026-07-02; 07-03 was the run date) was NEVER re-evaluated: no un-trigger/re-arm semantics exist. Any surface reading the status field (including the 2026-08-08 brief mock's 'day 36 below stop') reports stale state contradicted by E05.",
    "check_thesis_invalidations last ran as_of 2026-08-05 (E08): the 08-06 crash/re-breach is unevaluated by the discipline machinery as of packet build.",
    "Profile per_name_cap_pct=0.10 (E03) vs holdings_count=1 at 100% of capital (E06): the system's own configured cap is exceeded 10x with no surface flagging it.",
    "AUD P&L sign dispute: cost_base_usd 4500.96; at lot FX 0.6450 \u2192 AUD cost 6978.23 (booked); at vendor FX 0.7171 (2026-05-31) \u2192 AUD cost \u2248 6277.11. Value 2026-08-07: 24\u00d7210.45=5050.80 USD \u00f7 0.7067 \u2248 7147.02 AUD. Native USD P&L +549.84; AUD P&L +168.79 (booked FX) vs \u2248 +869.9 (vendor FX) \u2014 both positive at current prices, but the tax_notes warning stands: the sign flips at different price/FX combinations and the CGT base is unresolved.",
    "All 11 research theses have band_lo == band_hi (E02): degenerate point 'bands' \u2014 systematic authoring artifact.",
    "CBA watching thesis: revisit_due 2026-06-27 \u2014 42 days overdue at packet build; governor classifies its band as ERROR (meta.governor_answers).",
    "Only 2 of 3 approved macro theses carry machine_conditions (E07): the B1 scorer's first run covers 2/3."
   ]
  }
 }
}```

---

## Appendix B — Finance-rule manifest (Step -1)

# Finance-rule manifest (repo side) — frozen 2026-08-08

Repo SHA: origin/main 1b471b60cdaa176692cc5f987e8399acfdab03d9 (working tree identical).
Built by a read-only Explore sweep; DB-ROW rules (theses ladders, invalidation conditions,
profile caps, model flags) live in the evidence packet
(`evidence-packet-2026-08-08.json` entries E01-E04, E07) and are part of the same denominator.

DENOMINATOR STATUS: NOT fully reconciled. The 'Possibly missed surfaces' section at the end
lists unswept globs (migrations CHECK constraints, CLI display bands, API routes, ~120 test
files, several docs/proposals, tax spec TC matrix). Per governor correction #2, NO
"all rules" coverage claim is permitted; findings claim coverage over the SWEPT surfaces only.

---

I swept all 10 named surfaces plus adjacent ones. Manifest below, grouped by surface. Legend for compactness: `auth` = authority/type, `fresh` = freshness, `ovr` = override disposition, `audit` = audit disposition. Currency is `none` unless money is compared; `horizon` is the decision horizon the rule speaks to.

---

## 1. `asxos/domain/theses/discipline.py` (deterministic discipline evaluator)

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `disc.data_sanity_multiple` | discipline.py:59, :167 | `evaluate_thesis` → V1 brief discipline block | code-constant | live price ≥ 2× recorded target ⇒ RED "stale/broken thesis data"; also **suppresses** the trajectory finding | a 2× overshoot is always data error, never a real move | native (both legs) | point-in-time | every active thesis w/ target | per-run | unset | code edit only | not recorded (rendered in brief HTML only) |
| `disc.trajectory_suppression` | discipline.py:317-333 | same | code-constant | when data-sanity fires, trajectory check does **not** run — investor never sees ABOVE_TARGET | broken ladder outranks pace | native | point-in-time | per thesis | per-run | unset | none | not recorded |
| `disc.timeline_elapsed_red` | discipline.py:234-243 | brief | code-constant | RED "timeline elapsed Nd ago" | opened_at + timeline_days is the deadline | none | thesis timeline | theses w/ timeline_days | per-run | unset | edit thesis `timeline_days` | not recorded |
| `disc.timeline_near_yellow_14d` | discipline.py:244-250 | brief | code-constant | YELLOW when ≤14 days remain | 14d = actionable warning window | none | 14d | same | per-run | unset | code edit | not recorded |
| `disc.timeline_wording_firewall` | discipline.py:220-229 | brief | code-constant + s766B policy | deliberately drops "— review or close" from severity's message; no action verb reaches investor | "close" = trade direction under s766B | none | n/a | all discipline messages | static | james (policy) | none | not recorded |
| `disc.no_stop_set_info` | discipline.py:336-344 | brief | code-constant | INFO line when thesis has no stop | absent stop = discipline gap worth naming | none | n/a | theses w/ NULL stop | per-run | unset | set stop on thesis | not recorded |
| `disc.incomplete_price_info` | discipline.py:254-280 | brief | code-constant | INFO naming which of entry/current/target is missing + that checks were skipped | silent no-op is the failure mode | none | n/a | per thesis | per-run | unset | none | not recorded |
| `disc.conviction_unset_yellow` | discipline.py:356-377 | brief | code-constant | one portfolio-level YELLOW; declares size-vs-conviction check **disabled** | any NULL conviction disables the check portfolio-wide | none | n/a | portfolio | per-run | unset | set `conviction_level` | not recorded |
| `disc.unrealised_return_native` | discipline.py:380-413 | brief (appended, not evaluated) | code-constant | shows `(current−entry)/entry` price-only %, explicitly "not a total return" | FX cancels for native-vs-native; dividends excluded | native (AUD or USD) | since entry | theses w/ entry+current | per-run | unset | none | not recorded |
| `disc.check_failure_is_loud` | discipline.py:127-135, :300-333 | brief | code-constant | a check that raises becomes an `error` finding shown to investor, never a silent pass | silent omission > wrong answer in harm | none | n/a | all checks | per-run | unset | none | not recorded |
| `disc.trajectory_level_map` | discipline.py:207-211 | brief | code-constant | STOP_VIOLATED/STALLED → RED; BEHIND/ABOVE_TARGET → YELLOW; ON_TRACK → nothing | ABOVE_TARGET is a warning not a win | none | thesis timeline | per thesis | per-run | unset | code edit | not recorded |
| `disc.model_independence` | discipline.py:16-23 | module contract | code-constant + governed rule (CLAUDE.md #11) | forbids any Model A input reaching discipline findings | model has no usable edge (decay analysis) | none | standing | whole module | static | james | policy change | not recorded |

## 2. `asxos/domain/brief/severity.py` (shared severity ladder — consumed by discipline + collectors)

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `sev.revisit_overdue_red` | severity.py:15-29 | discipline, active_theses | code-constant | RED "review overdue by Nd" the day after `revisit_due_at` | any overdue day is red | none | per revisit cycle | active theses | per-run | unset | edit `revisit_due_at` | not recorded |
| `sev.approaching_target_5pct` | severity.py:32-52 | (defined; default 5%) | code-constant | YELLOW when price within 5% of target | 5% = "nearly there" | native | point-in-time | theses w/ target | per-run | unset | `threshold_pct` arg | not recorded |
| `sev.cgt_boundary_7_30` | severity.py:55-76 | tax_operational collector | code-constant | RED <7d with literal **"— do not sell"**; YELLOW 7–30d | 7d = act-now, 30d = plan | none | 30d | every open lot | per-run | james (spec §5.1) | none | not recorded |
| `sev.earnings_double_risk_14d` | severity.py:79-104 | active_theses | code-constant | RED when earnings within 14d of CGT discount date ("double-risk window") | overlapping events compound risk | none | 14d | theses w/ earnings date | per-run | unset | code edit | not recorded |
| `sev.earnings_30d_yellow` | severity.py:105-110 | active_theses | code-constant | YELLOW when earnings ≤30d away | 30d = pre-positioning window | none | 30d | same | per-run | unset | code edit | not recorded |
| `sev.timeline_expired_red_yellow` | severity.py:114-142 | active_theses (V2) | code-constant | RED past deadline **with "— review or close"**; YELLOW ≤14d | V2 collector wording is looser than discipline's | none | thesis timeline | active theses | per-run | unset | code edit | not recorded |
| `sev.drawdown_3_5pct` | severity.py:145-169 | wealth_state | code-constant | YELLOW ≥3% below high-water mark; RED ≥5% | peak = MAX(capital_aud) over all snapshots ≤ as_of | AUD | since inception | whole portfolio | per-run, stale-risk (capital_aud is flow-affected) | unset | code edit | not recorded |
| `sev.concentration_10_20pct` | severity.py:172-194 | wealth_state, discipline | code-constant | YELLOW ≥10% of portfolio; RED ≥20% "concentrated position" | independent of profile `per_name_cap_pct` | AUD | point-in-time | each holding | per-run | unset | code edit | not recorded |
| `sev.regime_warning_map` | severity.py:197-214 | market_context | code-constant | `risk_off_disorderly` → RED; `risk_off_orderly` → YELLOW + "review positions"; else nothing | only the two risk-off labels warrant a warning | none | daily | market-wide | per-run | unset | code edit | not recorded |

## 3. `asxos/domain/theses/trajectory.py` (pace classifier — also the agent's cited definition)

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `traj.priority_order` | trajectory.py:71-80 | discipline, thesis-milestone-monitor | code-constant | STOP_VIOLATED > ABOVE_TARGET > pace bands | terminal states outrank pace | native | n/a | per thesis | per-run | unset | none | not recorded |
| `traj.stop_violated` | trajectory.py:77 | same | code-constant | `current ≤ stop` ⇒ STOP VIOLATED (highest-severity investor signal) | close price is the trigger, not intraday | native | point-in-time | theses w/ stop | per-run | unset | edit stop | not recorded |
| `traj.above_target` | trajectory.py:79 | same | code-constant | `current ≥ target` ⇒ ABOVE TARGET (agent adds "flag for close + profit-realisation review") | target hit = decision point | native | point-in-time | theses w/ target | per-run | unset | edit target | not recorded |
| `traj.stalled_0.4_0.05` | trajectory.py:87 | same | code-constant | expected>0.4 AND progress<0.05 ⇒ STALLED (RED) | 40% of clock burned with <5% progress is terminal | native | thesis timeline | per thesis | per-run | unset | code edit | not recorded |
| `traj.behind_half_pace` | trajectory.py:92 | same | code-constant | progress < expected/2 ⇒ BEHIND, else ON TRACK | half the linear pace is the cut | native | thesis timeline | per thesis | per-run | unset | code edit | not recorded |
| `traj.linear_clamp` | trajectory.py:44-57 | same | code-constant | expectation clamped to [0,1]; `timeline_days ≤ 0` raises | past-deadline theses cap at 1.0 | none | thesis timeline | per thesis | per-run | unset | none | not recorded |

## 4. `asxos/domain/brief/collectors/*` (what the investor actually sees / doesn't)

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `brief.new_ideas_regime_suppression` | collectors/new_ideas.py:23, :44-50 | brief section 6 | code-constant | **entire New Ideas section suppressed** under `risk_off_orderly`/`risk_off_disorderly` | capital preservation > idea evaluation in stress | none | daily | all research-stage theses | per-run | unset | none | `brief_runs.section_runs[new_ideas].status='suppressed'` |
| `brief.cross_layer_riskoff_set` | cross_layer.py:17-18 | underlying_drivers | code-constant | same two labels drive the "bullish positions exposed — review stop discipline" observation | — | none | daily | active/watching theses | per-run | unset | none | not recorded |
| `brief.cross_layer_max3` | cross_layer.py:92 | underlying_drivers | code-constant | at most 3 cross-layer observations reach the investor; rules 3 & 4 gated on `len<3` | prioritised truncation | none | daily | portfolio | per-run | unset | none | not recorded |
| `brief.cross_layer_rules_1_4` | cross_layer.py:48-90 | underlying_drivers | code-constant | 1) risk-off+bullish ⇒ exposure warning; 2) diverging ⇒ hidden-risk line; 3) risk-on+confirming ⇒ "supportive"; 4) mixed-only ⇒ "no clear direction" | docstring claims a ≥50% gate on rule 1/3 that the **code does not implement** | none | daily | bullish theses | per-run | unset | none | not recorded |
| `brief.bullish_statuses` | cross_layer.py:19; divergence.py:12 | cross-layer, hidden-risk | code-constant | only `active`/`watching` count as "bullish" for exposure + hidden-risk warnings | research-stage carries no exposure | none | n/a | theses | per-run | unset | none | not recorded |
| `brief.cash_low_5pct` | collectors/wealth_state.py:86-93 | wealth_state | code-constant | cash <5% of capital ⇒ YELLOW "low liquidity"; else the green summary line replaces it | 5% liquidity floor for display | AUD | point-in-time | portfolio | per-run | unset | code edit | not recorded |
| `brief.concentration_denominator` | wealth_state.py:131-136 | wealth_state | code-constant | concentration % uses summed priced MVs, not the snapshot MV (falls back only if nothing priced) | numerator/denominator must share a source | AUD (FX-converted) | point-in-time | each holding | per-run | unset | none | not recorded |
| `brief.portfolio_return_line_removed` | wealth_state.py:101-108 | wealth_state | code-constant | the since-inception "Portfolio vs XJO-TR · alpha" line is **deliberately absent** (produced a false −75.7%) | no flow-adjusted return series exists | AUD | since inception | portfolio | static | unset | requires a rebuilt series | not recorded |
| `brief.oppcost_net_level_5pct` | collectors/opportunity_cost.py:39, :103-107 | opportunity_cost | code-constant | alternative flagged YELLOW when **absolute** CGT-adjusted net return > 5% — a level screen, **not** a delta vs the held name | no current-holding baseline exists yet | fraction of value | scenario horizon | active approved theses | per-run, stale-risk | unset | code edit | `opportunity_cost_scenarios` rows |
| `brief.active_theses_yellow_7d` | collectors/active_theses.py:157 | active_theses | code-constant | YELLOW when underlying `diverging` OR revisit due within 7d | 7d = pre-emptive nudge | none | 7d | active theses | per-run | unset | code edit | not recorded |
| `brief.active_theses_precedence` | active_theses.py:150-156 | active_theses | code-constant | expiry-red > overdue-red > expiry-yellow > diverging/7d-yellow > green (one item per thesis) | only one severity per card | none | n/a | active theses | per-run | unset | none | not recorded |
| `brief.governance_filter_approved` | active_theses.py:44-47; watchlist.py:30-35; new_ideas.py:55-60; underlying_drivers.py:40-45; opportunity_cost.py:52-58 | all thesis collectors | code-constant + governed rule | only `governance_status='approved'` rows reach the investor | unapproved = not shown | none | n/a | theses | per-run | james | governance approve | `governance_events` |
| `brief.themes_governed_views` | collectors/theme_dashboard.py:42-43 | theme_dashboard | code-constant | reads `governed_active_*` views so retired/unapproved themes never surface | — | none | n/a | themes/holdings | per-run | james | governance | `governance_events` |
| `brief.theme_stage_disagreement` | theme_dashboard.py:71-75 | theme_dashboard | code-constant | YELLOW when `stage_suggested != stage` ("AI suggests") | classifier never writes `stage` | none | theme lifecycle | active themes | per-run | unset | confirm stage | `themes.stage_metadata` |
| `brief.tax_regulatory_window` | collectors/tax_operational.py:59-60 | tax_operational | code-constant | regulatory items shown only if published ≥ as_of−2d **and** ingested ≥ as_of−24h | freshness double-gate | none | 2d | holdings | per-run | unset | code edit | not recorded |
| `brief.section_health_visibility` | collectors/section_health.py:33-36 | footer | code-constant | a suppressed section is announced as `[name: suppressed]` rather than vanishing | suppression must be visible | none | n/a | all sections | per-run | unset | none | `brief_runs.section_runs` |
| `brief.snapshot_triage_ladder` | snapshot.py:27-49 | "one thing" line | code-constant | ordering that picks the single item the investor reads first: overdue(1) > stop(2) > earnings(3) > allocation_health(4) > market_context(5) > opportunity_cost(6) > new_ideas(7) | fragment-match on message text | none | daily | all items | per-run | unset | code edit | `brief_runs.snapshot_json.one_thing` |
| `brief.time_estimate` | snapshot.py:84-90 | snapshot | code-constant | 8 min per red (cap 60), 3 min per yellow (cap 30), else 1 min — frames how much attention to give | — | none | daily | portfolio | per-run | unset | code edit | `brief_runs.snapshot_json` |
| `brief.suppressed_excluded_from_counts` | snapshot.py:55-58 | snapshot | code-constant | only `ok`/`degraded` sections contribute to red/yellow/green counts | suppressed ≠ green | none | daily | all sections | per-run | unset | none | `brief_runs` |
| `brief.model_a_display_gate` | active_theses.py:73-101 | thesis cards | code-constant + governed rule #11 | with 0 approved models, the "Model A: <label> / Top drivers" line disappears from every card; discipline still renders | display-only degradation | none | n/a | active theses | per-run | james | `approved_for_allocation` flag | `model_versions` |

## 5. V1 brief `asxos/brief/compose.py` (the email actually sent today)

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `v1.prices_stale_5d` | compose.py:226-230 | brief banner | code-constant | latest price >5 days old ⇒ "prices stale" warning on the brief | 5d tolerates holidays | none | daily | active universe | per-run | unset | code edit | not recorded |
| `v1.signals_stale_anchor` | compose.py:208-224 | brief banner | code-constant | stale iff no signals at all, or freshest < latest-complete-trading-day | calendar as_of would false-alarm daily | none | daily | model_a signals | per-run | unset | none | not recorded |
| `v1.model_shelved_calm_state` | compose.py:255-258 | brief banner | code-constant | 0 approved models ⇒ calm "shelved" state instead of red banners; >1 stays a loud error | quarantine ≠ malfunction | none | standing | brief | per-run | james | `approved_for_allocation` | `model_versions` |
| `v1.cgt_boundary_30d_gated` | compose.py:415-433, :445 | discipline block | code-constant | INFO line per lot within 30d of the 12-month CGT threshold, citing s 115-25(1); **suppressed entirely unless `ASXOS_PERSONAL_USE=1`** | firewall parity with discipline | none | 30d | every open lot | per-run | james (spec §5.1) | env var | not recorded |
| `v1.portfolio_section_triple_gate` | compose.py:655-694 | brief section 6 | code-constant + governed rule | section omitted entirely unless: `ASXOS_PERSONAL_USE=1` **and** `ASXOS_PORTFOLIO_BRIEF_ENABLED=1` **and** a successful `build_portfolio` run with `as_of ≥ brief−2d` | never partial, never stale | AUD | weekly | rebalance output | per-run | james | env vars | `job_runs`, `rebalance_runs` |
| `v1.portfolio_top3` | compose.py:699-731 | brief section 6 | code-constant | only top 3 buys and top 3 sells by \|delta_aud\| are shown; totals still full | attention budget | AUD | weekly | proposed trades | per-run | unset | code edit | `proposed_trades` |
| `v1.signal_change_lookback_7d` | compose.py:377-385 | signal-change section | code-constant | prior label sourced from the last 7 days; no prior ⇒ labelled `(new)` | 7d covers weekends/gaps | none | 7d | held symbols | per-run | unset | code edit | not recorded |
| `v1.regulatory_2d_24h` | compose.py:472-485 | regulatory section | code-constant | published ≥ as_of−2d AND ingested ≥ as_of−24h, matched to holdings | double freshness gate | none | 2d | holdings | per-run | unset | `lookback_hours` arg | not recorded |
| `v1.news_freshness_gate` | compose.py:558-609 | news section | code-constant | news section shown only if the **latest** ingest_news run in a both-sided window was `success` AND `error_message IS NULL` | row-count is not a health signal | none | 24h | holdings | per-run | unset | none | `job_runs` |
| `v1.news_24h_limit20` | compose.py:612-630 | news section | code-constant | at most 20 holding-matched articles from the last 24h | — | none | 24h | holdings | per-run | unset | `lookback_hours` arg | not recorded |

## 6. Position-check jobs (`jobs/check_*.py`) — the alert emails

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `au.stop_breach` | check_au_positions.py:83-87 | Resend email | code-constant | close < stop ⇒ `[STOP BREACH]` email | daily close, not intraday | AUD | daily | `status='active' AND symbol LIKE '%.AU'` | per-run | unset | edit `stop_price` | `job_runs.rows_written` (count only) |
| `au.stop_watch_5pct` | check_au_positions.py:88-93 | email | code-constant | close < stop×1.05 ⇒ `[WATCH] within 5% of stop` | 5% pre-warning band | AUD | daily | same | per-run | unset | code edit | count only |
| `au.target_hit` | check_au_positions.py:95-100 | email | code-constant | close ≥ target ⇒ `[TARGET HIT] … — review thesis` | — | AUD | daily | same | per-run | unset | edit target | count only |
| `au.target_near_5pct` | check_au_positions.py:101-106 | email | code-constant | close ≥ target×0.95 ⇒ `[TARGET NEAR]` | — | AUD | daily | same | per-run | unset | code edit | count only |
| `au.vol_alert_3pct` | check_au_positions.py:108-115 | email | code-constant | \|1-day move\| > 3% ⇒ `[VOL ALERT]` | prev close from the same table | AUD | daily | same | per-run | unset | code edit | count only |
| `au.earnings_5d` | check_au_positions.py:117-123 | email | code-constant | 0 ≤ days-to-earnings ≤ 5 ⇒ `[EARNINGS]` | `next_earnings_date` is current | none | 5d | same | per-run, **stale-risk** (manually maintained field) | unset | edit field | count only |
| `au.scope_filter` | check_au_positions.py:35-43 | job | code-constant | **only** `.AU` active theses monitored — no governance filter, so unapproved theses do alert | suffix = market | none | daily | AU theses | per-run | unset | none | — |
| `us.stop_breach` / `us.stop_watch_5pct` / `us.vol_alert_3pct` / `us.earnings_5d` | check_us_positions.py:83-93, :96-103, :105-111 | email | code-constant | identical ladder to AU **minus any target rules** — a US thesis hitting target is never alerted | targets not tracked for US | USD | daily | `.US/.NYSE/.NASDAQ/.AMEX` active theses | per-run | unset | code edit | count only |
| `us.scope_all_foreign_suffixes` | check_us_positions.py:39-47 | job | code-constant | matches every `FOREIGN_SUFFIXES` value, not just `.US` (else `.NYSE` silently unmonitored) | fx.py suffix list is complete | none | daily | foreign theses | per-run | unset | edit `FOREIGN_SUFFIXES` | — |
| `us.as_of_default_yesterday` | check_us_positions.py:181 | job | code-constant | defaults to **yesterday** (AU job defaults to today) — a US alert always describes the prior session | NYSE close lands overnight | none | daily | US theses | per-run | unset | `--as-of` | `job_runs.as_of` |
| `inval.price_below_regex` | check_thesis_invalidations.py:42-44, :66-74 | job | code-constant (regex-as-rule) | free-text condition matching `price/close/stock … below\|under\|falls below\|<\|<= $N` becomes a machine trigger | ≤40 chars between keyword and operator | native | daily | active theses w/ conditions | per-run | unset | reword condition | condition `note` field |
| `inval.price_above_regex` | check_thesis_invalidations.py:45-47 | job | code-constant | same for `above\|over\|rises above\|>\|>=` | — | native | daily | same | per-run | unset | reword | `note` field |
| `inval.unparseable_skipped` | check_thesis_invalidations.py:154-156 | job | code-constant | a condition that doesn't match either regex is **silently skipped** — never evaluated, never reported | manual check assumed | none | daily | same | per-run | unset | none | **not recorded** |
| `inval.trigger_writes_status` | check_thesis_invalidations.py:161-178 | `theses.invalidation_conditions` | code-constant | sets `status='triggered'` + a `note` by direct UPDATE — **no revision event**, no governance transition | automated bookkeeping ≠ discipline event | native | daily | same | per-run | unset | manual revise | JSONB `note` on the condition |
| `inval.alert_wording` | check_thesis_invalidations.py:179-185 | email | code-constant | email says **"Review thesis and consider exit. Run: asx thesis exit <SYM>"** — the only alert surface that names an exit action | — | none | daily | triggered theses | per-run | unset | code edit | count only |
| `inval.bare_string_is_active` | check_thesis_invalidations.py:50-63 | job | code-constant | a legacy bare-string condition is read as active + never-evaluated (coerce rather than crash) | — | none | daily | legacy rows | per-run | unset | none | rewritten on trigger |
| `jobs.personal_use_firewall` | check_au_positions.py:153; check_us_positions.py:141; check_thesis_invalidations.py:128 | all three jobs | code-constant + governed rule | job refuses to run unless `ASXOS_PERSONAL_USE=1` — no alerts at all | s766B firewall backstop | none | standing | all position jobs | static | james | env var | `job_runs.status` |
| `alert.send_never_raises` | check_au_positions.py:128-147 (and twins) | email | code-constant | a Resend failure is swallowed — the alert silently doesn't arrive and the job still reports success | delivery is best-effort | none | daily | all alerts | per-run | unset | none | **not recorded** |
| `model.signals_stale_3d` | check_model_staleness.py:34, :76-81 | alert email | code-constant | signals >3d old ⇒ `[MODEL STALE]` email + RuntimeError | — | none | daily | model_a | per-run | unset | code edit | `job_runs` |
| `model.consec_fail_2` | check_model_staleness.py:35, :99-104 | alert email | code-constant | ≥2 leading failures in last 5 `generate_signals` runs ⇒ `[GENERATE FAILING]` | — | none | daily | job | per-run | unset | code edit | `job_runs` |
| `model.retrain_checks_removed` | check_model_staleness.py:12-16, :106-111 | job | code-constant + policy | retrain-staleness (>14d) and model-age (>60d) alerts **deleted** because the engine is shelved | shelf is intentional | none | standing | model_a | static | james | shelf-doc revival | doc'd in code |
| `macro.falsifier_no_auto_retire` | score_macro_theses.py:14-17 | macro outcomes | code-constant + governed rule | a fired falsifier records an outcome + emails James; it never retires the thesis or changes `governance_status` | system proposes, human decides | none | multi-month | approved macro theses | per-run | james | none | `macro_thesis_outcomes` |
| `macro.null_is_not_satisfied` | score_macro_theses.py:19-22, :104-106 | evaluator | code-constant | a NULL signal value counts as does-NOT-satisfy — never confirms or falsifies on absent data | conservative-on-missing | none | window | machine_conditions | per-run | unset | none | `macro_thesis_outcomes` |
| `macro.window_aggregations` | score_macro_theses.py:99-114 | evaluator | code-constant | `consecutive` = all, `any` = any, `majority` = strict >50%; fewer than `window` rows ⇒ not met | — | none | N-day window | machine_conditions | per-run | unset | edit `machine_conditions` | `macro_thesis_outcomes` |
| `macro.float_threshold_rejected` | score_macro_theses.py:62-73 | evaluator | code-constant | a float threshold hard-fails rather than being coerced | precision loss is silent corruption | none | n/a | machine_conditions | per-run | unset | none | job failure |
| `oppcost.cash_rate_4.5pct` | compute_opportunity_cost.py:34-35 | opportunity_cost rows | code-constant | cash is scored as a redeployment candidate at a hardcoded 4.5% expected return | approximates the RBA cash rate | AUD | annual | all scenarios | **static — stale-risk if RBA moves** | unset | code edit | `opportunity_cost_scenarios` |
| `oppcost.prob_up_default` | compute_opportunity_cost.py:74 | scenarios | code-constant | missing `prob_up` defaults to 0.55 (i.e. a BUY-boundary prior) | — | none | scenario | candidates | per-run | unset | code edit | same |
| `snap.xjo_tr_proxy_4pct` | snapshot_portfolio.py:81, :94-96 | benchmark bar | code-constant | when the real accumulation index is absent, the "bar to beat" is XJO price × (1.04)^years | 4% trailing dividend yield | AUD | since epoch | benchmark | per-run, **stale-risk** | unset | code edit | `portfolio_daily_snapshots.trailing_div_yield_pct` (non-NULL flags the approximation) |
| `ctx.breadth_min_rows` | ingest_market_context.py:73, :81 | regime inputs | code-constant | 50d breadth needs ≥40 rows, 200d needs ≥180 rows per symbol, else that symbol is excluded from the denominator | — | none | daily | universe | per-run | unset | code edit | `market_context_current.ingestion_warnings` |

## 7. `asxos/domain/screening/` (Tier 2a mechanical screen)

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `scr.field_whitelist` | evaluator.py:77-90 | `parse_rule` | code-constant | the **only 12 screenable fields**: pe_ratio, pb_ratio, eps, dividend_yield, franking_pct, roe, debt_to_equity, revenue, net_income, market_cap, sector, latest_close. Anything else ⇒ ValueError | closed set is both policy and injection boundary | mixed (AUD fundamentals) | point-in-time | all rules | static | unset | add `_FIELD_MAP` entry | `screening_runs.rule_json_snapshot` |
| `scr.op_whitelist` | evaluator.py:55-58, :176-180 | `parse_rule` | code-constant | ops limited to eq/neq/lt/lte/gt/gte/in/not_in/is_null/is_not_null; text fields (`sector`) further restricted to eq/neq/in/not_in/is_null/is_not_null — no `sector > x` | — | none | n/a | all rules | static | unset | code edit | same |
| `scr.au_equity_only` | evaluator.py:296, :325 | base query | code-constant + governed rule | population is hardcoded to `is_active AND security_kind='au_equity'`; **ETFs/LICs/hybrids/US names can never be screened** | fund criteria are a different taxonomy | AUD | n/a | universe | static | james (proposal-scoped) | none (not author-controlled) | `screening_runs.universe_size` |
| `scr.curated_composite_only` | evaluator.py:268-275; types.py:5-12 | `evaluate_rule` | code-constant + governed rule #11 | refuses to evaluate any rule whose `source_method` isn't `curated_composite` — no signal/SHAP-derived screening rule can ever run | Model A quarantine, standing | none | standing | all rules | static | james | never widen | run refuses |
| `scr.inactive_rule_refused` | evaluator.py:274-275 | `evaluate_rule` | code-constant | inactive rule ⇒ RuntimeError, not an empty result | — | none | n/a | all rules | per-run | unset | activate rule | — |
| `scr.empty_universe_hard_fail` | evaluator.py:300-304 | `evaluate_rule` | code-constant | empty candidate universe ⇒ RuntimeError "config bug, not a valid zero-match answer" | zero must never look like a screen result | none | n/a | all runs | per-run | unset | none | — |
| `scr.sector_scope_conflict` | evaluator.py:355-379 | `evaluate_rule` | code-constant | runtime `--sector` outside the rule's own `sector_scope` ⇒ RuntimeError; multi-sector scope w/o `--sector` ⇒ RuntimeError | never silently return empty | none | n/a | scoped rules | per-run | unset | pass matching sector | `screening_runs.sector_scope` |
| `scr.limit_vs_match_count` | evaluator.py:255, :333-350; types.py:84-95 | CLI output | code-constant | shortlist capped at 20 but the **true** `match_count` is preserved — "1800/1872 matched" stays visible as a no-op signal | truncation must not hide breadth | none | n/a | all runs | per-run | unset | `limit` arg | `screening_runs.match_count` |
| `scr.decimal_decode` | evaluator.py:18-25, :93-99 | all callers | code-constant | thresholds must decode via `parse_float=Decimal`; a bare `json.loads` silently floats a numeric threshold | CLAUDE.md #5 | none | n/a | rule_json | static | unset | none | — |
| `scr.snapshot_on_log` | evaluator.py:382-409 | `screening_runs` | code-constant | the rule_json **at evaluation time** is snapshotted so a later rule edit can't reinterpret an old run | rules are mutable | none | n/a | logged runs | per-run | unset | `--no-log` skips logging | `screening_runs.rule_json_snapshot` |
| `scr.ungoverned_by_design` | evaluator.py:26-32; screening-conventions.md | governance | governed-doc | `screening_runs` carries no `governance_status` and no `agent_runs` link — running a screen needs no approval; the gate starts when a human converts a match to a thesis/theme | re-derivable cache | none | n/a | screening | static | james | deliberate scope change | none by design |

## 8. `asxos/domain/portfolio/` (allocator, constraints, rebalance, tax overlay, monitor)

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `pf.risk_scalar_map` | types.py:26-31 | Profile validation | code-constant | conservative 0.25 / balanced 0.50 / growth 0.75 / aggressive 1.00; label-scalar mismatch raises | canonical mapping | none | standing | active profile | static | james | new profile row | `profiles` |
| `pf.position_count_anchors` | allocator.py:36-41, :44-62 | `allocate` | code-constant | **how many names the investor is told to hold**: 0.25→30, 0.50→20, 0.75→15, 1.00→10; linear interpolation, clamped | explicitly "a UX heuristic, not a finance-research-grade model" | none | standing | build | per-run | james | `risk_tolerance_scalar` | `target_allocations` count |
| `pf.score_weights_default` | types.py:36-39; allocator.py:118-140 | `rank_candidates` | code-constant | composite = 0.6·z(prob_up) + 0.4·z(expected_return); determines the top-N cut | "a starting prior, not a calibrated ratio" | none | signal horizon | candidates | per-run | james | `profiles.score_weights_json` | `target_allocations` |
| `pf.score_weights_tolerance` | types.py:143-147 | Profile validation | code-constant | weight sum must be within [0.999, 1.001]; each weight in [0,1] | precision-tolerant band | none | n/a | profile | static | unset | none | `profiles` CHECK |
| `pf.buy_labels_only` | allocator.py:32, :83-84 | `filter_buy_universe` | code-constant | only STRONG_BUY/BUY are investable; HOLD/SELL/STRONG_SELL never allocated | — | none | signal horizon | candidates | per-run | unset | code edit | `target_allocations.signal_label` |
| `pf.min_market_cap_50m` | allocator.py:33, :90-91 | `filter_buy_universe` | code-constant | market cap < A$50m (or NULL) ⇒ excluded from the investable universe | micro-cap exclusion | AUD | n/a | candidates | per-run | unset | function arg | not logged per-symbol |
| `pf.vol_required` | allocator.py:92-93; build.py:246-247 | filter / build | code-constant | `daily_vol ≤ 0` excluded; a symbol with insufficient price history is **silently omitted** from candidates | intentional silent-omit (not a bug) | none | 60d | candidates | per-run | unset | none | **not recorded** |
| `pf.exclusions` | allocator.py:80-89 | filter | code-constant | `excluded_symbols` / `excluded_sectors` from the profile drop candidates; NULL sector escapes the sector filter | — | none | standing | candidates | per-run | james | profile columns | `profiles` |
| `pf.rank_tiebreak` | allocator.py:144-153 | `rank_candidates` | code-constant | ties break by confidence DESC then symbol ASC (alphabetical bias) | determinism | none | n/a | candidates | per-run | unset | none | ordering implicit |
| `pf.target_sum` | allocator.py:205; constraints.py:205 | allocate/constraints | code-constant | deployed fraction = `leverage_cap − cash_floor_pct` (e.g. 0.95) — the cash floor is what is **not** invested | — | AUD | standing | build | per-run | james | profile columns | `target_allocations` sum |
| `pf.inverse_vol_weighting` | allocator.py:156-172 | allocate | code-constant | weight ∝ 1/σ — the sizing rule the investor sees | risk-parity within the sleeve | none | 60d vol | targets | per-run | unset | none | `target_allocations.inv_vol_score` |
| `pf.empty_universe_hard_fail` | allocator.py:192-196 | allocate | code-constant | empty buy universe ⇒ RuntimeError, no portfolio produced | never a zero-name portfolio | none | n/a | build | per-run | james (conventions table) | none | `job_runs.status` |
| `pf.waterfall_order` | constraints.py:189-244 | build | code-constant | per-name cap → freeze → sector cap (unfrozen only, proportional) → residual by 1/σ → converge; max **5 iterations** then RuntimeError | frozen names never re-scaled | none | n/a | targets | per-run | james | `max_iterations` arg | `constraint_log` per target |
| `pf.per_name_cap` | constraints.py:35-56; types.py:62,111 | waterfall | code-constant (value in DB) | clips any name above `per_name_cap_pct`; bound (0, 0.5] | — | AUD | standing | targets | per-run | james | `profiles.per_name_cap_pct` | `constraint_log.capped_by_per_name` |
| `pf.sector_cap` | constraints.py:64-114; types.py:63,116 | waterfall | code-constant (value in DB) | scales unfrozen sector members when the sector exceeds `sector_cap_pct`; bound (0, 1] | frozen-alone-over-cap is left to fail convergence | AUD | standing | targets | per-run | james | `profiles.sector_cap_pct` | `constraint_log.capped_by_sector` |
| `pf.cash_floor_bound` | types.py:61, :105-106 | Profile | code-constant | `cash_floor_pct` ∈ [0,1]; one of only two structural protections in v1 | — | AUD | standing | profile | static | james | profile row | `profiles` |
| `pf.leverage_cap_bound` | types.py:61, :108-109 | Profile | code-constant | `leverage_cap` ∈ [1,3]; 1.0 = no margin | — | AUD | standing | profile | static | james | profile row | `profiles` |
| `pf.preflight_over_alloc` | constraints.py:209-216 | build | code-constant | `target_sum > N × per_name_cap` ⇒ RuntimeError naming the three fixes | — | none | n/a | build | per-run | james | none | `job_runs` |
| `pf.preflight_under_alloc` | constraints.py:218-226 | build | code-constant | `target_sum < min_position_aud / capital_aud` ⇒ RuntimeError "cannot place even one minimum-size position" | — | AUD | n/a | build | per-run | james | none | `job_runs` |
| `pf.trim_min_position` | constraints.py:272-281 | build | code-constant | positions below `min_position_aud` dropped, weight becomes **cash, not redistributed** ("a 12-position portfolio beats a 13th at $300") | — | AUD | n/a | targets | per-run | james | `profiles.min_position_aud` | absence from `target_allocations` |
| `pf.drift_threshold_0.5pct` | rebalance.py:65, :111, :146 | `compute_deltas` | code-constant | \|delta_aud\| < 0.5% of capital ⇒ side='hold' — the investor is told to do nothing | dust suppression | AUD | weekly | held ∪ target | per-run | unset | function arg | `proposed_trades.side` |
| `pf.boundary_defer_30d` | rebalance.py:28, :106-108, :155-160 | `compute_deltas` | code-constant + spec §5.1 | any sell with a lot at `0 < days_to_cgt_discount ≤ 30` is **forced to 'hold'** when `defer_near_boundary_sells`; tags preserved | calendar arithmetic, not day-count | AUD | 30d | sells | per-run | james (spec) | `profiles.defer_near_boundary_sells` | `rationale_tags.near_boundary_lot_ids`; `summary.n_deferrals` |
| `pf.concentration_alarm_10pct` | rebalance.py:31, :162-164 | `compute_deltas` | code-constant | any buy whose target > 10% of capital gets `concentration_alarm=True` — defence-in-depth, **separate from `per_name_cap_pct`** | higher profile caps can permit it | AUD | weekly | buys | per-run | unset | code edit | `rationale_tags.concentration_alarm` |
| `pf.universe_inactive_forced_sell` | rebalance.py:138-145; build.py:42-60 | `compute_deltas` | code-constant | a held **au_equity** gone `is_active=FALSE` is force-sold in full, drift threshold ignored; every fund/foreign kind is exempt | delisting vs. not-in-ML-universe | AUD | weekly | held symbols | per-run | unset | none | `rationale_tags.reason='universe_inactive'` |
| `pf.exited_universe_full_sell` | rebalance.py:151-153 | `compute_deltas` | code-constant | held but absent from targets ⇒ full sell tagged `exited_universe` | — | AUD | weekly | held symbols | per-run | unset | none | `rationale_tags.reason` |
| `pf.rebalance_exclusions` | build.py:63-110 | build | code-constant | US/foreign holdings and non-`au_equity` funds never enter `compute_deltas` — so they can never be auto-liquidated; no-price symbols omitted | two independent auto-liquidation guards | mixed | weekly | holdings | per-run | unset | none | absence from `proposed_trades` |
| `pf.signals_stale_2d` | build.py:224-230 | build | code-constant | signals more than 2 days older than the build date ⇒ RuntimeError, no portfolio | — | none | 2d | build | per-run | james (conventions) | `--signals-date` | `job_runs` |
| `pf.production_model_gate` | build.py:184-189; production_gate.py | build | code-constant + governed rule #11 | 0 or >1 rows with `is_active AND approved_for_allocation` ⇒ allocator refuses to run (brief degrades instead) | rule #11's mechanical enforcement point | none | standing | build | per-run | james | `approved_for_allocation` | `rebalance_runs.model_version` |
| `pf.no_active_profile` | build.py:170-174 | build | code-constant | no active profile ⇒ RuntimeError, not a default | never assume a mandate | none | n/a | build | per-run | james | `asx profile init --activate` | `job_runs` |
| `pf.loss_harvest_tag` | tax_overlay.py:69-118 | proposed trades | code-constant + spec §5.2 | sells on loss-making symbols tagged `reason='loss_harvest'` with lot hints ordered **largest loss first**; explicitly INFORMATION ONLY — no wash-sale/Part IVA assessment, no rebuy tracking | James is solely responsible for ATO compliance | AUD | n/a | sells | per-run | james (conventions I.5) | `--no-tax-overlay` | `rationale_tags`, `lot_hints.preferred_lot_ids` |
| `pf.unrealised_loss_def` | tax_overlay.py:48-66 | overlay | code-constant + spec §5.2 | `price × qty < cost_base_normal`; lots exactly at cost excluded | — | AUD | n/a | lots | per-run | james (spec) | none | — |
| `pf.near_boundary_def` | tax_overlay.py:24-45 | overlay/rebalance | code-constant + spec §5.1 | `0 < days_to_cgt_discount ≤ 30`; already-eligible lots (0) excluded | — | none | 30d | lots | per-run | james (spec) | `window_days` arg | — |
| `pf.vol_window_60d_cap252` | volatility.py:21-40 | build | code-constant | annualised vol over a 60-day window; >252 raises; insufficient history raises (caller omits the symbol) | 252 trading days/yr | none | 60d | candidates | per-run | unset | `window_days` arg | — |
| `pf.monitor_cost_model` | monitor.py:106-115 | perf report | code-constant | assumed 8bps commission + 5bps slippage on traded notional — an INFERRED, never-measured drag on reported performance | "conservative placeholders for a retail ASX account" | AUD | per build | paper runs | static | unset | `CostModel` override | `CostEstimate` in report |
| `pf.monitor_prob_buckets` | monitor.py:134-139 | perf report | code-constant | prob_up bucket edges 0.55/0.65/0.75/0.85; expected_return edges 0/0.05/0.5/2 — frames the "is the model calibrated?" read | edges mirror signal thresholds | none | per build | paper runs | static | unset | field override | report buckets |
| `pf.monitor_measurability_gate` | monitor.py:615-653 | perf report | code-constant | 0 forward trading days ⇒ **all headline numbers are None** with an explicit "not yet measurable" note | never report a return that doesn't exist | AUD | per build | paper runs | per-run | unset | none | `measurability_note` |
| `pf.monitor_no_lookahead` | monitor.py:622-628 | perf report | code-constant | any price dt > eval_as_of ⇒ ValueError | — | none | n/a | paper runs | per-run | unset | none | — |
| `pf.monitor_ff_flagged` | monitor.py:10-21, :310-395 | perf report | code-constant | forward-fill is off by default and, when on, is flagged on the NAV point **and** the event log — never hidden | — | AUD | daily | paper runs | per-run | unset | `forward_fill` flag | `MissingPrice` events |
| `pf.monitor_252` | monitor.py:44-45, :515-521 | perf report | code-constant | realised vol annualised on 252 trading days | ASX convention | none | annual | paper runs | per-run | unset | none | report |
| `pf.paper_continuity_14d` | paper_trade.py:266-281 | evaluable runs | code-constant | a paper run only counts if the weekly cron was continuous (max 14-day gap) across the maturation window | a gap invalidates the observation | none | 4 weeks | paper runs | per-run | unset | arg | `job_runs` |

## 9. `asxos/domain/tax/` — user-facing warnings/hints only

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `tax.45day_franking_warning` | dividends.py:79-114; spec §4.3/TC-21 | `tax_view_smsf` → `asx tax` CLI | code-constant + spec | disposed SMSF lot held <45 **clear** days with a franked dividend in the period ⇒ warning "may fail the qualified-person test (s 207-145). Franking credit NOT auto-removed." One line per lot | $5,000 small-shareholder exemption does **not** apply to SMSFs; system warns, never enforces | AUD | per dividend | SMSF disposed lots | per-run | james (spec) | spec amendment | printed only (`cli/tax.py:122-125`) |
| `tax.cgt_break_even_hint` | cgt.py:112-162; display.py:242-254; spec §5.4/TC-22/23 | position monitor | code-constant + spec | prints "CGT break-even: $X — selling below this today loses vs holding to <date>" | flat marginal 0.45 + 2% Medicare (individual) / 0.15 no Medicare (SMSF); price held constant; **valid only above the §7.1 low-income band** | native (must match cost) | to CGT eligibility | earliest-still-ineligible lot only | per-run | james (spec) | `marginal_rate` arg | `position_monitor_runs` (inputs only, not the hint) |
| `tax.break_even_suppression` | cgt.py:144-162 | monitor | code-constant | returns None (hint hidden) when: already eligible, no unrealised gain, r_eff ≥ 1, or result ≤ cost | no hint is better than a misleading one | native | n/a | lots | per-run | james (spec) | none | — |
| `tax.eligibility_alert_30d` | positions.py:91, :185 | `TaxView.eligibility_alerts` | code-constant | "<SYM> (lot N) crosses 12-month CGT discount in Nd" for open lots with 0 < days ≤ 30 | — | none | 30d | open lots, both account types | per-run | james (spec §5.1) | none | printed only |
| `tax.div296_election_warning` | positions.py:191-210; spec §6.5 | `franking_warnings` | code-constant + spec | when the election is made, one warning per lot where `cost_base_div296 < cost_base_normal` (pre-2026 loss extinguished); if none, an explicit "check ran" advisory | lots disposed before 2026-07-01 excluded | AUD | one-off | SMSF lots | per-run | james (spec) | spec amendment | printed only |
| `tax.fx_de_minimis_250` | fx_gain.py:29, :83; spec §8/s 775-30 | `is_de_minimis` | code-constant + spec | flags \|forex gain\| ≤ A$250 for user attention; **does not** apply the election (irrevocable — user decides) | per income year, across all events | AUD | financial year | US lots | per-run | james (spec) | none | not recorded |
| `tax.cgt_calendar_arithmetic` | cgt.py:28-42; policy line 53 | everything CGT | code-constant + governed doc | eligibility is `acquisition + relativedelta(years=1) + timedelta(days=1)`; day-count `≥365` is **forbidden** | CLAUDE.md #6 | none | 12 months | all lots | static | james | never | — |
| `tax.discount_rates` | types.py:19-20; cgt.py:45-50 | all CGT math | code-constant + spec §2 | individual 0.5, SMSF exactly 1/3 (Fraction, not 0.333) | — | none | n/a | disposals | static | james (spec) | none | — |
| `tax.rates` | types.py:23,26,29 | tax views | code-constant + spec | corporate/franking 0.30, Medicare 0.02, SMSF 0.15 | unknown franking rate ⇒ default 0.30 **and log a warning** (spec §3) | AUD | FY | all | static | james (spec) | config fields | — |
| `tax.div296_thresholds` | div_296.py:16-19 | Div 296 outcome | code-constant + spec §6.3 | LSBT $3,000,000 @15%, VLSBT $10,000,000 @+10% stacked | commencement values; indexed in future years, flagged `is_provisional` | AUD | FY | SMSF | **static — stale-risk on indexation** | james (spec) | `positions.py` args | `Div296Outcome.is_provisional` |
| `tax.marginal_rate_default` | cgt.py:118; brief/opportunity_cost.py:64 | break-even + opp-cost | code-constant | flat 0.45 top marginal rate assumed everywhere a marginal rate is needed | full-year taxable income is not modelled | AUD | FY | individual | static | unset | function arg | — |
| `tax.oppcost_exclude_negative` | brief/opportunity_cost.py:88-98 | opp-cost ranking | code-constant | candidates whose net-of-CGT return ≤ 0 are **excluded**, not ranked last — "avoid misleading best-of-bad recommendations" | — | fraction | scenario | candidates | per-run | unset | none | `opportunity_cost_scenarios` |
| `tax.oppcost_discount_gate` | brief/opportunity_cost.py:54-58 | friction calc | code-constant | discount applied only when `days_to_cgt_discount == 0`; otherwise full-rate friction | — | AUD | point-in-time | holdings | per-run | james (spec) | none | same |

## 10. Regime + signal classifiers

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `rgm.avix_disorderly_30` | regime/classifier.py:28, :69 | brief, suppression | code-constant | A-VIX > 30 ⇒ `risk_off_disorderly` ⇒ RED banner **and** New Ideas suppressed | — | none | daily | market-wide | per-run | unset | code edit + `CLASSIFIER_VERSION` bump | `market_context.regime_rationale` (conditions fired) |
| `rgm.hy_oas_stress_600` | classifier.py:33, :70 | same | code-constant | US HY OAS > 600bps ⇒ disorderly (single-condition OR) | US credit proxies AU | none (bps) | daily | market-wide | per-run | unset | same | same |
| `rgm.avix_riskoff_22` | classifier.py:29, :75 | same | code-constant | A-VIX > 22 ⇒ `risk_off_orderly` ⇒ YELLOW + suppression | — | none | daily | market-wide | per-run | unset | same | same |
| `rgm.hy_oas_elevated_450` | classifier.py:34, :76 | same | code-constant | HY OAS > 450bps ⇒ orderly | — | none (bps) | daily | market-wide | per-run | unset | same | same |
| `rgm.breadth_bearish_0.40` | classifier.py:38, :77-81 | same | code-constant | <40% above 200d MA ⇒ orderly (alone sufficient); skipped when breadth is NULL | soft-degrade | none | daily | market-wide | per-run | unset | same | same |
| `rgm.risk_on_broadening` | classifier.py:31,36, :86-98 | brief tone | code-constant | A-VIX < 14 **AND** breadth ≥ 0.70 **AND** net new highs > 0 (all three) | conjunctive | none | daily | market-wide | per-run | unset | same | same |
| `rgm.risk_on_narrowing` | classifier.py:30,37, :101-113 | brief tone | code-constant | A-VIX < 18 AND breadth ≥ 0.55 AND net new highs ≤ 0 | conjunctive | none | daily | market-wide | per-run | unset | same | same |
| `rgm.default_neutral` | classifier.py:115-116 | brief | code-constant | everything else ⇒ `neutral_mixed` (no suppression, no warning) | — | none | daily | market-wide | per-run | unset | none | same |
| `rgm.hard_fail_inputs` | classifier.py:57-60; indicators.py:16, :49-54 | regime pipeline | code-constant | missing `avix` or `us_hy_oas` (or `asx200_close` at load) ⇒ RuntimeError — the system refuses to name a regime rather than guess | — | none | daily | market-wide | per-run | unset | none | job failure |
| `rgm.classifier_version` | classifier.py:26 | audit | code-constant | `v1.0` — must be bumped on any threshold change | versioning discipline | none | n/a | classifier | static | unset | — | stamped in rationale |
| `rgm.threshold_pins` | tests/test_regime_classifier.py | CI | test | pins each threshold + waterfall precedence; a silent threshold change fails CI | — | none | n/a | classifier | per-CI | unset | — | CI |
| `sig.classify_bands` | signals/thresholds.py:26-35; ml-conventions.md | signal labels | code-constant + governed doc | STRONG_BUY ≥0.65 & ER>0.05 · BUY ≥0.55 & ER>0 · SELL ≤0.45 & ER<0 · STRONG_SELL ≤0.35 & ER<−0.05 · else HOLD — "canonical, do not modify without explicit instruction" | — | fraction | 5-day label horizon | all universe symbols | per-run | james (rule doc) | none | `signals.signal_label` |
| `sig.regime_overrides` | thresholds.py:38-50, :63-97 | signal labels | code-constant + governed doc | bear tightens STRONG_BUY to (0.70, 0.06); bull tightens STRONG_SELL to (0.30, −0.06); plain BUY/SELL fall through to neutral | — | fraction | 5d | all symbols | per-run | james | none | `signals` |
| `sig.confidence_formula` | thresholds.py:53-60 | display + tiebreak | code-constant | confidence = clip(round(\|p−0.5\|·200), 0, 100) | — | none | n/a | all signals | per-run | james | none | `signals.confidence` |
| `sig.regime_proxy` | signals/regime.py:22-24 | signal regime tag | code-constant | regime proxy = top-10 symbols, 200-day SMA, 20-day slope | — | none | daily | universe | per-run | unset | code edit | `signals.regime` |
| `sig.fundamental_lag_45d` | signals/loader.py:25, :206 | feature build | code-constant | fundamentals joined with a 45-day disclosure lag (point-in-time discipline) | ASX disclosure lag | none | 45d | features | per-run | james (ml-conventions) | none | — |
| `mdl.retrain_gates` | models/validation.py:17-19 | model activation | code-constant + governed doc | MIN_ROC_AUC 0.65 · MAX_DEGRADATION 5% · MIN_SAMPLES 1000 — all three must pass | — | none | n/a | candidate models | per-run | james (ml-conventions) | function args | `model_versions` |

## 11. Theme / underlying / position-monitor classifiers

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `und.confirming_2pct` | underlyings/attribution.py:18, :64 | brief, monitor | code-constant | weighted 5d move > +2% ⇒ `confirming` | exposure×direction weighted | none | 5d | theses w/ underlyings | per-run | unset | code edit | `position_monitor_runs.underlying_label` |
| `und.diverging_neg2pct` | attribution.py:19, :66 | brief, monitor | code-constant | < −2% ⇒ `diverging` ⇒ YELLOW + hidden-risk warning + cross-layer line | — | none | 5d | same | per-run | unset | code edit | same |
| `und.mixed_band` | attribution.py:68-69 | same | code-constant | [−2%, +2%] ⇒ `mixed`; a thesis with **no** underlyings also returns `mixed` (not "unknown") | absence ≡ neutral | none | 5d | all theses | per-run | unset | code edit | same |
| `und.hidden_risk` | underlyings/divergence.py:15-31 | active_theses | code-constant | bullish (`active`/`watching`) + `diverging` ⇒ "Hidden risk … Review underlying assumptions." | — | none | 5d | bullish theses | per-run | unset | none | not recorded |
| `thm.stage_thresholds` | themes/stage_classifier.py:43-53 | theme stage, monitor | code-constant | breadth 50d ≥0.50, breadth 200d ≥0.80, sentiment ≥0.65, retail spike ≥1.50×, momentum slowdown <2%/wk | version-stamped `v1.0` | none | theme lifecycle | themes, monitored positions | per-run | unset | `StageThresholds` override | `themes.stage_metadata.conditions_fired` |
| `thm.stage_waterfall` | stage_classifier.py:123-150 | same | code-constant | mature (slow+high breadth) → late-retail (retail spike OR sentiment+breadth) → mainstream → broad-institutional → early-institutional → early | first match wins | none | theme lifecycle | themes | per-run | unset | code edit | same |
| `thm.min_30d_history` | stage_classifier.py:96 | same | code-constant | <30 days of price history ⇒ **no stage suggested at all** | — | none | 30d | themes | per-run | unset | none | `insufficient_data` label |
| `thm.never_writes_stage` | stage_classifier.py:16-18 | themes | code-constant + governed rule | classifier writes only `stage_suggested` / `stage_metadata` — never the user-confirmed `stage` | — | none | n/a | themes | static | james | none | `themes` |
| `pm.default_underlyings` | position_monitor/service.py:45-56 | monitor | code-constant | with no thesis underlyings, defaults to VIX 0.5 + US HY OAS 0.5, both **negative** direction | risk-off proxies for any position | none | 5d | any monitored symbol | per-run | unset | attach real underlyings | `position_monitor_runs` |
| `pm.scenario_sell_now_20pct` | service.py:121-128 | monitor | code-constant | unrealised >20% ⇒ Sell-Now scenario status `confirmed`, else `available`; invalidation = "price falls below cost basis" | — | native | point-in-time | positions w/ cost | per-run | unset | code edit | `position_monitor_runs` (status not stored) |
| `pm.scenario_stop_state` | service.py:107-118 | monitor | code-constant | stop `active` w/ % buffer vs `TRIGGERED`; invalidation "breaks below on volume → exit" | — | native | daily | positions w/ stop | per-run | unset | edit stop | same |
| `pm.scenario_cgt_hold` | service.py:90-104 | monitor | code-constant | "Hold to CGT discount" scenario: `ON TRACK`/`ELIGIBLE NOW`, "Best risk-adjusted after-tax outcome" | — | none | to eligibility | positions w/ CGT date | per-run | james (spec) | none | same |
| `pm.lot_account_isolation` | service.py:180-201 | monitor | code-constant + statute | lots are filtered to the **active profile's** account type and never pooled (individual vs SMSF are separate CGT taxpayers, s 115-100); a default would silently re-introduce "assume individual" | — | AUD | n/a | lots | per-run | james | activate other profile | `position_monitor_runs` |
| `pm.intraday_2pct_stop` | position_monitor/display.py:255-263 | monitor output | code-constant | on intraday prices within 2% of stop ⇒ "⚠ INTRADAY … Confirm on close before acting." | intraday ≠ actionable | native | intraday | monitored positions | per-run | unset | code edit | not recorded |
| `pm.volume_150pct` | display.py:145-151 | monitor output | code-constant | volume >150% of 30d avg ⇒ "elevated — confirms move"; else "below avg — shake-out likely" | — | none | daily | monitored positions | per-run | unset | code edit | `volume_vs_avg_pct` stored |
| `pm.short_interest_5pct` | display.py:153-157 | monitor output | code-constant | short interest >5% of float ⇒ "elevated" | — | none | daily | same | per-run | unset | code edit | `short_interest_pct` stored |
| `pm.diverging_triggers_text` | display.py:196-199 | monitor output | code-constant (prose) | "VIX spikes above ~22–25", "US HY OAS widens above ~350bps" as the stated flip-to-diverging conditions | hardcoded prose, **not** tied to the regime classifier's 30/22/600/450 | none | daily | all monitor runs | static | unset | code edit | not recorded |
| `pm.weekly_watchlist_text` | display.py:266-278 | monitor output | code-constant (prose) | boxed "HOLD — CGT clock ticking. Macro confirming." with "VIX: stay below 20", "HY OAS: stay below 300bps", "don't break below 50d MA" — emitted whenever a CGT date exists, **regardless of actual regime/underlying state** | — | none | weekly | positions w/ CGT date | static | unset | code edit | not recorded |

## 12. Thesis lifecycle / governance constants

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `th.revisit_interval_30d` | theses/service.py:44, :64-67 | thesis creation | code-constant | every thesis gets `revisit_due_at = now + 30d`, which drives the RED overdue alert | 30d cadence for all theses | none | 30d | all theses | static | unset | manual edit | `theses.revisit_due_at` |
| `th.stale_evidence_14d` | theses/service.py:45, :889-894 | approval | code-constant | approval blocked when a cited evidence row is >14 days old unless `accept_stale_evidence` | — | none | 14d | agent-originated theses | per-run | james | explicit flag | `governance_events` |
| `th.symbol_suffix_gate` | theses/service.py:43, :53-58 | thesis creation | code-constant | symbol must end `.AU` or `.US` — a `.NYSE` thesis cannot be created by this path (though existing ones are monitored) | — | none | n/a | new theses | static | unset | code edit | — |
| `th.enter_thesis_governance_gate` | portfolio-conventions.md:70-83 | `enter_thesis` | governed-doc + code | capital cannot be deployed against a thesis unless `governance_status='approved'` | — | AUD | n/a | theses | per-run | james | approve | `governance_events` (DB trigger enforced) |
| `gov.transition_order` | governance/transitions.py; conventions:138-166 | all approvals | code-constant | `governance_events` INSERT must precede the status UPDATE in the same transaction; BEFORE-UPDATE triggers reject otherwise | order is load-bearing | none | n/a | 4 governed tables | per-run | james | none | `governance_events` |
| `gov.known_agents` | governance/agent_run_service.py:54 | agent runs | code-constant | only `macro-economist`, `sector-screener`, `theme-researcher` may log proposals | — | none | n/a | agent runs | static | unset | code edit | `agent_runs` |
| `gov.evidence_tiers` | agent_run_service.py:66 | agent runs | code-constant | tiers `verified`/`inferred`/`speculative`; a proposal citing a speculative claim **hard-fails** at log time | — | none | n/a | all proposals | per-run | james | none | `agent_evidence` |
| `px.coverage_gates` | prices/coverage.py:60-74 | data-quality gate | code-constant | MIN_COMPLETE_ROWS 1500 · COMPLETE_FRACTION 0.80 · NON_TRADING_MAX_ROWS 100 · lookback 30d · MAX_STALE_DAYS 5 | determines which symbols are considered priced | none | 30d | universe | per-run | unset | code edit | `job_runs` |
| `fx.foreign_suffixes` | prices/fx.py:20 | everything FX | code-constant | `.US/.NYSE/.NASDAQ/.AMEX` define "foreign" for FX conversion, rebalance exclusion, and the US alert job | suffix ≡ currency | mixed | n/a | all symbols | static | unset | code edit | — |
| `res.factor_constants` | research/factor_scores.py:46-79 | factor scores | code-constant | WINSOR 3.0σ · gross-up at 0.30 corporate rate · momentum 252d skip 21d · vol window 120d · price window 420d · composite over value+quality only | — | AUD | 1–12 months | universe | per-run | unset | code edit | `factor_scores` rows |

## 13. Agent prompts — `.claude/agents/*.md`

### `portfolio-coherence-reviewer.md`
| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `agt.pcr.conviction_bands` | :62 | agent output, `/pm-review` | agent-prompt | conviction **4–5 = high, 3 = medium, 1–2 = low, NULL = unassigned** (must be called out explicitly, never treated as low) | 1..5 SMALLINT | none | standing | held positions | per-run | unset | prompt edit | agent transcript only |
| `agt.pcr.size_drift_flags` | :65-66 | same | agent-prompt | flags a conviction-4/5 name below the **conviction-3 average** weight, or a conviction-1/2 name above the **conviction-4/5 average** | averages computed within the current book | AUD | standing | held positions | per-run | unset | prompt edit | none |
| `agt.pcr.signal_sell_30d` | :72-74 | same | agent-prompt | Model A SELL held >30 days with no acknowledging `thesis_revisions` event ⇒ flagged | — | none | 30d | held positions | per-run | unset | prompt edit | none |
| `agt.pcr.sector_gt_40pct` | :83-84 | same | agent-prompt | **sector >40% is flagged regardless of the configured `sector_cap_pct`** — a hardcoded band above the profile | concentration risk on its own | AUD | standing | sectors | per-run | unset | prompt edit | none |
| `agt.pcr.profile_caps` | :79-83 | same | agent-prompt | flags sector > `sector_cap_pct`, name > `per_name_cap_pct`, any holding in `excluded_sectors`/`excluded_symbols` | reads live profile | AUD | standing | held positions | per-run | james | profile row | none |
| `agt.pcr.cash_gt_20pct` | :86-90 | same | agent-prompt | cash >20% **and** IN-BAND entries exist ⇒ "High cash with actionable entries available — review deployment." | IN-BAND per thesis-milestone-monitor | AUD | standing | portfolio | per-run | unset | prompt edit | none |
| `agt.pcr.stop_proximity_5pct` | :99-104 | same | agent-prompt | price within 5% of `stop_price` ⇒ proximity warning (explicitly not a violation) | — | native | daily | held positions w/ stop | per-run | unset | prompt edit | none |
| `agt.pcr.theme_coherence` | :93-97 | same | agent-prompt | high-`conviction_band` theme with no weight = gap; low-`conviction_band` theme with large `exposure_strength` = inconsistency | non-retired themes only | none | standing | themes | per-run | unset | prompt edit | none |
| `agt.pcr.lot_aggregation` | :49-53 | same | agent-prompt | must aggregate MV **by symbol** across lots before weights/caps; `.US/.NYSE/.NASDAQ/.AMEX` converted to AUD or explicitly excluded and stated | the R10 currency trap | AUD | n/a | all weight math | per-run | james (R10) | none | none |
| `agt.pcr.lateral_limit1` | :30-48 | same | agent-prompt | anchor query uses LATERAL … LIMIT 1 on prices/theses/signals so one lot ≠ multiple rows (no unique constraint guarantees one active thesis per symbol) | — | none | n/a | anchor query | per-run | unset | none | none |
| `agt.pcr.documented_deviation_exempt` | :126-131 | same | agent-prompt | a deviation documented in `thesis_revisions`/`decisions` is **noted, not flagged** — only undocumented deviations are findings | — | none | standing | all checks | per-run | james | write a revision | `thesis_revisions` |
| `agt.pcr.own_framework_only` | :7-11, :126-129 | same | agent-prompt | checks against the user's own stated rules only — never an external standard of a "good portfolio"; never recommends selling | — | none | standing | all output | static | james | none | none |

### `thesis-milestone-monitor.md`
| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `agt.tmm.on_track` | :62 | agent output | agent-prompt | progress ≥ elapsed/timeline ⇒ ON TRACK | mirrors `classify_trajectory` | native | thesis timeline | active theses | per-run | unset | prompt edit | none |
| `agt.tmm.behind_50pct` | :63-64 | same | agent-prompt | progress < 50% of linear expectation ⇒ BEHIND (both halves of the timeline) | — | native | thesis timeline | same | per-run | unset | prompt edit | none |
| `agt.tmm.stalled_5_40` | :65 | same | agent-prompt | <5% progress after >40% of `timeline_days` ⇒ STALLED | — | native | thesis timeline | same | per-run | unset | prompt edit | none |
| `agt.tmm.stop_violated` | :66-68 | same | agent-prompt | `current ≤ stop` ⇒ STOP VIOLATED, highest priority, cite the close date; NULL stop ⇒ "no stop set", never assumed | — | native | daily | same | per-run | unset | prompt edit | none |
| `agt.tmm.above_target` | :69-70 | same | agent-prompt | `current ≥ target` ⇒ "thesis played out; flag for close + profit-realisation review" | — | native | daily | same | per-run | unset | prompt edit | none |
| `agt.tmm.cost_anchor` | :52-54 | same | agent-prompt | anchor = `actual_entry_price`, else `SUM(cost_base_normal)/SUM(quantity)` across **all** open lots — never a single arbitrary lot | (note: this fallback is the AUD base — the R10 trap for foreign lots) | mixed | n/a | all pace math | per-run | james (R10) | set `actual_entry_price` | none |
| `agt.tmm.required_rate_annualised` | :57-59 | same | agent-prompt | must report the implied annualised return; **"a 40% gain needed in 60 days is a red flag regardless of thesis quality"** | plausibility framing | native | remaining days | same | per-run | unset | prompt edit | none |
| `agt.tmm.entry_band_states` | :72-75 | same, feeds `agt.pcr.cash_gt_20pct` | agent-prompt | "IN BAND — entry opportunity" / "ABOVE BAND — wait" / "BELOW BAND — approaching" | for watching theses or active-with-no-lot | native | daily | watching theses | per-run | unset | prompt edit | none |
| `agt.tmm.no_timeline_advice` | :90-95 | same | agent-prompt | must not recommend extending timelines or changing stops; must not treat a % return as inherently achievable | — | none | standing | all output | static | james | none | none |

### `thesis-coherence-guard.md`
| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `agt.tcg.verdict_ladder` | :31-40 | `/pm-review` | agent-prompt | COHERENT / NEEDS REVIEW / CONTRADICTED, with worked examples (e.g. `pe_ratio+0.28` opposing a "PE compression" thesis ⇒ CONTRADICTED) | SHAP direction is interpretable | none | current signal | active theses | per-run | unset | prompt edit | none |
| `agt.tcg.top3_shap` | :26-29, :42-44 | same | agent-prompt | exactly the top 3 SHAP factors; **never** state coherence without quoting a factor + value | — | none | daily | symbols w/ signals | per-run | unset | prompt edit | none |
| `agt.tcg.thesis_fatigue` | :46-54 | same | agent-prompt | a run of `reviewed_no_change` revisions with no `assumption_change`/`target_adjusted` "may signal thesis fatigue rather than evidence-based holding" | last 3 revisions, joined on `thesis_id` not symbol | none | multi-cycle | active theses | per-run | unset | prompt edit | `thesis_revisions` |
| `agt.tcg.ambiguous_shap` | :68-70 | same | agent-prompt | must not invent SHAP interpretations; ambiguous keys must be flagged for the ML conventions doc | — | none | n/a | all output | static | unset | none | none |
| `agt.tcg.not_runtime` | :62-66 | same | agent-prompt | never embeds in the automated brief, never fires without a human invoking a workflow | — | none | standing | agent | static | james | none | none |

### `benchmark-performance-analyst.md`
| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `agt.bpa.availability_gate` | :33-38 | `/pm-review` | agent-prompt | zero snapshots with `benchmark_tr_level` ⇒ report the gap and **stop** — no alpha number is produced | — | AUD | n/a | portfolio | per-run | unset | none | none |
| `agt.bpa.periods_and_alpha` | :40-56 | same | agent-prompt | MTD / YTD / since-inception; Alpha = Portfolio return − XJO return, using `capital_aud` endpoints | (same flow-affected `capital_aud` the V1 brief removed a line over) | AUD | MTD/YTD/inception | portfolio | per-run, stale-risk | unset | none | none |
| `agt.bpa.tr_approx_label` | :17-20 | same | agent-prompt | when `trailing_div_yield_pct IS NOT NULL`, output must be labelled "XJO-TR approx" | proxy vs real accumulation index | AUD | n/a | benchmark | per-run | unset | none | `portfolio_daily_snapshots` |
| `agt.bpa.attribution_approximate` | :58-67 | same | agent-prompt | Brinson attribution flagged "approximate, no sector benchmark available"; must state what cannot be computed | — | AUD | n/a | portfolio | per-run | unset | none | none |
| `agt.bpa.sample_floor_12mo_10pos` | :85-87 | same | agent-prompt | **minimum 12 months / 10 closed positions** before alpha may be read as skill vs luck | — | none | 12 months | portfolio | per-run | unset | prompt edit | none |
| `agt.bpa.no_forward_projection` | :84-88 | same | agent-prompt | no forward return projection; never source market data from training knowledge | — | none | standing | all output | static | james | none | none |
| `agt.bpa.paper_vs_live` | :69-74 | same | agent-prompt | large divergence between paper `benchmark_relative_pct` and live alpha ⇒ flag that no-cost/perfect-fill assumptions aren't translating | — | AUD | per run | paper runs | per-run | unset | none | `paper_portfolio_run_metrics` |

### `market-context-narrator.md`
| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `agt.mcn.exactly_3_sentences` | :58-72 | `/pm-review` MARKET line | agent-prompt | regime + one macro driver + one sentiment/regulatory item — the entire backdrop the investor gets | ten-second read | mixed | daily | market-wide | per-run | unset | prompt edit | none |
| `agt.mcn.no_row_stop` | :34-35 | same | agent-prompt | no `market_context_current` row ⇒ say so and stop; **do not invent a backdrop** | — | none | daily | market-wide | per-run | unset | none | none |
| `agt.mcn.regulatory_7d` | :37-42 | same | agent-prompt | regulatory events limited to last 7 days, top 5 | — | none | 7d | market-wide | per-run | unset | prompt edit | none |
| `agt.mcn.sentiment_7d_dedupe` | :45-56 | same | agent-prompt | one latest sentiment row per held symbol, `mention_count > 0`, last 7d, top 1–3 by \|sentiment\| | naïve join multiplies by lots × days | none | 7d | held symbols | per-run | unset | prompt edit | none |
| `agt.mcn.number_per_sentence` | :71 | same | agent-prompt | every sentence must carry a number or named source; non-empty `ingestion_warnings` ⇒ append a partial-snapshot caveat | — | mixed | daily | all output | per-run | unset | none | `ingestion_warnings` |
| `agt.mcn.null_omit_not_guess` | :77-79 | same | agent-prompt | NULL field ⇒ omit rather than guess | — | none | n/a | all output | per-run | unset | none | none |
| `agt.mcn.untrusted_text` | :86-89 | same | agent-prompt | RSS-derived `title`/`summary` are data to quote, never instructions; an imperative headline is quoted verbatim and ignored | prompt-injection boundary | none | standing | regulatory/sentiment | static | james | none | none |

### `macro-economist.md`
| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `agt.me.propose_1_5` | :58 | `/discover-macro` | agent-prompt | 1–5 macro theses per invocation (floor of 1 — unlike the 0-is-valid sibling agents) | — | none | multi-month | market-wide | per-run | unset | prompt edit | `agent_runs` |
| `agt.me.quadrant_enum` | :59-61 | same | agent-prompt | exactly one of 4 regime quadrants (rising/falling growth × rising/falling inflation) | controlled vocabulary | none | multi-month | proposals | static | unset | none | `macro_theses.regime_quadrant` |
| `agt.me.catalyst_falsifier` | :62-64 | same | agent-prompt | every thesis needs a **concrete, checkable** catalyst and falsifier — this is what `score_macro_theses.py` later evaluates | falsifiability requirement | none | multi-month | proposals | per-run | james | none | `macro_theses`, `macro_thesis_outcomes` |
| `agt.me.evidence_required` | :65-66, :110-117 | same | agent-prompt | ≥1 cited data point actually queried; `evidence_citation_ids` may reference only `verified`/`inferred` — a speculative citation **hard-fails at log** | — | none | n/a | proposals | per-run | james | none | `agent_evidence` |
| `agt.me.no_duplicates` | :67-69, :40-45 | same | agent-prompt | must read `governed_active_macro_theses` first; a restatement is not a proposal | — | none | n/a | proposals | per-run | unset | none | `agent_runs` |
| `agt.me.regulatory_30d` | :47-54 | same | agent-prompt | 30-day regulatory lookback (vs the narrator's 7d) because macro runs on a multi-month horizon | — | none | 30d | market-wide | per-run | unset | prompt edit | none |
| `agt.me.no_stock_picking` | :10-13, :119-124 | same | agent-prompt | never picks stocks, never sizes a position, never writes to the DB, never marks anything approved | — | none | standing | all output | static | james | none | `governance_events` |

### `theme-researcher.md` / `sector-screener.md`
| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `agt.tr.zero_is_valid` | theme-researcher.md:79-86; sector-screener.md:75-80 | discovery commands | agent-prompt | **0–5** candidates; zero is an expected outcome reported as plainly as a positive; drafting proposals is "optional, never a mandate to produce content" | anti-content-pressure rule | none | multi-month | themes | per-run | james | none | `agent_runs` |
| `agt.tr.macro_conditioned` | theme-researcher.md:89-93 | `/discover-theme` | agent-prompt | every proposal must carry a non-NULL `macro_thesis_id`; a NULL one is by definition sector-screener's output | separates the two discovery directions | none | multi-month | themes | per-run | james | none | `themes.macro_thesis_id` |
| `agt.tr.no_macro_no_run` | theme-researcher.md:42-44 | same | agent-prompt | empty approved macro set ⇒ stop; do not invent a regime | — | none | n/a | themes | per-run | unset | none | none |
| `agt.tr.quadrant_containment` | theme-researcher.md:98-99 | same | agent-prompt | a theme fitting a different quadrant belongs to a different macro thesis and a different run | — | none | multi-month | themes | per-run | unset | none | none |
| `agt.tr.controlled_vocab` | theme-researcher.md:100-103 | same | agent-prompt | `conviction_band` ∈ {low, medium, high}; `stage` ∈ 6 lifecycle values — service layer hard-fails anything else | — | none | n/a | themes | static | unset | none | service raises |
| `agt.tr.exposure_not_weight` | theme-researcher.md:175-178 | same | agent-prompt | `exposure_strength` is a theme-exposure weight in [0,1], **not a portfolio weight**; never implies an order (s766B) | — | none | n/a | theme holdings | static | james | none | `theme_holdings` |
| `agt.tr.model_independent` | theme-researcher.md:180-182 | same | agent-prompt | reads no signals / ml_prob / allocator output (rule #11, standing) | — | none | standing | all output | static | james | none | none |
| `agt.ss.coverage_first` | sector-screener.md:24-40 | `/discover-sector` | agent-prompt | must confirm the sector is structurally low-coverage before screening; no rows ⇒ stop, don't invent a population | fills structural blindness, not re-covering | none | n/a | one sector | per-run | unset | none | `agent_runs` |
| `agt.ss.prior_screen_reuse` | sector-screener.md:51-56 | same | agent-prompt | a recent `screening_runs.matched_symbols` is "evidence to compose with, not to bypass or re-derive" | — | none | n/a | one sector | per-run | unset | none | `screening_runs` |
| `agt.ss.au_equity_population` | sector-screener.md:60-71 | same | agent-prompt | `is_active AND security_kind='au_equity'`, sector normalised via `COALESCE(NULLIF(sector,''),'Unclassified')` | — | AUD | n/a | one sector | per-run | unset | none | none |
| `agt.ss.stay_in_sector` | sector-screener.md:86-89 | same | agent-prompt | out-of-sector candidates belong to a different invocation; no duplicates of governed holdings | — | none | n/a | proposals | per-run | unset | none | `agent_runs` |
| `agt.discovery.readonly` | theme-researcher.md:165-173; sector-screener.md:144-156; macro-economist.md:126-128 | all three | agent-prompt + role grant | SELECT-only; only path to a live row is `--from-agent-run` (draft → pending_review) then a human `approve` | read-only role, not just prompt (per agent; macro-economist notes the known gap) | none | standing | all discovery | static | james | none | `governance_events` |

### `tax-spec-conformance.md` / `portfolio-invariant-guard.md`
| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `agt.tsc.spec_is_truth` | tax-spec-conformance.md:13-16 | tax diffs | agent-prompt + governed doc | `docs/foundation/spec/tax-alpha.md` governs all tax math; any deviation requires a **spec amendment**, not a fix | CLAUDE.md #8 | AUD | standing | `asxos/domain/tax/*` | per-diff | james | spec amendment | PR review |
| `agt.tsc.untested_vs_unimpl` | :26-31 | tax diffs | agent-prompt | must state explicitly which spec sections are implemented+tested / implemented+untested / **unimplemented** — refuses to let "untested" hide "unimplemented" | historical drift class (TC-20/21) | none | n/a | tax module | per-diff | james | none | PR review |
| `agt.tsc.inference_flags` | :32-35 | tax diffs | agent-prompt | any treatment correct-by-inference without a numeric §11 worked example (e.g. SMSF ECPI-on-CGT with non-zero pension proportion) must not be relied on until a new TC exists | — | AUD | n/a | tax module | per-diff | james | new TC | PR review |
| `agt.tsc.decimal_traps` | :36-37 | tax diffs | agent-prompt | SMSF 1/3 is truncated not exact; ledger lines quantize to cents; bases keep full precision | — | AUD | n/a | tax module | static | james | none | — |
| `agt.pig.hardfail_table` | portfolio-invariant-guard.md:23-27 | portfolio diffs | agent-prompt + governed doc | verifies no `logger.warning; continue` appears on: no active profile · empty buy universe · non-convergent waterfall (>5 iters) · stale signals (>2 days) · missing reference price | — | none | n/a | `asxos/domain/portfolio/*` | per-diff | james | none | PR review |
| `agt.pig.silent_omit_ok` | :28-30 | portfolio diffs | agent-prompt | insufficient price history → silent omission and missing price → omitted from snapshot are **deliberate**; must not be "fixed" into raises | characterisation not bug | none | n/a | same | per-diff | james | none | PR review |
| `agt.pig.boundary_defer_location` | :31-33 | portfolio diffs | agent-prompt | the `defer_near_boundary_sells` check must stay in `compute_deltas`, calendar arithmetic, **30-day window** | — | none | 30d | rebalance.py | per-diff | james | none | PR review |
| `agt.pig.firewall_check` | :17-22 | portfolio diffs | agent-prompt | every new surface that could emit personal-advice output must have `_require_personal_use()` / `ASXOS_PERSONAL_USE` / `ASXOS_PORTFOLIO_BRIEF_ENABLED` | s766B / Westpac v ASIC | none | standing | all portfolio surfaces | per-diff | james | none | PR review |
| `agt.pig.single_user_deliberate` | :38-41 | portfolio diffs | agent-prompt | never recommend multi-user auth/RLS | — | none | standing | all | static | james | none | — |

## 14. `.claude/commands/pm-review.md` — the verdict ladder

| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `cmd.pmr.verdict_labels` | pm-review.md:43 | investor-facing verdict | agent-prompt/spec | the four labels: **GOOD HOLD \| TRIM \| REVIEW \| EXIT-CANDIDATE** | labels summarise evidence, not advice | none | per review | one symbol or whole portfolio | per-run | james | none | none (no run row) |
| `cmd.pmr.good_hold` | :59-60 | same | agent-prompt | coherent thesis **and** on/ahead of pace **and** beating-or-matching benchmark **and** fits the framework (conjunctive) | all four agents must be positive | AUD | per review | holdings | per-run | james | none | none |
| `cmd.pmr.trim` | :61 | same | agent-prompt | fundamentally sound but **oversized vs conviction, or a cap breach** | maps to portfolio-coherence-reviewer findings | AUD | per review | holdings | per-run | james | none | none |
| `cmd.pmr.review` | :62-63 | same | agent-prompt | mixed/contradictory signals, or any agent flagged NEEDS REVIEW / BEHIND | — | none | per review | holdings | per-run | james | none | none |
| `cmd.pmr.exit_candidate` | :64-65 | same | agent-prompt | **stop violated**, or thesis contradicted by evidence, or sustained benchmark lag with no coherent thesis. "(Surfacing it ≠ recommending a sale.)" | disjunctive — any one triggers | AUD | per review | holdings | per-run | james | none | none |
| `cmd.pmr.for_against_3` | :46-51 | same | agent-prompt | ≤3 strongest FOR and ≤3 strongest AGAINST, each with evidence + source agent | attention budget | mixed | per review | holdings | per-run | unset | none | none |
| `cmd.pmr.every_claim_traced` | :38-40, :72-74 | same | agent-prompt | every claim must trace to a specific agent's cited data point; no number the agents didn't produce; **no invented price target** | — | mixed | per review | all output | per-run | james | none | none |
| `cmd.pmr.evidence_thin_gate` | :76-78 | same | agent-prompt | if ≥2 of the 5 agents return "data not available", the review must be declared **evidence-thin** with the gaps named rather than forcing a confident verdict | — | none | per review | all output | per-run | james | none | none |
| `cmd.pmr.gap_no_substitute` | :33-35 | same | agent-prompt | a reported data gap is recorded, never substituted; must wait for all five agents before synthesising | — | none | per review | all output | per-run | unset | none | none |
| `cmd.pmr.five_agent_fanout` | :20-32 | same | spec | the five inputs are fixed: coherence-guard, milestone-monitor, benchmark-analyst, portfolio-coherence-reviewer, market-context-narrator | subagents cannot spawn subagents | none | per review | all reviews | static | james | none | none |
| `cmd.pmr.no_order_placement` | :9-11, :71-74 | same | agent-prompt + statute | never places an order, never says "you should buy/sell N shares"; s766B / Westpac v ASIC firewall is structural even for a single user | — | none | standing | all output | static | james | none | none |
| `cmd.pmr.portfolio_mode` | :66-69 | same | agent-prompt | whole-portfolio review = one line per holding + a portfolio summary + **the weakest 1–2 positions to look at first** | — | AUD | per review | portfolio | per-run | unset | none | none |

## 15. Governed docs

### `docs/product/portfolio-policy.md` (owner: **james**; arbi may only draft changes)
| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `pol.sector_cap_30` | :48 | every arbi memo | governed-doc | sector cap stated as **30%** per GICS sector; a memo breaching it is a policy-change proposal (P5), not a recommendation | cites conventions I.1 — but the live value is `profiles.sector_cap_pct`; **doc and profile can diverge** | AUD | standing | all memos | static, **stale-risk** | james | P5 draft, James enacts | `decision-log.md` |
| `pol.cash_floor_hole` | :50 | memos | governed-doc | **[governor to set / read from profile]** — arbi must read the active profile or ask; **must never invent one** | one of only two v1 structural protections | AUD | standing | all memos | unset value | james | set profile | — |
| `pol.leverage_cap_hole` | :51 | memos | governed-doc | **[governor to set / read from profile]** — same | the other structural protection | AUD | standing | all memos | unset value | james | set profile | — |
| `pol.return_drawdown_hole` | :29 | memos | governed-doc | return / drawdown targets **[governor to set]** — arbi does not assume a number | — | AUD | standing | all memos | unset value | james | governor sets | — |
| `pol.position_count` | :35-39, :49 | memos | governed-doc | conservative≈30 · balanced≈20 · growth≈15 · aggressive≈10; explicitly "a UX heuristic, not a calibrated model … a prior, not a law" | conflates variance tolerance with concentration preference | none | standing | all memos | static | james | profile scalar | — |
| `pol.composite_weights` | :52 | memos | governed-doc | 0.6 prob_up / 0.4 expected_return, "a starting prior, tunable in `profiles.score_weights_json`" | — | none | standing | allocation memos | static | james | profile JSON | — |
| `pol.cgt_calendar` | :53 | memos | governed-doc | calendar arithmetic, never day-count | CLAUDE.md #6, spec §5.1 | none | 12 months | tax memos | static | james | never | — |
| `pol.boundary_defer_30` | :54 | memos | governed-doc | near-boundary sell deferral = 30 calendar days | — | none | 30d | sell memos | static | james | profile flag | — |
| `pol.benchmark_after_tax` | :26-28 | memos | governed-doc | the target is to beat **XJO total-return after tax and costs**; "matching the index is failure of the thesis, not success of the tool" | — | AUD | multi-year | all memos | static | james | P5 | — |
| `pol.risk_blindness_accepted` | :56-61 | memos | governed-doc | the allocator is risk-blind to ASX beta clustering; **any memo touching concentration must state this caveat**, never imply the caps protect against co-movement; drawdown preservation is James's responsibility | 20 names under a 30% sector cap can still carry 0.8+ pairwise correlation | AUD | standing | concentration memos | static | james | v2 beta cap | — |
| `pol.model_a_quarantine` | :63-74 | memos + allocator | governed-doc | **standing policy**: no allocation decision or memo may use Model A output; every memo is model-independent (thesis discipline, realised benchmark gap, tax/CGT, concentration, theme stewardship) | decay dispute resolved 2026-07-11 against Model A on 19,032 matured signals | none | permanent | all memos + allocator | static | james | a new model passing a pre-registered decay bar | `ml-engine-shelf-2026-07-11.md` |
| `pol.loss_harvest_info_only` | :80-83 | memos | governed-doc | must be cited **verbatim** in any memo emitting the tag; James is solely responsible for ATO compliance on rebuy | — | AUD | n/a | harvest memos | static | james | none | — |
| `pol.james_approves_capital` | :86-90 | memos | governed-doc | **any** capital deployment (buy/trim/add/exit) and any policy change require James's explicit approval; arbi proposes, James executes in his broker | — | AUD | standing | all | static | james | none | `decision-log.md` |
| `pol.memo_void_on_invention` | :92-97 | memos | governed-doc | a memo that omits the policy check, or invents a governor-set number, is **void** | circuit breaker | none | standing | all memos | per-memo | james | none | `arbi-scorecard.md` |

### `docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md`
| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `spec.posture_broadening` | :344 | brief tone | spec | "Permits new positions; can be assertive about ideas; standard stops" | — | none | daily | brief | static | james | — | — |
| `spec.posture_narrowing` | :345 | brief tone | spec | "Warns: gains concentrated, late-cycle behaviour; **prefer existing winners over new entries**" | — | none | daily | brief | static | james | — | — |
| `spec.posture_neutral` | :346 | brief tone | spec | "Defaults to position-level reasoning only; **suppresses theme-level enthusiasm**" | — | none | daily | brief | static | james | — | — |
| `spec.posture_orderly` | :347 | brief tone | spec | "Suggests tightening stops, holding cash, not opening new positions; looks for dislocations not themes" | — | none | daily | brief | static | james | — | — |
| `spec.posture_disorderly` | :348 | brief tone | spec | "Explicitly says **'do not act on new ideas today'**; re-examine existing positions only; consider whether stops should be moved further out to avoid forced selling" | — | none | daily | brief | static | james | — | — |
| `spec.thesis_card_regime_line` | :358 | thesis cards | spec | under risk-off or risk-on-narrowing each card should add "Regime context: late-cycle posture, consider whether sizing should be reduced." — **not implemented in the collectors** | — | none | daily | thesis cards | static | james | — | gap |
| `spec.new_ideas_suppression_msg` | :359 | brief section 6 | spec | suppression should read "N idea(s) identified but suppressed by current market regime. Re-evaluate when…" — code emits `error="regime=<label>"` instead | — | none | daily | new_ideas | static | james | — | gap |
| `spec.market_ctx_freshness_2td` | :370 | brief section 2 | spec | brief requires `market_context.as_of >= CURRENT_DATE − 2 trading days` or section 2 is suppressed with a stale warning — **collector uses exact `as_of = $1` and returns `no_data`, not `suppressed`** | — | none | 2 trading days | market_context | static | james | — | gap |
| `spec.user_override` | :350 | regime | spec | "The classifier … will be wrong sometimes. The user can override." — no override mechanism exists in code | — | none | daily | regime | static | james | — | gap |

### `.claude/rules/*` (load-bearing repo rules)
| rule_id | source | consumer | auth | decision effect | assumptions | ccy | horizon | applicability | fresh | owner | ovr | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `rul.firewall` | portfolio-conventions.md:8-18 | all portfolio surfaces | governed-doc | `ASXOS_PERSONAL_USE=1` on every CLI/job; brief section 6 needs the second gate `ASXOS_PORTFOLIO_BRIEF_ENABLED=1`, held at 0 until 4 weeks of paper-trade sign-off | s766B / Westpac v ASIC | none | standing | all | static | james | env vars | `job_runs` |
| `rul.model_gate` | portfolio-conventions.md:21-66 | allocator + brief | governed-doc | allocator `required=True` hard-fails on 0/>1 approved models (rule #11's enforcement point); brief paths `required=False` degrade | `approved_for_allocation` ⟂ `is_active` | none | standing | build + brief | static | james | manual UPDATE (no CLI verb exists yet) | `model_versions` |
| `rul.r10_currency` | portfolio-conventions.md:308-333 | all return math | governed-doc | `cost_base_normal` is **AUD**, not native; dividing by quantity for a foreign lot is a currency error — it made two agents report HUBS as −29%/stop-violated when it was ≈ +9.8% USD | HUBS acquisition FX 0.6450 confirmed against the statement | mixed | n/a | foreign lots | static | james | none | documented incident |
| `rul.hard_fail_table` | portfolio-conventions.md:370-383 | build | governed-doc | the 8-row canonical hard-fail/silent-omit table (mirrors `pf.*` rows above) | — | none | n/a | portfolio | static | james | none | — |
| `rul.brief_freshness_2d` | portfolio-conventions.md:387-393 | brief section 6 | governed-doc | Saturday 20:00 UTC build; if the cron fails, section 6 is **omitted — not partial, not stale** | — | none | weekly | brief | static | james | none | `job_runs` |
| `rul.signal_thresholds_canonical` | ml-conventions.md "Signal Thresholds" | signal generation | governed-doc | the 5-label block "canonical — do not modify without explicit instruction" | — | fraction | 5d | all signals | static | james | explicit instruction | `signals` |
| `rul.validation_thresholds` | ml-conventions.md "Validation Thresholds" | retrain gate | governed-doc | MIN_ROC_AUC 0.65 · MAX_DEGRADATION 5% · MIN_SAMPLES 1000 | — | none | n/a | retrain | static | james | none | `model_versions` |
| `rul.screening_scope` | screening-conventions.md "Scope" + "source_method" | screening | governed-doc | au_equity only in v1; `curated_composite` CHECK must never be widened to re-admit `shap_threshold`/`surrogate_tree` | rule #11 standing | none | standing | screening | static | james | never widen | migration 0038 |

---

## Possibly missed surfaces (globs not swept)

- `migrations/*.sql` — **highest-value gap.** DB `CHECK` constraints are repo-side rule text (conviction_level 1..5, `score_weights_json` sum ∈ [0.999,1.001], `source_method='curated_composite'` in 0038, governance-status enums, the `set_active_profile` function, the four governance audit triggers in 0034/0036, `machine_conditions` shape in 0041). I read these only via their Python mirrors.
- `asxos/api/routes/*.py` — not swept; any threshold or gate exposed over HTTP.
- `asxos/cli/*.py` (except `tax.py` grep and `screen`/`portfolio` references) — `thesis.py`, `portfolio.py`, `theme.py`, `macro.py`, `monitor.py`, `news.py`, `profile.py` likely carry display bands, confirmation prompts, and `_require_personal_use()` gates.
- `asxos/ingestion/*.py` — `fundamentals.py` propagate_* functions, `market_context` fetchers, sentiment normalisation ranges.
- `asxos/domain/signals/feature_engine.py` + `feature_groups/*` — the 22-feature contract and `_safe_quintile` boundaries.
- `asxos/domain/models/{train,training_config,metadata,cache,production_gate}.py` — read only `validation.py` and `production_gate` via references; `training_config.py:122 _CONFIGS_BY_VERSION` holds per-version label/horizon definitions.
- `asxos/domain/research/{alpha_eval,alpha_loader}.py` — horizons `(5,10,21,63)`, `_TRADING_DAYS_PER_CAL_DAY 1.40`, IC/decay bars used in the Model A decay verdict.
- `asxos/domain/journal/`, `asxos/domain/regulatory/`, `asxos/domain/governance/agent_run_guards.py` — skimmed only.
- `tests/**` — swept only `test_regime_classifier.py`/`test_thesis_discipline.py` by name; ~120 test files pin numeric boundaries that are de-facto rule specifications (`test_thresholds.py`, `test_constraints.py`, `test_severity.py`, `test_tax_*`).
- `scripts/`, `scripts/hooks/`, `.claude/hooks/`, `.claude/skills/**` — not swept (`arbi-mission`, `pr-readiness`, `reversible-work-window` skills may embed capital-boundary rules).
- `.claude/agents/arbi.md`, `arbi-red-team.md`, `guilfoyle.md` — not swept; `arbi.md` likely restates the P-ladder and capital boundaries.
- `docs/product/arbi-*.md` (permission-model, constitution, scorecard, autonomy-loop, promotion-gate, rubrics/*) — only `portfolio-manager-charter.md` was grepped; `arbi-permission-model.md §Portfolio ladder` defines P0–P6 and is directly action-gating.
- `docs/proposals/*.md` (~20 files) — `portfolio-team-visibility-2026-07-12.md` §7 (digest firewall), `personal-advice-firewall-amendment-2026-07-18.md`, `cgt-break-even-amendment-2026-06-28.md`, `broker-report-rubric-2026-07-18.md`, `etf-lic-screening-criteria-2026-07-12.md`, `macro-thesis-learning-loop-2026-07-21.md` all likely carry rules not yet in code.
- `docs/foundation/spec/tax-alpha.md` — grepped for warning-producing sections only; §5.2 loss-ordering, §6.3 Div 296 proportioning, §8.2 FX translation, and the full TC-01..TC-24 matrix are not enumerated above.
- `docs/product/recommendation-schema.md`, `portfolio-outcome-ledger.md`, `north-star.md`, `risk-register.md` — not swept; `recommendation-schema.md` in particular sounds like it defines memo-output rules.
- `CLAUDE.md` (21KB) — the numbered non-negotiables (#1 no silent clamping, #5 Decimal-only, #6 calendar CGT, #8 tax spec authoritative, #10 hard-fail, #11 Model A quarantine) are referenced throughout the rows above but the file itself was not read end-to-end.
- `render.yaml` — cron schedules only skimmed via `job-conventions.md`; the `as_of` anchoring per job is a freshness rule.


---

## Appendix C — Panel #1: finance adversary

# Panel agent #1 (finance adversary, general-purpose) — verbatim output, 2026-08-08

All evidence is assembled: the frozen packet, the full rule manifest, panel-4's self-audit, and independent code verification (invalidation job, wealth_state collector, V1 compose discipline path, agent #4's charter). Here is my deliverable.

---

# FINANCE ADVERSARY — panel agent #1 report, 2026-08-08

Evidence base: packet `finance-red-team-evidence-2026-08-08` (entries cited `id@hash`), rule manifest (frozen 2026-08-08, denominator NOT reconciled — coverage claims below apply to swept surfaces only), repo at origin/main 1b471b60, panel-4 file. Functional-influence classes used throughout: {informational | framing-influential | functionally-directive}. I direct no action on any live position; where a competent process is described, it is described as process, not as an instruction about HUBS or CBA.

---

## 1. The mock's decision framing

**1.1 (CONFIRMED) The headline number was false, and the production process that made it false is the finding.** "DAY 36 BELOW STOP" = days(2026-07-03 → 2026-08-08). Its sole source is `invalidation_conditions[0].status='triggered'` written once on 2026-07-03 (`E01@21ff37f2`) — a write-once flag with no re-arm semantics: the job explicitly never re-evaluates triggered conditions (`/Users/jpcino/Desktop/asxos/jobs/check_thesis_invalidations.py:18`, `:151-152`) and writes no reset path (`:161-178`). The price series contradicts the claim: closes above 230 USD on 07-20 (231.21 USD) and seven consecutive 07-28..08-05 (238.04 → 250.21 USD, high 251.12 USD) — 8 of the "36 days" were above the level (`E05@22e3234378`, re-verified against the raw closes; `D01@28d5d505` concurs). Even the trigger note's date is off by one: "close=192.120000 … on 2026-07-03" is the 2026-07-02 close; no 07-03 row exists (`E05`). A senior PM's first question to the junior — "did you pull the tape or did you trust the flag?" — has a known answer here. Worse, the flag's producer was dark through the only window that mattered: no `check_thesis_invalidations` run for as_of 2026-08-06/07/08 (`E08@ac39a924` note), so the card narrated the post-earnings state using discipline state frozen before the −19.1% USD day.

**1.2 (CONFIRMED as to facts; ASSESSMENT as to class) "Honour the stop and exit — `asx thesis close 2`" as path #1 is functionally-directive, toward an act that was simultaneously unauthored, unenforceable, and un-analysed.** Unauthored: the 230 USD stop is governor-confirmed placeholder/experiment (packet meta, governor_answers). Unenforceable: the shares are documented NON-DISPOSABLE inside a locked ESS window, and the row's own `tax_notes` demotes the stop to ALERT/REVIEW-only while locked (`E01@21ff37f2`) — a column the mock never read. Un-analysed: no tax consequence of exit appeared anywhere on the card, while the codebase carries an entire §9 tax-warning apparatus (manifest §9). "Honour" is a loaded verb: it frames obedience to a placeholder as integrity.

**1.3 (ASSESSMENT) The decision-of-three demanded a decision the facts could not support.** Path 1 required disposability (lock end date UNAVAILABLE — packet meta). Path 2 ("re-underwrite") required Q2 actuals vs the written falsifiers — unevaluated by any surface, actuals UNAVAILABLE (meta.unavailable_facts; `E09@5870e314` note). Path 3 ("hold in breach — record an override") presupposes a valid breach — the premise under dispute. All three options inherit "there is a live, seriously-authored, currently-breached stop," which fails on at least two of three components. The legitimate fourth option — "this rule is not well-formed; repair it, then decide" — was structurally absent. A card that offers only choices whose shared premise is false does not elicit a decision; it launders a premise.

**1.4 (ASSESSMENT) The disclaimer does not change the class.** "The system asks for a recorded decision. It does not recommend one" is a compliance sentence stapled to a recommendation architecture: urgency eyebrow ("ACTION REQUESTED"), verdict headline ("thesis invalidated by its own rules"), exit ranked first, "−8.5% vs stop" given equal billing with entry/target, a 36-day shame counter. Functional influence is a property of structure, not of the footer. The codebase itself already knows this: `disc.timeline_wording_firewall` deliberately strips "— review or close" from investor-facing discipline messages because naming an action is direction (manifest §1, discipline.py:220-229). The mock un-learned the repo's own firewall. Two further defects: the card presented a CGT discount date (1 Jun 2027) as fact while all HUBS ESS/CGT dates are UNKNOWN/NOT RELIABLE pending Div 83A facts (governor answers) — an unverified tax representation in a "dates rail" — and it juxtaposed "+12.2% vs entry" (USD leg: 210.45 vs 187.54 USD) with portfolio A$7,147.02 without disclosing that the AUD P&L rests on a disputed acquisition FX (0.6450 booked vs 0.7171 vendor; meta.unavailable_facts, `D01`), an R10-class omission.

**Functional-influence classification of the card: functionally-directive.** Rationale: for a single reader at 07:00, a ranked option list whose first entry names the exact CLI disposal command, under an "ACTION REQUESTED" eyebrow and an "invalidated" verdict, operates as a default recommendation regardless of the footer. (The footer earns the card "framing-influential" at most in intent; class is assigned on effect.)

**What a decision surface must do when rule-integrity is unproven — the ordering:**
1. **Rule integrity first.** Is the rule seriously authored, current, and in the state it claims? (placeholder? born-breached? stale trigger with no re-arm? semantics enum vs prose?) Fail → the only legitimate ask is *confirm or repair the rule*; render a rule-repair card, not an action card.
2. **Enforceability second.** Can any implied action be executed at all (lock windows, instrument constraints)? Fail → demote every trigger to ALERT/REVIEW on the face of the card — which `tax_notes` had already done in writing; the surface just never consumed it.
3. **Facts third.** Are the decision-relevant facts current and evaluated (price series vs flag; earnings actuals vs falsifiers; tax consequence per path; FX basis)? Unavailable facts are named on the card, not papered over.
4. **Options last**, unranked or status-quo-first, each carrying its own factual prerequisites and tax consequence, with any unavailable prerequisite printed on the option itself. "Insufficient evidence — no decision solicited today" is a valid and sometimes the correct output.

---

## 2. Ladders as authored, and the missing challenge-at-authoring

**HUBS (thesis 2, `E01@21ff37f2`):**

| Defect | What competent underwriting would have asked at authoring | Checkpoint needed |
|---|---|---|
| Stop 230 USD is 22.6% ABOVE entry 187.54 USD and above the whole entry band 185–190 USD on a long thesis; born-breached on the latest-close-at-authoring reading (2026-05-29 close 220.63 USD; `D01`, `E05`) | "Your stop is above your entry. Is this a stop, a trailing exit, or a placeholder? Which close series arms it?" | **Relational ladder lint at write time**: long thesis ⇒ stop < band_lo ≤ band_hi < target; violation requires an explicit attestation, not a silent save. `enter_thesis` today checks existence of stop/target, not coherence (portfolio-conventions.md:70-83; no ordering rule appears anywhere in the swept manifest — denominator caveat applies). |
| "on volume" qualifier in condition #1 is unenforceable: the production regex parses the price leg only (`check_thesis_invalidations.py:42-47`) and triggered on price alone (note text, `E01`) — the machine enforced a different rule than the human wrote. Conditions #2/#3/#4 match neither regex and are **silently skipped, never reported** (`inval.unparseable_skipped`, manifest §6): 3 of 4 written falsifiers were never machine-checkable and nothing says so. | "Which of these conditions can the machinery actually evaluate? Show me the parse." | **Round-trip parse-echo at authoring**: run the exact production parser on every condition at write time and echo back "what I will enforce: close < 230; the volume clause and conditions 2–4 will NOT be machine-checked." |
| `conviction_level` NULL on the position that is 100% of capital (`E01`, `E03`/`E06`) | "You are making the largest possible bet with no stated conviction." | **Required-at-activation field** (not at research stage). |
| ESS lock unrecorded at open (lot created 2026-06-03, `E06`); lock documentation appears in `tax_notes` only later; lock-at-authoring unproven (corrected frame, verbatim) | "Can these shares be sold at all? Until when?" | **Instrument-constraints field at open**: a stop on non-disposable shares is refused or auto-labelled ALERT-only at authoring — not discovered by a red team five weeks after the trigger. |
| 365d timeline with CGT-discount economics coexisting with a daily-close condition intended as an "immediate exit prompt" (governor answers) | "Your holding-period economics say ≥12 months; your trigger cadence says any single close. Which governs?" | **Horizon-consistency review** (see §3 item 3). |

**CBA (thesis 1, `E01@21ff37f2`):** band 42–45 AUD, stop 38 AUD, target 60 AUD against a market at 178.01 AUD (`E05@22e3234378`) — governor-classified ERROR from the start. A one-query sanity check (band vs last close: −76.4%) catches it at authoring. The system possesses the concept *downstream* — `disc.data_sanity_multiple` fires RED when live ≥ 2× target (manifest §1) — but (a) it exists only at read time, not write time, and (b) its applicability is *active* theses; CBA is `watching`, so on the swept surfaces no rule covers a watching thesis's band sanity at all. Checkpoint: the same sanity multiple, applied at write time, to every status. And the stronger evidence that the authoring pathway has no lint of any kind: **all 11 research theses carry degenerate point bands, band_lo == band_hi** (`E02@16d71743` note) — a systematic artifact, not two isolated typos.

**Attack on R1 (authoring-time linting) itself — what lint does NOT catch:**
- **Placeholder-vs-serious intent.** A placeholder that *passes* lint (a syntactically clean stop typed with no analysis) is more dangerous than one that fails: lint launders it into apparent seriousness. Intent needs an attestation field ("basis for this stop: ___") and a trigger-semantics enum (`hard_exit | alert_review`) on the row — the governor's "immediate exit prompt" intent and the later ALERT-only `tax_notes` are two meanings of one column that no validator can distinguish from prose.
- **Revision rot.** Condition #2 embeds "50d MA ($243.61)" as frozen text (`E01`) — the MA moved every session since authoring; a t0-valid rule decays silently. Lint at write time does nothing at t+60; the fix is re-validation on every revisit (a rule-freshness clock), which also would have caught the stale `triggered` flag.
- **Semantic drift and state hygiene.** No lint prevents a write-once trigger from becoming permanently stale; re-arm/un-trigger semantics are a state-machine design gap (`D01` item 3), not an authoring-input gap.
- **The echo-back is the binding half.** Lint validates the ladder against itself; the failures here were ladder-vs-enforceability (lock) and ladder-vs-evaluator (regex). R1 without author → machine-parse → echo → confirm is half a fix.

---

## 3. Competent-human-baseline rubric

The checklist a good human advisor's process runs before any of this reaches a client, scored against the swept surfaces (denominator caveat stands):

| # | Item | Score | Evidence |
|---|---|---|---|
| 1 | Position size vs net worth & liquidity | **ABSENT** | No net-worth or external-liquidity concept in any schema/rule swept. Profile `capital_aud` A$6,666.98 is itself stale vs snapshot A$7,147.02 (`E03@77859aad`, `E06@028a9870`). The 5% cash yellow (`brief.cash_low_5pct`, wealth_state.py:86-93) measures in-system cash only; cash is A$0.00 against a `cash_floor_pct` of 0 (`E03`). |
| 2 | Single-name + single-currency + EMPLOYER concentration | **ABSENT** (composite); PARTIAL (generic single-name, and defective) | Employer correlation — ESPP means income AND equity on one company — appears in no field, rule, or agent prompt anywhere swept: the single most important risk fact about this book is *unrepresentable*. Generic concentration: `sev.concentration_10_20pct` exists (severity.py:172-194) but on the V2 daily brief it is **mechanically unreachable**: `wealth_state` joins prices with `p.dt = $1` (wealth_state.py:57-59) while the brief's as_of is today and prices end yesterday — `holdings_rows` is empty every morning, so the 100% RED can never render there (CONFIRMED in code; consistent with `E08@ac39a924` wealth_state item_count=3 — ASSESSMENT on item identities). The V1 discipline path prices `dt <= as_of` (compose.py:834-843) and would fire the generic RED, gated on `ASXOS_PERSONAL_USE=1`. Nothing scheduled anywhere reads `per_name_cap_pct`: its only consumers are the allocator (dead behind the 0-approved-models gate, `E04@417d7cfe`, `pf.production_gate`) and the on-demand agent prompt (`agt.pcr.profile_caps`). |
| 3 | Horizon-vs-stop consistency | **ABSENT** | A 365d CGT-driven hold coexists with a daily-close "immediate exit prompt" (governor answers) and nothing reconciles them. Worse, the surfaces disagree with each other by construction: `pm.weekly_watchlist_text` emits a boxed "HOLD — CGT clock ticking" whenever a CGT date exists *regardless of regime or stop state* (manifest §11) while the invalidation job emails "consider exit" — the system said HOLD and EXIT about the same shares in the same period. |
| 4 | Scenario/valuation basis for re-underwriting | **ABSENT** | Target 318 USD has no recorded derivation; no valuation-basis field exists on `theses` (`E01` columns). The mock's "re-underwrite" path had nothing to re-underwrite from, and its "+51.1% to target" stat anchored on an unmodelled number. |
| 5 | Tax interaction at the point of decision | **PARTIAL — rich but misrouted** | Extensive machinery exists (`sev.cgt_boundary_7_30` with a literal "do not sell"; `tax.cgt_break_even_hint`; `pf.boundary_defer_30d` — manifest §2/§9/§8), but none of it was composed into the decision card; and for this lot every CGT computation rests on an UNKNOWN Div 83A base (governor answers), so the one tax item the card *did* show (the discount date) was the one item currently unknowable. |
| 6 | What-would-change-my-mind hygiene | **PARTIAL — authored well, orphaned at evaluation** | Falsifier metrics written in `earnings_notes` (`E01`) are genuinely above-average practice — and machine-read by nothing: prose field, no evaluator. The Q2 print (2026-08-05 AMC) passed with no surface checking actuals vs falsifiers (meta.unavailable_facts); the sentiment surface scored a "guidance cut" headline 0.997 *positive* (`E09@5870e314`). The one item done right at authoring had no consumer at the moment it mattered. |

Pattern: the system checks what code finds easy (prices vs thresholds) and is silent on everything a human advisor asks first — who are you, what else do you own, where does your income come from, can you even sell this.

---

## 4. Behavioral audit

**4.1 (CONFIRMED mechanism; ASSESSMENT on effect) A confidence-manufacturing pipeline.** Free text → regex → write-once flag → "ACTION REQUESTED" card. Each stage strips a hedge: "on volume" dropped by the regex (check_thesis_invalidations.py:42-47); placeholder intent dropped by the schema (no semantics field); the recapture dropped by write-once state (no re-arm); the lock dropped by the card (`tax_notes` unread). A tentative experimental note entered the pipeline; a confident demand exited it. That is action bias built into the architecture, not into the prose.

**4.2 (ASSESSMENT) Disposition-effect terrain, inverted.** The position is up +12.2% in USD versus entry yet "below stop" — because the stop sits above entry. A card framing this as "honour the stop and exit" invites crystallising a gain to obey a malformed rule; a stop-above-entry on a long functions as a profit-taking tripwire, not risk control. Meanwhile the classic disposition failure (holding through deterioration) had live fuel — possible falsifier fire on 08-06 — and got no card at all.

**4.3 (CONFIRMED) The system's only "immediate exit prompt" was unactionable on every axis.** Delivery: `_send_alert` swallows all failures *including missing env vars* and the job reports success regardless (check_thesis_invalidations.py:104-122; `alert.send_never_raises`) — delivery on 2026-07-03 is unverifiable by design. Content: the email's literal ask was "Review thesis and consider exit. Run: `asx thesis exit HUBS.NYSE`" (check_thesis_invalidations.py:179-184) — a named disposal command for shares documented non-disposable (`E01` tax_notes). Follow-through: no revision event exists (the trigger deliberately writes none — `:6-8`), `last_revisited_at` stuck at 2026-07-04, revisit overdue from 08-03 through the earnings event (`E01`), zero recorded decisions in 5 weeks. Then the job went dark for 08-06/07/08 (`E08` note).

**4.4 (ASSESSMENT) What this combination trains.** An exit prompt that cannot be obeyed, attached to an alarm that cannot turn off (write-once flag ringing through 8 above-level closes, `E05`/`D01`), teaches exactly one behavior: ignore [INVALIDATION] emails. When the lock opens and a real stop on disposable shares breaks, the trained response is "that's the broken one." Discipline systems die this way — not by missing events, but by keeping stale ones ringing until the user habituates. Five weeks of standing "triggered" state with no possible action is a de-sensitization protocol.

**4.5 (CONFIRMED) Urgency inversion.** The genuinely decision-relevant sequence — Q2 print 08-05 AMC, −19.1% USD day 08-06 (250.21 → 202.43 USD), a headline corroborating a written falsifier (`E09`) — produced no evaluation from any surface, while the stale July trigger carried the "ACTION REQUESTED" eyebrow. In the same week, the system shouted about the wrong thing and said nothing about the right one.

---

## 5. Cross-examination of panel-4's self-audit

Overall verdict: **candid within its scope, self-serving in scope-selection.** It volunteered its unsourced magic numbers, graded its own rules DEAD/CONFLICTING where warranted, and caught its template's currency-naming flaw (verified: charter line 109 reads "Portfolio: $XXX,XXX" — `/Users/jpcino/Desktop/asxos/.claude/agents/portfolio-coherence-reviewer.md:109`). But candor about listed rules is not completeness about the rulebook. Specific challenges:

**C1 — A1's severity is right-labelled, wrong-located.** 100% vs a self-set 10% cap is HIGH *as a state*, and lock-unremediability does not lower exposure severity — it changes remediation from "trim" to "know, and stop the framework pretending." But the finding that survives cross-examination is the one panel-4 never asked: **who was supposed to tell James, and why did nothing for the life of the position?** Verified answer: `per_name_cap_pct` has no scheduled reader (allocator dead behind the model gate, `E04`; agent prompt is on-demand only), and the generic concentration RED is unreachable on the V2 daily brief via the exact-date price join (wealth_state.py:57-59 — my independent find, not in the packet or panel-4). The SYSTEM had no surface that could say so — that is the remediable finding, and A1 buried it under the state description.

**C2 — A4 is too kind to its own rulebook's data supply.** It frames the `tax_notes`-vs-canonical-tables issue as documentation misplacement. Sharper: its exemption rule (`agt.pcr.documented_deviation_exempt`) depends on `thesis_revisions`/`decisions` — and the system's own automated trigger *deliberately writes no revision event* ("automated bookkeeping, not a user discipline event", check_thesis_invalidations.py:6-8). The canonical audit trail its exemption logic requires is structurally underfed by the machinery itself. Panel-4 audited its rule but not its rule's feedstock.

**C3 — A7 reproduces, gently, the frame it condemns.** It correctly assembles the three-way stop-semantics incoherence, yet still leads with "close 210.45 USD is 8.5% below the 230 USD stop" — measuring distance to a number its own Part B says "nobody firmly authored." If the stop is a placeholder, "below the stop" is a state of the *database*, not of the book. Its self-audit knew this (the stop-proximity entry says exactly that); finding A7's presentation didn't apply it.

**C4 — The self-inventory misses at least three charter-level defects (verified against the file):** (a) the anchor query's thesis LATERAL filters `status='active'` only (charter :42) — a watching thesis with a stop (CBA) is invisible to its stop-proximity and conviction checks even in live mode; unmentioned in Part B. (b) The anchor query itself still pulls `model_a` signal labels into every review's base row (charter :45-46) — Part B graded check 2 DEAD/CONFLICTING but not the anchor's own quarantine leak. (c) Charter :52-53 permits "state that non-AUD names are excluded from the weight math" as a compliant path — on this book that permission excludes 100% of holdings and yields an empty review; an absurd-on-current-book escape hatch it never noticed.

**C5 — Method rigor on its best extra finding.** "Noticed, not asked" item 1 computes −16.0% AUD (A$8,509.34 → A$7,147.02) off `capital_aud` endpoints — the flow-affected series the codebase itself removed a return line over (wealth_state.py:101-108) and that meta.unavailable_facts disqualifies for returns. It happens to be flow-clean here (one lot, cash A$0.00, constant cost across the window, `E06`), so the number stands — but the audit applied a method the system's own history flags without stating why it is valid this once.

**C6 — Scope blindness unnamed.** Part B counts `agt.pcr.own_framework_only` as LIVE and healthy. That meta-rule is precisely what scoped panel-4 away from C1's question (delivery machinery is not "the user's framework"). A rule that narrows your audit is not merely LIVE — it is load-bearing for what the audit missed. A candid self-audit names not just its data gaps but what its charter makes it structurally unable to see.

---

## 6. What I was not asked

Questions this envelope avoided: **(Q1)** Should the decision card have existed at all — what is the correct product response to a placeholder rule, as opposed to the correct card layout? **(Q2)** Did the system's live surfaces (the 07-03 email, the standing triggered flag) *cause* the five weeks of non-decision — an influence audit of what was actually delivered, not of the mock? **(Q3)** What single schema change (trigger-semantics enum + instrument-constraints + re-arm state machine) retires the largest class of these failures? **(Q4)** Who audits the auditors — the orchestrator built the flawed mock *and* the packet I graded it with, and `D01` pre-derives several findings; how much of this panel is independent adversarialism vs replaying the packet-builder's self-critique? (Disclosure: my independent contributions here are the wealth_state exact-date join, the charter defects in C4, the `_send_alert` env-var swallow, and the parse-echo/round-trip framing; the recapture timeline and stale-flag finding were packet-derived and re-verified against raw `E05`.) **(Q5)** Does the personal-advice firewall survive contact with ad-hoc surfaces?

**The most important is Q5, and here is the answer.** The codebase's s766B discipline is real and carefully built — env-var gates (`jobs.personal_use_firewall`, `v1.portfolio_section_triple_gate`), wording firewalls (`disc.timeline_wording_firewall`), advice-shaped-output bans (`cmd.pmr.no_order_placement`) — and **every one of them attaches to a pipeline.** The 2026-08-08 mock demonstrates that the highest-influence surface this system has ever produced — ranked action paths, a named exit command, an urgency eyebrow, on a live position — was generated in an ad-hoc artifact lane that none of those gates touch. The firewall is per-pipeline; surfaces are cheap to mint; therefore the protection is bounded by the discipline of whoever mints surfaces, which is exactly the failure mode a firewall exists to remove. The durable fix is that functional-influence classification attaches to the *output*, not the lane: any generated surface that renders a live position and names or ranks an action is functionally-directive by definition and must pass the §1 ordering (rule integrity → enforceability → facts → options) or be demoted to a rule-repair/informational card before it reaches the reader. Until a rule passes integrity and enforceability, it may not appear on any action-framed surface at all — which also answers Q1.

---

*Abstentions honoured: HUBS Q2 actuals vs falsifiers, ESS lock end date, Div 83A acquisition facts, the AUD acquisition-FX resolution, and actual alert delivery are all UNAVAILABLE (packet meta); no finding above depends on their resolution, and nothing in this report is a direction regarding any live position.*


---

## Appendix D — Panel #3: thesis-milestone-monitor

# Panel agent #3 (thesis-milestone-monitor) — verbatim output, 2026-08-08

# Finance red-team panel — agent #3 (thesis-milestone-monitor), work order D0-04

Scope discipline: per the governor mandate, this report contains **no computed returns, percentages, or performance figures**. All prices/dates are quoted verbatim from the frozen packet (`/Users/jpcino/.claude/jobs/cb048518/tmp/evidence-packet-2026-08-08.json`). Repo facts are from origin/main `1b471b60` at `/Users/jpcino/Desktop/asxos/jobs/check_thesis_invalidations.py` and the frozen manifest (`/Users/jpcino/.claude/jobs/cb048518/tmp/finance-rule-manifest-2026-08-08.md`, section 6). Facts not in the packet are marked UNAVAILABLE.

---

## Task 1 — Ladder coherence-as-authored

### 1.0 Independent re-derivation of the HUBS breach/recapture timeline (raw E05@22e32343, closing basis vs the 230 stop)

Re-derived directly from the raw close series, not from D01:

- **Authoring context**: thesis opened 2026-05-31 (E01@21ff37f2). Last close before opening: **220.63 on 2026-05-29** — below 230. First close after opening: **262.20 on 2026-06-01** — above 230. "Born-breached" therefore holds **only** on the latest-close-at-authoring reading, exactly as the governor frame states.
- Above 230: 06-01 (262.20), 06-02 (240.16).
- **Breach episode 1**: 06-03 (222.45) through 07-17 (224.26) — every listed close in that span is below 230.
- **Single-day recapture**: 07-20 (231.21).
- **Breach episode 2**: 07-21 (218.578) through 07-27 (223.01).
- **Recapture**: 07-28 (238.04), 07-29 (251.12), 07-30 (233.11), 07-31 (237.36), 08-03 (239.92), 08-04 (248.89), 08-05 (250.21) — seven consecutive closes above 230.
- **Breach episode 3**: 08-06 (202.43, day after the Q2 FY26 print 08-05 AMC per E01 earnings_notes) and 08-07 (210.45).

**Verdict on D01@28d5d505**: the derived timeline is **VERIFIED** against the raw closes, including the detail that the condition #1 note's close of 192.12 is the **2026-07-02** close (there is no 07-03 row in E05; 07-03 was the job run date — mechanism confirmed in code, `_fetch_latest_close` at `jobs/check_thesis_invalidations.py:91-101` selects `dt <= as_of`, and the note string interpolates `as_of` at line 165).

### 1.1 Per-thesis classification table

| Thesis | Labels | Evidence |
|---|---|---|
| **HUBS.NYSE** (id 2, active) | **MALFORMED + PLACEHOLDER + UNENFORCEABLE** | MALFORMED: stop 230 sits *above* both the entry band (185–190) and the actual entry (187.54, inside band) — a long thesis whose entry necessarily occurs below its own stop; born-breached on the latest-close-at-authoring reading (E01@21ff37f2; E05@22e32343, verified §1.0). Governor frame quoted: "Confirmed semantic/actionability defect; born-breached if intended as an immediate hard-exit trigger. Lock-at-authoring and intended trigger semantics remain unproven." PLACEHOLDER: governor answer — the 230 stop was "Placeholder / experiment (not firmed up)" at authoring (meta.governor_answers). UNENFORCEABLE: tax_notes documents shares as inside a LOCKED ESS window, NON-DISPOSABLE; stop and triggered condition #1 are ALERT/REVIEW levels only; lock end date UNKNOWN (E01@21ff37f2; meta.unavailable_facts). Not DETACHED: band 185–190 contained the actual fill and the price series has traded through band, stop, and near-stop levels (E05). Target 318 / timeline 365d are structurally ordered; the defect is concentrated in the stop rung. |
| **CBA.AU** (id 1, watching) | **MALFORMED + DETACHED** | MALFORMED: governor answer — the 42–45 band is "Error — wrong numbers from the start" (meta.governor_answers). DETACHED: the ladder is *internally* consistent as a long ladder (stop 38 < band 42–45 < target 60) but the live close is **178.01 AUD (2026-08-07)** (E05@22e32343) — outside every rung; on the entry-band check this is ABOVE BAND, but the whole ladder is unrelated to the live market, so "wait" framing would be meaningless. Aggravating: `invalidation_conditions` is empty, `conviction_level` NULL, `revisit_due_at` 2026-06-27 — D01@28d5d505 characterises it as 42 days overdue at packet build (derived figure, quoted not recomputed). |
| **TPW.AU** (id 3, research) | **MALFORMED** | Point band 5.67 == 5.67; stop NULL, target NULL (E02@16d71743). Market-relation label (DETACHED vs in-band): **ABSTAIN — no current price in the packet** (UNAVAILABLE). |
| **ATR.AU** (id 4, research) | **MALFORMED** | Point band 0.555; stop/target NULL (E02@16d71743). Market relation: ABSTAIN (no price in packet). |
| **WTC.AU** (id 5, research) | **MALFORMED** | Point band 36.88; stop/target NULL (E02@16d71743). Market relation: ABSTAIN. |
| **BAP.AU** (id 6, research) | **MALFORMED** | Point band 0.465; stop/target NULL (E02@16d71743). Market relation: ABSTAIN. |
| **BLX.AU** (id 7, research) | **MALFORMED** | Point band 1.72; stop/target NULL (E02@16d71743). Market relation: ABSTAIN. |
| **WA1.AU** (id 8, research) | **MALFORMED** | Point band 12.57; stop/target NULL (E02@16d71743). Market relation: ABSTAIN. |
| **OCL.AU** (id 9, research) | **MALFORMED** | Point band 10.2; stop/target NULL (E02@16d71743). Market relation: ABSTAIN. |
| **NEC.AU** (id 10, research) | **MALFORMED** | Point band 0.915; stop/target NULL (E02@16d71743). Market relation: ABSTAIN. |
| **EBR.AU** (id 11, research) | **MALFORMED** | Point band 0.38; stop/target NULL (E02@16d71743). Market relation: ABSTAIN. |
| **LLC.AU** (id 12, research) | **MALFORMED** | Point band 2.98; stop/target NULL (E02@16d71743). Market relation: ABSTAIN. |
| **KPG.AU** (id 13, research) | **MALFORMED** | Point band 3.57; stop/target NULL (E02@16d71743). Market relation: ABSTAIN. |

Notes on the 11 research ladders: E02's own note calls the degenerate point bands "a systematic authoring artifact"; all 11 carry `governance_status='approved'` by default. I did **not** label them UNENFORCEABLE — that label (per the mission's definition) denotes an external constraint blocking action on an otherwise-formed ladder; here the defect is internal (no rungs exist). Also material: no discipline machinery will ever flag these gaps while `status='research'` — the invalidation job selects `WHERE status='active'` (`check_thesis_invalidations.py:82`) and the manifest's `disc.no_stop_set_info` applies to active theses only (manifest §1).

**No active or watching thesis in the packet earns an unqualified WELL-FORMED.** Zero of 13.

---

## Task 2 — Invalidation-condition machinery audit (HUBS, 4 conditions in E01@21ff37f2)

### Machine-evaluability of the 4 conditions vs the regexes (`check_thesis_invalidations.py:42-47`; manifest `inval.price_below_regex` / `inval.price_above_regex` / `inval.unparseable_skipped`)

| # | Condition (verbatim) | Machine-evaluable? |
|---|---|---|
| 1 | "Price closes below $230 stop on volume" | **YES** — matches `_PRICE_BELOW_RE` ("Price…below…$230") → `('below', 230)`. **But the "on volume" qualifier is silently dropped**: the machine rule is close < 230 unconditionally, a narrowing of the authored condition with no record of the narrowing. |
| 2 | "50d MA ($243.61) not recaptured within 2 weeks of breach" | **NO — silently inert.** No `price/close/stock` keyword; matches neither regex → skipped at `check_thesis_invalidations.py:154-156`, never evaluated, never reported (`inval.unparseable_skipped`: "not recorded"). |
| 3 | "Macro regime shifts to risk_off_disorderly" | **NO — silently inert.** Not a price pattern. Note: the regime classifier emits exactly this label (`rgm.avix_disorderly_30`, manifest §10) and E08@ac39a924 shows the live regime string (`risk_off_orderly` in the new_ideas suppression error) — the datum exists in-system; no bridge to invalidation conditions exists. |
| 4 | "Three or more sell-side downgrades with consensus target below $220" | **NO — silently inert.** No keyword match ("consensus target below" lacks `price/close/stock`); also no downgrade-count data source is wired to this job. |

**3 of 4 conditions are dead text to the machinery, indistinguishable in the stored field from live ones** — an inert condition carries `status: "active"` exactly like a watched one, so the field cannot even represent "machine ignores this."

### Write-once trigger semantics as a rule defect

Code: `check_thesis_invalidations.py:151-152` (`if cond.get("status") != "active": continue`) plus docstring line 18 ("Already-triggered or resolved conditions are not re-evaluated"). Once condition #1 was set `triggered` on the 07-03 run (against the 07-02 close 192.12), no code path could ever touch it again. States the field **cannot represent**:

1. **Re-armed / currently-false**: the seven consecutive closes above 230 (07-28..08-05, verified §1.0) left the field asserting a breach the market had negated. D01 notes the 2026-08-08 brief mock read this stale state ("day 36 below stop").
2. **A second, distinct trigger episode**: the 08-06 re-breach (202.43, post-Q2-print — the breach the governor's intended semantics, "immediate exit prompt," most needed) cannot fire; the stored note remains frozen at "auto: close=192.120000 below 230 on 2026-07-03."
3. **Episode history/count**: E05 shows three separate breach episodes and two recaptures vs 230; the field holds exactly one state and one note.
4. **Partial satisfaction**: the price leg true but the "on volume" leg unevaluated — no representation exists.
5. **Resolution provenance**: nothing writes `resolved`; the only exit from `triggered` is a manual JSONB edit with no revision event and no governance transition (`inval.trigger_writes_status`).
6. **Note-date provenance**: the note records the *run* date (07-03), not the *price* date (07-02) — verified against E05 (no 07-03 row exists).

### Operational gap (separate from the semantic gap)

E08@ac39a924: `check_thesis_invalidations` last succeeded for `as_of` **2026-08-05**; no runs exist for 08-06, 08-07, or 08-08, while `compose_brief` ran for 08-08. The 08-06 crash close (202.43) has **never been evaluated by the discipline machinery**. The reason for the missed runs is **UNAVAILABLE** in the packet (no scheduling evidence for this job is frozen).

**Compound finding (the most important one)**: the two gaps mask each other. Had the job run on 08-06/08-07, it would have evaluated **nothing** for HUBS — condition #1 is non-`active` (skipped at line 152), conditions #2–#4 are unparseable (skipped at line 156). Under current semantics, closing the operational gap alone produces **zero alerts** on the re-breach. The write-once defect fully absorbs the crash.

### The 5 written falsifier metrics in earnings_notes

E01 earnings_notes (verbatim): "net adds <10k/qtr, avg sub revenue/customer stalling <=$11,700 CC, NRR <103%, credit consumption decelerating sharply from +67% QoQ, revenue below $897M guide or FY26 cut."

**Answer: no surface evaluates them. None.**
- The manifest contains **zero** rules referencing `earnings_notes` (grep: no matches in the frozen manifest).
- The invalidation job reads only `invalidation_conditions` (`check_thesis_invalidations.py:80-84`).
- The only reader in the brief domain, `asxos/domain/brief/collectors/active_theses.py:43`, SELECTs `earnings_notes` and then **never references it again** — fetched and dropped; the collector's earnings logic uses only `next_earnings_date` proximity (lines 167-173; manifest `sev.earnings_double_risk_14d`/`sev.earnings_30d_yellow`).
- The AU/US position jobs use `next_earnings_date` proximity only (`au.earnings_5d`/`us.earnings_5d`).
- The macro falsifier machinery (`macro.falsifier_no_auto_retire`, `score_macro_theses.py`) evaluates `macro_theses.machine_conditions` only — not thesis-level notes.
- Corroboration that this matters right now: meta.unavailable_facts lists the Q2 actuals-vs-falsifiers comparison as never evaluated; E09@5870e314 shows a "Guidance Cut" headline (2026-08-07) — touching the fifth written falsifier — scored **0.997 positive** polarity by the news pipeline.

### Findings list

| # | Finding | Evidence | Severity |
|---|---|---|---|
| F1 | 3 of 4 HUBS invalidation conditions are machine-inert and silently skipped; inert conditions are indistinguishable in the stored field from watched ones | E01@21ff37f2; `check_thesis_invalidations.py:42-47,154-156`; manifest `inval.unparseable_skipped` ("not recorded") | HIGH |
| F2 | Condition #1's "on volume" qualifier is silently dropped — machine rule is price-only, narrower than authored, with no record | E01; code:42-44,66-74 | MEDIUM |
| F3 | Write-once trigger state machine (`active`→`triggered`, one-way): cannot represent re-arm, re-trigger, episode history, partial satisfaction, or resolution provenance; asserted a breach through a 7-close recapture and cannot fire on the 08-06 re-breach | E05@22e32343 (verified §1.0); D01@28d5d505; code:151-152, docstring:18 | HIGH |
| F4 | Trigger note records run date, not price date ("close=192.120000 … on 2026-07-03"; 192.12 is the 07-02 close) | E01; E05; code:91-101,165 | MEDIUM |
| F5 | Operational gap: no invalidation run for as_of 08-06/07/08; the earnings-crash close was never machine-evaluated; cause UNAVAILABLE in packet | E08@ac39a924 (incl. packet note) | HIGH |
| F6 | Compound masking: even with the schedule fixed, current semantics would have evaluated nothing for HUBS on 08-06 — cond #1 non-active, #2–#4 unparseable. Semantic defect fully absorbs the operational fix | F1+F3+F5; code:151-156 | CRITICAL |
| F7 | The 5 written earnings falsifiers are evaluated by no surface; the sole reading query fetches and drops the column; a headline touching falsifier #5 was sentiment-scored 0.997 positive | E01; E09@5870e314; `active_theses.py:43,167-173`; manifest grep: no `earnings_notes` rule | HIGH |
| F8 | Trigger writes have no audit trail (direct UPDATE, no `thesis_revisions` row, no governance event) and alert delivery is best-effort — `_send_alert` swallows all exceptions and returns silently on missing env vars, so delivery of the one 07-03 alert is unverifiable from the packet | manifest `inval.trigger_writes_status`, `alert.send_never_raises`; code:104-122,172-186 | MEDIUM |
| F9 | The invalidation email is the only alert surface naming an exit action ("Run: asx thesis exit <SYM>") — for HUBS that action is unexecutable while the ESS lock holds (tax_notes: NON-DISPOSABLE), and the wording sits in tension with the discipline module's deliberate s766B action-verb firewall | E01 tax_notes; manifest `inval.alert_wording` vs `disc.timeline_wording_firewall`; code:179-185 | MEDIUM |
| F10 | No schema surface can represent per-thesis trigger semantics (hard-exit prompt vs ALERT/REVIEW-only). The governor's intended semantics ("immediate exit prompt") and the lock-period ALERT-only override both live solely in free-text `tax_notes`, invisible to every job and collector | meta.governor_answers; E01 tax_notes | HIGH |

---

## Material items not asked for (optional, cited)

- **CBA sits in a total machinery blind spot.** It is `status='watching'`: the AU position job monitors `status='active' AND symbol LIKE '%.AU'` (`au.scope_filter`), the invalidation job monitors `status='active'` (code:82), and the manifest's `sev.revisit_overdue_red` applies to active theses via collectors that filter `status='active'` (`active_theses.py:45`). The one thesis with a governor-confirmed ERROR band, an empty invalidation array, and a D01-flagged overdue revisit is watched by **no** alert or discipline surface (E01@21ff37f2; E08@ac39a924; manifest §2, §6).
- **Concentration**: D01@28d5d505 flags `per_name_cap_pct=0.10` (E03@77859aad) against `holdings_count=1` at 100% of capital (E06@028a9870) with no surface flagging it — outside this agent's lane but corroborated by the packet; noting for the panel without further analysis.
- **`inval.bare_string_is_active` history**: the HUBS conditions were originally bare strings (job docstring, lines 54-57, citing thesis #2's first live run 2026-07-03); the dict rewrite on trigger is what made conditions #2–#4 carry `status: "active"` — the status that now falsely implies machine coverage (F1).

Key files: `/Users/jpcino/Desktop/asxos/jobs/check_thesis_invalidations.py`, `/Users/jpcino/Desktop/asxos/asxos/domain/brief/collectors/active_theses.py`, `/Users/jpcino/.claude/jobs/cb048518/tmp/evidence-packet-2026-08-08.json`, `/Users/jpcino/.claude/jobs/cb048518/tmp/finance-rule-manifest-2026-08-08.md`.


---

## Appendix E — Panel #4: portfolio-coherence-reviewer

# Panel agent #4 (portfolio-coherence-reviewer) — verbatim output, 2026-08-08

Both source files read and cross-checked; all figures below are re-verified against raw packet entries (D01 derived items were re-derived from E01/E05/E06/E08 before use). No live DB queries were run.

Sources: `/Users/jpcino/.claude/jobs/cb048518/tmp/evidence-packet-2026-08-08.json`, `/Users/jpcino/.claude/jobs/cb048518/tmp/finance-rule-manifest-2026-08-08.md` (§13, §2, §15), `/Users/jpcino/Desktop/asxos/.claude/agents/portfolio-coherence-reviewer.md` (working tree == origin/main 1b471b60).

---

# PART A — Current-state coherence read (packet-only)

Book at 2026-08-07: A$7,147.02 total = 1 position (HUBS.NYSE, 24 sh × US$210.45 = US$5,050.80 ÷ 0.7067 AUDUSD), cash A$0.00 (`E06@028a9870`, `E05@22e32343`). Weight arithmetic is FX-dispute-invariant: a single holding with zero cash is 100% of the book under any resolution of the acquisition-FX question.

| # | Finding | Evidence citation | Severity | Conditionality |
|---|---|---|---|---|
| A1 | **Per-name cap breached 10x.** Active profile `per_name_cap_pct=0.10`; HUBS.NYSE = 100% of capital (A$7,147.02 of A$7,147.02). The user's own configured cap is exceeded by a factor of 10. | `E03@77859aad`, `E06@028a9870` | HIGH | None on the weight (FX-invariant). Remediability is nil while the ESS lock is open: shares are documented NON-DISPOSABLE (`E01@21ff37f2` tax_notes); lock end date UNAVAILABLE (packet meta). |
| A2 | **Sector cap breached by construction.** One name = 100% of exactly one sector bucket, vs `sector_cap_pct=0.30` and my own hardcoded >40% band. | `E03@77859aad`, `E06@028a9870` | HIGH | HUBS's `universe.sector` value is UNAVAILABLE in the packet; the conclusion is invariant to which sector (or NULL bucket) it is. |
| A3 | **Conviction framework has no input data.** `conviction_level` is NULL on every thesis, including the one carrying 100% of capital. Per my charter, NULL = unassigned, never "low" — so the entire conviction-vs-size discipline is undefined over the whole book: the largest possible bet carries no stated conviction. | `E01@21ff37f2` | HIGH | None. |
| A4 | **Deviation documentation is in the wrong place per my own rulebook.** The substantive reason the concentration exists (locked ESPP, non-disposable) is written in `theses.tax_notes` — but my exemption rule (`agt.pcr.documented_deviation_exempt`) only credits `thesis_revisions`/`decisions`. Whether a qualifying revision/decision row exists is UNAVAILABLE (neither table is in the packet). As written, I must flag A1/A2 as undocumented while a substantive rationale sits in a non-canonical column. | `E01@21ff37f2`; manifest §13 | MEDIUM | Fully conditional on `thesis_revisions`/`decisions` contents (UNAVAILABLE this mission). |
| A5 | **Watching-thesis discipline broken for its only entry.** CBA.AU: revisit due 2026-06-27, 42 days overdue at packet build; entry band 42–45 AUD is governor-classified ERROR vs latest close 178.01 AUD; stop 38 / target 60 AUD both far below market — internally incoherent numbers consistent with the ERROR classification. The entry-band state machine is meaningless for this thesis. | `E01@21ff37f2`, `E05@22e3234378`, governor context | MEDIUM | Band classified as authoring error by the governor; not a market fact in dispute. |
| A6 | **Active-thesis revisit overdue through the earnings event.** HUBS revisit was due 2026-08-03 (last revisited 2026-07-04) — 5 days overdue at packet build, spanning the 2026-08-05 AMC print and the 2026-08-06 −19.1% USD day (250.21 → 202.43 USD). The user's own severity ladder makes any overdue day RED (`sev.revisit_overdue_red`). | `E01@21ff37f2`, `E05@22e3234378`; manifest §2 | MEDIUM-HIGH | None on the dates. HUBS Q2 actuals vs the written falsifiers are UNAVAILABLE (packet meta) — I note the exposure, not the outcome. |
| A7 | **Stop state incoherent across surfaces.** Close 210.45 USD is 8.5% below the 230 USD stop (both legs USD). But: (a) governor classifies the 230 stop as placeholder/experiment; (b) tax_notes documents it as ALERT/REVIEW-only while locked; (c) governor states intended semantics were "immediate exit prompt"; (d) invalidation condition #1 sits at stale `status='triggered'` from 2026-07-03 with no re-arm semantics, despite 7 consecutive recapture closes 07-28..08-05 (re-verified vs E05) and a fresh re-breach 08-06; (e) `check_thesis_invalidations` has not run for as_of 2026-08-06/07/08 — the discipline machinery is dark exactly through the crash. Three mutually inconsistent stop semantics plus stale state plus an unevaluated re-breach. | `E01@21ff37f2`, `E05@22e3234378`, `E08@ac39a924` (note), `D01@28d5d505` re-verified | HIGH (as a framework-integrity finding, not a position directive) | Lock-at-authoring and intended trigger semantics remain unproven (governor frame, verbatim); I classify the incoherence, I do not direct action. |
| A8 | **Position-count heuristic vs actual: 1 vs ~20.** `risk_tolerance=balanced`, scalar 0.5 → ~20-name heuristic (`pol.position_count`: explicitly "a prior, not a law"). Actual: 1 name. Extreme divergence, undocumented as far as the packet shows. | `E03@77859aad`, `E06@028a9870`; manifest §15 | MEDIUM | Heuristic, not a cap; documentation status UNAVAILABLE (see A4). |
| A9 | **Entry-band machinery degenerate across the research book.** All 11 research theses have `band_lo == band_hi` (point "bands") — a systematic authoring artifact. My cash-deployment check depends on IN-BAND states derived from these bands; that dependency currently rests on corrupt inputs (moot today only because cash = 0%). | `E02@16d71743` | MEDIUM | None. |
| A10 | **Trivially satisfied constraints, structurally hollow.** `cash_floor_pct=0` is met by cash A$0 (0 ≥ 0), `leverage_cap=1` is met at exactly 1.0, `min_position_aud=1000` met (A$7,147.02), `excluded_sectors/symbols` empty. Compliant — but the governed policy doc carries cash-floor/leverage as "[governor to set]" holes (`pol.cash_floor_hole`), and portfolio-conventions calls these two the *only* structural protections in v1; set at 0/1 they protect nothing. | `E03@77859aad`, `E06@028a9870`; manifest §15 | LOW | Whether 0/1 are decisions or defaults is UNAVAILABLE. |
| A11 | **Two divergent "capital" figures.** Profile `capital_aud` = A$6,666.98 (updated 2026-07-04) vs snapshot `capital_aud` = A$7,147.02 (2026-08-07). Any surface computing weights off the profile figure gets >100%. | `E03@77859aad`, `E06@028a9870` | LOW | None. |
| A12 | **Theme coherence: ABSTAIN.** HUBS carries themes `us-saas-ai`/`us-equities`, CBA `big-4-banks`, but `themes.conviction_band` / `theme_holdings.exposure_strength` rows are not in the packet. UNAVAILABLE — no finding either way. | `E01@21ff37f2`; packet scope | — | Entirely unavailable. |
| A13 | **Signal/holding alignment: DEAD check.** Model A `approved_for_allocation=false` (rule #11 quarantine mechanically in place); no signal rows in packet; the check cannot and should not inform this read. | `E04@417d7cfe` | — | See B3. |

FX discipline note on P&L (stated, not relied on): native USD P&L +US$549.84 (4,500.96 → 5,050.80 USD); AUD P&L +A$168.79 at booked acquisition FX 0.6450, ≈ +A$869.9 at vendor FX 0.7171 — both positive at current prices, but the CGT base and the sign at other price/FX combinations are UNRESOLVED (`E06@028a9870`, `D01@28d5d505` re-derived, packet meta unavailable_facts). No coherence finding above depends on this resolution.

---

# PART B — Self-inventory of my own rulebook (agt.pcr.*)

Candid classifications; primary class first, defects stated even where a rule half-works.

| rule_id | classification | rationale |
|---|---|---|
| `agt.pcr.conviction_bands` | LIVE (with UNSOURCED component) | The NULL-handling half is live and load-bearing today — it is the mechanism that produced finding A3 (`E01@21ff37f2`: all NULL). But the band cutoffs (4–5 high / 3 medium / 1–2 low) are a prompt-invented mapping with no governed-doc source, and zero rows currently exercise them. |
| `agt.pcr.size_drift_flags` | NOT-RUNNABLE-NOW | Requires cohort averages (conviction-3 average, conviction-4/5 average) across ≥2 positions with assigned convictions. Current book: 1 position, conviction NULL (`E01`, `E06`). Both averages are undefined — empty cohorts. Also UNSOURCED: the compare-to-cohort-average heuristic has no governed source. |
| `agt.pcr.signal_sell_30d` | DEAD | Depends on Model A signal labels. `approved_for_allocation=false` (`E04@417d7cfe`); rule #11 is standing policy and `pol.model_a_quarantine` says no investor-facing memo may use Model A output. Secondary: CONFLICTING — my charter still instructs fetching model_a signals for an investor-facing review, which as written contradicts the quarantine. Also epistemically hollow: flagging a hold against a SELL from a model with corr(ml_prob, 21d) = −0.03 is noise dressed as discipline. |
| `agt.pcr.sector_gt_40pct` | CONFLICTING (also UNSOURCED) | The 40% band is the FOURTH concentration threshold across surfaces: profile `sector_cap_pct` 30% (`E03`), governed doc `pol.sector_cap_30` 30%, `sev.concentration_10_20pct` 10%/20% per holding, `per_name_cap_pct` 10% (manifest §2/§13/§15). 40% appears nowhere outside my prompt — no governed source. Technically runnable today (100% > 40%) but it adds no information beyond the profile cap it duplicates-with-a-different-number. |
| `agt.pcr.profile_caps` | LIVE | My healthiest rule: reads the live profile row (owner: james, override: profile row), and produced today's headline finding (A1: 100% vs 10%). Degenerate-but-correct on a 1-name book. Minor gap: sector grouping needs `universe.sector`, which for HUBS is UNAVAILABLE in this packet — did not block the conclusion (A2). |
| `agt.pcr.cash_gt_20pct` | NOT-RUNNABLE-NOW | Cash = 0% (`E06`) — the trigger cannot fire. Two latent defects for cross-examination: the 20% threshold is UNSOURCED (no governed doc), and the "actionable IN-BAND entries" leg depends on entry bands that are currently corrupt across the board — 11 degenerate point bands (`E02@16d71743`) plus one governor-classified-ERROR band (CBA). Even with cash, this rule would run on broken inputs. |
| `agt.pcr.stop_proximity_5pct` | UNSOURCED | The 5% has no governed source (severity.py's 5% is approaching-*target* — a coincidental number, different check). Also semantically defective on the current book: the only stop in existence is 230 USD with price 210.45 USD *below* it — "within 5% approaching" is undefined for already-breached; violations are explicitly not my job. And the stop itself is governor-classified placeholder/ALERT-only, so proximity to it measures distance to a number nobody firmly authored. Effectively NOT-RUNNABLE-NOW as well. |
| `agt.pcr.theme_coherence` | NOT-RUNNABLE-NOW (this mission) | `themes.conviction_band` / `theme_holdings.exposure_strength` are not in the frozen packet — UNAVAILABLE under the data discipline; abstained (A12). The high-band-no-weight / low-band-big-exposure heuristic is also UNSOURCED (no governed thresholds for "large"). |
| `agt.pcr.lot_aggregation` | LIVE | The best-governed rule I have: derives from R10 (`rul.r10_currency`, owner james, documented incident). Exercised this mission: 24 × 210.45 USD = 5,050.80 USD ÷ 0.7067 = A$7,147.02, matching the snapshot (`E05`, `E06`) — both currency legs named throughout Part A. |
| `agt.pcr.lateral_limit1` | LIVE (not exercised this mission) | A query-correctness invariant (prevents thesis fan-out double-counting weights). Meaningful whenever I query live; this mission ran zero queries per the data discipline, so it was policy-idle but remains correct and necessary. |
| `agt.pcr.documented_deviation_exempt` | NOT-RUNNABLE-NOW (this mission) | `thesis_revisions`/`decisions` are not in the packet — I could not adjudicate whether the 100% concentration is a documented deviation. Candid defect independent of the packet: the rule's canonical-location rigidity means a substantive rationale living in `tax_notes` (`E01` — the ESS lock) earns no exemption credit. Either the rule should recognise more documentation surfaces, or the documentation belongs in the canonical tables; as written it produces false "undocumented" flags. |
| `agt.pcr.own_framework_only` | LIVE | Meta-rule; static; governed this very output (no external "good portfolio" standard applied, no sell recommendation emitted, imperatives avoided per mission discipline). Consistent with `pol.james_approves_capital` and the s766B firewall. |

Additional self-defect not in the manifest's rule list: my charter's output template (`portfolio-coherence-reviewer.md:109`, "Portfolio: $XXX,XXX") does not name a currency — an R10-adjacent flaw in my own reporting format, corrected ad hoc in Part A.

Score: of 12 charter rules — 5 LIVE (one with an unsourced component, one policy-idle this mission), 1 DEAD, 1 CONFLICTING, 1 UNSOURCED, 4 NOT-RUNNABLE-NOW. Roughly half my rulebook cannot meaningfully execute against the actual current book, and my two concentration numbers (40% sector, 5% stop-proximity) plus three others carry magic numbers with no governed source.

---

# Noticed, not asked (optional, cited)

1. **The book took a RED-by-its-own-ladder drawdown while every discipline surface was dark.** Capital A$8,509.34 (08-05) → A$7,147.02 (08-07), −16.0% AUD in two days (USD leg: 250.21 → 210.45 USD closes; FX 0.7057 → 0.7067) — RED under `sev.drawdown_3_5pct` (≥5%) — while `check_thesis_invalidations` last ran as_of 2026-08-05 and never evaluated 08-06/07/08 (`E06@028a9870`, `E05@22e3234378`, `E08@ac39a924` note, manifest §2). Overlaps A6/A7 but the drawdown-ladder angle was outside my charter.
2. **Sentiment surface mislabeled the adverse event.** A "guidance cut" headline scored 0.997 *positive* polarity (`E09@5870e314`), and the written falsifier in `earnings_notes` ("revenue below $897M guide or FY26 cut", `E01@21ff37f2`) may have fired — no system surface has evaluated it; Q2 actuals UNAVAILABLE (packet meta).
3. **Regime suppression compounds the framework's own gap.** The 2026-08-08 brief suppressed New Ideas entirely (`regime=risk_off_orderly`, `E08@ac39a924`) while the book is one locked foreign name — the diversification channel the profile's own 10%/30% caps presuppose is switched off by another of the framework's rules. A rule-interaction observation, not a critique of either rule alone.
4. **`pol.sector_cap_30` currently agrees with the profile (0.30) but only by coincidence** — the manifest marks the governed doc stale-risk; today no divergence exists (`E03@77859aad`, manifest §15). Worth a periodic reconciliation check by whoever owns doc-profile drift.


---

## Appendix F — Panel #5: benchmark-performance-analyst

# Panel agent #5 (benchmark-performance-analyst) — verbatim output, 2026-08-08

# Benchmark red-team — agent #5 (benchmark identity, licence, comparability, valid-method spec)

Scope compliance: no return, alpha, attribution, or skill figure is computed anywhere below. One level-identity reproduction (a stored index level, not a return) is included under Task 1 to confirm the proxy formula.

---

## Task 1 — Benchmark identity

**CONFIRMED — `benchmark_tr_level` in the packet rows is the documented proxy, not a real accumulation index.**

- The job prefers a real accumulation close when present, else computes the overlay: `/Users/jpcino/Desktop/asxos/jobs/snapshot_portfolio.py:278-284` — `benchmark_tr_level = _accumulation_tr_level(xjo_close, as_of)` with `trailing_yield = 4%` written alongside.
- The proxy formula (`snapshot_portfolio.py:81-97`): `tr(t) = xjo_close(t) × (1.04)^((t − 2020-01-01)/365)`, `_ASX200_TR_YIELD = Decimal("0.04")`, epoch `date(2020, 1, 1)`. The docstring states the epoch cancels in ratios and that this is "an APPROXIMATION (cash yield, not franking-grossed-up; constant, not the realised monthly yield)" (`snapshot_portfolio.py:76-80`).
- **Flag semantics CONFIRMED:** `trailing_div_yield_pct` "records which path ran: NULL when the real index embeds dividends, the assumed % otherwise" (`snapshot_portfolio.py:274-284`; manifest `snap.xjo_tr_proxy_4pct`, finance-rule-manifest-2026-08-08.md:132). Every packet row has `trailing_div_yield_pct = 4` (E06@028a9870ed255b9f) ⇒ **every row shown is the proxy path**, and any output over these rows must be labelled "XJO-TR approx" (`agt.bpa.tr_approx_label`, manifest :319).
- **Identity reproduction (level, not a return):** 2026-08-07 row: `9263.6 × 1.04^(2410/365) ≈ 12001.80` index points, matching the stored `benchmark_tr_level = 12001.803172` (E06@028a9870ed255b9f). The stored level is exactly the formula's output.

**Licence / ingestion of a real S&P/ASX accumulation series:**

- **CONFIRMED — no real accumulation series is seeded or ingested anywhere.** `_XJO_TR_SYMBOL = "AXJOA.INDX"` is a *candidate* constant only, "Left unseeded until verified on Render (where EODHD_API_KEY exists)" (`snapshot_portfolio.py:65-70`). The only index row in `universe` is `AXJO.INDX` (price index, `is_active=false`) — migration `/Users/jpcino/Desktop/asxos/migrations/0031_thesis_disposal_return_and_benchmark_seed.sql:29-31`, confirmed live in E06@028a9870ed255b9f (`index_symbols`) and E05@22e3234378dca4da (units: "index points (price index, not total return)").
- **CONFIRMED — no S&P index-data licence artifact exists in the repo.** A repo-wide licence sweep finds only unrelated references; the closest is `docs/research/research-store-schema.md:105` naming "S&P licensed data" as one *unresolved option* for index-membership history.
- **ASSESSMENT:** whether EODHD carries AXJOA.INDX, and under what redistribution terms, is UNVERIFIED — this half of `meta.unavailable_facts` ("Benchmark TR identity/licence verification") **remains unavailable** and is abstained on. The identity half is now resolved (proxy).

---

## Task 2 — Comparability audit (design-level checklist for D0-04)

Why "portfolio vs XJO-TR" is structurally invalid for the current book:

| # | Defect | Evidence | What would resolve it |
|---|---|---|---|
| 1 | **Currency mismatch.** The book is one USD-denominated NYSE name at 100% weight (`holdings_count=1`, `us_holdings_mv_aud == holdings_mv_aud == capital_aud`, E06@028a9870ed255b9f); the AUD-converted portfolio embeds AUDUSD FX return (`fx_rate_audusd` per row, USD→AUD = price/rate, `snapshot_portfolio.py:193-194`) while XJO-TR carries none. | E06; snapshot_portfolio.py:187-195 | A declared benchmark policy for a mixed-currency book (Task 3c) plus an explicit FX-leg decomposition artifact per sleeve. |
| 2 | **Flow-affected `capital_aud` endpoints.** `capital_aud = holdings_mv_aud + cash_aud` where `cash_aud = cash_floor_pct × profile.capital_aud` — a static profile placeholder, "A real cash ledger replaces this after M13.8" (`snapshot_portfolio.py:29-31`, :269-272). Contributions (e.g. a new ESPP lot) enter the level as if they were performance. The V1 brief already deleted its return line over exactly this — it "produced a false −75.7% loss and a bogus alpha" (`/Users/jpcino/Desktop/asxos/asxos/domain/brief/collectors/wealth_state.py:101-108`). | code + manifest `brief.portfolio_return_line_removed` (:72) | Cash-flow ledger (Task 3a) + flow-adjusted TWR/MWR (Task 3b). |
| 3 | **Proxy-TR benchmark.** Constant 4% cash yield, not franking-grossed, not realised yield; flagged stale-risk in the manifest (`snap.xjo_tr_proxy_4pct`, manifest:132; snapshot_portfolio.py:76-81). | Task 1 | Ingest the real accumulation index (AXJOA.INDX candidate, `snapshot_portfolio.py:70`) after EODHD availability + licence verification; the job upgrades with no code change (`snapshot_portfolio.py:230-242`). Historical rows are re-derivable from stored `benchmark_xjo_close` once real data backfills. |
| 4 | **Disputed acquisition FX — the AUD cost-base leg is unresolved.** Lot carries `acquisition_fx_rate = 0.645` flagged "estimated"; vendor FX 0.7171 on 2026-05-31; "the AUD P&L sign depends on it" (E01@21ff37f2719bfa9c tax_notes; E06@028a9870ed255b9f holding_lots; meta.unavailable_facts). At the two candidate rates the AUD cost base differs by roughly A$700 on an ~A$7,000 position (D01@28d5d505457d0a37: A$6,978.23 booked vs ≈A$6,277.11 vendor). | packet | Brokerage-statement AUD/USD rate (already listed unavailable; accountant review pending per meta.corrected_hubs_frame). |
| 5 | **No cash-flow ledger.** No contributions/withdrawals table exists in `migrations/` (swept; the only "contribution" hit is an unrelated Div 296 comment, `migrations/0001_initial.sql:124`). The one acquisition (24 sh × US$187.54, `cost_base_usd` US$4,500.96, E06) has no recorded cash-side counterpart. | grep of migrations | Task 3a artifact. |
| 6 | **Sample too thin for any alpha/attribution reading regardless of method.** One name, zero disposed lots (`disposed_at` NULL, E06), position opened 2026-05-31 (E01) — ~2.3 months. My own charter's floor is 12 months / 10 closed positions (`agt.bpa.sample_floor_12mo_10pos`, manifest:321). | packet | Time and closed positions; nothing buildable shortcuts this. |
| 7 | **ASSESSMENT — timestamp misalignment.** A snapshot `as_of` pairs an ASX close (AXJO, ~16:00 AEST) with a NYSE close for the same calendar date (landing the following AEST morning), so even a valid daily series would embed a session-offset on every joint observation. | snapshot_portfolio.py:169-175, :220-227 | Declare the convention (e.g. benchmark lagged/led one session) in the measurement spec; not fixable from data alone. |

---

## Task 3 — Valid-method specification (minimal artifact set)

**(a) Cash-flow ledger — MUST BE BUILT.** A table of dated external flows: direction (contribution/withdrawal), amount, native currency, FX rate at flow date, linked broker reference. Nothing exists today (Task 2 #5); `cash_aud` is explicitly a placeholder pending "a real cash ledger" (`snapshot_portfolio.py:29-31`). Backfill requirement: the 2026-05-31 ESPP event (US$4,500.96 cost side, E06@028a9870ed255b9f) — its AUD value is blocked on the FX dispute (Task 2 #4), so the ledger design should store native amount + FX as separate fields rather than a pre-converted AUD figure.

**(b) TWR and/or MWR engine — MUST BE BUILT.**
- Exists today: daily AUD MV series (`portfolio_daily_snapshots.holdings_mv_aud`, E06); pure-Decimal level primitives `period_return`/`alpha` (`/Users/jpcino/Desktop/asxos/asxos/domain/benchmark/returns.py:14-32`) — valid arithmetic but **level-based only, no flow adjustment**; and a daily-NAV-linking precedent for paper runs (`migrations/0024_paper_portfolio_perf.sql:50+`), not reusable directly because paper runs have no external flows.
- Must be built: daily sub-period TWR with a declared flow-timing convention (start-of-day vs end-of-day flows), geometric linking; and/or XIRR (MWR) over the ledger + terminal MV. Both consume (a).

**(c) Benchmark choice logic for a mixed AUD/USD book — MUST BE BUILT (declared, not computed ex-post).**
- Exists today: XJO price close per snapshot (E06); AUDUSD `fx_rates` daily from eodhd (E08@ac39a924b03043fe), sufficient to AUD-convert a USD benchmark. The active profile has **no benchmark field** (E03@77859aad840e33de column set) and the governed policy names only XJO-TR (`docs/product/portfolio-policy.md:26-28`).
- Must be built: a governed, ex-ante blended policy benchmark declaration (profile or policy doc): e.g. XJO-TR for the AUD sleeve; an S&P 500 total-return series (not present anywhere in `universe`/`prices` per E06 `index_symbols` — would need seeding, availability + licence check, same as AXJOA) either AUD-converted (benchmark absorbs FX, matching an unhedged AUD investor) or in USD with FX reported as a separate leg. The choice is a governor decision (`pol.benchmark_after_tax` owner: james, manifest:406); an agent must not pick it retroactively to flatter or damn the book.

**(d) After-tax dimension — the policy bar is "beat XJO total-return after tax and costs"** (`portfolio-policy.md:26-28`; manifest `pol.benchmark_after_tax`:406). Minimal requirements:
- Realised tax outcomes per disposal — machinery EXISTS (`asxos/domain/tax/positions.py` emits `CgtTaxOutcome`, per CLAUDE.md coverage notes; `thesis_revisions.disposal_return_vs_xjo_pct` column exists, `migrations/0031...sql:26-27`) but has zero disposals to run on (E06).
- Measured transaction costs — only an INFERRED placeholder exists (8bps commission + 5bps slippage, `pf.monitor_cost_model`, manifest:188, "never-measured"). Must be replaced by actual broker fills/fees from the ledger.
- Portfolio dividend/franking cash records — no dividend-received ledger verified anywhere in migrations (ASSESSMENT: must be built; the tax module handles franking *warnings*, not received-cash accounting).
- A declared after-tax comparison convention — the index itself is pre-tax, and the current proxy is explicitly "cash yield, not franking-grossed-up" (`snapshot_portfolio.py:79-80`). ASSESSMENT: the minimal honest form is pre-tax TWR vs benchmark **plus a separately stated tax-and-cost drag reconciliation line**, rather than constructing a shadow after-tax index — whether to gross the benchmark for franking at James's marginal rate is a spec-level governor decision (spec amendment per CLAUDE.md #8).

---

## Task 4 — Self-inventory (`agt.bpa.*`, manifest section 13, lines 317-323)

| Rule | Classification | One-line rationale |
|---|---|---|
| `agt.bpa.availability_gate` (:317) | **LIVE** | Sound stop-gate; would currently pass (benchmark_tr_level non-NULL, E06) — but passing it feeds the invalid method below, so it is necessary-not-sufficient. |
| `agt.bpa.periods_and_alpha` (:318) | **INVALID-METHOD** | Uses flow-affected `capital_aud` endpoints — the exact construct the V1 brief deleted after the false −75.7% (`wealth_state.py:101-108`); governor ruling this mission confirms; also currency-mismatched for the current 100%-USD book (E06). |
| `agt.bpa.tr_approx_label` (:319) | **LIVE** | Flag semantics confirmed against code (`snapshot_portfolio.py:276-284`); correctly fires on every current row (`trailing_div_yield_pct=4`, E06). |
| `agt.bpa.attribution_approximate` (:320) | **NOT-RUNNABLE-NOW** | Requires multiple holding periods; one open lot, zero disposals (E06) — and its position-vs-portfolio proxy inherits the endpoint method, so it is also INVALID-METHOD until (a)+(b) exist. |
| `agt.bpa.sample_floor_12mo_10pos` (:321) | **LIVE** (constants UNSOURCED) | The guard binds correctly today (~2.3 months, 0 closed); the specific 12-month/10-position numbers are prompt constants with no cited derivation. |
| `agt.bpa.no_forward_projection` (:322) | **LIVE** | Standing prohibition, method-independent, honored here. |
| `agt.bpa.paper_vs_live` (:323) | **NOT-RUNNABLE-NOW** | `paper_portfolio_run_metrics` row existence is not in the packet (no live queries permitted — UNAVAILABLE); the allocator that produces runs is gated off (`approved_for_allocation=false`, E04@417d7cfe045d6562); and the "live alpha" comparand is INVALID-METHOD anyway. |

---

## Material items not asked (optional)

1. **`unrealised_fx_pnl_aud` is misnamed — it is total unrealised P&L, not the FX component.** The job computes it as `us_mv_aud − us_cost_aud` (`snapshot_portfolio.py:294-296`), i.e. AUD market value minus AUD cost base — which conflates price return and FX return into one number stored under an "fx_pnl" label (2026-08-07 row: A$168.791367, E06@028a9870ed255b9f, exactly MV A$7,147.021367 − cost A$6,978.23). D01@28d5d505457d0a37 independently shows the native-USD and AUD P&L diverge materially — the column name promises a decomposition the value does not deliver, and it also inherits the disputed 0.6450 acquisition FX on its cost leg. Any D0-04 measurement spec should rename or split this column (price-P&L vs FX-P&L legs).
2. **The proxy is loss-free and retro-correctable.** `benchmark_xjo_close` is stored raw per row (E06) and `portfolio_daily_snapshots` is documented re-derivable (CLAUDE.md schema notes), so once a real accumulation series is licensed/ingested, `benchmark_tr_level` history can be recomputed with no information loss — the proxy defect is reversible, unlike the missing cash-flow ledger, which loses history every day it does not exist. That asymmetry makes the ledger (Task 3a) the priority artifact.


---

## Appendix G — Panel #6: macro-economist

# Panel agent #6 (macro-economist, regime-gate design audit) — verbatim output, 2026-08-08

# Design audit — regime gating rules (work order D0-04, finance red-team panel agent #6, wave 1)

Scope: `asxos/domain/regime/classifier.py`, `asxos/domain/brief/collectors/new_ideas.py`, `asxos/domain/position_monitor/display.py`, `/Users/jpcino/Desktop/asxos/docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md:338-370`, `jobs/score_macro_theses.py`, plus frozen packet entries (cited `id@hash`). No live DB queries were run. No macro theses are proposed and no thesis-proposal JSON block is emitted, per the mission envelope (design audit, not a discovery run).

Repo files verified at the working tree stated to match origin/main `1b471b60`. Packet: `/Users/jpcino/.claude/jobs/cb048518/tmp/evidence-packet-2026-08-08.json`; manifest: `/Users/jpcino/.claude/jobs/cb048518/tmp/finance-rule-manifest-2026-08-08.md`.

---

## Findings, ranked by severity

### F1 (SEV-1, Q1) — A single-indicator, single-print, stateless OR gate zeroes the entire idea-generation surface

**CONFIRMED.** `classifier.py:75-83`: `risk_off_orderly` fires if ANY ONE of A-VIX > 22, HY OAS > 450bps, breadth < 0.40 crosses (`r2_avix or r2_hy or r2_breadth`). `classifier.py:69-72`: same single-OR structure for disorderly (30 / 600). `new_ideas.py:23,44-50`: either risk-off label returns the section suppressed before any work. Live consequence: E08@ac39a924 — `new_ideas: status=suppressed, error="regime=risk_off_orderly", item_count=0` on the 2026-08-08 brief.

**CONFIRMED — the gate is stateless.** `classify()` is a pure function of one day's snapshot (`classifier.py:41-55`); there is no hysteresis, no confirmation window, no memory. An A-VIX print of 22.1 today and 21.9 tomorrow flips the product's entire discovery surface off and on day-to-day.

**CONFIRMED — stale-input fragility.** The classifier hard-fails only on *missing* inputs (`classifier.py:57-60`; `jobs/ingest_market_context.py:287-301`), never on *stale* ones. `FREDClient.latest_value` returns the most recent non-missing observation with no date bound and no staleness cap (`asxos/clients/fred.py:112-116`, via `get_series(limit=5, sort_order="desc")` at :81-110; call site `ingest_market_context.py:242`). A frozen `BAMLH0A0HYM2` series would silently pin `us_hy_oas` at an arbitrarily old value on the load-bearing 450/600 gates.

**ASSESSMENT (practitioner judgment).** As a v1 fail-toward-caution posture, a binary gate is a defensible starting point — suppressing ideas is a cheap error, missing a crash is not. As a steady-state design it is unsound: (a) vol and spread series cluster around exactly these thresholds during regime *transitions*, which is when dislocation-hunting has the most value, so the whipsaw cost is concentrated at the worst time; (b) one bad vendor print (A-VIX is a single EODHD value with no plausibility check against VIX) reclassifies the whole day; (c) a 0.2-point move across 22 changes nothing about the world but 100% of section 6.

**NEW DESIGN — defensible replacement, with evaluable parameters** (all require a `CLASSIFIER_VERSION` bump, `classifier.py:24-26`, and updating the CI pins in `tests/test_regime_classifier.py` per manifest `rgm.threshold_pins`):

1. **Hysteresis (enter/exit bands).** Enter `risk_off_orderly` at A-VIX > 22 / OAS > 450 / breadth < 0.40; exit only when A-VIX < 20 AND OAS < 420 AND breadth > 0.45. Disorderly: enter > 30 / > 600, exit < 26 AND < 550.
2. **Confirmation windows, asymmetric by rung.** Orderly entry: condition true on ≥2 of the last 3 daily rows (`majority`, window=3). Disorderly entry: single print, deliberately — speed matters at the tail, so the extreme rung keeps the current behaviour. All exits: 3 consecutive clear rows (`consecutive`, window=3). The window/aggregation machinery already exists in-repo and is tested against the same `market_context_current` history: `jobs/score_macro_theses.py:84-114` (`consecutive`/`any`/`majority`, fewer-than-window ⇒ not met). The classifier would need to read history instead of one snapshot — a structural but small change.
3. **Graduated posture instead of binary suppression** (interacts with F2): risk-on/neutral ⇒ section 6 normal; orderly ⇒ dislocation mode (F2) + counted line (F5); disorderly only ⇒ total suppression + counted line. This is exactly the spec's own ladder (spec :347-348).
4. **Staleness gate on classifier inputs:** treat an OAS observation older than as_of − 5 calendar days as missing (which then hard-fails per the existing `rgm.hard_fail_inputs` philosophy) and record it in `ingestion_warnings`.

### F2 (SEV-1, Q2) — The spec's 5-rung posture ladder is flattened to on/off; the current, milder rung gets the maximal penalty

**CONFIRMED.** Spec :347 (orderly): "Suggests tightening stops, holding cash, not opening new positions; **looks for dislocations not themes**." Spec :348 (disorderly): "do not act on new ideas today." Code: `new_ideas.py:23` puts both labels in one `_RISK_OFF_REGIMES` set with identical total suppression. The codebase elsewhere already distinguishes the two rungs (manifest `sev.regime_warning_map`, severity.py:197-214: orderly ⇒ YELLOW, disorderly ⇒ RED), so section 6 is an isolated flattening, not a systemic one. The spec never defined what "looks for dislocations" evaluates — confirmed absent from :340-360.

**NEW DESIGN — flagged explicitly for James's approval; this is invention, not spec restoration.** Smallest machine-evaluable "dislocation mode" for section 6, under `risk_off_orderly` only, over the section's existing population (approved research theses, `new_ideas.py:52-61`):

> A research thesis is a *dislocation candidate* when its latest close is at least `dislocation_discount_pct` (proposed 0.10) below its own researched entry level (`entry_band_lower`).

```sql
SELECT t.symbol, t.entry_band_lower, p.close,
       (t.entry_band_lower - p.close) / t.entry_band_lower AS discount
FROM theses t
JOIN LATERAL (SELECT close FROM prices
              WHERE symbol = t.symbol AND dt <= $1
              ORDER BY dt DESC LIMIT 1) p ON TRUE
WHERE t.status = 'research' AND t.governance_status = 'approved'
  AND t.entry_band_lower IS NOT NULL
  AND p.close <= t.entry_band_lower * (1 - 0.10)
ORDER BY discount DESC LIMIT 3
```

Render at most 3, labelled "DISLOCATION WATCH — price N% below researched entry level"; all non-qualifying ideas roll into the counted suppression line (F5). Zero matches is a valid result (counted line only). Parameters: `dislocation_discount_pct = 0.10`, `max_items = 3`.

Honest caveats to carry into the approval decision: (a) **the data foundation is currently weak** — all 11 research theses have degenerate point bands, `band_lo == band_hi` (E02@16d71743, packet note "systematic authoring artifact"), so "below band" degenerates to "below the researched point price"; (b) "cheaper than when researched" is a price displacement, not a valuation dislocation — the minimal version knowingly accepts that; (c) all current research theses are `.AU` (E02) so native-currency comparison is safe, but the query should guard the suffix to avoid the R10 currency trap if a foreign research thesis ever appears.

### F3 (SEV-2, Q6) — An approved macro thesis without machine conditions scores `open` forever: never evaluated, never expired, never alerted

**CONFIRMED (packet).** E07@e7a394d1: 3 approved macro theses (ids 7, 6, 11); id 11 `has_machine_conditions=false`; `macro_outcomes_count=0`. meta.unavailable_facts: "macro_thesis_id=11 machine_conditions (NULL — tonight's scorer can evaluate only 2 of 3 approved macro theses)."

**CONFIRMED (code) — the scorer is not silent at the row level, but it is silent at the status level, and it has a defect.** `jobs/score_macro_theses.py:148-157`: NULL/empty `machine_conditions` returns early with `status='open'`, `evaluation_detail={"reason": "no_machine_conditions"}`. So an outcome row IS written with a reason — good. But: (a) the status string `open` is indistinguishable from a genuinely-monitored thesis awaiting evidence, and no surface reads `evaluation_detail`; (b) **the early return skips the horizon-expiry check at :167-173**, so a no-conditions thesis can never even reach `expired` — id 11 will report `open` in perpetuity; (c) no alert fires (alerts only on `falsified`, :322-334).

**ASSESSMENT.** Yes, this is a governance gap, on two layers. At approval time: manifest `agt.me.catalyst_falsifier` (section 13, owner james) makes a concrete checkable catalyst/falsifier the point of a macro thesis; approving one whose falsifier has no machine encoding leaves the falsifiability requirement satisfied only as prose that nothing will ever check. At scoring time: the codebase's own doctrine is that silent omission is the failure mode (`disc.incomplete_price_info`, `brief.section_health_visibility`, and the scorer's own conservative-on-missing invariant at :19-22). The scorer should report an **explicit NOT-EVALUABLE outcome, never a skip and not a plain `open`**: a distinct status value (e.g. `not_evaluable`) written to `macro_thesis_outcomes`, with the horizon check still applied so the thesis at least expires on schedule, and a visible count on whatever surface reads the macro board ("1 of 3 approved macro theses is not machine-evaluable"). Complementary gate (NEW DESIGN, for approval): `asx macro-thesis approve` warns — or blocks without an explicit acknowledgment flag — when `machine_conditions IS NULL`, grandfathering existing rows deliberately rather than silently.

### F4 (SEV-2, Q4) — Three numeric vocabularies (and two different vol indices) for the same risk, one of them asserting "Macro confirming" unconditionally

**CONFIRMED.** Same investor, three ladders:

| Surface | Vol | Credit | Source |
|---|---|---|---|
| Regime classifier | **A-VIX** 22 / 30 | HY OAS 450 / 600 | classifier.py:28-34 |
| Monitor flip-to-diverging prose | "**VIX** spikes above ~22–25" | "~350bps" | display.py:196-199 |
| Weekly watchlist box | "**VIX**: stay below 20" | "below 300bps" | display.py:273, :275 |

Note the vocabularies do not even name the same instrument: the classifier gates on A-VIX; the monitor's default underlyings and its prose are US VIX (manifest `pm.default_underlyings`, service.py:45-56) — yet "22" appears in both, inviting the reader to conflate them. The watchlist box is emitted whenever a CGT date exists "regardless of actual regime/underlying state" (manifest `pm.weekly_watchlist_text`, display.py:266-278), and its header hardcodes **"HOLD — CGT clock ticking. Macro confirming."** (display.py:269). Under the current regime that text is contradicted by the system's own classifier the day it prints: E08@ac39a924 shows `risk_off_orderly` live.

**ASSESSMENT — which should be canonical:** the classifier's constants, and only them. They are the sole version-stamped (`CLASSIFIER_VERSION v1.0`, classifier.py:26), CI-pinned (manifest `rgm.threshold_pins`), audit-recorded (`regime_rationale`) numbers in the system. Concretely: (a) display prose should interpolate from imported classifier constants, never carry free-text numbers ("flips risk-off above A-VIX 22 / HY OAS 450bps"); (b) if the monitor deliberately watches US VIX for a US holding, it must say "US VIX" and define its own named constants rather than colliding with A-VIX's 22; the ~350bps and "below 20 / 300bps" figures have no authoritative source anywhere in the swept rule set; (c) "Macro confirming." must be conditional on the computed `underlying_label`/regime, or removed — a static claim of confirmation inside an advice-shaped box is the single worst instance of the incoherence.

### F5 (SEV-3, Q3) — Counted suppression line: conformance gap confirmed

**CONFIRMED.** Spec :359 requires: "1 idea was identified but is suppressed by current market regime. Re-evaluate when regime classifier returns to neutral or risk-on." Code returns at `new_ideas.py:44-50` — before the research-theses SELECT at :52-61 — so nothing is counted; the emitted artifact is `error="regime=risk_off_orderly", item_count=0` (E08@ac39a924). Manifest row `spec.new_ideas_suppression_msg` records the same gap.

**The fix must preserve:** (a) suppression itself — a count only, no symbols or thesis text leak into a risk-off brief; (b) section status stays `suppressed`, not `ok`, so `brief.section_health_visibility` and `brief.suppressed_excluded_from_counts` (snapshot.py:55-58 per manifest) keep excluding it from red/yellow/green tallies; (c) the governance filter — the count must be over `governance_status='approved' AND status='research'` rows only (`new_ideas.py:55-57`; manifest `brief.governance_filter_approved`), otherwise the count leaks the existence of unapproved drafts; (d) the regime short-circuit design (regime passed in from the market_context collector, :26-34) — the counting query is one extra SELECT inside the suppressed branch, not a second regime fetch; (e) the audit trail — the count should land in `brief_runs.section_runs` (e.g. in the message/error field) so suppression remains replayable.

### F6 (SEV-3, Q5) — "The user can override" exists only in the spec

**CONFIRMED.** Spec :350: "The classifier is not perfect. It will be wrong sometimes. The user can override." No mechanism exists: `classify()` is pure (classifier.py:41), no override table/column/CLI appears anywhere in the swept surfaces (manifest `spec.user_override`, section 15: "no override mechanism exists in code"). Current practical "override" is editing a threshold constant — the worst possible form, since it is silent, unversioned in intent, and permanent.

**NEW DESIGN — minimal override primitive that resists silent bypass (ASSESSMENT on the design properties):** a time-boxed, reason-mandatory, consumption-side override:

- One row: `override_label, reason TEXT NOT NULL, created_at, expires_at NOT NULL` (cap ≤ 5 trading days), created only via an explicit CLI (`asx regime override <label> --days N --reason "..."`), at most one active.
- **Consumption-side only:** the brief/collectors compute `effective_regime = override if unexpired else computed`; the classifier keeps writing the true label to `market_context` unchanged. This is load-bearing: `score_macro_theses.py:234-245` evaluates falsifiers against `market_context_current` history — an override that rewrote history would poison every macro-thesis outcome.
- Anti-bypass properties: (i) mandatory reason, recorded (a `decisions` journal or governance-events-style row); (ii) hard expiry, no auto-renew — a fresh command per extension; (iii) every consuming surface displays both labels ("regime: neutral_mixed (OVERRIDE, expires 08-12; computed: risk_off_orderly — A-VIX 23.1)"); (iv) the F5 counted line still reports what the computed regime would have suppressed; (v) optionally, an override may move at most one rung down the ladder (disorderly→orderly, orderly→neutral) — a parameter for James — so one command can never take a crash day to risk-on.

---

## Material items not asked (regime-adjacent only)

- **Suppression fails OPEN on a missing market-context row.** `new_ideas.py:37-50`: when no `regime_label` is passed and `market_context_current` has no row for `as_of` (exact-match `WHERE as_of = $1`), `effective_regime` is `None`, which is not in `_RISK_OFF_REGIMES` — the section renders normally, as if the regime were benign. A broken market-context ingest therefore *un-suppresses* ideas. This inverts the collector's stated capital-preservation intent (new_ideas.py:4-6) and the repo's fail-loud doctrine (CLAUDE.md #10); the spec's own freshness gate at :370 (suppress section 2 when `as_of < CURRENT_DATE − 2 trading days`) is also unimplemented (manifest `spec.market_ctx_freshness_2td`). CONFIRMED. I would rank this SEV-2 alongside F3/F4.
- **Breadth soft-degrade is asymmetric in the permissive direction.** `classifier.py:77-81`: NULL breadth silently skips the `breadth < 0.40` trigger, so a breadth-ingestion failure removes one of the three risk-off tripwires while leaving risk-on rules merely harder to satisfy. This contradicts the conservative-on-missing invariant the macro scorer states explicitly (`score_macro_theses.py:19-22`, manifest `macro.null_is_not_satisfied`). CONFIRMED code path; ASSESSMENT on the inconsistency.
- **The scorer had never run at packet build** — `macro_outcomes_count=0` (E07@e7a394d1) and no `score_macro_theses` rows among the recent `job_runs` (E08@ac39a924) — so F3's "open forever" defect is a prediction from code, not yet an observed outcome series; it will materialise on first run against id 11. CONFIRMED from packet + code.

**UNAVAILABLE:** whether any A-VIX/OAS print near the 22/450 boundaries actually whipsawed the regime label historically (would need `market_context` history, which is outside the frozen packet); current live A-VIX/OAS/breadth values (packet carries no market_context row). The whipsaw failure mode in F1 is therefore structural (CONFIRMED from code), with its realised frequency unmeasured.


---

## Appendix H — Panel #7: tax-spec-conformance

# Panel agent #7 (tax-spec-conformance, consequence-gap audit) — verbatim output, 2026-08-08

# Tax-consequence surfacing audit — finance red-team panel agent #7 (tax-spec-conformance)

Frozen inputs: evidence packet `/Users/jpcino/.claude/jobs/cb048518/tmp/evidence-packet-2026-08-08.json`, rule manifest `/Users/jpcino/.claude/jobs/cb048518/tmp/finance-rule-manifest-2026-08-08.md`, repo at origin/main 1b471b60. Spec: `/Users/jpcino/Desktop/asxos/docs/foundation/spec/tax-alpha.md` (v1.5). Scope honoured: gap identification only; no view on any HUBS economic action; all HUBS ESS/CGT dates and computations treated as UNKNOWN / NOT RELIABLE per the governor frame.

---

## TASK 1 — Decision-surface × tax-consequence gap matrix

Legend: P = present, A = absent, DEF = present-but-defective, N-A = not applicable. "Lock note" = any surfacing of the ESS trading-window non-disposability recorded in `theses.tax_notes` (E01@21ff37f2).

| # | Surface | §5.1 discount timing | §5.4 break-even | Div 775 forex (§8) | ESS/Div 83A caveat | Lock-enforceability note | Influence class |
|---|---|---|---|---|---|---|---|
| a | Invalidation alert email — `jobs/check_thesis_invalidations.py:179-185` | A | A | A | A | A | **functionally-directive** — the only alert surface that names an executable exit command ("Review thesis and consider exit. Run: `asx thesis exit <SYM>`", manifest `inval.alert_wording`) |
| b1 | AU position alerts — `jobs/check_au_positions.py:83-123` | A | A | A | A | A | framing-influential — "[STOP BREACH] … CLOSED BELOW STOP", "[TARGET HIT] … review thesis"; severity framing, no command |
| b2 | US position alerts — `jobs/check_us_positions.py:83-111` | A | A | A | A | A | framing-influential — same ladder minus targets (manifest `us.stop_breach`) |
| c1 | V1 brief discipline block — `asxos/brief/compose.py:415-469` | **P** (30-day s 115-25(1) INFO line, gated `ASXOS_PERSONAL_USE=1`, compose.py:432) | A | A | A | A | informational — evidence-only wording by design (compose.py:426-430) |
| c2 | V2 `active_theses` thesis cards — `asxos/domain/brief/collectors/active_theses.py` | **DEF** — the §5.1-adjacent "earnings within 14d of CGT date" RED exists in `severity.py:96-104` but the sole caller hardcodes `cgt_date=None` (active_theses.py:169-175); the CGT arm can never fire | A | A | A | A | framing-influential — severity cards feed the one-thing triage |
| c3 | V2 `tax_operational` collector — `collectors/tax_operational.py:36-45` + `severity.py:55-76` | **P** (7/30-day window only; RED literal "— do not sell") | A | A | A | A | framing-influential — note the RED wording is the tax rule-set's only imperative, and it fires with no ESS/lock awareness. Currently emits 0 items (HUBS eligibility ~10 months out; E08@ac39a924 `tax_operational.item_count=0`) |
| d | Position monitor — `position_monitor/service.py:80-130,180-293` + `display.py:82-98,242-282` | **P** (header days-to-CGT, Scenario D "Hold to CGT discount … Best risk-adjusted after-tax outcome", boxed weekly card, §5.1 arithmetic at service.py:277) | **DEF** — see finding F3: for a foreign lot the §5.4 same-currency precondition is violated, structurally suppressing the hint | A | A | A — Scenario A renders "Sell Now … Valid exit at any time" (service.py:122-128) with no channel to the lock; `tax_notes` is not in the monitor's query (service.py:202-233) | **functionally-directive** — boxed "HOLD — CGT clock ticking. Macro confirming." emitted whenever a CGT date exists, regardless of regime (display.py:266-278; manifest `pm.weekly_watchlist_text`) |
| e | `/pm-review` verdict ladder — `.claude/commands/pm-review.md:43,58-65` | A | A | A | A | A | framing-influential — EXIT-CANDIDATE label requires zero tax context; none of the five fan-out agents carries a single tax rule (manifest §13/§14 contain no `tax.*` row); disclaimer "surfacing ≠ recommending" present |
| f | Redesigned brief mock decision card (taken as given per envelope) | **P** (CGT discount date) | A (stated) | A (stated) | A (stated) | A (stated) | **functionally-directive** — presents three named decision paths (exit / re-underwrite / hold-override) |

**Structural asymmetry (headline of Task 1):** tax consequences concentrate on informational surfaces and vanish exactly where decisions are framed. The two most directive surfaces (a: names an exit command; d/f: named decision paths) carry respectively zero and one of the five consequence types. Conversely the surface with the most tax content (`asx tax view`/`asx tax action`, `asxos/cli/tax.py`) frames no decision at all. The ESS lock and the FX dispute — the two facts the governor frame says make every HUBS tax number unreliable — live only in `theses.tax_notes`, which is read by exactly one surface: manual `asx thesis show` (`asxos/cli/thesis.py:926`). No alert job queries it (`check_thesis_invalidations.py:80-86`, `check_us_positions.py:39-47` SELECT lists), no collector, no monitor, no agent prompt.

---

## TASK 2 — HUBS tax-fact verification table

| Fact | Classification | Evidence |
|---|---|---|
| Acquisition date 2026-05-31 as a recorded lot value | VERIFIED (as a DB record only) | E06@028a9870 `acquired_at=2026-05-31`, `broker_ref=ESPP-2026-05-31`; E01@21ff37f2 `actual_entry_at`. Note 2026-05-31 is a non-trading day (E05@22e3234 shows closes only 05-29 and 06-01) — consistent with an ESPP period-end, not a market fill. |
| 2026-05-31 as the **CGT acquisition date / Div 83A taxing point** | **UNVERIFIED — spec gap** | The spec does not answer this. §9 reserves all of Div 83A for v2 ("will produce wrong tax answers in v1; the user must not rely on v1 outputs for any ESS position", spec:355-359). §8.5 states cost base starts at market value on "vesting date" (s 130-80) but never defines the taxing point, and is silent on deferred taxing points where disposal restrictions (a locked window) apply. §10's contract-date rule (spec:371) covers ordinary listed-share purchases, not ESS interests. Whether broker_ref date = taxing point = CGT acquisition date is undetermined by the spec. This absence is a D0-04 finding. |
| `cost_base_usd = 4500.96` | UNVERIFIED (internally consistent, legally unresolved) | E06@028a9870. Arithmetic checks: 24 × 187.54 = 4,500.96; 187.54 ≈ 220.63 (05-29 close, E05@22e3234) × 0.85 — consistent with tax_notes "15% plan discount vs 2026-05-29 close" (E01@21ff37f2). But spec §8.5's own statement of law says the CGT cost base starts at market value on vesting date, *not* the discounted price; v1 knowingly imports the user-supplied figure and defers to accountant review (spec:346). Pending Div 83A facts, the booked figure's correctness is undetermined. |
| `cost_base_normal = 6978.23` AUD at acquisition FX 0.6450 | **CONTRADICTED** | Four mutually inconsistent sources: (1) lot FX 0.6450 flagged "estimated — update from brokerage statement" (E06@028a9870 notes); (2) vendor FX 0.7171 on 2026-05-31 → AUD cost ≈ 6,277.11 (packet meta.unavailable_facts; D01@28d5d505); (3) `scripts/hubs_espp_scenarios.py:35` uses a third value, `FX_ACQ = 0.7162`; (4) `.claude/rules/portfolio-conventions.md` ("cost_base_normal currency" section) asserts 0.6450 is "**confirmed** against the brokerage statement — not a data error", directly contradicting the DB's own "estimated" flag. The AUD P&L sign depends on resolution (governor frame; D01@28d5d505). Internal arithmetic 4500.96 ÷ 0.6450 = 6,978.23 is consistent. |
| Derived 12-month discount date 2027-06-01 | VERIFIED as the system's derivation; UNVERIFIED as a tax fact | §5.1 calendar arithmetic (`service.py:277`, `cgt.py`, `compose.py:447`) applied to `acquired_at` yields 2026-05-31 + 1y + 1d = 2027-06-01. Every surface showing a HUBS CGT date shows this. Its validity is wholly derivative of the unverified acquisition-date fact above — no surface marks it as provisional. |
| 15% plan discount — ESS assessability implication | Spec coverage: **acknowledged, explicitly unimplemented; no TC** | §8.5 names the assessable discount; §9 reserves treatment for v2. The §11 matrix (TC-01..TC-24, spec:397-422) contains no ESS case. No code computes an assessable discount; no surface carries an ESS caveat (Task 1 matrix, column 5 — all A). |
| Does the spec address ESS/Div 83A at all? | Yes — two short reserved sections (§8.5, §9) — **but §9's claimed v1 accommodation is unimplemented** | Spec:359: "V1 data model accommodation: every position has an `acquisition_type` field defaulting to `\"purchase\"` … V1 ignores the field." Repo-wide grep finds `acquisition_type` **only in the spec**; the `holding_lots` column list (E06@028a9870) has no such field. The spec's stated data-model accommodation does not exist in code or schema. This is precisely the "spec says X exists, nothing implements it" drift class (TC-20/21 history) — D0-04 finding. |

---

## TASK 3 — Orphaned rules and unreached surfaces

### List A — tax rules (manifest §9) with NO consuming decision surface

1. **`tax.fx_de_minimis_250` and the entire §8 Div 775 path — computed, tested, wired to nothing.** `fx_capital_gain()`/`is_de_minimis()` exist (`asxos/domain/tax/fx_gain.py:32,75`) with tests (`tests/test_fx_gain.py`), but a repo-wide grep finds **zero product consumers** — not `positions.py`, not any CLI, collector, job, or monitor. The only caller is the one-off `scripts/hubs_espp_scenarios.py`. **Spec §8.3 is falsified by the code**: "The calling code in `asxos/domain/tax/positions.py` flags `forex_gain_aud` on each disposed US lot" (spec:338) — `positions.py` contains no reference to fx_gain/forex/775 (grep: no matches). Under CLAUDE.md #8 this deviation routes to a spec amendment (or the missing wiring), not silence.
2. **`sev.earnings_double_risk_14d` (CGT arm)** — defined `severity.py:96-104`, unreachable: sole caller passes `cgt_date=None` (`active_theses.py:173`).
3. **`tax.45day_franking_warning`** — consumer is `tax_view_smsf` → `asx tax view --account smsf` print only (`cli/tax.py:122-126`); the active profile is `individual` (E03@77859aad), so it currently reaches no live output, and no alert/brief/monitor surface ever consumes it.
4. **`tax.div296_election_warning`** — same: `asx tax view` SMSF branch only (`cli/tax.py:138-143`); no decision-framing consumer.
5. **`tax.eligibility_alert_30d`** — `asx tax view`/`asx tax action` print only (`cli/tax.py:118-121,146-205`). §5.1 timing separately reaches the V1 brief and `tax_operational` via parallel implementations, so the *consequence* is covered elsewhere; this rule instance is CLI-only.
6. **`tax.cgt_break_even_hint`** — nominally consumed (monitor) but structurally suppressed for the only current holding; see F3 below. Functionally orphaned for foreign lots.

### List B — decision surfaces with NO tax rule reaching them

1. `jobs/check_thesis_invalidations.py` alert email (the only surface naming an exit command) — zero tax content (Task 1a).
2. `jobs/check_au_positions.py` / `check_us_positions.py` alert emails — zero tax content (Task 1b).
3. `/pm-review` — no tax agent among the five; no `tax.*` rule in manifest §13/§14; verdict ladder tax-blind (Task 1e).
4. V2 `active_theses` thesis cards — CGT arm dead (Task 1c2).
5. Redesigned brief mock decision card — discount date only, per the given description (Task 1f).
6. Borderline: the `opportunity_cost` collector *does* carry CGT friction (`tax.oppcost_discount_gate`, `tax.marginal_rate_default`, manifest §9) — the one decision-adjacent surface with tax math — but its latest run returned `no_data` ("no opportunity cost scenarios computed", E08@ac39a924), so it currently delivers nothing.

---

## Ranked findings

**F1 (highest).** Div 775 (§8) is implemented + tested but consumed by no product surface, and spec §8.3's implementation-contract sentence about `positions.py` is contradicted by the code (Task 3.A.1). Given the HUBS AUD P&L sign is FX-dependent (D01@28d5d505), the one consequence class whose omission can flip a sign is the one wired to nothing.

**F2.** Spec §9's `acquisition_type` v1 data-model accommodation is unimplemented anywhere (spec:359 vs E06 schema + repo grep). Combined with no ESS TC in §11, ESS treatment currently has *no* machine-readable marker distinguishing the HUBS lot from an ordinary purchase — every tax surface treats it as one, and no surface can even conditionally attach an ESS caveat. Needs a spec amendment (either implement the field or amend §9 to state the accommodation does not exist in v1).

**F3.** The single §5.4 break-even surface violates §5.4's own precondition for foreign lots. Spec:163 and `cgt.py:137-139` require price and cost in the same currency, translated per §8.2 before calling. The monitor feeds `current_price` = native close (`cli/position.py:177`; USD for HUBS) against `cost` = `cost_base_normal/quantity` (AUD; `display.py:35`, `service.py:216-222,286`) with no FX step anywhere in the path. Characterizing system output with packet numbers only: AUD cost/share 6,978.23÷24 = 290.76 vs USD close 210.45 (E05@22e3234, 2026-08-07) → `current_price ≤ cost` → `cgt_break_even_price` returns `None` (`cgt.py:146-147`), silently suppressing the hint; the same mixing makes the monitor header P&L render ≈ −27.6% (`display.py:82-90`) — the identical R10 error class `.claude/rules/portfolio-conventions.md` documents from the 2026-07-11 incident, now in the flagship tax-decision surface. The suppression is structural, not parameter-sensitive: even at the disputed vendor FX (cost/share ≈ 261.55 AUD) the cross-currency comparison still suppresses. `tax.break_even_suppression`'s "no hint is better than a misleading one" here hides a currency bug as a quiet non-answer.

**F4.** Directive/consequence inversion (Task 1 headline): the exit-command email carries zero tax content; the "do not sell" imperative (`severity.py:67`) is the only imperative in the tax rule set and fires only in a 7-day boundary window, with no ESS/lock awareness. Between those, all decision framing is tax-silent.

**F5.** The lock and FX-dispute caveats (`tax_notes`) are unreachable by every automated surface — one manual CLI read path (`cli/thesis.py:926`). Any alert generated on the HUBS lot (stop breach, invalidation) is emitted with no channel to the recorded "ALERT/REVIEW-only while locked" semantics (E01@21ff37f2).

**F6.** Four-way acquisition-FX contradiction, including a governed repo doc ("confirmed") vs the DB's own "estimated" flag (Task 2 row 4). Whichever is right, one governed source of truth is wrong.

**F7.** Dead CGT arm in the brief's earnings double-risk check (`active_theses.py:173`).

## Abstentions (insufficient evidence)

- Whether `ASXOS_PERSONAL_USE=1` is set for the production `compose_brief` service (so whether c1's §5.1 lines actually appear in the sent email): inferable from the alert jobs' successful runs (they hard-require it, `check_au_positions.py:153`; E08@ac39a924 shows successes) but not directly evidenced for the brief service; render.yaml env not in the packet.
- Whether `check_us_positions` ran on 2026-08-06/07 (the packet's `job_runs` query covered only three other jobs, E08@ac39a924).
- What the ESS deferred taxing point actually is for this lot — the spec doesn't answer it (that abstention *is* the Task-2 result).

## Not asked, material (optional)

- Position-monitor Scenario A's invalidation text "Price falls below cost basis (${cost})" (`service.py:127`) prints the AUD-derived per-share figure against a USD price stream — the same F3 currency mix, presented as a monitoring threshold.
- The boxed weekly card "HOLD — CGT clock ticking. **Macro confirming.**" is emitted from static prose whenever a CGT date exists, regardless of the actual regime or underlying score (`display.py:266-278`; manifest `pm.weekly_watchlist_text`) — a tax-motivated framing whose macro claim is not computed. On 2026-08-08 the live regime was `risk_off_orderly` (E08@ac39a924 `new_ideas.error`).
- `scripts/hubs_espp_scenarios.py:13-14` contains the repo's only decision-adjacent ESS caveat ("Division 83A may alter the cost base — consult a tax advisor") — in an unwired one-off script, not any product surface.


---

## Appendix I — Plan-level critique 1: arbi-red-team

# Plan-level critique 1 — arbi-red-team on the rev-1 mission plan (2026-08-08, pre-execution)

Verdict: PROCEED-WITH-CHANGES. Its six required amendments were applied in plan rev 2; the governor's 12-point correction packet then produced rev 4, which superseded parts of this critique's frame (notably: the mission became a bounded evidence input to D0-04; the "tonight" B1 claim was corrected to Sun 20:30 UTC; agent constraints were tightened beyond what this critique asked). Recorded verbatim below as it was delivered.

---

# Verdict: PROCEED-WITH-CHANGES

Every load-bearing citation in the plan verifies against repo truth — I re-checked them, and none is memory-over-repo. The mission's core is legitimate and level-0 directed. But four of my five challenges land partial hits, and the panel design has two missing lenses and an unguarded conflict of interest. Specific amendments below; the plan can absorb all of them without changing its spine.

## The five charter challenges

**1. Recency overfit — PARTIAL FIRE (scoped to R5/R6, not the mission).**
The core mission is not overfit to this morning. James's charge is level 0 on the ladder (`docs/product/arbi-authority.md:21`), the defect class is the north star's own named failure mode (`docs/product/north-star.md:50-55` — "monitor it and change it… the CBA thesis is the worked example"; `:85-89` — the HUBS-stop-unseen success criterion), and the evidence pre-dates the morning by ten weeks (thesis opened 2026-05-31 already violated). Crucially, the 2026-08-08 handoff's own next item — "build one real vertical: governed thesis → monitor/change events → disposition" (`docs/session-handoff-2026-08-08.md:209-223`) — **cannot pass acceptance through an invalidation job that silently skips unparseable conditions** (`jobs/check_thesis_invalidations.py:154-156`). The mission is on the standing plan's critical path, not a detour.

Where overfit DOES fire: **R5 and R6** balloon a rule-defect audit into a fleet-and-scorecard reorganisation within hours of James's frustration — exactly the shape the handoff bans: "must not manufacture architecture, agents, docs, or reviews merely to stay busy" (`session-handoff-2026-08-08.md:40-41`; also `:268` — "do not create a ninth roadmap"). And R6 is built on an overstated claim: the scorecard does **not** ignore investment quality "anywhere" — metric family 7, "Investment evidence quality," already exists (`docs/product/arbi-scorecard.md:126-130`); the actual defect is that it carries no Layer-3 weight. R6 should be re-scoped to *wiring the existing family in*, constrained by the anti-reward-hacking note directly below it (`:132-139` — a naive thesis-quality term rewards thesis production, the exact failure that section predicts).

**2. Task-switching — FIRES, on omission.** This is the challenge that came closest to killing the plan. Lines 3-6 assert Workstream A and B1 "continue unchanged," and then the mission body never operationalises that: no checkpoint for B1's first `score_macro_theses` run tonight, no owner for the weekend decommission gates (first scheduled green daily run, green Saturday chain, verified backup artifact — `session-handoff-2026-08-08.md:105-112`), and no mention of the `us-positions.yml` 13:30-UTC schedule error the handoff says must be corrected or re-decided **before** decommission (`:108-110`). A 6-agent fan-out plus synthesis plus a docs PR is a full session; as written, the gates get watched by nobody. The verification section verifies panel claims only. Amendment: name the B1 first-run check and the weekend gate watches as non-displaceable checkpoints inside this session, or explicitly hand them to a named wake with dates.

**3. Cleanup-mistaken-for-progress / report mill — PARTIAL.** The deliverable shape (challenge + ranked proposals before any code) is James's explicit scoping — level 0, not a distortion, and it does force one true decision (keep/reframe/rebuild the mock). Two report-mill risks remain:
- The panel is tasked with re-validating already-CONFIRMED defects. Born-violated stop, symbol-suffix-only validation (`asxos/domain/theses/service.py:233` — `_validate_symbol` is the sole check before INSERT), silent parse-skip and no `thesis_revisions` audit row (`check_thesis_invalidations.py:154-156`, `:172-178` — raw JSONB UPDATE only), deferred direction CHECK (`migrations/0012_theses_and_themes.sql:92-93`). These need no panel; **R1 and R2 should go to James as ready-for-ruling asks regardless of panel outcome**, with panel time reserved for genuine judgment calls (warn-vs-hard-fail, regime design, conviction values).
- No decision-forcing output format. Precedent: the `agent_runs` review backlog sat 4-unacted past the team's own 14-day health bar (`docs/product/roadmap-state.md:578-581`). Each R-item should land as a `james-inbox.md`-shaped row (approve/reject/defer + default recommendation), or R1-R7 becomes the next unacted backlog.

**4. Low-trust memory overriding repo truth — PASSES, with one precision correction.** All citations verified live (service.py, the invalidation job, migration 0012, the agent-fleet grep — only `arbi.md`/`guilfoyle.md`/`arbi-red-team.md`/`README.md` reference north-star; conviction bands prompt-hardcoded at `.claude/agents/portfolio-coherence-reviewer.md:60` with a live Model A anchor-query section at `:23,46,115` that is dead under rule #11; `[governor to set]` holes at `docs/product/portfolio-policy.md:16,29,50,51`). One overstatement to fix before briefing agent #6: the plan claims the code "collapses orderly/disorderly into total suppression" *against* the spec — but the spec's own §4.4 says "when regime is risk-off (**either kind**), new ideas are explicitly suppressed" (`docs/strategy/V2_PRODUCT_THESIS_AND_BRIEF_SPEC.md:359`). The genuine divergences are narrower: the **counted** suppression line (":359") versus the code returning before counting (`asxos/domain/brief/collectors/new_ideas.py:44-50`, error string only), and the orderly "looks for dislocations not themes" posture (`:347`) existing nowhere. R4's "orderly = dislocation posture" is half spec-conformance, half **new design the spec never defined for section 6** — the macro-economist envelope must say so, or the panel will "restore" a spec behaviour that doesn't exist.

**5. Perfectionism blocking a shippable build — DOES NOT FIRE, one date coupling required.** The mission challenges rule integrity, it doesn't re-polish a working surface. But: the portfolio brief and paper-trade evaluator KEEP-DARKs both expire **2026-08-31** — three weeks out (`docs/product/dark-launch-exit-plan.md:23,102,120-123`), and surface #1's ship gate requires exactly the governed conviction/cap re-scope that R3 creates. R3 is therefore not one of seven peers — it is on the critical path of a dated expiry and should be ranked and dated accordingly. Also: the news-brief SHIP condition (a) is VOID with a restated artifact-level condition (`dark-launch-exit-plan.md:51-54`); if M0/CANARY_PROVEN satisfied it, the exit-plan needs the re-verify recorded — if not, that is the shippable thing no R-item covers.

## The remaining specifics

**Q3 — panel composition.** The self-audit (#4) is acceptable as *inventory* (enumerate your own dead/unsourced checks) but must not be the only audit of itself — assign agent #1 to cross-examine #4's self-audit explicitly. Two lenses are conspicuously missing:

- **Tax.** Zero tax lens on a panel judging an exit-framing decision card, in a product whose moat is "discipline, **tax**, themes, ETFs." HUBS acquired 2026-05-31 → CGT discount from 2027-06-01 (spec §5.1 calendar arithmetic, CLAUDE.md rule #6); the mock's "honour the stop and exit" path forfeits the 50% discount ~10 months early and the card never says so. That omission *is* the "bad advice" class James named. `tax-spec-conformance` exists and is unused.
- **The ESPP lock.** HUBS is "currently **locked/unsellable**," ruled 2026-07-13 a concentration ceiling, not a conviction thesis (`docs/product/james-inbox.md:31`). A closing-stop ladder on an unsellable position may be a category error *upstream* of "born violated" — the stop was unenforceable at authoring regardless of level. No envelope owns this question, and envelope #5 (benchmark analyst: "what following the triggered HUBS invalidation would have meant") computes a counterfactual that was **physically impossible during the lock** — without the lock caveat it produces exactly the confident nonsense the mission exists to kill.

The "competent human advisor baseline" belongs inside agent #1's charter (one added line), not a 7th agent. Operational note: 6 parallel agents is the shape that died at 3/5 on a session spend limit in the 2026-07-18 audit (`docs/product/decision-log.md:46`) — order #1/#3/#6 ahead of #4/#5.

**Q5 — grading your own homework.** The plan's guard is citation discipline — necessary, not sufficient. Three holes:
1. The synthesizer is the mock's author with unilateral drop authority ("uncited claims are dropped at synthesis") — the author can discard adverse-but-imperfectly-cited findings about its own artifact. Fix: panel outputs attach **verbatim** as an appendix in the docs PR; James sees raw findings, not only synthesis.
2. Deliverable #1 (keep/reframe/rebuild the mock) is synthesized by the mock's author. The verdict recommendation must come from agent #1's output, with the main loop *recording* disagreement, not adjudicating it — the scorecard's own rule for high-impact changes: separate grader AND second reviewer AND deterministic checks, "not one of the three alone" (`arbi-scorecard.md:137-139`).
3. Every envelope was authored by the entity under critique — the framing of what each agent may attack was chosen by the author of the thing attacked. Cheapest mitigation: add to agent #1's charter the explicit question "what were you not asked that you should have been?"

(R5's proposal to amend this charter — mine — is fine as a James-gated draft; nothing in this mission can enact it.)

## Required amendments (by reference, no new plan)

1. Carry B1-first-run + the three Render-decommission gates + the `us-positions` schedule fix as named, non-displaceable checkpoints (`session-handoff-2026-08-08.md:105-112, 259-264`).
2. Split CONFIRMED defects from judgment questions: R1/R2 go to James ready-for-ruling; panel time goes to warn-vs-hard-fail, R3 values, R4 design.
3. Demote R5; re-scope R6 as "wire existing scorecard family 7 into Layer 3" (`arbi-scorecard.md:126-139`), both explicitly tagged as governance changes needing their own James gate.
4. Add the tax lens (CGT boundary 2027-06-01) and the ESPP-lock lens; add the lock caveat to envelope #5; precision-fix envelope #6 per spec `:347` vs `:359`.
5. COI guards: verbatim panel appendix; mock verdict recommended by agent #1; every R-item lands `james-inbox.md`-shaped.
6. Date-couple R3 to the 2026-08-31 dark-launch expiries (`dark-launch-exit-plan.md:120-123`) and record the news-brief condition-(a) re-verification status either way.

Precedent supports proceeding once amended: the last time this gate returned CHALLENGE on a mission and was honored (2026-07-16), spec-first review caught a duplicate build before it happened (`decision-log.md:42`). Challenge-before-build is this system's proven pattern — this mission is that pattern applied to the finance rules themselves, and with the six amendments it survives.


---

## Appendix J — Plan-level critique 2: completeness critic

# Plan-level critique 2 — completeness critic (general-purpose, read-only) on the rev-1 mission plan (2026-08-08, pre-execution)

Twelve concrete gaps, ranked. All were absorbed into plan rev 2/rev 4 (tax lens became panel seat #7; the R10 FX rule, pinned data frame, and read-only constraints went into every envelope; the root-cause hypothesis table and governor interrogation became mandatory synthesis steps; the fresh-synthesizer requirement in the governor's rev-4 packet superseded gap 12's weaker form). Recorded verbatim below as delivered.

---

Numbered gaps, ranked:

1. **No tax lens on a tax-dominated decision.** The panel's central exhibit is "honour the stop and exit" on HUBS — but exiting before 2027-06-01 forfeits the 50% CGT discount, plus Div 775 forex treatment (§8) and the ESPP cost-base caveat (§9/Div 83A) apply to this exact lot. The repo already has the tool the plan ignores: `cgt_break_even_price()` (§5.4, "decision-support hint"), wired into `tax_overlay.py`, `brief/collectors/tax_operational.py`, `positions.py`. No panel member checks whether any decision surface cites it. **Fix:** add a 7th envelope (charter for `tax-spec-conformance` or a general-purpose tax charter): audit every exit-framing surface for whether §5.4 break-even, Div 775, and the ESPP caveat appear at the point of decision — consequence-surfacing audit, not advice.

2. **The known FX failure mode is unguarded — and it corrupted this exact analysis before.** Portfolio-conventions R10: in the 2026-07-11 `/pm-review`, two analysis agents reported HUBS as −29%/stop-violated by dividing AUD `cost_base_normal` by quantity against a USD close. The plan re-runs the same agent types over the same tables with no currency instruction, and agent 5 additionally benchmarks a 100% single-USD-name portfolio against XJO (FX + market conflated; benchmark columns may be unpopulated per the agents README caveat). **Fix:** paste the R10 convention into every DB-touching envelope, require every return figure to state both currency legs, and make agent 5 validate benchmark data availability and state the XJO-mismatch caveat up front.

3. **Root-cause monoculture.** The plan pre-commits to "authoring was unvalidated" and every R item flows from it. Unlisted competitors: (a) maintenance failure — the CBA 4× detachment is a *revision* failure R1's authoring lint can never catch on an already-open thesis; (b) decision-support gap — the system demands "honour or override" with zero re-underwriting basis (no valuation, no scenario framing); (c) wrong primitive — a single static stop for a 12-month CGT-driven hold contradicts the north star's own identify→monitor→change reframe (a re-evaluation trigger may be the right primitive); (d) sandbox theses indistinguishable from serious ones. **Fix:** add a mandatory hypothesis table to the synthesis: evidence for/against each of (a)-(d) before the R-ranking is allowed.

4. **The cheapest evidence — asking James — is never gathered.** Whether stop $230 and band $42-45 were deliberate, placeholders, or data-entry errors decides which root cause is real; six agents will infer what three governor questions answer. **Fix:** insert a pre-synthesis "governor interrogation" step (≤3 questions: were HUBS/CBA parameters deliberate at authoring? was CBA a sandbox? what did you expect the invalidation trigger to do?).

5. **No success metric for the remediation — the plan repeats the scorecard blindness it indicts.** R1-R7 carry no acceptance criteria and no baseline. **Fix:** require the defect register to double as the baseline (counts per defect class) and each R item to carry a measurable acceptance test (re-audit shows zero born-violated active theses; zero silently-skipped invalidation conditions; detachment >2× flagged within one revisit cycle).

6. **Revision hygiene has no standing mechanism.** R1 lints at authoring/revision time, but a thesis nobody revises is never re-linted — CBA's detachment fires no invalidation condition and would survive R1-R7 untouched. The deferred `m14_candidate_governance_aware_revisit_cadence` (portfolio-conventions) is the natural vehicle and is never mentioned. **Fix:** add R8 — a periodic rule-integrity sweep (extend `check_thesis_invalidations` or the revisit cadence: stop/band-vs-live-price detachment check on every run, writing `thesis_revisions` flag rows) — and, post-approval, write the register's per-thesis findings into `thesis_revisions` so the system's own audit trail knows its theses were flagged (a docs-only PR leaves the DB ignorant of its own defects).

7. **Solution-space in R1 is two options wide (warn vs hard-fail) when the shape space is five wide.** The plan itself cites the deferred direction-aware CHECK (`migrations/0012:92-93`) yet R1 is service-layer only; the repo's documented threat model (manual SQL / MCP bypass, `m14_candidate_agent_db_role_scoping`) makes service-only lint bypassable. Missing shapes: DB CHECK constraint, interactive authoring wizard, an underwriter-agent-in-the-loop at `asx thesis open` (the recon names "missing challenge-at-authoring" but no R item builds it), periodic sweep (item 6). **Fix:** R1 must enumerate the layering options explicitly and have the panel choose a defense-in-depth combination, not a warn/fail toggle.

8. **Serious-vs-sandbox provenance is unaddressed, and a concrete laundering mechanism exists.** `theses.governance_status` DEFAULTs to `'approved'` for human-authored rows, and `enter_thesis()` gates on exactly that — so a placeholder thesis is born capital-eligible. **Fix:** add a candidate R item: a provenance/seriousness marker, or default human-authored theses to `pending_review` when capital entry is intended.

9. **No competent-human-advisor baseline lens.** No envelope holds the checklist a good advisor's process runs: position size vs net worth/liquidity, 100% single-foreign-name concentration with $0 cash, horizon-vs-stop consistency, tax interaction, scenario/valuation basis. Agent 4 covers a fragment (coherence vs James's own framework), which is circular when the framework itself is the defect. **Fix:** add the baseline checklist to agent 1's charter as an explicit rubric ("what would a competent human process check that no system surface checks"), each miss becoming a register entry.

10. **No behavioral-finance lens.** The invalidation has been triggered since 2026-07-03 with no decision event for 5 weeks — alert fatigue and framing failure are findings in themselves; decision cards that convert malformed rules into confident "act now" asks are action-bias machinery, and a tax-locked underwater position is prime disposition-effect terrain. **Fix:** add to agent 1's charter: audit nudge design — does the system distinguish "decide now" from "re-underwrite by date," and why did a 5-week trigger produce zero recorded decisions.

11. **Firewall language is too blunt for this panel.** "Never recommends buy/sell/hold" doesn't govern agent 5's counterfactual P&L of "following vs ignoring the HUBS invalidation" on a live position, or R7's rebuilt decision card — both sit near the s766B line the moment framing implies a preferred action. **Fix:** add per-output shape rules: counterfactuals as historical arithmetic only, tax as consequence tables, no imperative verbs about live positions, and the decision card must present rule-integrity status before any action menu.

12. **Execution-process gaps: consistency, containment, self-grading.** (i) Six agents query the live DB at different moments — pin one as-of timestamp and one FX rate in every envelope, and require each agent to report its query time. (ii) Agent 1 runs as `general-purpose` (tools: `*`) with read-only-ness enforced only by prompt — the exact gap the repo already closed for discovery agents via the supabase-ro repoint; constrain its envelope explicitly and say so in Boundaries. (iii) Synthesis is performed by the actor whose own brief mock is under challenge (the plan's finding 3 admits inheriting the flaw) — route the draft register and verdict through `arbi-red-team` (or a second adversary pass) for a dissent check before the docs-only PR lands.

Note on deliverable durability (question 5, partially covered): landing in `docs/proposals/finance-red-team-2026-08-08.md` does match the repo's existing proposals convention (17 precedents in `docs/proposals/`), so the vehicle is right; the durable-record gap is item 6's second clause (register findings never reach `thesis_revisions`).


---

## Appendix K — Dissent pass (arbi-red-team)

# DISSENT PASS — verdict on `synthesis-fresh-synthesizer.md`

**VERDICT: CONCUR-WITH-NOTES.** I replayed the load-bearing citations against the repo working tree (stated identical to origin/main 1b471b60) and the frozen packet. Every code citation I checked holds exactly as cited. The notes below are recordable refinements, none rises to DISSENT.

## Spot-verification record (what I independently confirmed)

- `/Users/jpcino/Desktop/asxos/jobs/check_thesis_invalidations.py` — write-once skip (:151-152), unparseable skip (:154-156), regexes (:42-47), run-date note (:165), bare UPDATE (:173-178), exit-command email (:179-185), `_send_alert` total swallow incl. missing env vars (:104-122). Register #1/#4/#5/#20/#21 anchored.
- Tape math from E05: 8 of the 36 days (07-03→08-08) closed above 230 (07-20, 07-28..08-05); 192.12 is the 07-02 close, no 07-03 row; −19.1% on 08-06. "DAY 36 BELOW STOP" (`brief-mock.html:297`) is false as stated. REBUILD reason 1 is evidence-forced.
- `/Users/jpcino/Desktop/asxos/asxos/domain/brief/collectors/wealth_state.py:57-59` exact-date join (register #8), :101-108 removed −75.7% return line (register #14/#15).
- Cross-currency chain (register #11): `position_monitor/service.py:216-222` sums `cost_base_normal` (AUD) → :286 per-share → :247 returned under the key **`cost_usd`** → `display.py:82-90` header P&L; `display.py:35` `cost_base_normal / quantity`; `tax/cgt.py:146-147` returns `None`. Math checks: 6,978.23÷24 = 290.76 vs 210.45 → −27.6%.
- `positions.py` grep: zero `fx_gain|forex|775` matches; spec `tax-alpha.md:338` contradicted (register #12). Spec :355-359 `acquisition_type` accommodation, absent from the E06 column list (register #13). `scripts/hubs_espp_scenarios.py:35` FX_ACQ 0.7162 — the third FX value (register #25).
- `classifier.py:69-83` single-print OR + permissive breadth skip (:77-81); `new_ideas.py:37-50` fail-open and return-before-count (registers #16/#17/#27); V2 spec :347-350, :359 as cited.
- `snapshot_portfolio.py:81-97/:274-284` proxy + flag semantics; `:294-296` `unrealised_fx_pnl` = MV − cost (registers #14/#26). `score_macro_theses.py:151-157` early return skips the :167-173 horizon check (register #19).
- `active_theses.py:43` `earnings_notes` fetched once, never referenced again (grep: single hit); :172 `cgt_date=None` (registers #7/#24). `severity.py:64-67` "do not sell"; :96-104 dead arm.
- Charter `/Users/jpcino/Desktop/asxos/.claude/agents/portfolio-coherence-reviewer.md` :41-43 `status='active'` LATERAL, :45-46 `model_a` pull, :52-53 non-AUD escape hatch, :109 currency-less template (registers #22/#23). `cli/thesis.py:926` sole `tax_notes` reader (register #4). `discipline.py:220-229` wording firewall — REBUILD reason 3 anchored.

## The six challenges

**1. Native failure modes — PASS, one note.** No recency overfit (the HUBS incident *is* the mandate), no cleanup-dressed-as-product (rule-integrity work is the charged mission, bounded to D0-04 inputs), and no memory-over-repo: the synthesis cites zero consolidated-memory content, and its FX ruling (§6 disagreement 2) correctly puts the governor's live answer above a stale governed doc *while surfacing the contradiction for a James-gated correction* rather than silently overriding — the right ladder handling. **Note (leverage-ranking):** the claim "R2 alone retires the CRITICAL compound class and five further register rows" (synthesis :99) leans on two stretched mappings — register **#7** (falsifiers live in `earnings_notes`, a column R2's scope text never touches; R2 governs `invalidation_conditions`) and **#19** (`score_macro_theses`, a sibling pipeline R2's scope doesn't name). Discount those two and R2's mass edge over R1 narrows; the R2→R1 order may still be right, but the stated justification overstates it.

**2. Overclaiming — PASS.** Every CONFIRMED row I replayed is confirmed; #31 is correctly PLAUSIBLE; #6 correctly carries "cause un-evidenced"; #3's class is honestly labeled adopted-assessment; #10 carries the swept-surfaces caveat. §5 restates the denominator caveat, and §2 note (iii) correctly treats zero-defect D0-04 items as unexercised, not cleared. The E08 latest-9 window is deep enough (spans back to 08-02) that the missed-runs inference is sound.

**3. Firewall — PASS.** No sentence in the synthesis or its quoted panel content is functionally-directive about HUBS/CBA; all HUBS ESS/CGT facts are held UNKNOWN; the closing abstentions line is honoured in the body. The closest approach — "the correct first successor artifact is the rule-repair card itself" (:79) — is product-process, not position direction.

**4. REBUILD verdict — SURVIVES; one wording note.** Reason 1 alone forces REBUILD: no layout change fixes a headline sourced solely from write-once state (verified in code). Reason 3 is anchored by `discipline.py:220-229` vs `brief-mock.html:297,344`. **Note (reason 2):** "the legitimate response — repair the rule, then decide — was structurally absent" is attackable as written: the mock's path 2 ("Re-underwrite… `asx thesis revise 2`", `brief-mock.html:345`) *is* a repair-shaped option. The claim survives only on the framing distinction (path 2 is offered as a co-equal same-day decision under an "invalidated" verdict and "Action requested" eyebrow, requiring UNAVAILABLE Q2 actuals — not a demotion to a repair card), and the proposal should carry that qualification explicitly.

**5. Bounded authority — PASS, one note.** Schema migrations (R1/R2/R3/R9), governed docs (R3/R4/R6/R7/R9), and parameters (R3 thresholds, R4 hysteresis/dislocation, R9 attestation/grandfathering) are all correctly James-gated; :101 explicitly declines to invent a mandate for the unmapped tax rows. **Note:** R5's authority class, "agent-charter change" (:96), is the only governed-text edit *not* marked James-gated. In a mission whose charge is "written rules are arbitrary," charter edits (e.g. stripping `model_a` from `portfolio-coherence-reviewer.md:45-46`) should carry the same gate flag as governed docs.

**6. Most likely rejection trigger.** The **R2 → R1 leverage ordering** (:99). All three of James's own interrogation answers — placeholder stop, error band, misunderstood trigger semantics — are *authoring/attestation* failures, i.e. R1/R9 territory; ranking the machinery fix first can read as the system again prioritising plumbing over the intake that produced 13/13 malformed rules, and the stated justification for R2-first partly rests on the two stretched row-mappings in note 1. Runner-up: the four tax-wiring rows (#11, #12, #13, #24) mapping to **no** R item, flagged-not-assigned (:101) — defensible under the Div 83A hold, but it leaves the money question James actually has visibly unowned.

**One enrichment, free to take:** the mechanism behind register #11 is sharper than either panel-7 or the synthesis states — the monitor's input key is literally named `cost_usd` while `service.py:247` populates it with the AUD-derived `cost_base_normal/quantity`. The misnamed field *is* the R10 trap in schema form and belongs in whichever work order carries the currency-consistency item.

Key files: `/Users/jpcino/.claude/jobs/cb048518/tmp/synthesis-fresh-synthesizer.md`, `/Users/jpcino/.claude/jobs/cb048518/tmp/evidence-packet-2026-08-08.json`, `/Users/jpcino/.claude/jobs/cb048518/tmp/brief-mock.html`, `/Users/jpcino/Desktop/asxos/jobs/check_thesis_invalidations.py`, `/Users/jpcino/Desktop/asxos/asxos/domain/position_monitor/service.py`, `/Users/jpcino/Desktop/asxos/asxos/domain/tax/cgt.py`, `/Users/jpcino/Desktop/asxos/docs/foundation/spec/tax-alpha.md`, `/Users/jpcino/Desktop/asxos/.claude/agents/portfolio-coherence-reviewer.md`, `/Users/jpcino/Desktop/asxos/asxos/domain/theses/discipline.py`.
