# Cloudflare Worker for `docs.<your-product>.com`

This directory contains a **product-neutral** Cloudflare Worker that you put in front of any docs origin (GitHub Pages, R2, S3, etc.) to add agent-discoverability to a documentation site built with `mkdocs-shadcn-mewbo`.

The worker.js itself never needs editing per-product — every Mewbo umbrella product configures it via `wrangler.toml [vars]`.

## What it does

1. Serves three `.well-known/` agent-discovery endpoints inline (so they're not subject to GitHub Pages MIME-type quirks):

   | Path | Spec | Purpose |
   |---|---|---|
   | `/.well-known/api-catalog` | [RFC 9727](https://www.rfc-editor.org/rfc/rfc9727) (linkset) | Points agents at your API's reference docs, OpenAPI spec, and health endpoint |
   | `/.well-known/mcp/server-card.json` | [SEP-1649](https://github.com/modelcontextprotocol/specification/discussions/1649) | Advertises your product's MCP server (transport + capabilities) |
   | `/.well-known/agent-skills/index.json` | [Agent Skills v0.2.0](https://agentskills.io/) | Lists agent-callable skills your product publishes |

2. Injects [RFC 8288](https://www.rfc-editor.org/rfc/rfc8288) `Link:` headers on every HTML response pointing at those endpoints + your reference docs page, so agents that crawl your docs find them without requesting `/.well-known/` directly.

3. Pass-through proxy for everything else.

## Deploy

```bash
# From your product repo root
mkdir -p .github/cloudflare
curl -L https://github.com/mewbo-com/mkdocs-shadcn/archive/v1.0.0.tar.gz \
  | tar xzf - --strip=2 -C .github/ mkdocs-shadcn-1.0.0/cloudflare

cd .github/cloudflare
mv wrangler.example.toml wrangler.toml
$EDITOR wrangler.toml          # fill in routes + [vars]
wrangler login                 # one-time
wrangler deploy
```

For CI deploys, set `CLOUDFLARE_API_TOKEN` and run `wrangler deploy --env production` (or whichever env you've configured) instead of `wrangler login`.

## Required `[vars]`

| Var | Example | Notes |
|---|---|---|
| `SITE_URL` | `https://docs.mewbo.com` | Absolute origin of your docs site |
| `API_URL`  | `https://api.mewbo.com`  | Absolute origin of your product's API (used by the api-catalog linkset) |

## Optional `[vars]`

| Var | Default | Notes |
|---|---|---|
| `MCP_SERVER_NAME` | `"Docs"` | Shows in `mcp/server-card.json` |
| `MCP_SERVER_VERSION` | `"1.0.0"` | semver |
| `MCP_SERVER_URL` | `${API_URL}/mcp` | streamable-http endpoint |
| `API_OPENAPI_URL` | `${API_URL}/swagger.json` | Service description URL in api-catalog |
| `API_HEALTH_URL` | `${API_URL}/healthz` | Status URL in api-catalog |
| `REFERENCE_PATH` | `/reference/` | Site-relative path to human reference docs (becomes `Link rel="service-doc"`) |
| `SKILLS_INDEX_JSON` | empty list | Full agent-skills index, JSON-encoded one-liner |

## Sanity-check after deploy

```bash
curl -i https://docs.example.com/.well-known/api-catalog
# expect 200, Content-Type: application/linkset+json

curl -I https://docs.example.com/
# expect Link: </.well-known/api-catalog>; rel="api-catalog"
# expect Link: </reference/>; rel="service-doc"
# expect Link: </.well-known/mcp/server-card.json>; rel="https://modelcontextprotocol.io/ns/server-card"
```

## Why this lives in the theme repo

Every product under the mewbo-com umbrella publishes docs that benefit from the same agent-discoverability scaffold. Shipping the worker as a templated asset alongside the theme means a new product gets `.well-known/` endpoints for free by copying this directory and filling in two vars — no per-repo rewrite of the worker JS.
