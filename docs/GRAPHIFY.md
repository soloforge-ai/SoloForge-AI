# Graphify in SoloForge

SoloForge uses Graphify as an architecture map for the repository. The first integration is intentionally code-only: Python, Dart/Flutter, SQL and other source files are parsed locally through Graphify's deterministic code extraction, with no LLM API key required.

## What it is for

Use the graph before large refactors or new cross-cutting sprints to inspect file relationships, call paths and likely blast radius. The highest-priority production flow to trace is:

```
content_jobs
  -> content_generation
  -> content_router
  -> content_asset_generation
  -> audio_generation / final_render
  -> publishing_api / publora_publishing
  -> PUBLISHED
```

The Flutter side should be traced from the content queue and job detail pages through `ContentJobService` to the backend API.

## CI usage

The workflow `.github/workflows/graphify.yml` runs Graphify on pull requests to `main` and can also be started manually.

It uploads an artifact named:

```
soloforge-graphify-architecture
```

The artifact contains at least `graphify-out/graph.json`. When Graphify can produce the call-flow HTML for the current graph, that visualization is included too.

## Local usage

Install Graphify:

```bash
uv tool install graphifyy
```

Build the code graph:

```bash
graphify extract . --code-only --timing
```

For an incremental refresh after code changes:

```bash
graphify update .
```

Graphify also supports Dart files, so the Flutter frontend is included in the repository map.
