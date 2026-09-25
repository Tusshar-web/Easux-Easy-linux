# Easux - Easy linux

> **MVP specification for a safe, fast command companion for Bash and Zsh.**

**Easeux** augments, rather than replaces, your shell. It delivers instant local completion (< 80 ms p95), context-aware suggestions, opt-in natural-language command generation, plain-language command explanations, error-aware repair, personal history ranking, and a strict safety gate before risky execution.

The assistant is built **local-first**: local completion and history-based suggestions operate completely offline with zero network latency. The LLM is invoked only for explicit natural-language requests, explanations, and error repairs—and it **never** executes a generated command automatically.

---

## Key Features

- ⚡ **Instant Local Autocomplete (`ai complete`)**:
  - Predicts subcommands, flags, and paths on <kbd>Tab</kbd> with **p95 latency under 80 ms**.
  - Operates completely offline with zero network requests.
  - Curated adapters for `git`, `npm`, `pip`, `docker`, `make`, and native filesystem paths.
  - Bash and Zsh native completion integration.

- 💡 **Context-Aware Smart Suggestions (`ai suggest`)**:
  - Displays up to 5 ranked, explainable commands based on current directory context, project manifests (`package.json`, `pyproject.toml`, `Makefile`), git status (dirty, ahead/behind), and personal history.
  - Inserts the selected command into the shell editing buffer rather than executing directly.

- 🛡️ **Natural-Language Command Generation with Safety Gate (`ai <task>`)**:
  - Translates natural-language intent into an inspectable shell command (e.g. `ai find Python files modified in the last 7 days`).
  - Classifies commands into `low`, `medium`, `high`, and `blocked` risk levels.
  - **Never auto-runs**: user chooses `[Enter] insert`, `[r] run`, `[e] edit`, or `[q] cancel`.
  - High-risk operations (e.g., `sudo`, `rm -rf`, force-push) require an explicit secondary confirmation.

- 📖 **Safe Command Explanation (`ai explain <command>`)**:
  - Explains arbitrary pasted commands with breakdown of flags and effects (e.g. `ai explain tar -xzf archive.tgz`).
  - **Never executes** the command while explaining.
  - Recommends safer variants where available.

- 🔧 **Error-Aware Repair (`ai fix`)**:
  - Automatically captures post-command exit status and bounded redacted error excerpts.
  - User explicitly opts in to send the excerpt for diagnosis.
  - Proposes safe next steps (e.g., handling git non-fast-forward push rejections).

- 🔒 **Privacy & Redaction Engine**:
  - Automatically redacts API keys, tokens, private keys, bearer tokens, and passwords from logs and outbound payloads.
  - SQLite local database stores preferences, events, and history-derived scores with a configurable retention policy (90 days for events, 7 days for errors).
  - Clear and export commands: `ai history clear` and `ai data export`.

---

## Architecture Overview

```
                      +-----------------------------+
                      |         User Terminal       |
                      |         (Bash / Zsh)        |
                      +--------------+--------------+
                                     |
              +----------------------+----------------------+
              |                      |                      |
     [Tab Autocomplete]      [Ctrl-G / ai suggest]    [ai <task> / ai fix]
              |                      |                      |
              v                      v                      v
     +-----------------+    +-----------------+    +-----------------+
     |   Tokenizer     |    | ProjectDetector |    | Safety Engine   |
     | TokenClassifier |    | Git / Manifests |    | Risk Classifier |
     +--------+--------+    +--------+--------+    | Redaction Engine|
              |                      |             +--------+--------+
              +----------+-----------+                      |
                         |                                  v
                         v                         +-----------------+
              +--------------------+               | LLM Provider    |
              | Deterministic      |               | OpenAI / Local /|
              | Weighted Ranker    |               | Offline Fallback|
              +----------+---------+               +-----------------+
                         |
                         v
              +--------------------+
              | SQLite State &     |
              | History Events     |
              +--------------------+
```

---

## Installation & Setup

### 1. Requirements
- Linux (x86_64 / arm64) with **Bash 4+** or **Zsh**
- Python 3.10+
- SQLite 3

### 2. Install Local Package
```bash
git clone https://github.com/Easux/ai-terminal.git
cd ai-terminal
pip install -e .
```

### 3. Activate Shell Integration

#### For Bash:
Add the following to your `~/.bashrc`:
```bash
eval "$(ai shell init bash)"
```
Or run the automatic installer:
```bash
ai shell install bash
```

