# Stage 2.3 Source Access Guide

This guide describes how Stage 2.3 should read the high-priority Skill, MCP, and Plugin sources planned by `SourceCatalog`.

The key rule is: do not treat every GitHub result as a single installable candidate. Some repositories are marketplaces or indexes. Read them first, enumerate their entries, then convert individual entries into candidates only after verifying their detail files.

## Common Source Fields

Each source in the catalog has:

- `source_id`: stable internal identifier.
- `source_kind`: official docs, registry API, marketplace repo, example repo, or community repo.
- `base_url`: human-facing page or repository.
- `index_url`: raw markdown or raw JSON index when available.
- `api_url`: structured API or GitHub Contents API when available.
- `reader_type`: the Stage 2.3 reader that should be used.
- `searcher_type`: the search strategy to use inside the source.

Recommended Stage 2.3 behavior:

- Fetch source indexes with short timeouts and explicit proxy support.
- Record failures per source without aborting the whole pipeline.
- Cache large JSON or markdown indexes by URL and GitHub SHA/ETag when available.
- Preserve source provenance on every candidate: source id, source kind, entry URL, raw detail URL, and reader type.
- Use community and commercial sources for discovery or enrichment, but keep official sources as higher-trust signals.
- Do not use broad DuckDuckGo-style fallback search as a primary discovery path. Search inside curated sources first, and record unsupported source readers as skipped rather than fabricating coverage.

## Skill Sources

### `anthropic_skills_repo`

- URL: `https://github.com/anthropics/skills`
- Index: `https://raw.githubusercontent.com/anthropics/skills/main/.claude-plugin/marketplace.json`
- API: `https://api.github.com/repos/anthropics/skills/contents/skills`
- Data form: official GitHub repository, marketplace JSON, `skills/*/SKILL.md` directories.
- Reader: `github_marketplace_manifest_reader` plus `github_skill_tree_reader`.

Access steps:

1. Fetch `.claude-plugin/marketplace.json` from `index_url`.
2. Parse entries and resolve relative `source` paths against the repository root.
3. For each entry that matches the requirement, read the corresponding `SKILL.md`.
4. Extract frontmatter, title, description, capabilities, allowed resources, scripts, and evidence quotes.
5. If the manifest is unavailable, fall back to GitHub Contents API under `skills/`.

Failure handling:

- If manifest parsing fails, record `failed` for this source and try the `skills/` tree.
- If an individual `SKILL.md` fails, skip only that entry.

### `anthropic_agent_skills_docs`

- URL: `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview`
- Index: `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview.md`
- Data form: official documentation markdown.
- Reader: `docs_markdown_reader`.

Access steps:

1. Fetch the markdown page.
2. Extract built-in skill IDs, capability descriptions, limitations, and safety notes.
3. Treat this source as normative documentation, not as a broad marketplace.
4. Use it to enrich reports and validate fields extracted from `SKILL.md`.

### `anthropic_skills_cookbook`

- URL: `https://github.com/anthropics/anthropic-cookbook/tree/main/skills`
- Index: `https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/skills/README.md`
- API: `https://api.github.com/repos/anthropics/anthropic-cookbook/contents/skills`
- Data form: official examples, notebooks, README files, and sample assets.
- Reader: `github_repo_tree_reader`.

Access steps:

1. Fetch the skills README and GitHub tree.
2. Identify example directories related to the requirement.
3. Read README or notebook summaries, but mark candidates as examples/tutorials.
4. Do not rank cookbook examples above installable official skills unless the user asks for examples.

### `skillsmp_directory`

- URL: `https://skillsmp.com`
- Search page: `https://skillsmp.com/search?q={query}`
- API docs: `https://skillsmp.com/docs/api`
- OpenAPI spec: `https://skillsmp.com/openapi.json`
- API: `https://skillsmp.com/api/v1/skills/search`
- LLM guide: `https://skillsmp.com/llms.txt`
- Data form: community web directory plus REST API over public GitHub `SKILL.md` files.
- Reader: `skillsmp_api_reader`.

Observed web behavior:

- The homepage and `/search?q=pdf` render skill cards directly in HTML, including skill name, GitHub source, description, stars, and update time.
- The site exposes Schema.org `SearchAction` with URL template `https://skillsmp.com/search?q={search_term_string}`.
- `robots.txt` allows public pages but disallows `/api/` for generic crawlers. The site's own `/llms.txt` and API docs state that keyword search is available for agents and anonymous API users. SkillPilot should treat API use as an explicit source-specific integration with rate-limit handling, not as broad crawling.
- `sitemap.xml` returned 500 during investigation, so do not rely on sitemap discovery.

API behavior from docs:

- Endpoint: `GET /api/v1/skills/search`
- Required parameter: `q`
- Optional parameters: `page`, `limit`, `sortBy` (`stars` or `recent`), `category`, `occupation`
- Anonymous limits: 50 requests/day, 10 requests/min, keyword search only.
- Authenticated limits: 500 requests/day, 30 requests/min.
- Response includes `data.skills[]` with `id`, `name`, `author`, `description`, `githubUrl`, `skillUrl`, `stars`, and `updatedAt`.

Access steps:

1. Prefer API search for keyword matching when rate limits allow.
2. Use the public search page only as a fallback or for manual verification.
3. Convert SkillsMP search hits into provisional source results pointing at `githubUrl`.
4. Read the returned GitHub repository or skill path before creating a `Candidate`.
5. Preserve `skillUrl`, `stars`, `updatedAt`, and `author` as marketplace metadata.
6. Mark trust as community/discovery: SkillsMP indexes public GitHub sources and does not certify safety.
7. On HTTP 429, record the rate-limit headers and continue with official Skill sources.

