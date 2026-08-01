---
name: project-spec-writer
description: Write comprehensive XML-structured project specifications (build plans / PRDs) for software projects. Use when a user wants to create a build plan, project spec, technical specification, PRD, or detailed requirements document for an application they want built — or wants to spec a new feature for an existing codebase, or to review, refine, or expand an existing spec. Triggers include requests like "write a project spec", "create a build plan", "make a technical specification", "spec out this app idea", "write requirements for my project", "write a PRD", and Korean requests like "프로젝트 스펙 작성해줘", "기획서/명세서 써줘", "빌드 플랜 만들어줘", "요구사항 정의서 작성", "이 아이디어 스펙으로 정리해줘", "기능 스펙 써줘", "스펙 검토/개선해줘". The output is an XML-formatted .md file optimized for consumption by AI coding agents (e.g., Claude Code, Cursor, Copilot Workspace) or human developers.
---

# Project Specification Writer

Generate detailed, structured XML project specifications that serve as comprehensive build plans for software projects. The specs are designed to be consumed by AI coding agents or developers to build applications with minimal ambiguity.

## Modes

Pick the mode that matches the request before doing anything else:

| Mode | When | Instructions |
|------|------|--------------|
| **New project spec** | Greenfield app/service/tool idea | Workflow below |
| **Feature spec** | Adding/changing features in an existing codebase | Read [references/feature-spec-mode.md](references/feature-spec-mode.md) |
| **Refine existing spec** | User has a spec file to review, improve, or expand | "Refining an Existing Spec" below |

## Language Policy

- Converse with the user in the user's language.
- Write spec **content in Korean by default**. Keep XML tag names, code, field names, file paths, library names, env var names, and CLI commands in English — only prose is localized. Reason: the spec is reviewed by Korean readers, but identifiers must match what actually appears in code.
- If the user requests another language (or the project context is clearly non-Korean, e.g. an English-speaking team), follow that instead.

## Workflow (New Project Spec)

### 1. Gather Project Intent

Understand, in order of priority:

1. **What** — Core purpose and key features (e.g., "a JIRA-like project management app")
2. **How** — Technical preferences: framework, language, hosting model
3. **Who** — Target users and usage context
4. **Look & Feel** — Design preferences, reference apps, color themes

If the user provides a brief idea, ask focused follow-up questions. When the AskUserQuestion tool is available, prefer it over free-form questions — give concrete options so the user can decide quickly. Keep it to 1–2 rounds; don't interrogate.

**Confirm the technology stack with the user before drafting.** Derive 2–3 candidate stacks from the project's actual requirements (offline needs, team skills, hosting budget, scale) and present them with one-line tradeoffs, e.g.:

- "React + Vite + IndexedDB — 서버 없음, 배포 단순, 협업 기능 불가"
- "Next.js + Supabase — 인증/DB 즉시 확보, 벤더 의존 발생"

Let the user pick or adjust. Don't silently apply a default stack to a project whose requirements point elsewhere.

**If the user can't respond** (headless run, or they said "알아서 진행해"): choose the best-fit stack yourself and record the choice and rationale in `<assumptions>` so it's auditable later.

**Version numbers — never invent them.** Model memory of "latest versions" is stale. For each pinned library either:
- verify the current version (`npm view <pkg> version`, PyPI, or web search) when tools are available, or
- write the major version only with a note: `React 19 (latest stable at build time)`.

Exact minor/patch numbers that were not verified are worse than none — an AI builder will faithfully install a version that may not exist.

### 2. Draft the Specification

Read the XML schema reference: [references/xml-schema.md](references/xml-schema.md) (it has a table of contents — read the sections relevant to this project type).

Write the specification inside a single `<project_specification>` root tag. Follow this section order:

```
project_name → overview → assumptions → open_questions → scope_boundaries →
technology_stack → prerequisites → environment_variables → file_structure →
core_data_entities → authentication → route_definitions → component_hierarchy →
pages_and_interfaces (or api_endpoints / commands_and_flags / public_api) →
core_functionality → ai_integration → error_handling →
third_party_integrations → aesthetic_guidelines → internationalization →
security_considerations → advanced_functionality →
final_integration_test → success_criteria → build_output →
deployment_and_operations → key_implementation_notes
```

Skip sections that don't apply (see applicability table in the schema reference). Complete examples:
- [references/example-spec.md](references/example-spec.md) — web app, English content
- [references/example-api-spec.md](references/example-api-spec.md) — backend API, Korean content (default language policy in action)

#### Writing Principles