#### For Zsh:
Add the following to your `~/.zshrc`:
```bash
eval "$(ai shell init zsh)"
```
Or run the automatic installer:
```bash
ai shell install zsh
```

Restart your shell or reload configuration (`source ~/.bashrc`).

---

## CLI Reference

### 1. Autocomplete (`ai complete`)
Invoked automatically on <kbd>Tab</kbd> via shell hooks or manually:
```bash
ai complete --shell bash --buffer "git che" --cursor 7
# Output:
# checkout
# cherry
# cherry-pick

# Structured JSON output:
ai complete --shell bash --buffer "git che" --cursor 7 --json
```

### 2. Context Suggestions (`ai suggest`)
Invoked via `ai suggest` or <kbd>Ctrl-G</kbd>:
```bash
$ cd ~/projects/web-app
$ ai suggest
1. npm run dev       Found scripts.dev in package.json
2. npm test          Found scripts.test in package.json
3. git status        Repository has modified files
Select [1–3, q]: 1
Inserted: npm run dev
```

### 3. Natural Language Queries (`ai <task...>`)
```bash
$ ai find Python files modified in the last 7 days

Suggested command: find . -type f -name "*.py" -mtime -7
Why: Finds regular Python files below the current directory changed in seven days.
Assumptions: Search starts in the current directory.
Risk: low
Alternatives: find . -name "*.py" -ctime -7, git log --name-only --since="7 days ago"

[Enter] insert  [r] run  [e] edit  [q] cancel
```

### 4. Command Explanation (`ai explain`)
```bash
$ ai explain tar -xzf archive.tgz

Command: tar -xzf archive.tgz
Explanation: The tar command extracts files (-x), decompresses gzip (-z), reads from specified archive file (-f).
Effects: Extracts archive content into the current working directory without modifying the archive itself.
Risk: low
Safer variant: tar -tvf archive.tgz
```

### 5. Error Repair (`ai fix`)
```bash
$ git push origin main
! [rejected] main -> main (non-fast-forward)

$ ai fix
Send the redacted error excerpt to the configured LLM? [y/N]: y

Likely cause: The remote branch contains commits not in your local branch.
Safe next step: git pull --rebase origin main
Risk: medium — rewrites local commits during rebase if conflicts require resolution.

[Enter] insert  [e] edit  [q] cancel
```

### 6. Diagnostics & Verification (`ai doctor`)
Verify that local database, shell hooks, latency, and providers meet the PRD specifications:
```bash
$ ai doctor
ai-terminal v0.1.0 Diagnostics

  Python version: 3.14.4
  SQLite database: OK (~/.local/share/ai_terminal/ai_terminal.db)
  Local completion latency: PASS (16.13 ms, target < 80 ms)
  Bash hook: installed in ~/.bashrc
  Zsh hook: not installed in ~/.zshrc
  LLM Provider: OfflineHeuristicProvider

System check complete.
```

### 7. Configuration & Privacy
```bash
# View configuration
ai config list

# Set LLM model or endpoint
ai config set model "gpt-4o-mini"
ai config set retention_days 90

# View history stats
ai history stats

# Purge local history and caches
ai history clear

# Export data in JSON
ai data export
```

---

## Configuration Variables

| Key | Default | Description |
|---|---|---|
| `provider` | `auto` | LLM provider: `auto`, `openai`, `offline` |
| `model` | `gpt-4o-mini` | Model identifier |
| `api_key_env` | `AI_TERMINAL_API_KEY` | Environment variable name storing the API key |
| `retention_days` | `90` | Days to retain command events |
| `error_retention_days` | `7` | Days to retain error logs |
| `privacy_mode` | `least_context` | Context minimization level |
| `weight_prefix` | `45` | Score weight for token prefix matching (0-45) |
| `weight_context` | `25` | Score weight for repository/manifest context (0-25) |
| `weight_recency` | `15` | Score weight for command recency (0-15) |
| `weight_frequency` | `10` | Score weight for command frequency (0-10) |
| `weight_source` | `5` | Score weight for adapter source confidence (0-5) |

---

## Running the Automated Test Suite

The test suite validates ranking, tokenization, redaction, safety policies, SQLite storage, CLI subcommands, and performance benchmarks:
```bash
python3 -m pytest -v
```

---

## License
MIT License
