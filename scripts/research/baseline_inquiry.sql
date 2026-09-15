-- Baseline inquiry — live, read-only sweep of the ASX universe (first run 2026-09-16).
--
-- WHAT THIS IS. The residual-income model in asxos/domain/valuation/residual_income.py
-- expressed as SQL, so it can run through the read-only `supabase-ro` connector from a
-- sandbox that cannot reach the database directly. It persists nothing. It reproduces
-- `value_per_share()` exactly (parity to 0.000001 on five names, 2026-09-16 — see
-- scripts/research/parity_check.py). It is the acceptance test for the sprint's S1
-- runner: the persisted `valuation_runs` for the same as_of must match REPORT B.
--
-- MODEL (residual income, reported-book base, 10-year linear ROE fade, clean surplus):
--   roe_t   = roe_start + (roe_term - roe_start) * t / 10        t = 1..10
--   B_t     = B_{t-1} * (1 + roe_t * (1 - payout))
--   RI_t    = (roe_t - ke) * B_{t-1}
--   value   = B_0 + sum RI_t/(1+ke)^t [+ PV of franking credits] [+ CV under fading_excess]
--   zero_excess (conv 'zx', pre-registered): roe_term = ke, terminal value = book.
--   fading_excess (conv 'fx', ILLUSTRATIVE, w = 0.5, not pre-registered):
--     roe_term = ke + w*(roe_start-ke); CV = RI_10 * w / (1 + ke - w) discounted 10 years.
--   Scenarios (pre-registered 2026-09-08): bear/base/bull = 0.70/1.00/1.20 x own ROE,
--     probabilities 25/50/25. 'avg3' = base scenario at the 3-period average ROE (a
--     sensitivity against peak-cycle trailing ROE), probability 0.
--   Ke band: rf (market_context.aus_10y_yield, latest) + beta * 5.5% ERP, beta band
--     0.55/0.70/0.85 — the CITED bank band (capm.py), not a measurement; not sector-specific.
--
-- INPUTS (rule #11: no `signals`, no `model_versions`):
--   rs_fundamentals_pit  latest usable row per symbol (knowledge_date <= today)
--   prices               last close, 90-session ADV (close*volume), 3m/12m realised return
--   universe             active au_equity only (ETF/LIC/hybrid excluded: no book/ROE basis)
--   rs_security_master   GICS sector / industry
--   USD reporters are converted at the AUDUSD in `params` (portfolio_daily_snapshots.fx_rate_audusd
--   on the run date); currency NULL/'' is VALUED and FLAGGED ('valued_currency_unverified'),
--   not dropped — the sprint's C-20 backfill closes that flag.
--
-- HOW TO RUN. Each report is PRELUDE + one final SELECT. `scripts/research/baseline_inquiry.py`
-- prints a chosen report as one statement (paste into supabase-ro) or runs it when
-- DATABASE_URL reaches the pooler. Refresh the three `params` values before a re-run.

-- ============================================================================ PRELUDE
WITH RECURSIVE params AS (
  SELECT 0.04831::numeric AS rf,       -- market_context.aus_10y_yield as_of 2026-09-15
         0.055::numeric   AS erp,      -- James's ruling: ERP in [5%, 6%]
         0.7134::numeric  AS audusd),  -- fx_rate_audusd, portfolio_daily_snapshots 2026-09-14
pit AS (
  SELECT DISTINCT ON (symbol) symbol, as_of, book_value_ps, roe, eps_ttm, dividend_ttm,
         franking_avg_pct, currency
  FROM rs_fundamentals_pit WHERE knowledge_date <= CURRENT_DATE
  ORDER BY symbol, as_of DESC, knowledge_date DESC),
pit3 AS (
  SELECT symbol, avg(roe) AS roe_avg3, count(*) AS n_roe
  FROM (SELECT symbol, roe,
               row_number() OVER (PARTITION BY symbol ORDER BY as_of DESC, knowledge_date DESC) AS rn
        FROM rs_fundamentals_pit WHERE knowledge_date <= CURRENT_DATE AND roe IS NOT NULL) t
  WHERE rn <= 3 GROUP BY symbol),
px  AS (SELECT DISTINCT ON (symbol) symbol, dt, close FROM prices WHERE dt <= CURRENT_DATE
        ORDER BY symbol, dt DESC),
adv AS (SELECT symbol, avg(close*volume) AS adv_aud FROM prices
        WHERE dt >= CURRENT_DATE - 130 GROUP BY symbol),
p3  AS (SELECT DISTINCT ON (symbol) symbol, close AS c FROM prices WHERE dt <= CURRENT_DATE - 91
        ORDER BY symbol, dt DESC),
p12 AS (SELECT DISTINCT ON (symbol) symbol, close AS c FROM prices WHERE dt <= CURRENT_DATE - 365
        ORDER BY symbol, dt DESC),
base AS (
  SELECT u.symbol, u.name, u.market_cap, m.gics_sector, m.gics_industry, p.as_of, p.currency,
         pit3.roe_avg3, pit3.n_roe,
         CASE WHEN p.currency='USD' THEN p.book_value_ps/params.audusd ELSE p.book_value_ps END AS b0,
         p.roe AS roe0,
         CASE WHEN p.eps_ttm > 0 AND p.dividend_ttm IS NOT NULL
              THEN LEAST(1, GREATEST(0, p.dividend_ttm/p.eps_ttm)) ELSE 0 END AS payout,
         COALESCE(p.franking_avg_pct, 0) AS frank,
         CASE WHEN p.currency='USD' THEN p.dividend_ttm/params.audusd ELSE p.dividend_ttm END AS dps,
         px.close, px.dt, adv.adv_aud,
         px.close/NULLIF(p3.c,0)-1 AS r3, px.close/NULLIF(p12.c,0)-1 AS r12,
         CASE WHEN p.symbol IS NULL THEN 'no_pit'
              WHEN p.book_value_ps IS NULL OR p.book_value_ps <= 0 THEN 'book_nonpositive'
              WHEN p.roe IS NULL THEN 'roe_missing'
              WHEN p.roe <= 0 THEN 'roe_nonpositive'
              WHEN px.close IS NULL THEN 'no_price'
              WHEN p.currency IS NOT NULL AND p.currency NOT IN ('AUD','USD','') THEN 'currency_other'
              WHEN p.currency IS NULL OR p.currency = '' THEN 'valued_currency_unverified'
              ELSE 'valued' END AS status
  FROM universe u CROSS JOIN params
  LEFT JOIN pit p USING (symbol) LEFT JOIN pit3 USING (symbol) LEFT JOIN px USING (symbol)
  LEFT JOIN adv USING (symbol) LEFT JOIN p3 USING (symbol) LEFT JOIN p12 USING (symbol)
  LEFT JOIN rs_security_master m USING (symbol)
  WHERE u.security_kind = 'au_equity' AND u.is_active),
grid AS (
  SELECT b.symbol, b.b0, b.payout, b.frank, s.scen, s.prob, c.conv, c.w, k.kname,
         (params.rf + k.beta*params.erp) AS ke,
         CASE WHEN s.scen='avg3' THEN COALESCE(b.roe_avg3, b.roe0) ELSE b.roe0*s.factor END AS roe_start
  FROM base b CROSS JOIN params
  CROSS JOIN (VALUES ('bear',0.25,0.70),('base',0.50,1.00),('bull',0.25,1.20),('avg3',0.0,1.00))
       AS s(scen,prob,factor)
  CROSS JOIN (VALUES ('zx',0.0),('fx',0.5)) AS c(conv,w)
  CROSS JOIN (VALUES ('lo',0.55),('mid',0.70),('hi',0.85)) AS k(kname,beta)
  WHERE b.status LIKE 'valued%'
    AND NOT (s.scen='avg3' AND c.conv='fx')          -- avg3 is a zero-excess sensitivity only
    AND (k.kname='mid' OR (c.conv='zx' AND s.scen<>'avg3'))),  -- lo/hi only for the registered case
rec AS (
  SELECT symbol, scen, prob, conv, w, kname, ke, 0 AS t, b0 AS book,
         0::numeric AS pv_ri, 0::numeric AS pv_fr, roe_start,
         (ke + w*(roe_start-ke)) AS roe_term, payout, frank, b0, 0::numeric AS ri_last
  FROM grid
  UNION ALL
  SELECT r.symbol, r.scen, r.prob, r.conv, r.w, r.kname, r.ke, r.t+1,
         r.book*(1 + x.roe_t*(1-r.payout)),
         r.pv_ri + (x.roe_t - r.ke)*r.book/power(1+r.ke, r.t+1),
         r.pv_fr + x.roe_t*r.book*r.payout*(r.frank/100)*(0.3/0.7)/power(1+r.ke, r.t+1),
         r.roe_start, r.roe_term, r.payout, r.frank, r.b0, (x.roe_t - r.ke)*r.book
  FROM rec r
  CROSS JOIN LATERAL (SELECT r.roe_start + (r.roe_term - r.roe_start)*(r.t+1)/10.0 AS roe_t) x
  WHERE r.t < 10),
vals AS (
  SELECT symbol, conv, scen, prob, kname,
         b0 + pv_ri + pv_fr
           + CASE WHEN w > 0 THEN ri_last*w/(1+ke-w)/power(1+ke,10) ELSE 0 END AS v
  FROM rec WHERE t = 10),
agg AS (
  SELECT symbol,
         sum(prob*v) FILTER (WHERE conv='zx' AND scen<>'avg3' AND kname='mid') AS pw_zx,
         sum(prob*v) FILTER (WHERE conv='zx' AND scen<>'avg3' AND kname='lo')  AS pw_zx_lo,
         sum(prob*v) FILTER (WHERE conv='zx' AND scen<>'avg3' AND kname='hi')  AS pw_zx_hi,
         sum(prob*v) FILTER (WHERE conv='fx' AND scen<>'avg3' AND kname='mid') AS pw_fx,
         max(v) FILTER (WHERE conv='zx' AND scen='avg3' AND kname='mid') AS v_avg3,
         max(v) FILTER (WHERE conv='zx' AND scen='bear' AND kname='mid') AS bear_zx,
         max(v) FILTER (WHERE conv='zx' AND scen='bull' AND kname='mid') AS bull_zx
  FROM vals GROUP BY symbol),
sweep AS (
  SELECT b.*, (params.rf + 0.70*params.erp) AS ke_mid,
         a.pw_zx, a.pw_zx_lo, a.pw_zx_hi, a.pw_fx, a.v_avg3, a.bear_zx, a.bull_zx,
         a.pw_zx/NULLIF(b.close,0)   AS vp_zx,
         a.pw_fx/NULLIF(b.close,0)   AS vp_fx,
         a.v_avg3/NULLIF(b.close,0)  AS vp_avg3
  FROM base b CROSS JOIN params LEFT JOIN agg a USING (symbol))
-- ============================================================================ END PRELUDE

-- REPORT A — status histogram and value/price distribution (zero-excess, Ke mid)
SELECT status, count(*) AS n,
       round(percentile_cont(0.1)  WITHIN GROUP (ORDER BY vp_zx)::numeric,3) AS vp_p10,
       round(percentile_cont(0.25) WITHIN GROUP (ORDER BY vp_zx)::numeric,3) AS vp_p25,
       round(percentile_cont(0.5)  WITHIN GROUP (ORDER BY vp_zx)::numeric,3) AS vp_p50,
       round(percentile_cont(0.75) WITHIN GROUP (ORDER BY vp_zx)::numeric,3) AS vp_p75,
       round(percentile_cont(0.9)  WITHIN GROUP (ORDER BY vp_zx)::numeric,3) AS vp_p90,
       count(*) FILTER (WHERE vp_zx >= 1) AS n_value_ge_price,
       count(*) FILTER (WHERE roe0 > ke_mid) AS n_roe_gt_ke,
       count(*) FILTER (WHERE vp_zx >= 1 AND roe0 > ke_mid AND adv_aud >= 250000
                          AND market_cap >= 1e8) AS n_candidates_liquid
FROM sweep GROUP BY status ORDER BY n DESC;

-- REPORT B — the per-name sweep (this is what S1's `valuation_runs` must reproduce)
SELECT symbol, status, as_of, currency, close, dt, round(b0,6) AS b0, round(roe0,6) AS roe0,
       round(roe_avg3,6) AS roe_avg3, round(payout,6) AS payout, frank,
       round(pw_zx,6) AS pw_zx, round(pw_zx_lo,6) AS pw_zx_lo, round(pw_zx_hi,6) AS pw_zx_hi,
       round(bear_zx,6) AS bear_zx, round(bull_zx,6) AS bull_zx, round(pw_fx,6) AS pw_fx,
       round(v_avg3,6) AS v_avg3, round(vp_zx,6) AS vp_zx, round(adv_aud) AS adv_aud
FROM sweep ORDER BY symbol;

-- REPORT C — top 25 opportunities: quality (ROE > Ke) + liquidity (ADV >= A$250k, mcap >= A$100m)
SELECT symbol, left(name,26) AS name, gics_sector, left(gics_industry,22) AS industry, close,
       round(pw_zx,2) AS tgt_zx, round(vp_zx,2) AS vp_zx, round(pw_fx,2) AS tgt_fx,
       round(vp_fx,2) AS vp_fx, round(v_avg3,2) AS tgt_avg3, round(vp_avg3,2) AS vp_avg3,
       round(bear_zx,2) AS bear, round(bull_zx,2) AS bull, round(roe0,3) AS roe,
       round(roe_avg3,3) AS roe_avg3, round(payout,2) AS payout, frank::int AS frk,
       CASE WHEN status='valued' THEN currency ELSE 'UNVERIFIED' END AS ccy,
       round(adv_aud/1e3) AS adv_k, round(market_cap/1e6) AS mcap_m,
       round(r3*100,1) AS r3_pct, round(r12*100,1) AS r12_pct, round(dps/close*100,1) AS dy_pct
FROM sweep
WHERE status LIKE 'valued%' AND roe0 > ke_mid AND adv_aud >= 250000 AND market_cap >= 1e8
ORDER BY vp_zx DESC LIMIT 25;

-- REPORT D — the robust set: value >= price under BOTH zero-excess and 3-period-average ROE
SELECT symbol, left(name,24) AS name, gics_sector, left(gics_industry,20) AS industry, close,
       round(pw_zx,2) AS tgt, round(v_avg3,2) AS tgt_avg3, round(bear_zx,2) AS bear,
       round(LEAST(vp_zx, vp_avg3),2) AS vp_min, round(roe0,3) AS roe, round(roe_avg3,3) AS roe3,
       round(payout,2) AS po, frank::int AS frk,
       CASE WHEN status='valued' THEN currency ELSE 'UNV' END AS ccy,
       round(adv_aud/1e3) AS adv_k, round(market_cap/1e6) AS mcap_m,
       round(r12*100,1) AS r12_pct, round(dps/close*100,1) AS dy_pct
FROM sweep
WHERE status LIKE 'valued%' AND adv_aud >= 250000 AND market_cap >= 1e8
  AND vp_zx >= 1 AND vp_avg3 >= 1 AND roe_avg3 > ke_mid
ORDER BY vp_min DESC;

-- REPORT E — segment table (GICS sector)
SELECT coalesce(gics_sector,'(none)') AS sector, count(*) AS n_active,
       count(*) FILTER (WHERE status LIKE 'valued%') AS n_valued,
       count(*) FILTER (WHERE status LIKE 'valued%' AND adv_aud >= 250000 AND market_cap >= 1e8)
         AS n_valued_liquid,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY vp_zx)
             FILTER (WHERE status LIKE 'valued%' AND adv_aud >= 250000)::numeric,2) AS med_vp_liquid,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY roe0-ke_mid)
             FILTER (WHERE status LIKE 'valued%')::numeric,3) AS med_roe_minus_ke,
       count(*) FILTER (WHERE vp_zx >= 1 AND roe0 > ke_mid AND adv_aud >= 250000
                          AND market_cap >= 1e8) AS n_candidates,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY r12)
             FILTER (WHERE adv_aud >= 250000)::numeric*100,1) AS med_r12_pct_liquid,
       round(sum(market_cap) FILTER (WHERE market_cap IS NOT NULL)/1e9,1) AS mcap_bn
