# Engineering escalation notes — simulated, not sent

## P1 — API OOM and restart (L3/on-call), exercise 09:55 Dubai

**Impact:** Multi-customer upload interruption; Marina Bay go-live readiness unconfirmed. Peak reproduction of 240 uploads at concurrency eight returned 212 successful and 28 failed requests. Two Docker OOM events and exit 137 restarts around 07:34:45 and 07:35:13 UTC, 14 Nov lab replay. Database snapshot after load: 39 Validated and 683 Submitted invoices across the four peak sellers, with queue depth zero; reconcile each, since some may still be settling or affected by rate limits.  
**Evidence:** [load](peak-load.log), [Docker events](peak-docker-events.jsonl), [Grafana](grafana-overview.png), [API logs](peak-api-web-logs.txt), [SQL](peak-sql-results.txt), [metrics](peak-prometheus-queries.json).  
**Likely mechanism:** 128 MiB API limit plus unbounded source cache of uploads/parsed workbooks/mapped invoices; in-memory submission queue disappears on restart. OOM is confirmed; the individual stranded invoice set requires reconciliation.  
**Request:** Stabilize capacity/cache, establish durable queue or recovery, return affected invoice IDs and safe targeted retry plan, verify with sustained peak test. L1 owns 30–60-minute customer updates and will not certify go-live without evidence. Next simulated update 10:25.

## P2 — Al Noor rounding defect (L3), exercise 12:25 Dubai

**Impact:** ANF-2611-0042, 0044, 0046 rejected by ASP BR-CO-15; 0041, 0043, 0045 accepted. Import c44b2ba7-c470-41a1-a444-7d3acfbb8fab.  
**Evidence:** [invoice payload/error/event JSON](al-noor-invoice-details.json), [ASP list](al-noor-asp-documents.json), [workbook arithmetic](workbook-analysis.csv), [logs](case-log-excerpts.txt). Got/expected gross: 0042 15022.42/15022.43; 0044 11817.57/11817.59; 0046 5610.99/5611.00.  
**Cause:** Gross calculated independently from unrounded quantity × unit price, inconsistent with rounded net/VAT.  
**Request:** Correct mapping, add three-decimal-price regression tests, define safe repair/reissue of ASP-rejected invoices. Do not tell customer to alter valid source values. L1 owns Fatima's written explanation and next update 14:25.

## P2 — Sahara/Bluepeak 429 handling (L3), exercise 13:40 Dubai

**Impact:** Import 4426b2ed-da49-4d42-b9c9-28db7db6ea03: SMS-1116-001..008 ASP Accepted; 009..040 Submitted without ASP references. Logs and metrics show 32 ASP HTTP 429s.  
**Evidence:** [invoice events](sahara-invoice-details.json), [ASP documents](sahara-asp-documents.json), [logs](case-log-excerpts.txt), [metrics](api-metrics-during-oasis.txt), [SQL](case-sql-results.txt).  
**Cause:** API marks Submitted before ASP call; no 429/Retry-After branch; in-memory queue drains without a terminal status or retry.  
**Request:** Reconcile ASP and DB per invoice, recover only missing numbers with backoff and idempotency, persist retries and expose truthful state. No whole-file resend. L1 owns Daniel's update at 15:40.

## P2 — Oasis misleading timeout (L3 product defect), exercise 11:15 Dubai

**Impact:** Portal returns 504 at 60 seconds for 600-row file; backend completes at ~121 seconds, all eight originals ASP Accepted. Second identical upload gets eight portal duplicate rejections.  
**Evidence:** [proxy timing](oasis-proxy-http.txt), [first import](oasis-first-import.json), [second import](oasis-duplicate-import.json), [ASP list](oasis-asp-documents.json).  
**Request:** Cache repeated participant lookups; expose asynchronous import ID/progress to client and avoid presenting an ambiguous failure. L1 already tells Rashid the eight ASP references and to stop resending.
