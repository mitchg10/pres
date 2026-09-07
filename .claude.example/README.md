# Sample Claude Code configuration

Copy what you want into `.claude/` (which is gitignored, so your local settings stay yours):

```bash
cp -R .claude.example/skills .claude/skills
```

That installs the **preview-slides** skill, which teaches Claude Code to screenshot a slide
after editing it instead of guessing whether the change worked.

`settings.example.json` is a minimal permission allowlist so the capture commands run without
a prompt each time. Merge it into `.claude/settings.local.json` if you want it — review it
first; permissions are personal.

Using a different agent? Everything here is a thin pointer to `AGENTS.md` at the repo root,
which is plain Markdown and tool-agnostic. Point your tool at that file instead.
