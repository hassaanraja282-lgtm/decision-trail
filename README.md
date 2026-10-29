# Decision Trail

**Stop re-litigating decisions.** Decision Trail is an Atlassian Forge app for Jira that captures the decisions your team makes, surfaces them on related work, and warns when a new decision contradicts an old one. A Rovo agent, **Decision Keeper**, answers "did we already decide this?" in plain language.

Built for Codegeist 2026 (Apps for Software Teams, Best Agents bonus).

## The problem
Teams make decisions in comments, meetings and Slack threads, then forget them. Months later someone reopens the same debate, or ships something that quietly contradicts an earlier call. The context exists, but nobody can find it at the moment it matters.

## What it does
- **Auto-capture from comments**: any Jira comment that starts with `DECISION:` (or `Decided:` / `Agreed:`) is stored automatically by a Forge trigger.
- **Issue panel**: every issue shows its own decisions, lets you log a new one, and mark old ones superseded.
- **Already decided elsewhere**: the panel reads the issue's summary and description and surfaces related decisions from other issues, so you see prior context before you start.
- **Conflict warning**: when a decision on this issue looks opposite to one made elsewhere (same topic, one says "use X", the other "don't use X"), the panel shows a warning.
- **Rovo agent – Decision Keeper**: ask "what did we decide about the database?" and it calls the `find-decisions` action; tell it "log that we're using Okta for SSO on KAN-4" and it calls `log-decision`.

## Forge modules
| Module | Purpose |
| --- | --- |
| `jira:issuePanel` (UI Kit) | Decision list, log form, related decisions, conflict warning |
| `trigger` on `avi:jira:commented:issue` | Captures `DECISION:` comments |
| `rovo:agent` + 2 `action`s | Decision Keeper agent with search and log tools |
| Forge KVS storage | Decisions stored in the app's own storage; nothing leaves Atlassian |

## Run it yourself
```bash
npm install
npm test                 # unit tests for parsing, search and conflict detection
forge register           # first time only
forge deploy
forge install --site <your-site>.atlassian.net --product jira
```

Deployment is automated with GitHub Actions (`.github/workflows/deploy.yml`) using `FORGE_EMAIL` and `FORGE_API_TOKEN` repository secrets.

## How it works
- `src/decisions.js` – pure logic: ADF to text, decision parsing, keyword extraction, relevance scoring, conflict heuristic.
- `src/index.js` – resolver for the panel, comment trigger, and Rovo action handlers.
- `src/frontend/index.jsx` – UI Kit panel.

## License
MIT
