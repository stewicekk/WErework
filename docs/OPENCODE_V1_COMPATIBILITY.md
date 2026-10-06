# OpenCode V1 Compatibility

The target environment reported a V1 parser.

## Required V1 forms

- `permission` is singular and uses tool-keyed values.
- Project agents live under `.opencode/agents/`.
- Agent frontmatter uses `description`, `mode`, and the markdown body as the prompt.
- Project commands live under `.opencode/commands/`.
- Skills live under `.opencode/skills/`.

Do not introduce native V2-only top-level fields such as `permissions` or `agents` into this V1 project config.
