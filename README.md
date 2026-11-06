# Degree Apprenticeship Tracker

A Python tool that checks UK degree apprenticeship listings every day, scores
each one against a personal profile, remembers what it has seen in SQLite, and
emails me when something relevant opens.

I'm a Year 12 A-level student (Maths, Further Maths, Computer Science)
applying for September 2027 degree apprenticeships in London. Good listings
open and close within weeks and are spread across several sites, so I built
something to watch them for me.

- **Weekly digest** (Mondays): new listings, newly opened applications,
  deadlines coming up, and high-match roles still open.
- **Emergency alert**: sent the same day a high-match vacancy opens. The score
  threshold is `minimum_score_for_emergency` in `config.yaml` (currently 60).

It runs unattended on GitHub Actions at 07:17 UTC every day.

## How it works

```
fetch sources -> normalise -> deduplicate -> score -> compare with DB
      -> detect new / newly opened / changed -> store -> send emails
```

| Source | How | Status |
|---|---|---|
| Find an Apprenticeship (gov.uk) | HTML scrape, anchored on the stable `/apprenticeship/VAC<id>` URL pattern rather than CSS classes | Working |
| ApprentiFinder | Public JSON endpoint its own site uses (`/api/opportunities`); `robots.txt` allows it | Working |
| Employer / university careers pages | Generic scraper for schema.org `JobPosting` data | Working in principle; several seed URLs are dead or bot-blocked (see limitations) |
| UCAS | Client-rendered app with no public API | Deliberately a no-op, not faked |

Design rules I held it to:

- **Never invent data.** A field a source doesn't provide is stored as unknown.
  A vacancy is only `OPEN` when the source gave real evidence (an active
  listing, explicit dates), never because "the page exists".
- **One failing source never stops the run.** Failures are logged and the rest
  carry on.
- **Be a polite client.** Real User-Agent, per-host rate limiting, `robots.txt`
  respected, back-off on HTTP 429, no CAPTCHA or login bypassing.
- **No duplicate alerts.** Alert history lives in the database, and the first
  run only builds a baseline instead of emailing about everything already open.

## Scoring

`app/scoring.py` is a plain, transparent 0-100 point system. It is not an AI
judgement. Every point added or removed is recorded in `score_reasons`, which
is how the emails explain *why* something matched.

Two hard exclusions override everything else (score forced to -100,
`EXCLUDED`):

- not London-based
- below Level 6

Otherwise: +25 London, +20 Level 6, +15 starts 2027, +15 CS/software subject,
+10 programming, +10 data/AI/cyber, +8 algorithms/optimisation, +8 each for a
*technical* role combined with sport, crime/security or transport, +5
mathematical modelling, +5 Python, +5 strong technical degree content, +5
partnered with Queen Mary University of London. Penalties: -50 wrong start
year, -30 for IT support, business/HR/marketing or pure finance roles.

Interest combinations only count when the vacancy has real technical content
alongside them. A generic admin job at an airline is not "computer science +
aviation".

Scores map to `EXCEPTIONAL_MATCH` (85+), `STRONG_MATCH` (70+), `GOOD_MATCH`
(50+), `POSSIBLE_MATCH` (25+), `LOW_MATCH`, or `EXCLUDED`.

## Project layout

```
app/
  main.py            CLI entrypoint and orchestration
  models.py          Vacancy dataclass, status and match-category enums
  database.py        SQLite schema and queries
  scoring.py         Transparent scoring and tagging
  deduplication.py   Fuzzy cross-source matching
  status.py          Status transitions (closed -> open, etc.)
  alerts.py          Emergency selection and weekly grouping
  email.py           SMTP + HTML email rendering
  http_client.py     Rate limiting, robots.txt, retries
  sources/           One module per source, each returning Vacancy objects
tests/               55 offline tests (fixtures, no live requests)
config.yaml          Interests, London terms, entry year, thresholds
.github/workflows/   Daily scheduled run
```

## Run it locally

