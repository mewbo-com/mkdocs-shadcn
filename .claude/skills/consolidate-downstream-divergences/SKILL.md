---
name: consolidate-downstream-divergences
description: >-
  Probe one or more consumer/downstream repos that depend on a shared library,
  theme, framework, or package; catalog every customization they layered on top
  of it; absorb the ones that belong upstream into the shared package itself; and
  then file adoption issues in each consumer so their engineers can drop the
  now-redundant forks. Use this whenever the user wants to consolidate
  divergences, reduce per-consumer forks/overrides, "pull customizations back
  into" or "absorb changes into" a shared package, audit what downstream repos
  changed on top of a shared dependency, or make consumers able to use the shared
  package out of the box with minimal config — even if they never say the word
  "consolidate." The user supplies the source (shared) repo and the consumer
  repos as references when they invoke this.
---

# Consolidate downstream divergences

A shared package (library, theme, framework, design system, config preset) is
consumed by several repos. Over time each consumer accumulates local
customizations — overrides, extra assets, config, copied-and-edited files,
inline workarounds — to make the shared package fit. That drift is expensive:
every consumer re-solves the same problems, and upgrades get harder.

This skill pulls the *shareable* drift back into the source package so consumers
can use it out of the box, then hands each consumer team a precise to-do list
for removing their now-redundant local copies. The source repo becomes the one
place branding/behavior decisions live; consumers stay thin.

**You do not get the repos by guessing.** The user names the source repo and the
consumer repos when they invoke this. If they only named some, ask for the rest
before starting.

## The shape of the work

Four phases. Phases 1 and 3 fan out across consumers in parallel; phase 2 is the
careful, conflict-prone work in the source repo.

1. **Probe & catalog** every divergence in each consumer (read-only).
2. **Absorb** the shareable divergences into the source repo (+ verify).
3. **File adoption issues** in each consumer (default) — do not edit consumers
   unless the user explicitly asks.
4. **Finish**: source-repo docs, version, release per the repo's own norms.

---

## Phase 1 — Probe & catalog (parallel, read-only)

