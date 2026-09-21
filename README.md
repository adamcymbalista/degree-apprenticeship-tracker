# Degree Apprenticeship Tracker

Scans UK degree apprenticeship sources once a day, scores every vacancy
against your interests, stores everything in SQLite, and emails you:

- a **weekly digest** (new/opened/closing-soon opportunities), and
- an **emergency alert** the same day a high-match (score ≥ 75) vacancy opens.

Built for one specific profile (London, Level 6, September 2027, CS/software/
data/cyber, with bonus interest in sport/crime/security/transport tech) but
everything about that profile lives in `config.yaml`, not in code.

## What it does, and doesn't, do

It currently scrapes **findapprenticeship.service.gov.uk** (the official DfE
service) reliably, and any employer/university careers page that publishes
schema.org `JobPosting` structured data (most large ATSs do - Workday,
SuccessFactors, Greenhouse, etc.). UCAS's apprenticeship search is a
client-side app with no public API, so that source is a documented no-op
rather than a fake scraper - see **Known limitations** below.

Status is only ever reported as `OPEN` when a source gave real evidence for
it (an active listing, a JobPosting's presence, explicit dates) - never
guessed from "the page exists". Nothing is invented: a field a source
doesn't provide is stored as `None`/"Unknown".

## How scoring works

`app/scoring.py` is a plain, transparent point system (0-100), not an AI
judgement - every point added or removed is recorded in `score_reasons` so
the weekly email can explain *why* something scored well. Two hard rules
override everything else:

- **not London** → score forced to -100 (`MATCH_CATEGORY = EXCLUDED`)
- **below Level 6** → score forced to -100 (`EXCLUDED`)

Above that: +25 London, +20 Level 6, +15 starts 2027, +15 CS/software
subject, +10 programming content, +10 data/AI/cyber, +8 algorithms, +8 each
for a *technical* combination with sport/crime-security/transport, +5 maths
modelling, +5 Python, +5 strong technical degree content. Penalties: -50
wrong start year, -30 IT support / business-HR-marketing / pure finance.

Scores map to `MATCH_CATEGORY`: EXCEPTIONAL_MATCH (≥85), STRONG_MATCH (≥70),
GOOD_MATCH (≥50), POSSIBLE_MATCH (≥25), LOW_MATCH, or EXCLUDED. Change any
weight in `app/scoring.py` - it's one function, `score_vacancy`.

## Install locally

```bash
git clone <your-repo-url>
cd degree-apprenticeship-tracker
pip install -r requirements.txt
```

Requires Python 3.10+.

## Configure email

Uses SMTP via environment variables (never put credentials in `config.yaml`
or commit them):

```bash
export EMAIL_HOST=smtp.gmail.com
export EMAIL_PORT=587
export EMAIL_USERNAME=you@gmail.com
export EMAIL_PASSWORD=your-gmail-app-password   # not your normal password - see below
export EMAIL_FROM=you@gmail.com
export EMAIL_TO=you@gmail.com
```

For Gmail: enable 2-Step Verification, then create an **App Password**
(Google Account → Security → App passwords) and use that as
`EMAIL_PASSWORD`. Any other STARTTLS SMTP provider works by changing
`EMAIL_HOST`/`EMAIL_PORT`.

## Run it

```bash
python -m app.main --dry-run      # fetch + score, print top matches, write NOTHING
python -m app.main --test-email   # send yourself a test email to check SMTP config
python -m app.main --daily        # the real daily scan: detect changes, maybe send emergency email
python -m app.main --weekly       # force-send the weekly digest right now
```

First `--daily` run populates the database as a baseline and sends **no**
emergency emails for vacancies that already existed - alerts only fire for
changes detected *after* that baseline.

The database path defaults to `tracker.db` in the project root; override
with `TRACKER_DB_PATH`. Config path defaults to `config.yaml`; override with
`TRACKER_CONFIG`.

## Run tests

```bash
python -m unittest discover -s tests
```

45 tests, all offline (fixtures + mocked HTTP, no live requests). `pytest`
also works if you have it installed (`pytest tests/`) - the tests are plain
`unittest.TestCase`s, which pytest runs natively.

## GitHub Actions (automatic daily run)

`.github/workflows/daily_tracker.yml` runs every day at 07:00 UTC (and via
"Run workflow" in the Actions tab). Add these **repository secrets**
(Settings → Secrets and variables → Actions → New repository secret):

```
EMAIL_HOST
EMAIL_PORT
EMAIL_USERNAME
EMAIL_PASSWORD
EMAIL_FROM
EMAIL_TO
```

The workflow needs `contents: write` permission (already set) so it can
commit the updated `tracker.db` back to the repo after each run - see
**Known limitations** for why, and the tradeoff.

## Adding another website (source)

Every source is a module under `app/sources/` with one function:
`fetch(config: dict) -> list[Vacancy]`. Add a new file, implement `fetch`,
and register it in `SOURCE_MODULES` in `app/main.py`. Reuse `app.http_client.get`
for rate-limited, robots.txt-respecting requests. If the site exposes an
API/feed, prefer it over HTML scraping.

## Adding another employer

If the employer's careers site publishes JSON-LD `JobPosting` data (check
page source for `<script type="application/ld+json">`), just add it to
`employers_seed` in `config.yaml`:

