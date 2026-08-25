# keith-marketplace

Agent skills by keith. Skills follow the [Agent Skills](https://agentskills.io/specification) open format, so one `skills/<name>/SKILL.md` works in Claude Code, Codex, Cursor, OpenCode, Gemini CLI, Copilot CLI and 70+ other agents.

**Quality gate:** every skill must pass [NVIDIA SkillEvaluator](https://github.com/NVIDIA/SkillEvaluator) Tier 1 (schema, PII, license, unicode, lint, quality score ≥ 80) — enforced by `scripts/gate.sh` and CI.

## Skills

| Skill | What it does |
|---|---|
| [memory-inventory](skills/memory-inventory/SKILL.md) | Audit Claude Code auto-memory: verify stale claims against gh/git/deploy logs, find orphans and broken links, archive instead of delete. |

## Install

### Any agent (recommended) — `npx skills`

```bash
npx skills add You-keitou/keith-marketplace                 # pick skills interactively
npx skills add You-keitou/keith-marketplace --skill memory-inventory
npx skills add You-keitou/keith-marketplace --list           # see what's here
```

`npx skills` installs into the right directory for each agent it detects (`.claude/skills/`, `.codex/skills/`, `.cursor/skills/`, `.agents/skills/` …). Add `-g` for a global install.

### Claude Code (plugin marketplace)

```
/plugin marketplace add You-keitou/keith-marketplace
/plugin install memory-inventory@keith-marketplace
```

### Codex

```
/plugins
```
then pick `keith-marketplace`, or add the repo URL under Plugins in the Codex app. The manifest is `.codex-plugin/plugin.json`.

### Cursor

```
/add-plugin You-keitou/keith-marketplace
```

### Gemini CLI

```bash
gemini extensions install https://github.com/You-keitou/keith-marketplace
```

### Manual (any agent that reads SKILL.md)

Copy `skills/<name>/` into your agent's skills directory (e.g. `~/.claude/skills/`, `~/.codex/skills/`, `~/.config/agents/skills/`).

## Contributing a skill

1. `skills/<name>/SKILL.md` with `name` (== directory name), `description`, `license`, `metadata.author` as `Name <email>`.
2. Keep the body under 500 lines; put scripts in `scripts/`, docs in `references/`.
3. Run `./scripts/gate.sh` — it must exit 0 (installs `skillevaluator` via `uv` on first run).
4. Optional: `skills/<name>/evals/evals.json` for [skill-creator](https://github.com/anthropics/skills) eval runs. Eval workspaces live in `.workspace/` and are git-ignored.

## Layout

```
.claude-plugin/marketplace.json   Claude Code marketplace manifest
.codex-plugin/plugin.json         Codex plugin manifest
skills/<name>/SKILL.md            the skills (agentskills.io format)
scripts/gate.sh                   SkillEvaluator quality gate
.github/workflows/gate.yml        CI: gate on every push/PR
```

## License

MIT
