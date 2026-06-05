from __future__ import annotations

from skillpilot.models import ExtensionType, SearchSource


class SourceCatalog:
    """Curated high-priority sources for Stage 2 search planning."""

    def __init__(self) -> None:
        self._sources = self._build_sources()

    def sources_for(self, extension_type: ExtensionType) -> list[SearchSource]:
        if extension_type == "mixed":
            return self._dedupe(
                self.sources_for("skill")
                + self.sources_for("mcp")
                + self.sources_for("plugin")
            )
        if extension_type == "unknown":
            return self._dedupe(
                self.sources_for("skill")
                + self.sources_for("mcp")
                + self.sources_for("plugin")
            )
        return [
            source
            for source in self._sources
            if extension_type in source.extension_types
        ]

    def by_id(self, source_id: str) -> SearchSource | None:
        return next((source for source in self._sources if source.source_id == source_id), None)

    def _dedupe(self, sources: list[SearchSource]) -> list[SearchSource]:
        seen: set[str] = set()
        deduped: list[SearchSource] = []
        for source in sources:
            if source.source_id in seen:
                continue
            seen.add(source.source_id)
            deduped.append(source)
        return deduped

    def _build_sources(self) -> list[SearchSource]:
        return [
            SearchSource(
                source_id="anthropic_skills_repo",
                name="Anthropic Skills Repository",
                extension_types=["skill"],
                source_kind="official_github_marketplace_repo",
                trust_level="official",
                reader_type="github_marketplace_manifest_reader",
                searcher_type="marketplace_json_searcher",
                base_url="https://github.com/anthropics/skills",
                index_url="https://raw.githubusercontent.com/anthropics/skills/main/.claude-plugin/marketplace.json",
                api_url="https://api.github.com/repos/anthropics/skills/contents/skills",
                data_format="GitHub repo with marketplace JSON and skills/*/SKILL.md",
                notes="Canonical official Skill source; verify each skill by reading SKILL.md.",
            ),
            SearchSource(
                source_id="anthropic_agent_skills_docs",
                name="Anthropic Agent Skills Docs",
                extension_types=["skill"],
                source_kind="official_docs",
                trust_level="official",
                reader_type="docs_markdown_reader",
                searcher_type="docs_keyword_searcher",
                base_url="https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview",
                index_url="https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview.md",
                data_format="Official documentation page and markdown",
                notes="Use for built-in skill IDs, field semantics, and policy context rather than broad discovery.",
            ),
            SearchSource(
                source_id="anthropic_skills_cookbook",
                name="Anthropic Skills Cookbook",
                extension_types=["skill"],
                source_kind="official_example_repo",
                trust_level="official",
                reader_type="github_repo_tree_reader",
                searcher_type="github_contents_searcher",
                base_url="https://github.com/anthropics/anthropic-cookbook/tree/main/skills",
                index_url="https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/skills/README.md",
                api_url="https://api.github.com/repos/anthropics/anthropic-cookbook/contents/skills",
                data_format="GitHub examples, README, notebooks, and sample files",
                notes="Treat as example/tutorial source, not a complete Skill market.",
            ),
            SearchSource(
                source_id="skillsmp_directory",
                name="SkillsMP Skills Marketplace",
                extension_types=["skill"],
                source_kind="community_skill_directory_api",
                trust_level="community",
                reader_type="skillsmp_api_reader",
                searcher_type="skillsmp_api_searcher",
                base_url="https://skillsmp.com",
                index_url="https://skillsmp.com/search?q={query}",
                api_url="https://skillsmp.com/api/v1/skills/search",
                data_format="Community web directory plus REST API and OpenAPI spec",
                notes=(
                    "Search public GitHub SKILL.md index by keyword. Anonymous API is rate limited; "
                    "always verify returned GitHub source before recommending."
                ),
            ),
            SearchSource(
                source_id="official_mcp_registry",
                name="Official MCP Registry",
                extension_types=["mcp"],
                source_kind="official_registry_api",
                trust_level="official",
                reader_type="generic_mcp_registry_reader",
                searcher_type="mcp_registry_api_searcher",
                base_url="https://registry.modelcontextprotocol.io/",
                api_url="https://registry.modelcontextprotocol.io/v0.1/servers",
                data_format="Official JSON registry API",
                notes="Primary canonical MCP source; registry is preview, so record API failures and schema drift.",
            ),
            SearchSource(
                source_id="glama_mcp",
                name="Glama MCP Registry",
                extension_types=["mcp"],
                source_kind="community_registry_api",
                trust_level="community",
                reader_type="glama_api_reader",
                searcher_type="glama_api_searcher",
                base_url="https://glama.ai/mcp/servers",
                api_url="https://glama.ai/api/mcp/v1/servers",
                data_format="Community JSON API and web directory",
                notes="Good enrichment source for tools, license, attributes, and quality signals.",
            ),
            SearchSource(
                source_id="smithery_mcp",
                name="Smithery MCP Registry",
                extension_types=["mcp"],
                source_kind="commercial_hosted_registry_api",
                trust_level="commercial",
                reader_type="smithery_api_reader",
                searcher_type="smithery_api_searcher",
                base_url="https://smithery.ai/",
                api_url="https://api.smithery.ai/servers",
                data_format="Commercial hosted registry API",
                notes="Use as hosted/verified/remote signal source; support API key if needed.",
            ),
            SearchSource(
                source_id="anthropic_official_plugin_marketplace",
                name="Anthropic Official Claude Code Plugins",
                extension_types=["plugin"],
                source_kind="official_github_marketplace_repo",
                trust_level="official",
                reader_type="claude_marketplace_json_reader",
                searcher_type="marketplace_json_searcher",
                base_url="https://github.com/anthropics/claude-plugins-official",
                index_url="https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json",
                data_format="Official marketplace JSON",
                notes="Highest-trust plugin marketplace; details may require reading each plugin source.",
            ),
            SearchSource(
                source_id="anthropic_community_plugin_marketplace",
                name="Anthropic Community Claude Code Plugins",
                extension_types=["plugin"],
                source_kind="official_github_marketplace_repo",
                trust_level="official",
                reader_type="large_marketplace_json_reader",
                searcher_type="marketplace_json_searcher",
                base_url="https://github.com/anthropics/claude-plugins-community",
                index_url="https://raw.githubusercontent.com/anthropics/claude-plugins-community/main/.claude-plugin/marketplace.json",
                api_url="https://api.github.com/repos/anthropics/claude-plugins-community/contents/.claude-plugin/marketplace.json",
                data_format="Large official community marketplace JSON",
                notes="Cache by GitHub SHA or ETag; entries may point to external repositories.",
            ),
            SearchSource(
                source_id="anthropic_demo_plugin_marketplace",
                name="Anthropic Claude Code Demo Marketplace",
                extension_types=["plugin"],
                source_kind="official_example_repo",
                trust_level="official",
                reader_type="github_repo_marketplace_reader",
                searcher_type="marketplace_json_searcher",
                base_url="https://github.com/anthropics/claude-code",
                index_url="https://raw.githubusercontent.com/anthropics/claude-code/main/.claude-plugin/marketplace.json",
                api_url="https://api.github.com/repos/anthropics/claude-code/contents/plugins",
                data_format="Example marketplace JSON plus plugins/ directory",
                notes="Use as format example and test fixture; do not rank as a formal marketplace above official/community sources.",
            ),
            SearchSource(
                source_id="ccplugins_awesome_marketplace",
                name="Awesome Claude Code Plugins",
                extension_types=["plugin"],
                source_kind="community_github_marketplace_repo",
                trust_level="community",
                reader_type="claude_marketplace_json_reader",
                searcher_type="marketplace_json_searcher",
                base_url="https://github.com/ccplugins/awesome-claude-code-plugins",
                index_url="https://raw.githubusercontent.com/ccplugins/awesome-claude-code-plugins/main/.claude-plugin/marketplace.json",
                data_format="Community marketplace JSON plus README directory",
                notes="Treat as marketplace index repo; verify plugin details before recommendation.",
            ),
        ]
