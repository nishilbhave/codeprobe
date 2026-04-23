# Security Policy

## Read-Only Guarantee

`codeprobe` is strictly read-only with respect to the codebase it reviews. The skill:

- **Never modifies, writes, edits, or deletes** any file in the user's source tree.
- **Never runs commands with side effects** on the reviewed project (no `npm install`, `pip install`, git commits, database mutations).
- **Never exfiltrates** source code or findings to any external service. All analysis runs locally.

### One documented exception: report artifact

After a successful `/codeprobe audit`, the skill writes a single markdown report to `./codeprobe-reports/<project>-<cmd>-<timestamp>.md` in the current working directory (e.g. `./codeprobe-reports/growth-engine-audit-2026-04-23-221047.md`). This is the skill's own output artifact, not modification of reviewed code. Add `codeprobe-reports/` to your `.gitignore` if you don't want to commit reports.

## Bundled Scripts

Three Python 3 scripts ship with the skill, all read-only:

- `scripts/file_stats.py` — LOC and file counts for the audit dashboard.
- `scripts/complexity_scorer.py` — cyclomatic complexity (optional input for the performance sub-skill).
- `scripts/dependency_mapper.py` — import graph + cycle detection (input for the architecture sub-skill).

Scripts use only the Python 3.8+ standard library. No network access. No file writes. Review them at `skills/codeprobe/scripts/`.

## Tool Permissions

The orchestrator requests these tools in its `allowed-tools`:

- `Read`, `Grep`, `Glob` — source-file inspection (read-only).
- `Bash` — to run the bundled Python scripts above.
- `Agent` — to dispatch the nine sub-skill agents.
- `Write` — used exactly once per audit, to save the report artifact described above.

Sub-skills run with a narrower `allowed-tools` (typically `Read`, `Grep`, `Glob`, `Bash`) and ship no executable code.

## Reporting a vulnerability

Open an issue at https://github.com/nishilbhave/codeprobe/issues or contact the maintainer listed in `skills/codeprobe/SKILL.md`.