**Be concrete, not abstract.** Every design decision should have a specific value:
- Colors: hex codes (`#1B4332`), not names ("dark green")
- Dimensions: pixel values (`56px`), not vague sizes ("large")
- Libraries: name + verified version or major+latest, not categories ("a charting library")
- Enums: list all values (`enum (Story, Bug, Task, Epic, Sub-task)`)

**Be exhaustive on data models.** Every entity needs complete field definitions with types, constraints, and relationships. Include compound indexes for any non-trivial querying patterns.

**Be specific on UI.** For each view/page: layout structure, dimensions, colors, content hierarchy, interactive behaviors (hover/click/drag/keyboard), empty states, and animations with durations.

**Be opinionated on design.** Provide a complete design system: color palette, typography, spacing scale, component styles, animation specifications.

**Be actionable on implementation.** Include a recommended implementation order that respects dependency chains. Provide concrete code for schemas/configs where helpful.

**Be honest about uncertainty.** Decisions you made without user confirmation go in `<assumptions>`; decisions only the user can make go in `<open_questions>`. A builder silently implementing on top of a wrong guess is the most expensive failure mode a spec can cause.

**Write for AI agents.** Prefer explicit, unambiguous descriptions. State architectural constraints with `CRITICAL:` prefix. Avoid prose that requires interpretation — use structured lists and specific values.

### 3. Review: Consistency Pass

Sections written hours (or context windows) apart drift. Before delivering, cross-check:

- Every route in `route_definitions` has a matching page/view in `pages_and_interfaces`
- Every field displayed in UI specs exists in `core_data_entities`
- Every color used in page specs exists in the `aesthetic_guidelines` palette
- Every env var mentioned anywhere is listed in `environment_variables`
- Every library mentioned in the body appears in `technology_stack`
- Every feature in `core_functionality` is exercised by at least one test scenario
- No TBD/TODO/미정 markers outside `open_questions`

Then run the mechanical validator and fix what it reports:

```bash
python3 scripts/validate_spec.py <path/to/SPEC.md>
```

Finally, check the writing quality checklist at the end of the schema reference.

### 4. Output and Handoff

Save as a `.md` file in the current working directory (or a user-specified path). Filename: project name in SCREAMING_SNAKE_CASE with `_SPEC` suffix — `CANOPY_SPEC.md`, `RECIPE_TRACKER_SPEC.md`.

For large specs (>500 lines), write iteratively: outline first, then fill sections one at a time.

When presenting the finished spec to the user:
1. Summarize what was specced (stack, scope, size)
2. Surface `<open_questions>` explicitly — these need the user's answers before a build starts
3. Offer to expand, revise, or add detail to any section

## Refining an Existing Spec

When the user brings an existing spec to improve:

1. **Read the entire spec first** — never edit based on the filename or a skim.
2. **Diagnose**: run the consistency pass and `scripts/validate_spec.py`, and compare against the quality checklist. List concrete gaps (missing sections, vague values, contradictions), not generic advice.
3. **Confirm direction**: present the diagnosis and let the user choose what to fix — unless they already specified the changes.
4. **Edit surgically**: use targeted edits, preserving decisions the user already made. Rewriting sections wholesale discards deliberate choices that took feedback rounds to reach.
5. **Update `<assumptions>` / `<open_questions>`** to reflect any new decisions, re-run the validator, and summarize what changed and why.

## Section Depth Guidelines

Match detail level to project complexity:

| Project Complexity | Spec Length | Data Entities | UI Pages | Test Scenarios |
|-------------------|-------------|---------------|----------|----------------|
| Simple (todo, timer) | 200-400 lines | 2-4 entities | 2-4 views | 3-5 scenarios |
| Medium (blog, dashboard) | 400-800 lines | 5-8 entities | 5-10 views | 6-8 scenarios |
| Complex (PM tool, CRM) | 800-1700 lines | 8-15 entities | 10-20 views | 10-15 scenarios |

## Adaptation for Non-Web Projects

Each replacement section below is fully defined in the schema reference:

- **API/backend**: replace `pages_and_interfaces` with `<api_endpoints>`; skip `aesthetic_guidelines`. See [references/example-api-spec.md](references/example-api-spec.md).
- **CLI tools**: replace `pages_and_interfaces` with `<commands_and_flags>`; replace `aesthetic_guidelines` with `<output_formatting>`.
- **Libraries/SDKs**: replace `pages_and_interfaces` with `<public_api>`; replace `aesthetic_guidelines` with `<api_design_principles>`.