## MCP Sources

### `official_mcp_registry`

- URL: `https://registry.modelcontextprotocol.io/`
- API: `https://registry.modelcontextprotocol.io/v0.1/servers`
- Data form: official JSON registry API.
- Reader: `generic_mcp_registry_reader`.

Access steps:

1. Query the API with source-specific search terms when supported.
2. Support pagination and `updated_since` for future caching.
3. Normalize server fields: name, description, repository, packages, remotes, latest version, and metadata.
4. If package metadata points to npm/PyPI/OCI, keep the package ID for Stage 2.5 trust checks.

Failure handling:

- The official registry is preview. If schema or availability changes, record the exact response and continue with Glama and Smithery.

### `glama_mcp`

- URL: `https://glama.ai/mcp/servers`
- API: `https://glama.ai/api/mcp/v1/servers`
- Data form: community JSON API plus web directory.
- Reader: `glama_api_reader`.

Access steps:

1. Use the public API as the primary path, not the web page.
2. Extract repository URL, tools, license, attributes, maintenance, and quality signals.
3. Use Glama as an enrichment source and cross-check against official registry or GitHub.
4. Deduplicate by normalized server name and repository URL.

### `smithery_mcp`

- URL: `https://smithery.ai/`
- API: `https://api.smithery.ai/servers`
- Data form: commercial hosted registry API.
- Reader: `smithery_api_reader`.

Access steps:

1. Query with `q`, `page`, and `pageSize` when available.
2. Preserve hosted/remote/verified/deployed fields as trust or convenience signals.
3. Support optional API key configuration if the endpoint requires authentication later.
4. Do not treat Smithery verification as MCP official verification.

## Plugin Sources

### `anthropic_official_plugin_marketplace`

- URL: `https://github.com/anthropics/claude-plugins-official`
- Index: `https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json`
- Data form: official marketplace JSON.
- Reader: `claude_marketplace_json_reader`.

Access steps:

1. Fetch `marketplace.json`.
2. Parse `plugins[]` entries: name, description, category, keywords, homepage, source.
3. Resolve each source. It may be a local path, GitHub source, URL, npm source, or git subdirectory.
4. For matching entries, read `.claude-plugin/plugin.json` or inline entry fields.
5. Extract components: slash commands, subagents, skills, MCP servers, hooks, binaries, and config files.

Risk notes:

- Hooks, MCP servers, local executables, npm packages, and unpinned external sources should raise risk.

### `anthropic_community_plugin_marketplace`

- URL: `https://github.com/anthropics/claude-plugins-community`
- Index: `https://raw.githubusercontent.com/anthropics/claude-plugins-community/main/.claude-plugin/marketplace.json`
- API: `https://api.github.com/repos/anthropics/claude-plugins-community/contents/.claude-plugin/marketplace.json`
- Data form: large official community marketplace JSON.
- Reader: `large_marketplace_json_reader`.

Access steps:

1. Fetch through GitHub API first when possible to get `sha`, `download_url`, and file size.
2. Cache by SHA/ETag.
3. Parse in a memory-conscious way if the file grows.
4. Resolve plugin details only for entries that match the requirement.
5. Deduplicate with the official marketplace and other community marketplaces.

### `anthropic_demo_plugin_marketplace`

- URL: `https://github.com/anthropics/claude-code`
- Index: `https://raw.githubusercontent.com/anthropics/claude-code/main/.claude-plugin/marketplace.json`
- API: `https://api.github.com/repos/anthropics/claude-code/contents/plugins`
- Data form: example marketplace JSON plus `plugins/` directory.
- Reader: `github_repo_marketplace_reader`.

Access steps:

1. Use this source as a format reference and test fixture.
2. Read marketplace JSON, then plugin directories under `plugins/`.
3. Do not rank demo/example entries above official or community marketplace entries unless evidence is stronger.

### `ccplugins_awesome_marketplace`

- URL: `https://github.com/ccplugins/awesome-claude-code-plugins`
- Index: `https://raw.githubusercontent.com/ccplugins/awesome-claude-code-plugins/main/.claude-plugin/marketplace.json`
- Data form: community marketplace JSON plus README directory.
- Reader: `claude_marketplace_json_reader`.

Access steps:

1. Prefer `.claude-plugin/marketplace.json` over README parsing.
2. Use README categories only as supplemental tags.
3. For matching plugins, resolve `source` paths such as `./plugins/<name>`.
4. Read plugin detail files and README before creating candidates.
5. Mark trust as community and require stronger evidence before direct recommendation.

## Generic Readers Needed In Stage 2.3

- `docs_markdown_reader`: fetch markdown docs and extract normative guidance.
- `github_marketplace_manifest_reader`: parse `.claude-plugin/marketplace.json` or Skill marketplace manifests.
- `large_marketplace_json_reader`: same as marketplace reader, but with cache and size safeguards.
- `github_repo_marketplace_reader`: parse marketplace JSON and then inspect local plugin directories.
- `github_skill_tree_reader`: enumerate `SKILL.md` files from a GitHub tree.
- `generic_mcp_registry_reader`: parse official-compatible MCP registry JSON.
- `glama_api_reader`: parse Glama-specific fields.
- `smithery_api_reader`: parse Smithery-specific fields and optional auth.

## Candidate Creation Rule

Create a `Candidate` only after one of these is true:

- A concrete `SKILL.md` was read.
- A concrete MCP server registry entry or repository was read.
- A concrete plugin entry plus plugin detail file or source directory was read.
- A community awesome list entry was verified against a concrete repository or manifest.

Do not create candidates directly from:

- A marketplace homepage.
- A broad README list without verifying the linked item.
- A web article or tutorial page.
- A GitHub repository that only aggregates links.
