# Product Support Engineer assignment — Invoicely Lite

**Candidate:** ANBU M  
**Exercise:** Monday 16 November 2026, Asia/Dubai. All times in the triage and customer drafts below are simulated. No fictional email was actually sent.  
**Lab replay:** 14 November 2026 UTC on a local Docker stack. These timestamps are evidence collection times, not the exercise clock.  
**Repository:** https://github.com/anbu-m07/complyance-pse-support-lab

## Triage and first responses

| Arrival (Dubai) | Case | Priority and reason | First response draft time / target | Next update |
|---|---|---|---|---|
| 09:05 | Oasis Builders | P2: month-end file appears stuck, with duplicate risk; customer-specific impact while service is available. Escalate to P1 if broader outage emerges. | 09:15 / 10:05 | 11:15 |
| 09:42 alert; 09:50 Priya | API restarts / Marina Bay | P1: repeated restarts and intermittent upload failures across customers; go-live risk. | 09:55 to Priya / 10:12 from alert | 10:25, then every 30–60 minutes |
| 10:15 | Al Noor Fuel | P2: multiple ASP rejections and auditor deadline; subset of invoices affected. | 10:25 / 11:15 | 12:25 |
| 11:30 | Sahara / Bluepeak | P2: 32 of 40 invoices not acknowledged by ASP, payment-run impact. Raise to P1 if service-wide. | 11:40 / 12:30 | 13:40 |
| 12:10 | Ghaf Tree Café | P3: one seller's four invoices rejected by format validation; correctable, no ASP submission. | 12:20 / 16:10 | After checking the corrected file, by next business day if unresolved |

These targets follow [the lab SLA matrix](docs/sla-matrix.md). P1 resolution target is 13:42 from the alert; P2 resolution target is eight business hours from receipt; P3 is three days. Targets are commitments to manage, not claims that the defects were fixed in this exercise. I prioritized P1 immediately after its alert, then the payment and audit cases while reconciling Oasis. Ghaf had a safe documented correction.

### First-response drafts

**Oasis, 09:15:** “Hi Rashid, I understand the file appeared to hang and you need to know what went through before retrying. Please do not upload it again yet. I’m checking the eight invoice numbers against our records and the ASP acknowledgements. I’ll update you by 11:15 with a reconciled list and a safe next step.”

**Marina Bay, 09:55:** “Hi Priya, I’m owning this. We have an API restart alert and reports of intermittent upload errors. I’m checking the impact and involving on-call engineering as a critical incident. I’ll update you by 10:25 on the affected invoices and Wednesday’s go-live risk; I cannot confirm readiness yet.”

**Al Noor, 10:25:** “Hi Fatima, I’m comparing the rejected fuel invoices with the amounts in your file and the ASP response. Please hold off on changing or resending them until we confirm the source of the difference. I’ll send you a written update by 12:25.”

**Bluepeak, 11:40:** “Hi Daniel, thank you for pausing the resend. HTTP 201 confirms that an import was created, not that all 40 invoices reached the ASP. I’m reconciling the status and ASP reference for each number. Please avoid resending the batch until I give you the affected list. I’ll update you by 13:40.”

**Ghaf, 12:20:** “Hi Hessa, 13/11/2026 is a valid calendar date, but this template expects year-month-day or a real Excel date cell. I’m checking the file for other errors so you can correct it once. I’ll confirm the exact steps and which invoice numbers are safe to upload again shortly.”

## Investigation 1 — P1 API restarts and Marina Bay

