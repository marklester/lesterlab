# LesterLab agent skills

This directory is the canonical home for reusable agent skills associated with
the LesterLab repository. Keep each skill in its own directory with a
`SKILL.md` file at the top level. Optional `scripts/`, `references/`, and
`assets/` directories may live beside it.

The layout follows the open Agent Skills convention and is intentionally not
tied to a particular agent implementation:

```text
.agents/skills/
└── skill-name/
    ├── SKILL.md
    ├── scripts/       # optional
    ├── references/    # optional
    └── assets/        # optional
```

## Sparse checkout

To fetch only the skills from a fresh clone:

```bash
git clone --no-checkout https://github.com/marklester/lesterlab.git
cd lesterlab
git sparse-checkout set --no-cone '.agents/skills/**'
git checkout
```

To include the repository guidance as well:

```bash
git sparse-checkout set --no-cone '.agents/skills/**' AGENTS.md
```

Do not put credentials, machine-specific configuration, or generated files in
this directory.