```bash
git clone https://github.com/adamcymbalista/degree-apprenticeship-tracker.git
cd degree-apprenticeship-tracker
pip install -r requirements.txt          # Python 3.10+

python -m app.main --dry-run      # fetch + score, print top matches, write nothing
python -m app.main --test-email   # check your SMTP settings
python -m app.main --daily        # the real scan
python -m app.main --weekly       # force-send the weekly digest
```

Email uses SMTP via environment variables, never `config.yaml`:
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_FROM`,
`EMAIL_TO`. For Gmail, use an App Password (needs 2-Step Verification on).

Run the tests:

```bash
python -m unittest discover -s tests
```

## Deploying on GitHub Actions

`.github/workflows/daily_tracker.yml` runs daily and can be triggered by hand
from the Actions tab, with a mode picker (`daily`, `weekly`, `test-email`). Add
the six `EMAIL_*` values as repository secrets.

Actions runners are ephemeral, so the workflow commits the updated `tracker.db`
back to the repo after each run. That's the simplest reliable option for a
single-user project. The trade-off is one small commit per day; moving to
Postgres/Supabase would remove that.

## Customising

- **Interests, London terms, entry year, alert threshold:** edit `config.yaml`.
- **Scoring weights:** edit `score_vacancy` in `app/scoring.py`.
- **A new website:** add a module under `app/sources/` with
  `fetch(config) -> list[Vacancy]` and register it in `SOURCE_MODULES` in
  `app/main.py`.
- **A new employer:** if their careers page publishes `JobPosting` JSON-LD, add
  it to `employers_seed` in `config.yaml`. No code needed.

## Things I learned from running it on the real sites

The first version passed its tests and found nothing at all. Running it against
live sites showed why:

1. **`robots.txt` was blocking everything.** Python's `urllib.robotparser`
   fetches `robots.txt` with a generic User-Agent, which the gov.uk firewall
   rejects with a 403, and the parser treats a 403 as "disallow everything". The
   fix was to fetch `robots.txt` with the tool's own User-Agent.
2. **The search is exact-phrase, not topical.** "computer science" returns 0
   results on Find an Apprenticeship while "software" returns dozens, so the
   search terms are short single words and the real filtering happens in the
   scorer.
3. **The listing URL pattern was wrong.** I had assumed
   `/apprenticeship/reference/<id>`; the real one is `/apprenticeship/VAC<id>`.
   Reading the raw HTML the live site returned showed it.
4. **Inline tags split field labels from their values**, breaking date parsing,
   so the parser reads whole `<p>` elements instead of flattening text.
5. **GitHub can silently drop scheduled runs at the top of the hour**, which is
   why the cron is `17 7 * * *` and not `0 7 * * *`.

## Known limitations

- **UCAS** has no public API and is not scraped.
- **Some employer/university seed URLs are dead or bot-blocked** (BT, Greenwich,
  Open University, TfL). They're logged as unavailable and skipped.
- **QMUL's site is course information, not a vacancy feed**, so there is
  nothing to scrape there. QMUL-partnered roles are picked up through
  ApprentiFinder's training-provider field instead.
- **Find an Apprenticeship has no public read API**, so this scrapes its public
  search HTML. It's built to skip a bad listing rather than crash, but a site
  redesign could still break parsing.
- **Deduplication** is fuzzy (employer, normalised title, start year via
  `difflib`). It can occasionally merge two different roles with near-identical
  titles.
- **The database lives in the repo.** See the deployment note above.

## How this was built

I built this with Claude (Anthropic's AI assistant), and I want to be clear
about who did what.

- **What I did:** defined the problem and requirements (what to track, the
  London / Level 6 / 2027 criteria, the scoring weights and how my interests
  should affect ranking); chose which sources to add (ApprentiFinder, QMUL);
  set up the GitHub repository, secrets and Actions schedule; ran it against
  the live sites on my own machine; and fed back the logs that exposed the bugs
  above.
- **What Claude did:** wrote most of the Python code, the tests and the first
  draft of this documentation, working from my spec.

The commit history reflects this, with Claude credited as co-author.