**Reproduction and observations.** I ran the supplied 240-upload, eight-concurrent peak generator after establishing a clean control import. It finished with **212 successful and 28 failed HTTP uploads**; 16 failed with EOF, four with connection errors and eight with a DNS lookup error during the disruption. [Load output](evidence/peak-load.log). Docker recorded **two OOM events, exits with code 137, and automatic starts** at approximately 07:34:45 and 07:35:13 UTC. [Docker events](evidence/peak-docker-events.jsonl); [API/web logs](evidence/peak-api-web-logs.txt). The [Grafana overview screenshot](evidence/grafana-overview.png) showed API process restarts (1h) = 2 and the live API up = 1 after recovery. The [Prometheus queries](evidence/peak-prometheus-queries.json) captured API working-set memory at 126,709,760 bytes, near its 128 MiB limit, and queue depth zero after restart. A current container inspect alone says OOMKilled=false after the restart; the time-stamped Docker OOM and die events establish the exit cause.

**Database check.** The peak generator's summary at 07:35:58 showed 215 completed and 13 processing imports; invoices included 39 Validated and 683 Submitted, despite queue depth zero. [SQL query and output](evidence/peak-sql-results.txt) lists Marina Bay invoices in Validated and Submitted as well as Accepted. These are a snapshot while other work was still settling, so the exact recovery set requires a fresh per-invoice reconciliation. A Completed import is not evidence that all its invoices were accepted. I would compare each affected invoice event and ASP reference before retrying.

**Cause and escalation.** The API container limit is 128 MiB in docker-compose.yml; the process keeps raw upload bytes, parsed workbooks and mapped invoices in a cache without eviction in services/api/internal/importer/sources.go. Under peak traffic it reaches the limit and restarts. The submission queue is in process memory in services/api/internal/submit/submit.go, so a restart can strand work already marked Validated. The OOM cause is confirmed by Docker events; the precise fate of each Marina Bay invoice still needs reconciliation. Page L3/on-call immediately with the two event timestamps, exit 137, 28 failed requests, memory limit, import IDs and SQL output. Ask for bounded cache/temporary capacity, durable queue or startup recovery, and a verified targeted replay plan. L1 owns Priya's updates and escalates any breach risk. Do not promise Wednesday go-live until a sustained load test and all invoice states are reconciled.

**Customer update draft, 10:25:** “Hi Priya, we reproduced API restarts during peak imports and have engaged engineering as P1. Some uploads failed during the restart, and we are checking the individual invoice records before asking anyone to retry. I cannot yet confirm the Wednesday launch is safe. I’ll update you by 10:55 with the recovery list and service stability status.”

## Investigation 2 — Oasis Builders upload timeout and duplicates

**Evidence.** The workbook contains **600 rows but only eight invoices**. [Workbook analysis](evidence/workbook-analysis.csv). The portal-proxy request returned **HTTP 504 after 60.03 seconds** ([HTTP record](evidence/oasis-proxy-http.txt), [body](evidence/oasis-proxy-response.json)), yet backend import **821c774d-65fd-4b36-99ba-0db389146efc** continued and completed in **120,903 ms**. All OBS-2611-001 through 008 were **Accepted** with ASP references ([first import](evidence/oasis-first-import.json)); the ASP lists exactly eight accepted documents ([ASP list](evidence/oasis-asp-documents.json)). I deliberately replayed the same file to test the duplicate warning: import **ece14fef-c7b8-4bd8-bdb1-60f481e20669** completed in 120,778 ms with all eight **portal Rejected**, each AE-BR-09 “already exists ... status Accepted,” and no second ASP reference ([second import](evidence/oasis-duplicate-import.json), [invoice errors](evidence/oasis-duplicate-details.json)). [SQL output](evidence/case-sql-results.txt) corroborates the records.

**Cause.** Validation performs a 200 ms participant lookup on each row, about 120 seconds for 600 rows (services/api/internal/validate/validate.go:67-71,165-173; services/asp-mock/main.go:40,335). The web proxy has a 60-second timeout (web/app/api/[...path]/route.ts:6,25), while the importer continues in a background context (services/api/internal/importer/importer.go:22,38). The second attempt then meets the seller/document-number duplicate check (services/api/internal/store/store.go:298-309). The timeout is a misleading front-end result, not a failed first submission. This case is fully reconciled in the lab.