Dispatch one investigation agent per consumer repo, concurrently — they are
independent and this conserves your context. Give each agent the consumer path,
the source-package path (so it can diff against the *installed* copy, usually
under the consumer's virtualenv / `node_modules` / vendor dir), and a short
description of the source package's layout so it can judge what is a "shared
concern." Tell agents to ignore noise: `.venv`, `node_modules`, `.git`,
build output, worktrees, test fixtures.

Each agent returns a catalog. **Classify every divergence into exactly one
bucket** — this classification is the whole point:

- **(A) Belongs upstream** — styling, branding, layout, behavior, or a feature
  that any consumer would want. The primary target.
- **(B) Legitimately consumer-specific** — content, nav, URLs, names, per-repo
  config, deployment paths. Stays in the consumer.
- **(C) Workaround** — an inline hack/override that exists *only* because the
  shared package is missing something. Absorb the missing capability, not the
  hack. Note what upstream feature makes it unnecessary.

Have each agent return, per divergence: file(s) + line, bucket, what it does,
how it differs from the stock package (or "net-new"), and a consolidation note
(for A/C: which source file/mechanism it should land in; for B: why it stays).
End with a per-bucket count and the top consolidation candidates ranked by how
much consumer boilerplate each would eliminate.

**Reconcile before designing.** When consumers disagree (one forks a file, one
doesn't), figure out *why* — often one is on an older version, or one already
got a fix. Inspect the source repo's *current* state directly; don't trust a
single consumer's snapshot.

### The highest-leverage pattern: de-hardcode

The biggest wins are usually values **hardcoded in the shared package** that
force consumers to fork whole files just to change them — a brand name baked
into a template, a product string in a script, a fixed path. Driving these from
config/inputs (and falling back to a sane default) deletes the fork for *every*
consumer at once. Look for it specifically; it often outranks net-new features.

---

## Phase 2 — Absorb into the source repo

Do this work yourself (it touches shared, conflict-prone files); use parallel
agents only for genuinely independent, single-file edits.

**Read the source repo's conventions first.** Its contributor docs / agent notes
(`CLAUDE.md`, `AGENTS.md`, `README`, `CONTRIBUTING`) encode how *this* repo wants
changes made. Match its file layout, naming, and idioms. Write code that reads
like the surrounding code.

When you absorb a divergence, **generalize it**: strip consumer-specific names
and values, expose the tunable bits as config/tokens/variables with sensible
defaults, and keep one consumer's domain-specific specializations *out* (those
stay bucket B). A reusable primitive beats a verbatim copy.

**Respect the repo's build contract.** Common traps that silently break a deploy
if skipped — look for whichever apply here:
- Committed build artifacts (e.g., a compiled CSS/JS bundle) that a normal build
  does *not* regenerate — rebuild and commit them after editing source.
- Integrity/hash attributes (SRI) baked into templates — regenerate them after
  editing any hashed asset, or the browser blocks it.
- Version-sync hooks that mirror a version field across files — keep them in sync.
- Feature flags / optional-integration patterns — wire new optional features the
  same way existing ones are gated, so they cost nothing when off.

**Verify before claiming done.** Run the repo's own build and test suite. If the
repo has a regression/smoke test, make sure your change keeps it green and add
coverage for net-new behavior. For anything visual or subjective, render it and
look (screenshot) — assertions don't capture "does this look right."

---

## Phase 3 — File adoption issues in the consumers (default)

Unless the user explicitly says to edit the consumer repos, your deliverable for
each consumer is an **issue**, not a commit. Confirm scope if unsure.

**Detect each consumer's forge from its git remote** and use the matching tool:
- `github.com` → `gh issue create`
- GitLab (saas or self-hosted) → `glab issue create`, or the GitLab REST API
- A self-hosted Gitea / Forgejo → `tea issues create`, or the REST API
  (`POST /api/v1/repos/{owner}/{repo}/issues`; build the JSON body with `jq` so
  markdown survives)

**Check token scope before relying on it.** A token can carry repo/write scope
yet still lack *issue* scope and 403 on create. Verify with a read first; if it
fails, say so and ask the user for an issue-scoped token rather than faking
success.

Each issue should be a concrete checklist an engineer can execute: bump the
shared-package dependency to the new version; delete the specific forked files /
overrides now provided upstream; switch hand-rolled markup to the new shared
primitives/feature flags; remove redundant config that now matches the default;
and a "build + verify" line. Reference the source version that delivers it.

---

## Phase 4 — Finish in the source repo

- **Docs/memory**: capture the *durable, non-obvious* decisions (the new config
  surface, gotchas a future contributor would re-discover the hard way) in the
  repo's CLAUDE.md/AGENTS.md and any persistent memory — concisely, without
  bloat. Record insights, not a changelog.
- **Version + release**: bump and release the way *this* repo already does it
  (its version source of truth, its release workflow). Commit as whatever
  identity the repo uses, not your global git identity.

---

## Guardrails (read before any irreversible or outward step)

- **Never leak a consumer's private details into a public source repo.** Internal
  hostnames, tokens, internal codenames, private repo identifiers, private branch
  names must not appear in the source repo's commits, comments, or *built
  artifacts* (wheels/bundles ship file contents — a codename in a config comment
  ships too). Scrub names to generic placeholders while absorbing. If you find
  such leakage already present and must purge git history, know that a
  *whole-history* rewrite re-SHAs the shared upstream commits too and breaks the
  fork's ahead/behind on the host — instead rebuild only your own commits on top
  of the real upstream base (e.g. `git commit-tree` with the upstream commit as
  parent and the cleaned tree) so shared ancestry is preserved.
- **Confirm before irreversible, outward actions**: force-pushing, deleting
  published releases/tags, rewriting public history. Lay out exactly what will be
  destroyed and get explicit go-ahead — directional approval earlier doesn't
  cover a newly-discovered, larger blast radius.
- **Parallelize the safe parts, serialize the risky ones.** Catalog consumers in
  parallel and make independent single-file edits in parallel, but keep edits to
  one shared/conflict-prone file with a single editor, and never hand secrets to
  subagents.
- **Report faithfully.** If a token lacks scope, a test fails, or a step was
  skipped, say so with the evidence. Don't claim a deploy is clean without
  verifying it.
