# Alfred GitHub CLI Workflow

A fast, lightweight Alfred 5 workflow for searching GitHub and navigating repositories, pull requests, issues, and organizations, powered by **pure Python 3** and the **GitHub CLI (`gh`)**.

## Features

- **Zero-Dependency Python**: Built entirely with Python 3 standard library (`sqlite3`, `subprocess`, `json`, `dataclasses`). Runs cleanly without external packages or virtual environments.
- **Native macOS Execution**: Direct execution via macOS's native Python runtime, avoiding binary quarantine or Gatekeeper friction.
- **Automatic Authentication**: Seamlessly inherits your existing `gh auth` credentials. No manual Personal Access Tokens or local OAuth servers needed.
- **Instant Response Times**: Cached in local SQLite with Write-Ahead Logging (WAL) and automatic background synchronization.
- **Deep Repository Navigation**: Jump directly into pull requests, issues, actions, commits, releases, discussions, or settings.

---

## Prerequisites

1. **GitHub CLI (`gh`)**:
   ```bash
   brew install gh
   gh auth login
   ```
2. **Python 3**: Included by default on macOS (or installed via Xcode CLI tools).

---

## Usage

| Query | Action |
| :--- | :--- |
| `gh <search>` | Instant search across your own, organization, and starred repositories |
| `gh <repo> ` | Deep navigation (pulls, issues, actions, commits, branches, releases, settings) |
| `gh my pulls` | View and open your Pull Requests |
| `gh my issues` | View and open your assigned Issues |
| `gh my stars` | Browse and open your Starred Repositories |
| `gh @<user>` | Filter repositories by user or organization |
| `gh s <query>` | Global search on GitHub.com |
| `gh > refresh` | Force refresh the local repository cache |
| `gh > clear-cache` | Clear the local SQLite cache |

### Keyboard Modifiers
When viewing search results:
- **`Enter`**: Open repository in default browser.
- **`⌘ + Enter`**: Open repository's **Pull Requests** page.
- **`⌥ + Enter`**: Open repository's **Issues** page.
- **`Tab`**: Autocomplete repository name and reveal deep navigation subcommands.

---

## Development

```bash
# Run test suite
uv run pytest

# Lint and format
uv run ruff check .
```

### Linking to Alfred for Local Testing
```bash
./scripts/link-alfred.sh
```

---

## License
MIT
