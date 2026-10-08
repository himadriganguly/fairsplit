# FairSplit

[![Test](https://github.com/himadriganguly/fairsplit/actions/workflows/test.yml/badge.svg)](https://github.com/himadriganguly/fairsplit/actions/workflows/test.yml)
![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)
![Dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/himadriganguly/fairsplit/blob/main/LICENSE)

A [Hermes Agent](https://hermes-agent.nousresearch.com) skill for splitting
group expenses and settling debts with the fewest possible payments. You
don't need an app, an account, or an API key.

If you already run an AI agent in your trip, flat, or team group chat, this
skill lets it handle shared expenses directly in the chat. Nobody has to
install another app or add the same five people again. For example:
"Alice paid ₹1000 for dinner, split evenly" logs the expense, and "Who owes
who?" returns the minimum number of payments that clears every balance.

---

## Contents

- [Why this exists](#why-this-exists)
- [Features](#features)
- [Requirements](#requirements)
- [Install](#install)
- [Configuration](#configuration)
- [Usage with Hermes](#usage-with-hermes)
- [Standalone CLI usage](#standalone-cli-usage)
- [Split types](#split-types)
- [Multi-currency expenses](#multi-currency-expenses)
- [Recording settle-up payments](#recording-settle-up-payments)
- [Recurring expenses](#recurring-expenses)
- [How settlement works](#how-settlement-works)
- [Data storage and format](#data-storage-and-format)
- [Privacy and security](#privacy-and-security)
- [Repo layout](#repo-layout)
- [Testing](#testing)
- [Publishing to the Skills Hub](#publishing-to-the-skills-hub)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Why this exists

Group-expense apps such as Splitwise and its clones assume that everyone
installs an app and creates an account. That is too much friction for many
real situations: a two-day trip, a one-off dinner, or a flatmates' group
where most people already talk to a bot in the chat.

FairSplit is a CLI and one JSON file per group. It works inside a
conversation your agent already has access to, and the data stays wherever
you put it (`fairsplit.data_dir`), on your machine or your server.

It's built for
[Hermes Agent's Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
(SKILL.md, references that load on demand, and config settings). The
ledger engine itself is plain standard-library Python, so it also works as
a standalone CLI without any agent.

## Features

| Feature | Details |
| --- | --- |
| **Four split types** | `equal`, `exact` amounts, weighted `shares`, and `percent`. See [Split types](#split-types). |
| **Net balances** | Each person's position in one number: owed, owes, or settled. |
| **Minimum-payment settlement** | At most `members - 1` payments instead of a pairwise list of IOUs. |
| **Multi-currency** | Log an expense in any currency with a manual rate. An optional keyless FX lookup (Frankfurter/ECB) can supply the rate. |
| **Exact money arithmetic** | All amounts are stored as integer minor units (cents/paise), so balances always sum to exactly zero. |
| **History and undo** | Filter expenses by person, category, or count. Remove a mistaken entry by id. |
| **Export** | A Markdown summary for pasting into chat, or CSV for spreadsheets. |
| **Works across platforms** | One ledger per group, whether the chat is on Telegram, Discord, Slack, or the Hermes CLI. |
| **Zero dependencies** | Python 3.8+ standard library only. No `pip install`. |

FairSplit is a ledger and a calculator, not a payments product. It does
**not** hold money, move real payments, connect to a payment processor, or
need an account. To settle up, someone still pays someone else the usual
way, and you then [record it](#recording-settle-up-payments).

## Requirements

- [Hermes Agent](https://hermes-agent.nousresearch.com) with the `terminal`
  toolset enabled, which the skill needs to run its script. Not needed for
  standalone CLI use.
- Python 3.8 or newer on the machine that runs the agent's terminal.
- Linux, macOS, or Windows.
- Network access only for the optional `fx` rate lookup. Everything else
  works offline.

## Install

The repo is laid out as a standard Hermes **tap**: the skill lives in
`skills/fairsplit/`. That is the path `hermes skills tap add` and Hub
discovery look in. They list the subdirectories of a tap's `skills/` path
and look for a `SKILL.md` in each.

**Option 1: add the tap.** The skill then shows up next to your other taps
and receives updates:

```bash
hermes skills tap add himadriganguly/fairsplit
hermes skills install fairsplit
```

**Option 2: install only this skill**, without subscribing to the tap:

```bash
hermes skills install himadriganguly/fairsplit/skills/fairsplit
```

**Option 3: install from [ClawHub](https://clawhub.ai/himadriganguly/skills/fairsplit)**:

```bash
hermes skills install clawhub/fairsplit
```

**Option 4: copy it manually** (no GitHub required):

```bash
git clone https://github.com/himadriganguly/fairsplit.git
cp -r fairsplit/skills/fairsplit ~/.hermes/skills/finance/fairsplit
```

Hermes loads skills at startup, so start a new session after installing.
To confirm the install, run `hermes skills list`, or type `/fairsplit` in a
chat. Hub-installed skills go through Hermes's security scanner. See the
[Skills System docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
for all install paths, including raw-URL installs.

### Other agents

FairSplit is written for Hermes, but the skill is a plain `SKILL.md` plus a
standard-library Python script, so other agents that read Agent Skills can
load it too:

```bash
# Claude Code, Codex, Cursor, and other agents supported by skills.sh
npx skills add himadriganguly/fairsplit

# OpenClaw
clawhub install fairsplit
```

Outside Hermes the `fairsplit.*` config prompts don't run. Set
`FAIRSPLIT_DATA_DIR` to choose where ledgers are stored; otherwise they go
to `~/.hermes/data/fairsplit`.

## Configuration

FairSplit declares two non-secret settings. Hermes asks for them on first
use and adds their values to the agent's context whenever the skill loads.

| Key | Default | Purpose |
| --- | --- | --- |
| `fairsplit.data_dir` | `~/.hermes/data/fairsplit` | Directory that holds one JSON ledger per group. Point it at a synced or backed-up folder if you want the data to survive machine changes. |
| `fairsplit.default_currency` | `USD` | ISO 4217 code used when you create a group without naming a currency. |

The skill tells the agent to pass both values to the script on every call
(`--data-dir`, `--currency`). When you run the script yourself, it falls
back to the `FAIRSPLIT_DATA_DIR` environment variable and then to
`~/.hermes/data/fairsplit`.

## Usage with Hermes

Talk to the agent normally. It loads the skill when it sees an
expense-splitting request, or you can invoke the skill directly with
`/fairsplit`:

```text
/fairsplit start a group called "Goa Trip" in INR with Alice, Bob, and Priya

Alice paid 1000 for dinner tonight, split evenly

Bob paid 2400 for the scooters. He used two, Alice and Priya one each

Priya paid $30 for museum tickets for all three of us, rate is 83.5

who owes who in the Goa Trip group?

Alice just paid Priya 736.67, record it

export the Goa Trip summary as markdown
```

Here is what the agent does with these messages:

- It always runs the bundled script for the arithmetic and never computes
  splits itself.
- It shows the per-person shares after every `add`, so you can catch a
  mistake before more expenses build on it.
- It asks one specific question when a split is ambiguous ("evenly, or
  does someone owe a different share?") instead of guessing.
- If the model can see images, it reads receipt photos and confirms the
  numbers with you before it records anything.
- It answers "who owes who" with the settlement plan, for example "Alice
  pays Priya 736.67", rather than a list of raw balances.

## Standalone CLI usage

Every command works without an agent. Run from the repo root:

```bash
LEDGER=skills/fairsplit/scripts/ledger.py

python3 $LEDGER init --group "Goa Trip" --currency INR --members "Alice,Bob,Priya"
python3 $LEDGER add --group "Goa Trip" --payer Alice --amount 1000 --description Dinner
python3 $LEDGER add --group "Goa Trip" --payer Bob --amount 2400 --description "Scooter rental" \
  --split shares --detail "Alice:1,Bob:2,Priya:1" --category transport
python3 $LEDGER add --group "Goa Trip" --payer Priya --amount 30 --currency USD --fx-rate 83.5 \
  --description "Museum tickets"
python3 $LEDGER settle --group "Goa Trip"
```

Real output:

```text
Added e1: Alice paid 1000.00 INR for "Dinner", split equal across Alice, Bob, Priya
  Alice: owes 333.34 INR
  Bob: owes 333.33 INR
  Priya: owes 333.33 INR
...
Settlement plan for 'Goa Trip' (2 payments):
  Alice pays Priya: 736.67 INR
  Alice pays Bob: 31.67 INR
```

### Command overview

| Command | Purpose |
| --- | --- |
| `init` | Create a group with a home currency and starting members. |
| `add` | Record one expense. New names are added to the group automatically. |
| `add-member` | Add someone with no expenses yet, so they appear in `balances`. |
| `balances` | Show each member's net position. |
| `settle` | Show the minimum-payment settlement plan. |
| `history` | List expenses. Filter with `--person`, `--category`, `--limit`. |
| `undo` | Delete an expense by id (`e1`, `e2`, ...). |
| `export` | Write a Markdown (`--format md`) or CSV (`--format csv`) file. |
| `list-groups` | List every group in the data directory. |
| `fx` | Best-effort live exchange-rate lookup. Optional. |

`--data-dir` is a global flag, so it goes before the subcommand. Every
command accepts `--help`. The full flag reference is in
[`skills/fairsplit/references/cli-reference.md`](skills/fairsplit/references/cli-reference.md).

Errors go to stderr with a non-zero exit code. Invalid input never
produces a stack trace, and nothing is written to the ledger when a
command fails.

## Split types

| Type | Flag | Example | Behaviour |
| --- | --- | --- | --- |
| Equal | `--split equal` (default) | — | Splits the amount evenly. Leftover cents go one at a time to participants in alphabetical order, so the result is reproducible. ₹1000 / 3 → 333.34, 333.33, 333.33. |
| Exact | `--split exact` | `--detail "Alice:300,Bob:450,Priya:250"` | Uses the named amounts. They must add up to the total exactly, or the command fails. |
| Shares | `--split shares` | `--detail "Alice:1,Bob:2,Priya:1"` | Splits in proportion to the weights. The last participant listed takes the rounding remainder. |
| Percent | `--split percent` | `--detail "Alice:60,Bob:40"` | Works like shares. Weights are normalized, but should add up to 100. |

Leave out `--participants` to split across the whole group. To split among
a subset, list them: `--participants "Alice,Bob"`. Names are
case-sensitive.

## Multi-currency expenses

Each group has one **home currency**. Balances and settlement are always
calculated in it. To log an expense paid in another currency, give the
rate as home-currency units per 1 unit of the foreign currency:

```bash
python3 $LEDGER add --group "Goa Trip" --payer Priya --amount 30 \
  --currency USD --fx-rate 83.5 --description "Museum tickets"
# Added e3: Priya paid 2505.00 INR ... (converted from 30.00 USD at rate 83.5)
```

The original amount, currency, and rate are kept on the expense record.
To fetch a current rate instead of entering one:

```bash
python3 $LEDGER fx --base USD --quote INR
```

The `fx` command calls the free, keyless
[Frankfurter](https://frankfurter.dev) API (ECB reference rates). If there
is no network access or the currency isn't covered, it fails with a clear
error and you can enter the rate manually.

## Recording settle-up payments

When someone pays back what they owe, record it as an expense **paid by
the sender**, with the **recipient as the only participant**:

```bash
python3 $LEDGER add --group "Goa Trip" --payer Alice --amount 736.67 \
  --participants Priya --description "Settle-up" --category settlement
```

Both balances move toward zero, and `settle` then shows only what is still
outstanding.

## Recurring expenses

FairSplit doesn't schedule anything itself. For rent or subscriptions, use
Hermes's own cron:

```bash
hermes cron create \
  --schedule "0 9 1 * *" \
  --prompt "Use the fairsplit skill: add this month's rent (₹30000, equal split) to the 'Flat 4B' group, then post the current settle-up plan to this chat." \
  --skill fairsplit
```

## How settlement works

All expenses are combined into one net balance per person. A greedy
algorithm then repeatedly matches the largest creditor with the largest
debtor and settles the smaller of the two amounts. Every step clears at
least one person, so the plan never has more than `n - 1` payments for `n`
people.

Finding the absolute minimum number of payments in every case is
NP-hard. This greedy approach is the practical standard that
expense-splitting apps use. Integer minor units mean balances always sum
to exactly zero, with no floating-point drift. The full explanation and a
worked example are in
[`skills/fairsplit/references/settlement-algorithm.md`](skills/fairsplit/references/settlement-algorithm.md).

## Data storage and format

Each group is stored as one human-readable JSON file:
`<data_dir>/<group-slug>.json`. For example, "Goa Trip" becomes
`goa-trip.json`. Writes are atomic: the script writes a temp file and then
renames it, so a crash can't leave a half-written ledger.

```json
{
  "group": "Goa Trip",
  "currency": "INR",
  "members": ["Alice", "Bob", "Priya"],
  "next_id": 2,
  "created_at": "2026-10-08T11:30:02",
  "expenses": [
    {
      "id": "e1",
      "date": "2026-10-08",
      "payer": "Alice",
      "description": "Dinner",
      "category": "general",
      "amount_minor": 100000,
      "currency": "INR",
      "original_amount_minor": 100000,
      "original_currency": "INR",
      "fx_rate": null,
      "participants": ["Alice", "Bob", "Priya"],
      "split_type": "equal",
      "split_detail": null,
      "shares_minor": { "Alice": 33334, "Bob": 33333, "Priya": 33333 },
      "created_at": "2026-10-08T11:30:02"
    }
  ]
}
```

`*_minor` fields are integers in hundredths of the currency unit. To back
up or move a group, copy its file. Avoid editing it by hand: if you do and
the balances stop adding up to zero, `balances` prints a warning.

## Privacy and security

- **Your data stays local.** Ledgers are stored only in `fairsplit.data_dir`.
  Nothing is uploaded anywhere.
- **One optional network call.** `fx` sends a read-only GET request with
  two currency codes to Frankfurter. No ledger data, names, or amounts are
  sent. Currency codes are validated before the URL is built.
- **No secrets.** The skill uses no API keys, tokens, or environment
  credentials.
- **No shell-outs.** The script never runs other programs and only writes
  inside the data directory and the `export --out` path you choose.
- **Group names are slugified** before they become file names, so a group
  name can't escape the data directory.

## Repo layout

```text
fairsplit/                              # tap root
├── skills/
│   └── fairsplit/                      # the installable skill
│       ├── SKILL.md                    # agent instructions + frontmatter (start here)
│       ├── scripts/
│       │   └── ledger.py               # the whole engine, stdlib only
│       ├── references/                 # loaded on demand by the agent
│       │   ├── cli-reference.md        # full flag reference
│       │   └── settlement-algorithm.md # how settle() works, why integer cents
│       └── examples/
│           └── stress_test.py          # 200-expense randomized regression test
├── tests/
│   └── validate_skill.py               # Hub pre-publish checks for SKILL.md
├── .github/workflows/test.yml          # CI on Linux, macOS, Windows
├── skills.sh.json                      # skills.sh directory grouping
├── README.md
└── LICENSE                             # MIT
```

The extra `skills/` level is required by Hermes's tap-discovery
convention. See "Publishing a custom skill tap" in the
[Skills System docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills).

## Testing

Both checks use only the standard library. Run them from the repo root:

```bash
# SKILL.md metadata: name, description of 60 chars or less, semver,
# no broken file references
python3 tests/validate_skill.py

# Ledger engine: 200 random expenses with mixed split types across 5 people
python3 skills/fairsplit/examples/stress_test.py
```

The stress test checks that balances sum to *exactly* zero in integer
minor units and that settlement never needs more than `members - 1`
payments. It uses a temporary directory and leaves nothing behind. CI runs
both checks on Linux, macOS, and Windows for every push and pull request.

## Publishing to the Skills Hub

Before you publish or tag a release:

1. Bump `version` in `skills/fairsplit/SKILL.md` (semver).
2. Run both test commands above. They must pass.
3. Keep `description` to one sentence of 60 characters or less, ending
   with a period. The Hub index truncates at about 57 characters, so the
   key point must come first.
4. Push to `main` and tag the release (`git tag v1.0.1 && git push --tags`).
   GitHub installs, Hermes taps, and skills.sh all read straight from the
   repo, so nothing else is needed for them.
5. Publish the new version to [ClawHub](https://clawhub.ai/himadriganguly/skills/fairsplit):

   ```bash
   clawhub publish skills/fairsplit --slug fairsplit --name FairSplit \
     --version <version> --changelog "<what changed>" \
     --source-repo himadriganguly/fairsplit --source-path skills/fairsplit
   ```

Hub installs are security-scanned. Keep `ledger.py` free of shell-outs,
dynamic code execution, and network calls other than the documented `fx`
lookup, so it stays a clean community-tier install.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `error: No group called '...'` | Wrong name, or a different `--data-dir`. Run `list-groups` and check the data directory. |
| `error: exact amounts sum to X but the expense total is Y` | The `exact` amounts must add up to the total to the cent. Correct the figure that's wrong. |
| `error: expense is in USD but group currency is INR` | Add `--fx-rate`, or fetch one with `fx`. |
| `error: could not fetch a live rate` | No network or the currency isn't covered. Pass `--fx-rate` manually. |
| A person shows up twice with different spelling | Names are case-sensitive. `undo` the bad entries and add them again with the correct spelling. |
| `warning: balances do not sum to zero` | The JSON file was edited by hand. Restore it from a backup or fix the record. |
| The agent doesn't use the skill | Start a new Hermes session (skills load at startup), and check that the `terminal` toolset is enabled. |

## Contributing

Issues and PRs are welcome. FairSplit was built to fill a real gap: the
expense-splitting tools in the agent-skills ecosystem either depend on an
external app or API, or are a prompt with no arithmetic engine behind
them. It isn't finished. Contributions that would help:

- Itemized receipt splitting: assign line items to people and distribute
  tax and tip proportionally
- A built-in recurring-expense helper, instead of the documented `hermes
  cron create` call
- An `edit` command, instead of undo plus re-add
- Currencies with 0 or 3 minor-unit digits (JPY, KWD); the engine
  currently assumes 2
- Ports of the data format and CLI to other agent-skill runtimes (both are
  framework-agnostic)

Please keep `scripts/ledger.py` stdlib-only, since zero install friction is
half the point. Run both checks in [Testing](#testing) before you open a PR.

## License

MIT. See [`LICENSE`](LICENSE).