```yaml
employers_seed:
  - name: "Some Company"
    careers_url: "https://example.com/careers/apprenticeships"
```

No code change needed. If they don't publish structured data, `app/sources/employers.py`
will log that and return nothing for that page rather than guessing - you'd
need a bespoke parser (a new source module) for that employer.

## Changing interests / scoring

- **Interests, London terms, subjects, entry year, minimum score for
  emergency alerts**: edit `config.yaml`. No Python required.
- **Scoring weights/logic**: edit `app/scoring.py` (`score_vacancy`). Every
  weight is a plain `+N`/`-N` in that one function.

## Security considerations

- Credentials are read only from environment variables / GitHub Secrets,
  never from `config.yaml` or hardcoded. `.gitignore` excludes `.env` and
  logs.
- The scraper identifies itself with a descriptive User-Agent, respects
  `robots.txt`, rate-limits requests per host, and backs off on HTTP 429.
  It never bypasses CAPTCHAs, logins, or anti-bot systems - a source that
  blocks it is marked unavailable for that run, logged, and skipped.
- The committed SQLite database contains only publicly-listed vacancy data
  (titles, employers, URLs, dates) - no credentials or personal data beyond
  what you configure in `EMAIL_TO`, which stays in Secrets, not the DB.

## Known limitations

- **UCAS** (`app/sources/ucas.py`) is a documented no-op: its search page
  loads results client-side from a private Algolia index with no public
  API, so it can't be reliably scraped with plain HTTP requests. Find an
  Apprenticeship already carries the same official vacancies.
- **Employer/university pages** only work when the page publishes schema.org
  `JobPosting` structured data. Several career pages guessed for the seed
  list (BT, TfL, QMUL, Greenwich, Open University) returned 404s or
  unknown structure when last checked - **verify and fix these URLs before
  relying on them** (`config.yaml` → `employers_seed`, and
  `app/sources/qmul.py` → `UNIVERSITY_PAGES`). They're wired up and will
  silently log "no results" rather than break anything if left as-is.
- **findapprenticeship.service.gov.uk has no public read API.** DfE's
  Recruitment/Display Advert APIs exist but require registering as an
  employer/training provider, or self-registering for a Display-Advert-only
  key, neither of which this tool can do on your behalf. The scraper in
  `app/sources/findapprenticeship.py` uses the public search HTML instead,
  anchored on the stable `/apprenticeship/VAC<id>` URL pattern rather than
  CSS classes so it degrades gracefully (skips one bad listing, never
  crashes) if the site's markup changes. **Verified against the live site**
  (not just a fixture): correctly pulls title, employer, location, level,
  wage, dates and a real vacancy count (149 stored on a live test run).
  The site's own search box does exact-phrase matching, not topic search -
  `config.yaml`'s `subjects` list is deliberately short, broad, single
  words for that reason (see the comment there).
- **SQLite-in-repo persistence**: GitHub Actions runners are ephemeral, so
  the workflow commits `tracker.db` back to the repo after every run. This
  is the simplest reliable option for a first version, but it means every
  daily run adds a commit, and concurrent runs could conflict (unlikely at
  once-a-day). If that becomes a problem, swap `TRACKER_DB_PATH` for a
  Postgres/Supabase connection in `app/database.py` (schema is plain SQL,
  porting is mostly changing `sqlite3.connect` to a `psycopg2`/Supabase
  client and `?` placeholders to `%s`) and drop the "commit database" step
  from the workflow.
- **Deduplication** is fuzzy-matched on (employer, normalised title, start
  year) using `difflib` - good enough for a few hundred vacancies/day, but
  it can occasionally merge two genuinely different roles with near-identical
  titles at the same employer, or miss a match if the same role has a
  substantially reworded title across two sources. Check `also_seen_on` in
  a vacancy's `raw_source_data` if a merge looks wrong.