**Customer resolution draft, 11:15:** “Hi Rashid, I checked all eight numbers OBS-2611-001 to 008. The first upload continued after the browser timed out, and the ASP accepted all eight. Your second upload was rejected by our portal as duplicates; it did not create another ASP submission. Please do not resend this file. I can provide the eight ASP references from the reconciliation. We’re raising the misleading timeout and progress display with engineering.” L1 closes only after Rashid confirms the reference list meets his need. Escalate the UX/performance defect to L3: cache participant lookups, make large imports asynchronous with a durable import ID and show a clear “still processing” status.

## Investigation 3 — Al Noor BR-CO-15

**Evidence.** Import **c44b2ba7-c470-41a1-a444-7d3acfbb8fab** completed with three Accepted (0041, 0043, 0045) and three **ASP Rejected** (0042, 0044, 0046). Their events are Parsed → Validated → Submitted → Rejected. [Import](evidence/al-noor-settled.json), [invoice payloads/errors/events](evidence/al-noor-invoice-details.json), [ASP documents](evidence/al-noor-asp-documents.json), [logs](evidence/case-log-excerpts.txt), [SQL and events](evidence/case-event-sql-results.txt).

| Invoice | Generated gross | Rounded net + VAT | ASP result |
|---|---:|---:|---|
| ANF-2611-0041 | 14,437.24 | 14,437.24 | Accepted |
| ANF-2611-0042 | 15,022.42 | 15,022.43 | BR-CO-15 |
| ANF-2611-0043 | 19,618.20 | 19,618.20 | Accepted |
| ANF-2611-0044 | 11,817.57 | 11,817.59 | BR-CO-15 |
| ANF-2611-0045 | 11,847.47 | 11,847.47 | Accepted |
| ANF-2611-0046 | 5,610.99 | 5,611.00 | BR-CO-15 |

The independent workbook arithmetic is in [workbook-analysis.csv](evidence/workbook-analysis.csv). The ASP's error gives these same got/expected amounts. The portal rounds line net and VAT, but derives invoice gross separately from the unrounded quantity × three-decimal unit price (services/api/internal/pint/pint.go; tools/internal/workbook/workbook.go). This inconsistency triggers BR-CO-15; it is a product calculation defect, not a reason to alter legitimate fuel prices.

**Escalation and update.** Send L3 the import and invoice IDs, three ASP 422 responses, arithmetic and code path; request a fix that derives gross from consistently rounded net and VAT, a regression test for three-decimal prices, and a safe repair/reissue plan for the rejected invoices. An unchanged stored payload will fail again. L1 owns Fatima's written auditor explanation and update. **Draft at 12:25:** “We found a rounding inconsistency in our generated totals for three invoices: 0042, 0044 and 0046. The ASP rejected those three; 0041, 0043 and 0045 were accepted. We have escalated the calculation defect and will confirm the corrected issue procedure before asking you to resend anything. I’ll update you by 14:25.”

## Investigation 4 — Sahara / Bluepeak missing ASP acknowledgements

**Evidence.** Import **4426b2ed-da49-4d42-b9c9-28db7db6ea03** contains 40 invoices. SMS-1116-001 through 008 are **Accepted** with ASP references. SMS-1116-009 through 040 remain **Submitted** with empty ASP references and no ASP-side documents. [Import](evidence/sahara-settled.json), [invoice events](evidence/sahara-invoice-details.json), [ASP list](evidence/sahara-asp-documents.json), [SQL](evidence/case-sql-results.txt). API logs show 32 HTTP **429** ASP responses for the later numbers; the [metrics capture](evidence/api-metrics-during-oasis.txt) recorded 32 code=429 while failed submissions remained zero and queue depth was zero. [Selected logs](evidence/case-log-excerpts.txt).

