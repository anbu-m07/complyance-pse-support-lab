# Static evidence from the supplied lab repository

This evidence was collected without starting the Docker stack. It establishes sample inputs and code behavior, **not** observed production outcomes. See `workbook-analysis.csv`; regenerate with `python3 evidence/analyze_workbooks.py`.

## Oasis: long import and duplicate risk

- The supplied workbook has **600 line rows grouped into eight invoices** (`workbook-analysis.csv`).
- `services/api/internal/validate/validate.go:67-71` validates every row; `validate.go:165-173` calls participant lookup for every row. The simulated ASP sleeps **200 ms per lookup** (`services/asp-mock/main.go:40,335`). Sequential lookup time alone is approximately **120 seconds**, before parsing and database work.
- The portal proxy aborts its upstream call after **60 seconds** (`web/app/api/[...path]/route.ts:6,25`) and returns 504 for a timeout (`route.ts:39-53`). The importer uses its own background context with a 10-minute budget (`services/api/internal/importer/importer.go:22,38`), so the backend may keep processing after the browser gives up.
- A new upload creates a new import, and duplicate numbers are checked against non-rejected invoices from other imports (`services/api/internal/store/store.go:298-309`; `services/api/internal/validate/validate.go:73-82`). The source therefore explains why a retry may show AE-BR-09 without proving which original invoices reached the ASP.
- **Still needed:** both/all import IDs, per-invoice status history and ASP references; timestamps for the web 504 and API completion; ASP accepted list. Reconcile by invoice number before proposing a retry.

## API restarts: memory hypothesis

- The API container has a **128 MiB memory limit** (`docker-compose.yml:60-61`).
- Each import stores the raw workbook, parsed workbook, and mapped invoices in an in-memory cache (`services/api/internal/importer/importer.go:95`; `sources.go:11-36`). That cache has no expiry or eviction in its implementation. `make load` replays four customer files and **240 peak uploads** (`tools/cmd/loadgen/main.go`).
- Retained imports under peak traffic could exhaust memory and cause restarts. This remains a **hypothesis** until container OOM state, memory graph, restart timestamps, and API logs are captured. A restart also loses the in-memory source preview, and the submit queue is in memory (`services/api/internal/submit/submit.go:57-66`); this could leave validated invoices unsent. Confirm against the database and events.

## Al Noor: inconsistent rounding

- The six supplied invoices and line values are in `samples/al-noor-fuel-nov-2026.xlsx`. The workbook's line net amounts are already rounded to cents.
- The mapper uses those rounded net amounts and rounds each line VAT (`services/api/internal/pint/pint.go:135-148`), yet independently sums **unrounded quantity × unit price × 1.05** for gross (`pint.go:156-185`).
- The simulated ASP checks `gross == net + VAT` in cents (`services/asp-mock/main.go:225-229`). Independent calculation predicts mismatches for **ANF-2611-0042 (-0.01 AED), 0044 (-0.02), and 0046 (-0.01)**; see the CSV. It predicts 0041, 0043, 0045 pass this rule. This is a product calculation defect, not evidence that the customer's dispatch records are wrong.
- **Still needed:** actual invoice payload totals, ASP 422/BR-CO-15 response and rejection events, accepted comparator, and invoice IDs. Escalate a verified defect to engineering; do not tell the customer to alter prices or blindly retry an unchanged stored payload.

## Sahara: unhandled rate limit

- The supplied workbook has **40 invoices**, of which five target Coral Reef Resorts and 35 target Emirates Palm Hospital (see CSV).
- The ASP permits a burst of eight documents per sender followed by two per second and returns **429 with Retry-After** when throttled (`services/asp-mock/main.go:35-37,136-151,268-282`).
- The API marks an invoice **Submitted before** the ASP call (`services/api/internal/submit/submit.go:114-120`). Its response switch handles 200, 422, and certain 5xx, but **no 429** (`submit.go:133-155`). A throttled invoice can therefore remain Submitted without an ASP message ID or automatic retry. HTTP 201 for the import merely means parsing/validation completed (`services/api/internal/httpapi/httpapi.go:156-162`).
- **Still needed:** actual 429 response count and invoice IDs; ASP accepted list; status-event history; reconcile by buyer. Do not resend all 40. Engineering should repair the response handling and provide a safe retry path for those left Submitted (the normal retry endpoint only permits Validated or Failed).

## Ghaf: documented date rule

- The four supplied invoice numbers GTC-118 through GTC-121 use `DD/MM/YYYY` **text** for issue and due dates (CSV).
- `services/api/internal/sheet/sheet.go:171-185` accepts ISO `YYYY-MM-DD` or an Excel serial date. `services/api/internal/validate/validate.go:113-119` emits AE-BR-04 otherwise. `docs/template-field-guide.md` documents the conversion, and `docs/status-lifecycle.md` permits a corrected invoice number after portal rejection.
- **Still needed:** confirm the four actual portal rejection records and check for other errors before sending a final customer reply. Do not escalate the documented input rule as a product outage.

## Live evidence commands when Docker becomes available

Run these in the cloned repository after `make up` and a clean Desert Rose import. Record actual execution times separately from the simulated reply times.

```bash
make load
make ps
docker compose logs --timestamps api web asp-mock > evidence/container-logs.txt
docker inspect invoicely-lite-api-1 --format '{{json .State}}' > evidence/api-container-state.json
curl -s http://localhost:8080/v1/imports?limit=500 > evidence/imports.json
```

In `make psql`, save both each query **and its output**:

```sql
SELECT s.name, i.id, i.filename, i.status, i.row_count, i.invoice_count,
       i.duration_ms, i.created_at, i.completed_at
FROM imports i JOIN sellers s ON s.id = i.seller_id
ORDER BY i.created_at;

SELECT s.name, v.invoice_number, v.id, v.import_id, v.status,
       v.rejected_by, v.asp_message_id, v.errors, v.updated_at
FROM invoices v JOIN sellers s ON s.id = v.seller_id
WHERE s.name IN ('Oasis Builders Supply LLC', 'Al Noor Fuel & Lubricants LLC',
                 'Sahara Medical Supplies FZE', 'Ghaf Tree Café LLC')
ORDER BY s.name, v.invoice_number, v.created_at;

SELECT v.invoice_number, e.status, e.detail, e.created_at
FROM invoice_events e JOIN invoices v ON v.id = e.invoice_id
ORDER BY v.invoice_number, e.id;
```

In Grafana, capture the dashboard's exact time range and panels for API restarts, memory, HTTP errors, queue depth, participant lookup latency, ASP 429 responses, and invoice outcomes. Log excerpts must retain timestamps and import/invoice IDs. Avoid including passwords or irrelevant full customer payloads.