FROM sweep GROUP BY 1 ORDER BY mcap_bn DESC NULLS LAST;

-- REPORT F — counts by convention among liquid valued names (the calibration metric, both conventions)
SELECT count(*) AS n_liquid_valued,
       count(*) FILTER (WHERE vp_zx >= 1 AND roe0 > ke_mid) AS cand_zx,
       count(*) FILTER (WHERE vp_fx >= 1 AND roe0 > ke_mid) AS cand_fx,
       count(*) FILTER (WHERE vp_avg3 >= 1 AND roe_avg3 > ke_mid) AS cand_avg3,
       count(*) FILTER (WHERE vp_zx >= 1 AND vp_avg3 >= 1 AND roe_avg3 > ke_mid) AS cand_zx_and_avg3,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY vp_zx)::numeric,2)   AS med_vp_zx,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY vp_fx)::numeric,2)   AS med_vp_fx,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY vp_avg3)::numeric,2) AS med_vp_avg3
FROM sweep WHERE status LIKE 'valued%' AND adv_aud >= 250000 AND market_cap >= 1e8;

-- REPORT G — ETF map (name-keyword classes; ETFs are mapped, not valued). Standalone, no prelude.
-- WITH px AS (...), adv AS (...) SELECT klass, count(*), ... — see baseline_inquiry.py:ETF_MAP.
