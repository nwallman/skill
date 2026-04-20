# Claude Skills

Shared Claude skills, checked in for team reuse.

Each subfolder is a single skill — a Markdown-driven playbook Claude loads when a matching task comes up. See Anthropic's [skill docs](https://docs.claude.com/en/docs/claude-code/skills) for background.

## Layout

```
skill/
├── <skill-name>/
│   ├── SKILL.md          # required: YAML frontmatter (name, description) + instructions
│   ├── assets/           # optional: templates, reference files
│   └── scripts/          # optional: executable helpers the skill invokes
└── README.md (this file)
```

One skill per folder. The folder name must match the `name` field in the skill's YAML frontmatter (kebab-case, lowercase).

## Current skills

| Skill | Purpose |
| --- | --- |
| [handoff-to-claude-code](./handoff-to-claude-code/) | Hand off a software plan built in Cowork to Claude Code in a dedicated git worktree, with a review-first preamble. |
| [local-seo-optimizer](./local-seo-optimizer/) | Full local SEO overhaul for React + Vite + TypeScript client sites. |

## Adding a new skill

1. Create a new top-level folder: `skill/<new-skill-name>/`
2. Add a `SKILL.md` with YAML frontmatter (`name`, `description`) and instructions
3. Put supporting files under `assets/` or `scripts/`
4. Validate before committing — from the skill-creator directory in the Cowork skills plugin:
   ```bash
   python -m scripts.quick_validate <path-to-new-skill>
   ```
5. Commit

Description constraints worth knowing: the YAML `description` field has a hard 1024-character limit, must be a single line, and cannot contain `<` or `>`. The `name` must match `^[a-z0-9-]+$` and be <= 64 characters.

## Installing a skill into Cowork or Claude Code

Two options.

**Option A — package and install:**
From the skill-creator directory (bundled with Cowork's skills plugin):
```bash
python -m scripts.package_skill <path-to-skill-folder> <output-dir>
```
This produces `<skill-name>.skill` — a zip that Cowork's "Save skill" card installs.

**Option B — symlink / copy into the local skills folder:**
Copy or symlink `<skill-name>/` into your local Claude skills directory. The exact location depends on the client (Cowork, Claude Code CLI, etc.); check the docs for your client.

## Conventions

- Skills should do one thing well. If a skill is trying to cover two unrelated workflows, split it.
- Keep `SKILL.md` under ~500 lines. Push long reference material into `assets/` or a `references/` subfolder and link to it from `SKILL.md`.
- Prefer deterministic scripts (in `scripts/`) over asking Claude to reinvent shell commands on every run.
- Explain *why* an instruction matters in the skill body — LLMs follow imperatives better when they understand the intent.