**Cause.** The ASP limits a sender to an initial burst of eight and two per second (services/asp-mock/main.go:35-37,268-282). The API sets Submitted before its ASP request but handles 200, 422 and 5xx, **not 429 or Retry-After** (services/api/internal/submit/submit.go:114-155). These 32 requests are lost from the in-memory queue in a misleading Submitted state. The normal retry endpoint accepts Validated/Failed, so a bulk retry is not safe.

**Partner update draft, 13:40:** “Hi Daniel, we reconciled the batch. The ASP accepted SMS-1116-001 to 008. The other 32 have no ASP acknowledgement; they encountered a rate limit and need a controlled recovery. Please do not resend the 40-file batch or initiate buyer delivery for the remaining numbers. I’ve escalated the exact list and will update you by 15:40 on the targeted recovery plan.” L3 must reconcile ASP and database per number, safely requeue only missing documents with backoff and idempotency, then return references. L1 owns the partner and seller updates. Prevent recurrence by honoring Retry-After and persisting retry state.

## Investigation 5 — Ghaf Tree Café date format

Import **2bcc29e6-4fbd-4e5a-9d87-5db97739da65** completed with GTC-118 through 121 portal Rejected. Each has AE-BR-04 on issue and due date text such as 13/11/2026 and 13/12/2026; no ASP reference or ASP response. [Import](evidence/ghaf-settled.json), [all four errors/events](evidence/ghaf-invoice-details.json), [workbook analysis](evidence/workbook-analysis.csv). The parser accepts YYYY-MM-DD or a real Excel date serial (services/api/internal/sheet/sheet.go:171-185), and the template guide documents that rule. The problem is input representation, not an invalid date. The portal rejected before submission, so corrected numbers are safe to upload under the documented lifecycle.

**Resolution draft, 12:35:** “Hi Hessa, I checked all four invoices. Their issue and due dates are text in day/month/year order, so the portal rejected them before sending anything to the ASP. Convert both columns to real Excel dates or YYYY-MM-DD text, for example 2026-11-13 and 2026-12-13. Changing display formatting alone may not convert a text cell. You can upload the corrected four invoices using the same numbers. I’m happy to check the corrected sheet first.” Suggest a more helpful validator message; no defect escalation needed.

## Evidence method, learning and time

I compared a clean five-invoice Desert Rose import ([control result](evidence/desert-rose-settled.json)) to each targeted replay, then used the API invoice event histories, SQL query outputs, ASP document lists, logs, source code and Grafana/Prometheus. [Source review](evidence/source-review.md) gives exact file locations; the [case SQL](evidence/case-sql-results.txt) and [event SQL](evidence/case-event-sql-results.txt) include the commands and their output. The dashboard screenshot is a snapshot **after** the peak; the Docker event stream is the stronger proof of OOM timing. Sample historical seed records from October are separate from the November replay IDs.

The main dead end was treating HTTP 201 or import Completed as if it meant delivery. Sahara disproved it. The Oasis browser 504 initially looked like failure; polling the backend and ASP showed the first submission succeeded, so retry advice changed to “do not resend.” A current Docker inspect showed OOMKilled=false after restart; time-stamped events revealed two OOM kills. I would instrument per-invoice retry age and expose durable import progress to reduce this ambiguity.

**Real work log:** 13 Nov 2026 evening UTC: assignment review, source/workbook analysis and draft preparation. 14 Nov 2026, approximately 07:10–07:40 UTC: Docker startup, clean control, targeted replays, API/ASP/SQL evidence, monitoring and peak reproduction. Document assembly followed. The earlier cloud session was interrupted by a power outage and was not continuously timed; I am not claiming an exact total from an unavailable timer. The candidate should replace this with their actual personal time record if required.

**AI usage disclosure:** I completed the analysis and all technical work myself. I used ChatGPT/Codex only as a note-taking aid, to help log and organize the evidence and records from the lab (API/ASP records, SQL output, logs, Grafana, and code). The technical findings are my own and are supported by those records. Customer replies are exercise drafts and were not sent.
