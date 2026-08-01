# Project Specification XML Schema Reference

This document defines each section of the `<project_specification>` XML structure. Use it as a checklist and structural guide when writing specs.

## Table of Contents

- [Top-Level Structure](#top-level-structure)
- Section Details
  - [project_name](#project_name) · [overview](#overview) · [assumptions](#assumptions) · [open_questions](#open_questions) · [scope_boundaries](#scope_boundaries)
  - [technology_stack](#technology_stack) · [prerequisites](#prerequisites) · [environment_variables](#environment_variables) · [file_structure](#file_structure)
  - [core_data_entities](#core_data_entities) · [authentication](#authentication) · [route_definitions](#route_definitions) · [component_hierarchy](#component_hierarchy)
  - [pages_and_interfaces](#pages_and_interfaces) · [api_endpoints](#api_endpoints) · [commands_and_flags](#commands_and_flags) · [public_api](#public_api)
  - [core_functionality](#core_functionality) · [ai_integration](#ai_integration) · [error_handling](#error_handling) · [third_party_integrations](#third_party_integrations)
  - [aesthetic_guidelines](#aesthetic_guidelines) (incl. accessibility) · [output_formatting](#output_formatting) · [api_design_principles](#api_design_principles) · [internationalization](#internationalization)
  - [security_considerations](#security_considerations) · [advanced_functionality](#advanced_functionality)
  - [final_integration_test](#final_integration_test) · [success_criteria](#success_criteria) · [build_output](#build_output) · [deployment_and_operations](#deployment_and_operations) · [key_implementation_notes](#key_implementation_notes)
- [Section Applicability by Project Type](#section-applicability-by-project-type)
- [Writing Quality Checklist](#writing-quality-checklist)

## Top-Level Structure

```xml
<project_specification>
  <project_name>...</project_name>
  <overview>...</overview>
  <assumptions>...</assumptions>
  <open_questions>...</open_questions>
  <scope_boundaries>...</scope_boundaries>
  <technology_stack>...</technology_stack>
  <prerequisites>...</prerequisites>
  <environment_variables>...</environment_variables>
  <file_structure>...</file_structure>
  <core_data_entities>...</core_data_entities>
  <authentication>...</authentication>
  <route_definitions>...</route_definitions>
  <component_hierarchy>...</component_hierarchy>
  <pages_and_interfaces>...</pages_and_interfaces>  <!-- or api_endpoints / commands_and_flags / public_api -->
  <core_functionality>...</core_functionality>
  <ai_integration>...</ai_integration>
  <error_handling>...</error_handling>
  <third_party_integrations>...</third_party_integrations>
  <aesthetic_guidelines>...</aesthetic_guidelines>  <!-- or output_formatting / api_design_principles -->
  <internationalization>...</internationalization>
  <security_considerations>...</security_considerations>
  <advanced_functionality>...</advanced_functionality>
  <final_integration_test>...</final_integration_test>
  <success_criteria>...</success_criteria>
  <build_output>...</build_output>
  <deployment_and_operations>...</deployment_and_operations>
  <key_implementation_notes>...</key_implementation_notes>
</project_specification>
```

Not all sections are required for every project. Include only sections relevant to the project type.

---

## Section Details

### `<project_name>`
Single line. Format: `AppName - Short Description`.

### `<overview>`
3-4 paragraphs covering:
- What the app does (1st paragraph: core purpose and value proposition)
- Key features and user workflows (2nd paragraph)
- Critical architectural constraints (3rd paragraph, prefixed with `CRITICAL:` for hard rules like "no server", "offline-only", etc.)

### `<assumptions>`
Decisions the spec author made **without explicit user confirmation**. Every entry names the decision, the rationale, and what to do if the assumption is wrong. This protects the builder from silently building on a wrong guess.

```xml
<assumptions>
  - 스택: 사용자가 무응답이어서 React + Vite + IndexedDB 선택. 근거: 오프라인 요구 + 서버 비용 0. 서버가 필요해지면 technology_stack 재검토 필요.
  - 동시 사용자: 단일 사용자 가정 (협업 언급 없음). 멀티유저 필요 시 데이터 모델에 ownerId 추가 필요.
  - 브라우저 지원: 최신 2개 버전만 지원 (레거시 요구 없음).
</assumptions>
```

Rules:
- Only include decisions that could plausibly be wrong — don't pad with obvious facts
- Each entry: decision + rationale + impact if wrong
- If the user confirmed everything interactively, this section can be a single line: "모든 주요 결정은 사용자와 확인함."

### `<open_questions>`
Decisions **only the user can make**, left unresolved at spec time. The builder must NOT guess these — they should be answered before or during the build.

```xml
<open_questions>
  - Q1. 결제 수단: Stripe 단독인지, 국내 PG(토스페이먼츠) 병행인지? → third_party_integrations 확정에 필요
  - Q2. 데이터 보존 기간: 탈퇴 후 유예 기간 30일로 가정했으나 법무 확인 필요
  - Q3. 관리자 화면: MVP 범위에 포함 여부 미정 (포함 시 +3 views)
</open_questions>
```

Rules:
- Number each question (Q1, Q2, ...) so answers can reference them
- State which spec section each answer unblocks
- Present these to the user when delivering the spec; remove resolved items in later revisions

### `<scope_boundaries>`
Explicitly define what is NOT part of this project. Prevents scope creep and sets clear expectations for the builder.

```xml
<scope_boundaries>
  <in_scope>
    - User authentication via email/password and Google OAuth
    - Task CRUD with drag-and-drop reordering
    - Real-time collaboration for up to 5 users per board
  </in_scope>
  <out_of_scope>
    - Native mobile apps (web-only, responsive)
    - Payment/billing features
    - Admin dashboard for user management
    - Email notification system
    - Data export/import beyond CSV
  </out_of_scope>
  <future_considerations>
    - Webhook integrations (Phase 2)
    - Custom fields on tasks (Phase 2)
    - Gantt chart view (Phase 3)
  </future_considerations>
</scope_boundaries>
```

Rules:
- `in_scope`: concrete features included in this build
- `out_of_scope`: things the builder should NOT implement, even if they seem implied
- `future_considerations`: features intentionally deferred, with rough phase labels

### `<technology_stack>`
Group by layer. Common sub-sections:

```xml
<technology_stack>
  <frontend_application>
    <framework>...</framework>
    <build_tool>...</build_tool>
    <styling>...</styling>
    <routing>...</routing>
    <state_management>...</state_management>
  </frontend_application>
  <data_layer>
    <database>...</database>
    <reactive_queries>...</reactive_queries>
    <search>...</search>
    <export>...</export>
    <note>...</note>  <!-- architectural constraints -->
  </data_layer>
  <backend> <!-- if applicable -->
    <runtime>...</runtime>
    <framework>...</framework>
    <auth>...</auth>
    <api_style>...</api_style>
  </backend>
  <build_output>
    <build_command>...</build_command>
    <note>...</note>
  </build_output>
  <libraries>
    <!-- one tag per library: name + version + purpose -->
    <dnd>@dnd-kit/core v6.3.1 for drag-and-drop</dnd>
    <charts>Recharts v3.5 for dashboard visualizations</charts>
  </libraries>
</technology_stack>
```

Rules:
- Include version numbers only if verified (`npm view <pkg> version`, PyPI, web search); otherwise write major version + "(latest stable)". Never invent exact minor/patch numbers from memory — builders will install them verbatim
- State purpose after each library/tool
- Use `<note>` for architectural constraints ("NO server", "NO API", etc.)

### `<prerequisites>`
Sub-sections: `<environment_setup>` (runtime, tools) and `<build_configuration>` (build settings, plugins).

### `<environment_variables>`
List all environment variables the project requires. Prevents AI agents from hardcoding secrets or missing configuration.

```xml
<environment_variables>
  <variable>
    <name>DATABASE_URL</name>
    <description>PostgreSQL connection string</description>
    <required>true</required>
    <example>postgresql://user:pass@localhost:5432/mydb</example>
  </variable>
  <variable>
    <name>NEXT_PUBLIC_SUPABASE_URL</name>
    <description>Supabase project URL (public, safe for client)</description>
    <required>true</required>
    <example>https://xxx.supabase.co</example>
  </variable>
  <variable>
    <name>STRIPE_SECRET_KEY</name>
    <description>Stripe API secret key (server-only)</description>
    <required>false</required>
    <note>Only needed if payment features are enabled</note>
  </variable>
</environment_variables>
```

Rules:
- Mark each as required/optional
- Indicate client-safe vs server-only for frontend frameworks
- Provide realistic example values (never real secrets)
- Add `<note>` for conditional requirements

### `<file_structure>`
Exact folder/file tree for the project. AI agents can use this to scaffold the project immediately.

```xml
<file_structure>
src/
├── app/
│   ├── layout.tsx              # Root layout with providers
│   ├── page.tsx                # Landing/home page
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── signup/page.tsx
│   ├── dashboard/
│   │   ├── layout.tsx          # Dashboard shell with sidebar
│   │   ├── page.tsx            # Dashboard overview
│   │   └── projects/
│   │       ├── page.tsx        # Project list
│   │       └── [id]/page.tsx   # Single project view
│   └── api/
│       └── trpc/[trpc]/route.ts
├── components/
│   ├── ui/                     # Reusable primitives (Button, Input, Modal)
│   ├── layout/                 # Sidebar, Header, Footer
│   └── features/               # Feature-specific composites
│       ├── project/
│       └── task/
├── lib/
│   ├── supabase.ts             # Supabase client
│   ├── trpc.ts                 # tRPC client setup
│   └── utils.ts                # Shared utilities
├── server/
│   ├── routers/                # tRPC routers
│   └── db/                     # Database schema, migrations
├── types/                      # Shared TypeScript types
└── styles/
    └── globals.css             # Tailwind imports + custom CSS
</file_structure>
```

Rules:
- Use tree format with `├──` and `└──` connectors
- Add inline comments (`# description`) for non-obvious files
- Group by feature or layer depending on project convention
- Include config files at root (`.env.example`, `tailwind.config.ts`, etc.)

### `<core_data_entities>`
One child tag per entity. Each entity lists fields as `- field_name: type (constraints, description)`.

Field format examples:
```
- id: string (uuid)
- name: string (required, max 100 characters)
- status: enum (draft, active, archived)
- tags: string[] (array of tag IDs)
- settings: object (theme, notifications)
- createdAt: Date
- sortOrder: number (for manual ordering)
```

Include compound indexes when relevant to querying:
```
[projectId+status], [projectId+sprintId]
```

### `<authentication>`
Define the complete auth flow. Skip for projects with no user accounts.

```xml
<authentication>
  <strategy>Session-based with Supabase Auth</strategy>
  <providers>
    <email_password>
      - Sign up with email verification
      - Password reset via magic link
      - Minimum password: 8 chars, 1 uppercase, 1 number
    </email_password>
    <oauth>
      <google>Sign in with Google (default for quick onboarding)</google>
      <github>Sign in with GitHub (developer-focused audience)</github>
    </oauth>
  </providers>
  <session>
    <storage>HTTP-only cookie via Supabase SSR helper</storage>
    <duration>7 days, refresh on activity</duration>
    <refresh>Auto-refresh when token has less than 1 hour remaining</refresh>
  </session>
  <authorization>
    <roles>enum (owner, admin, member, viewer)</roles>
    <rules>
      - owner: full access, can delete project, transfer ownership
      - admin: manage members, edit settings, cannot delete project
      - member: create/edit own items, comment on others
      - viewer: read-only access to all project data
    </rules>
    <row_level_security>CRITICAL: All Supabase tables MUST have RLS policies. No direct table access without auth context.</row_level_security>
  </authorization>
  <protected_routes>
    - /dashboard/* — requires authenticated user
    - /admin/* — requires admin or owner role
    - /api/* — requires valid session token
  </protected_routes>
  <redirect_flows>
    - Unauthenticated user → /login (preserve intended destination)
    - After login → redirect to preserved destination or /dashboard
    - After signup → /onboarding (first-time flow)
  </redirect_flows>
</authentication>
```

### `<route_definitions>`
Complete URL structure. AI agents use this to scaffold all pages and set up routing guards.

```xml
<route_definitions>
  <public_routes>
    <route path="/" page="LandingPage" />
    <route path="/login" page="LoginPage" />
    <route path="/signup" page="SignupPage" />
    <route path="/reset-password" page="ResetPasswordPage" />
  </public_routes>
  <protected_routes guard="requireAuth">
    <route path="/dashboard" page="DashboardOverview" />
    <route path="/projects" page="ProjectListPage" />
    <route path="/projects/:id" page="ProjectDetailPage" />
    <route path="/projects/:id/settings" page="ProjectSettingsPage" guard="requireAdmin" />
    <route path="/settings" page="UserSettingsPage" />
  </protected_routes>
  <api_routes>
    <route path="/api/trpc/*" handler="tRPC router" />
    <route path="/api/webhooks/stripe" handler="Stripe webhook" method="POST" />
  </api_routes>
  <redirects>
    <redirect from="/app" to="/dashboard" status="301" />
  </redirects>
</route_definitions>
```

Rules:
- Use `:param` for dynamic segments
- Specify guards for protected routes (auth, role-based)
- Include API routes and webhooks
- List permanent redirects for legacy URLs

### `<component_hierarchy>`
Visual tree of React/UI components. Shows parent-child relationships and where shared components are reused.

```xml
<component_hierarchy>
  <app_shell>
    <providers> <!-- ThemeProvider → AuthProvider → QueryProvider → TRPCProvider -->
      <router>
        <!-- Public layout -->
        <public_layout>
          <navbar />                <!-- Logo, Login/Signup buttons -->
          <outlet />                <!-- LandingPage, LoginPage, etc. -->
          <footer />
        </public_layout>

        <!-- Authenticated layout -->
        <dashboard_layout>
          <sidebar>                 <!-- 240px fixed -->
            <workspace_switcher />
            <nav_links />           <!-- Dashboard, Projects, Settings -->
            <user_menu />           <!-- Avatar, logout -->
          </sidebar>
          <main_area>
            <top_bar>               <!-- Breadcrumb, search, notifications -->
              <breadcrumb />
              <global_search />
              <notification_bell />
            </top_bar>
            <page_content>          <!-- Scrollable area -->
              <outlet />            <!-- Dashboard, ProjectList, etc. -->
            </page_content>
          </main_area>
        </dashboard_layout>
      </router>
    </providers>
  </app_shell>

  <!-- Shared components (used across multiple pages) -->
  <shared>
    <modal />                       <!-- Generic modal wrapper -->
    <confirm_dialog />              <!-- Delete confirmation, etc. -->
    <toast_container />             <!-- Notification toasts -->
    <data_table />                  <!-- Sortable, filterable table -->
    <empty_state />                 <!-- Icon + message + CTA -->
    <loading_skeleton />            <!-- Placeholder while loading -->
  </shared>
</component_hierarchy>
```

Rules:
- Show nesting with indentation
- Add inline comments for dimensions, purpose
- Mark shared/reusable components separately
- Show provider wrapping order (outermost → innermost)

### `<pages_and_interfaces>`
The largest section. Organized hierarchically:

```xml
<pages_and_interfaces>
  <global_layout>
    <top_navigation>...</top_navigation>
    <sidebar>...</sidebar>
    <main_content>...</main_content>
  </global_layout>
  <page_name_view>
    <header>...</header>
    <main_section>...</main_section>
    <sub_component>...</sub_component>
    <empty_state>...</empty_state>
  </page_name_view>
  <!-- repeat for each page/view -->
  <keyboard_shortcuts_reference>...</keyboard_shortcuts_reference>
</pages_and_interfaces>
```

For each UI element, specify:
- Dimensions (px values: height, width, padding, gap)
- Colors (hex codes with semantic names)
- Behaviors (hover, click, drag, keyboard)
- Content structure (what appears, order, truncation)
- States (empty, loading, error, active, selected)
- Animations (duration, easing, effect)

### `<api_endpoints>`
Replaces `pages_and_interfaces` for API/backend projects. One `<endpoint>` per route, grouped by resource.

```xml
<api_endpoints>
  <base_url>/api/v1</base_url>
  <content_type>application/json (요청/응답 모두)</content_type>
  <resource name="links">
    <endpoint>
      <route>POST /links</route>
      <purpose>단축 링크 생성</purpose>
      <auth>Bearer token 필수</auth>
      <request>
        {
          "url": "string (required, 유효한 http/https URL, max 2048자)",
          "slug": "string (optional, 3-32자, [a-z0-9-], 미지정 시 자동 생성)",
          "expiresAt": "ISO 8601 datetime (optional, 미래 시각만 허용)"
        }
      </request>
      <response status="201">
        { "id": "uuid", "slug": "string", "shortUrl": "string", "createdAt": "ISO 8601" }
      </response>
      <errors>
        - 400 INVALID_URL: url 형식 오류 또는 길이 초과
        - 409 SLUG_TAKEN: slug 중복
        - 401 UNAUTHORIZED: 토큰 누락/만료
        - 422 EXPIRY_IN_PAST: expiresAt이 과거 시각
      </errors>
      <rate_limit>60 req/min per user</rate_limit>
    </endpoint>
  </resource>
  <error_response_format>
    모든 에러는 { "error": { "code": "MACHINE_READABLE_CODE", "message": "사람이 읽는 설명" } } 형식.
    code는 SCREAMING_SNAKE_CASE, 클라이언트 분기용. message는 로깅/디버깅용이며 UI 노출 금지.
  </error_response_format>
  <pagination>cursor 기반: ?cursor=<opaque>&limit=20 (max 100). 응답에 nextCursor 포함, 마지막 페이지는 null.</pagination>
  <versioning>URL prefix (/api/v1). 브레이킹 체인지 시 v2 신설, v1은 6개월 유지.</versioning>
</api_endpoints>
```

Rules:
- Every endpoint: route, purpose, auth requirement, full request/response schemas with types and constraints, error cases with machine-readable codes
- Define the global error envelope, pagination, and versioning strategy once — endpoints reference them
- Include rate limits per endpoint when they differ from the global default

### `<commands_and_flags>`
Replaces `pages_and_interfaces` for CLI tools. One `<command>` per subcommand.

```xml
<commands_and_flags>
  <binary_name>snapkit</binary_name>
  <global_flags>
    - --config <path>: 설정 파일 경로 (기본: ~/.snapkit/config.toml)
    - --json: 사람용 출력 대신 JSON 출력 (스크립팅용)
    - --quiet / -q: 에러 외 출력 억제
    - --version / -V, --help / -h
  </global_flags>
  <command>
    <name>snapkit backup <target-dir></name>
    <purpose>대상 디렉토리의 스냅샷 생성</purpose>
    <arguments>
      - target-dir: 백업할 디렉토리 (required, 존재해야 함)
    </arguments>
    <flags>
      - --exclude <glob>: 제외 패턴, 반복 지정 가능
      - --dry-run: 실제 쓰기 없이 대상 파일 목록만 출력
    </flags>
    <output>
      성공: "✓ Backed up 1,204 files (89 MB) → snapshots/2026-07-28T09-00-00/" (stdout)
      --json: {"files": 1204, "bytes": 93323264, "path": "..."}
    </output>
    <exit_codes>0 성공, 1 일반 오류, 2 인자 오류, 3 대상 디렉토리 없음</exit_codes>
    <interactive_prompts>덮어쓰기 충돌 시 [y/N] 확인. --quiet 또는 non-TTY에서는 프롬프트 없이 실패(exit 4).</interactive_prompts>
  </command>
</commands_and_flags>
```

Rules:
- Specify exit codes per command — scripts depend on them
- Define behavior in non-TTY/piped contexts (no colors, no prompts, no spinners)
- Show exact output text for success and failure cases

### `<public_api>`
Replaces `pages_and_interfaces` for libraries/SDKs. Organized by export.

```xml
<public_api>
  <entry_point>import { createClient, RateLimitError } from '@acme/sdk'</entry_point>
  <export>
    <signature>createClient(options: ClientOptions): AcmeClient</signature>
    <purpose>SDK 진입점. 인증 정보와 기본 설정으로 클라이언트 생성.</purpose>
    <parameters>
      - options.apiKey: string (required)
      - options.baseUrl: string (optional, 기본 https://api.acme.dev)
      - options.timeout: number (optional, ms, 기본 30000)
      - options.retries: number (optional, 기본 3, 지수 백오프)
    </parameters>
    <returns>AcmeClient 인스턴스 (모든 리소스 메서드의 루트)</returns>
    <throws>ConfigError: apiKey 누락 시 (생성 시점에 즉시)</throws>
    <example>
      const client = createClient({ apiKey: process.env.ACME_API_KEY });
      const user = await client.users.get('usr_123');
    </example>
  </export>
  <error_hierarchy>
    AcmeError (base) ← ApiError (status, code 보유) ← RateLimitError (retryAfter 보유)
    CRITICAL: 모든 공개 메서드는 AcmeError 하위 타입만 throw. 원시 fetch 에러 노출 금지.
  </error_hierarchy>
  <breaking_change_policy>SemVer 준수. deprecated API는 최소 1 minor 버전 동안 경고 후 major에서 제거.</breaking_change_policy>
</public_api>
```

Rules:
- Every export: full signature with types, parameters with defaults, return value, thrown errors, usage example
- Define the error hierarchy — consumers program against it
- State the SemVer/deprecation policy

### `<core_functionality>`
Group by functional domain. Each domain lists capabilities as bullet points.

```xml
<core_functionality>
  <entity_management>
    - CRUD operations
    - Relationships and linking
    - Bulk operations with specific actions listed
  </entity_management>
  <search_and_filter>...</search_and_filter>
  <data_persistence>...</data_persistence>
  <!-- etc. -->
</core_functionality>
```

### `<ai_integration>`
For any project with LLM-powered features. AI features fail differently from normal code (nondeterminism, latency, cost, refusals), so the spec must pin down what regular sections can't.

```xml
<ai_integration>
  <features>
    - 문서 요약: 업로드된 PDF를 3문단 이내로 요약
    - 태그 추천: 요약 결과 기반으로 기존 태그 중 최대 5개 추천
  </features>
  <provider_and_models>
    <provider>Anthropic Claude API (@anthropic-ai/sdk, latest stable)</provider>
    <model_per_feature>
      - 문서 요약: claude-sonnet-5 (긴 문서, 품질 우선)
      - 태그 추천: claude-haiku-4-5-20251001 (짧은 입력, 저지연/저비용)
    </model_per_feature>
    <note>모델 ID는 설정/env로 주입 — 코드에 하드코딩 금지 (모델 교체 대비)</note>
  </provider_and_models>
  <prompts>
    <summarize_document>
      - System: 역할, 출력 형식(3문단, 한국어), 금지사항 명시
      - 문서 본문은 XML 태그로 감싸 전달: <document>...</document>
      - 프롬프트는 코드가 아닌 별도 파일(prompts/)로 관리, 버전 주석 포함
    </summarize_document>
  </prompts>
  <io_constraints>
    - 입력 한도: 문서당 최대 100K tokens, 초과 시 앞부분 우선 truncate + 사용자 경고
    - 출력 형식: JSON 강제 시 tool use(structured output) 사용 — 프롬프트로만 강제하지 않기
    - 스트리밍: 요약은 streaming으로 UI에 점진 표시, 태그 추천은 non-streaming
  </io_constraints>
  <failure_handling>
    - 타임아웃: 60s, 초과 시 재시도 1회 후 "요약 실패" 상태로 저장 (원문은 보존)
    - Rate limit(429): 지수 백오프 재시도 (2s, 8s), 이후 큐 대기 상태 표시
    - 거부/빈 응답: "AI가 이 문서를 처리할 수 없습니다" + 수동 태그 입력 폴백
    - CRITICAL: AI 실패가 핵심 기능(업로드/저장)을 블로킹하면 안 됨 — AI는 항상 부가 기능
  </failure_handling>
  <cost_and_limits>
    - 사용자당 요약 한도: 50건/일 (초과 시 안내 메시지)
    - 예상 비용 상한 계산 근거 명시: 평균 20K input tokens × 50건 × 단가
  </cost_and_limits>
  <evaluation>
    - 요약 품질 스모크 테스트: 고정 문서 3종에 대해 핵심 키워드 포함 여부 검증
  </evaluation>
</ai_integration>
```

Rules:
- Specify model per feature with rationale (quality vs latency vs cost) — one model for everything is usually wrong
- Model IDs go in config/env, never hardcoded
- Define failure behavior for every AI call: timeout, rate limit, refusal, malformed output
- State cost guardrails (per-user limits, token caps) — AI features without limits are a billing incident waiting to happen

### `<aesthetic_guidelines>`
The design system. Sub-sections:

```xml
<aesthetic_guidelines>
  <design_fusion>  <!-- high-level design philosophy -->
  <color_palette>
    <primary_colors>  <!-- brand colors with hex + usage -->
    <background_colors>
    <text_colors>
    <status_colors>
    <priority_colors>  <!-- or other semantic groups -->
    <dark_theme>  <!-- if applicable -->
  </color_palette>
  <typography>
    <font_families>  <!-- with fallback stacks -->
    <font_sizes>     <!-- with weight and context -->
    <line_heights>
  </typography>
  <spacing>  <!-- base unit and scale -->
  <borders_and_shadows>
    <borders>  <!-- thickness, color, radius -->
    <shadows>  <!-- named levels: card, dropdown, modal -->
  </borders_and_shadows>
  <component_styling>
    <!-- one sub-tag per component type: buttons, inputs, dropdowns, cards, badges, avatars, modals, panels -->
  </component_styling>
  <animations>
    <micro_interactions>
    <page_transitions>
    <drag_and_drop>
    <loading_states>
    <orchestrated_entrance>
  </animations>
  <responsive_design>
    <breakpoints>
      <!-- Define breakpoints with layout changes -->
    </breakpoints>
    <mobile_adaptations>
      <!-- How components transform on small screens -->
    </mobile_adaptations>
    <touch_interactions>
      <!-- Touch-specific behaviors (swipe, long-press) -->
    </touch_interactions>
  </responsive_design>
  <icons>  <!-- library, sizes, stroke -->
  <accessibility>  <!-- WCAG, focus, keyboard, motion -->
</aesthetic_guidelines>
```

#### Responsive Design Detail

The `<responsive_design>` section should specify:

```xml
<responsive_design>
  <breakpoints>
    - mobile: 0–639px (single column, bottom nav, full-width cards)
    - tablet: 640–1023px (collapsible sidebar, 2-column grid)
    - desktop: 1024–1279px (fixed sidebar, 3-column grid)
    - wide: 1280px+ (max-width 1440px container, centered)
  </breakpoints>
  <mobile_adaptations>
    - Sidebar → bottom tab bar (5 icons max, 56px height)
    - Data tables → card list view (one card per row)
    - Modal dialogs → full-screen sheets (slide up from bottom)
    - Multi-column layouts → single column, stacked
    - Hover tooltips → long-press tooltips (300ms delay)
    - Drag-and-drop → disabled on touch, use move up/down buttons
  </mobile_adaptations>
  <touch_interactions>
    - Swipe left on list item → reveal delete action (red, 80px)
    - Swipe right on list item → reveal archive action (blue, 80px)
    - Pull-to-refresh on list views (spinner appears at -60px threshold)
    - Long-press (500ms) on card → enter selection mode
    - Minimum tap target: 44x44px (WCAG 2.5.8)
  </touch_interactions>
</responsive_design>
```

Color format: `- Semantic Name: #HEX - usage description`

#### Accessibility Detail

The `<accessibility>` subsection is not a one-liner — specify concretely:

```xml
<accessibility>
  <target>WCAG 2.1 AA</target>
  <contrast>
    - 본문 텍스트: 배경 대비 4.5:1 이상 (팔레트의 text/background 조합으로 검증)
    - 대형 텍스트(18px+ bold, 24px+): 3:1 이상
    - 비활성 요소는 예외이나 placeholder 텍스트는 4.5:1 준수
  </contrast>
  <keyboard>
    - 모든 인터랙티브 요소는 Tab 도달 가능, 논리적 포커스 순서 (DOM 순서 = 시각 순서)
    - 포커스 링: 2px solid accent 색, offset 2px — outline 제거 금지
    - 모달: 포커스 트랩, Escape로 닫기, 닫힌 후 트리거 요소로 포커스 복귀
  </keyboard>
  <screen_readers>
    - 아이콘 전용 버튼: aria-label 필수
    - 동적 콘텐츠(토스트, 검색 결과 수): aria-live="polite"
    - 폼 에러: aria-describedby로 입력과 연결
  </screen_readers>
  <motion>
    - prefers-reduced-motion 존중: 애니메이션 → 즉시 전환으로 대체
  </motion>
</accessibility>
```

### `<output_formatting>`
Replaces `aesthetic_guidelines` for CLI tools — terminal output styling.

```xml
<output_formatting>
  <colors>
    - 성공: green (ANSI 32), 에러: red (31), 경고: yellow (33), 정보 라벨: dim (2)
    - NO_COLOR env var 또는 non-TTY 감지 시 색상 전면 비활성화
  </colors>
  <structure>
    - 진행 표시: TTY에서 spinner, non-TTY에서는 라인 단위 로그
    - 표 출력: 컬럼 정렬, 터미널 폭 초과 시 우선순위 낮은 컬럼부터 생략
    - 에러 메시지 형식: "error: <원인>. <해결 힌트>" (stderr로 출력)
  </structure>
  <verbosity>-q(에러만) / 기본 / -v(디버그) 3단계, --json은 verbosity 무시하고 구조화 출력만</verbosity>
</output_formatting>
```

### `<api_design_principles>`
Replaces `aesthetic_guidelines` for libraries/SDKs — API ergonomics rules.

```xml
<api_design_principles>
  - 네이밍: 동사+명사 메서드 (getUser, listInvoices), boolean은 is/has 접두사
  - 비동기: 모든 I/O는 Promise 반환, 콜백 API 금지
  - 기본값: 제로 컨피그로 동작하되 모든 기본값을 옵션으로 재정의 가능
  - 에러: 문자열 throw 금지, 타입 있는 에러 계층만 사용
  - 의존성: 런타임 의존성 최소화 (목표 0-2개), peer dependency 명시
  - 타입: 공개 API 전체에 명시적 타입 선언, any 노출 금지
</api_design_principles>
```

### `<internationalization>`
Include when the product targets multiple languages/locales. Skip for single-locale projects (state the locale in `<overview>` instead).

```xml
<internationalization>
  <locales>
    - 지원: ko-KR (기본), en-US
    - 언어 감지: 사용자 설정 > 브라우저 Accept-Language > 기본값
  </locales>
  <strings>
    - 라이브러리: i18next v25 (latest stable) + react-i18next
    - 모든 사용자 노출 문자열은 리소스 파일(locales/{lang}/common.json)로 분리 — 하드코딩 금지
    - 키 네이밍: 화면.요소.상태 (예: taskList.emptyState.title)
    - 복수형: 라이브러리의 plural 규칙 사용, 수동 분기 금지
  </strings>
  <formatting>
    - 날짜/시간: Intl.DateTimeFormat, 로케일별 형식 (2026. 7. 28. vs Jul 28, 2026)
    - 숫자/통화: Intl.NumberFormat (₩1,234 vs $1,234.00)
    - CRITICAL: 서버 저장은 항상 UTC + ISO 8601, 표시 시점에만 로케일 변환
  </formatting>
  <layout>
    - 텍스트 확장 대비: 버튼/라벨은 영어 대비 한국어 ±30% 길이 변화 수용 (truncate 규칙 명시)
    - RTL: 지원 안 함 (out_of_scope에 명시)
  </layout>
</internationalization>
```

### `<error_handling>`
Define how the app communicates errors to users and how it recovers from failures.

```xml
<error_handling>
  <user_facing>
    <toast_notifications>
      - Success: green (#22C55E), 3s auto-dismiss, bottom-right
      - Error: red (#EF4444), persistent until dismissed, bottom-right
      - Warning: amber (#F59E0B), 5s auto-dismiss, bottom-right
      - Info: blue (#3B82F6), 3s auto-dismiss, bottom-right
      - Max 3 toasts stacked, oldest dismissed first
    </toast_notifications>
    <form_validation>
      - Inline errors below each field, red (#EF4444) text, 13px
      - Show on blur (not on keystroke) for better UX
      - Scroll to first error on submit
      - Shake animation (200ms) on invalid submit attempt
    </form_validation>
    <error_pages>
      - 404: illustration + "Page not found" + link to dashboard
      - 500: illustration + "Something went wrong" + retry button
      - 403: "You don't have access" + request access CTA
      - Offline: banner at top "You're offline. Changes will sync when reconnected."
    </error_pages>
  </user_facing>
  <error_boundaries>
    - Wrap each page in a React Error Boundary
    - Show fallback UI with "Something went wrong" + retry button
    - Log error details to console in development
  </error_boundaries>
  <api_errors>
    - Network failure: retry up to 3 times with exponential backoff (1s, 2s, 4s)
    - 401 Unauthorized: redirect to /login, clear session
    - 429 Rate limited: show "Too many requests, please wait" toast
    - 5xx: show generic error toast, log to error tracking
  </api_errors>
</error_handling>
```

### `<third_party_integrations>`
External services and APIs the project depends on. Include setup steps, SDK usage, and webhook handling.

```xml
<third_party_integrations>
  <integration name="Stripe">
    <purpose>Payment processing for subscription billing</purpose>
    <sdk>@stripe/stripe-js v2.4 (client) + stripe v14.x (server)</sdk>
    <features>
      - Checkout session for subscription signup
      - Customer portal for billing management
      - Webhook for payment events (invoice.paid, subscription.deleted)
    </features>
    <webhook_endpoint>/api/webhooks/stripe</webhook_endpoint>
    <events_handled>
      - checkout.session.completed → activate subscription
      - invoice.paid → extend billing period
      - customer.subscription.deleted → downgrade to free tier
    </events_handled>
  </integration>
  <integration name="Resend">
    <purpose>Transactional email (welcome, password reset, notifications)</purpose>
    <sdk>resend v3.x</sdk>
    <templates>
      - welcome_email: sent after signup confirmation
      - password_reset: magic link with 1h expiry
      - weekly_digest: project activity summary (opt-in)
    </templates>
  </integration>
</third_party_integrations>
```

### `<security_considerations>`
Security requirements and hardening measures. CRITICAL for any app handling user data.

```xml
<security_considerations>
  <input_validation>
    - CRITICAL: Sanitize ALL user input on the server side, even if validated on client
    - Use zod schemas for request validation on every API endpoint
    - Max input lengths: title (200 chars), description (10,000 chars), comment (5,000 chars)
    - Strip HTML tags from text inputs (use DOMPurify if rich text is needed)
  </input_validation>
  <authentication_security>
    - Passwords: bcrypt with cost factor 12 (handled by Supabase Auth)
    - Session tokens: HTTP-only, Secure, SameSite=Lax cookies
    - CSRF: Supabase Auth handles via cookie-based sessions
    - Rate limit login attempts: 5 per minute per IP
  </authentication_security>
  <data_protection>
    - CRITICAL: Never expose user IDs or internal IDs in URLs if predictable (use UUIDs)
    - Row Level Security on ALL Supabase tables
    - API responses must never include fields the requesting user shouldn't see
    - Soft-delete user data, hard-delete after 30 days
  </data_protection>
  <api_security>
    - All API routes require valid session (except public endpoints)
    - CORS: restrict to application domain only
    - Rate limiting: 100 requests/minute per authenticated user
    - File uploads: max 10MB, allowed types (image/png, image/jpeg, application/pdf)
  </api_security>
  <client_security>
    - CRITICAL: Never store secrets in client-side code or NEXT_PUBLIC_ env vars
    - Content Security Policy headers
    - Strict-Transport-Security header
    - X-Content-Type-Options: nosniff
  </client_security>
</security_considerations>
```

Rules:
- Prefix non-negotiable rules with `CRITICAL:`
- Be specific about limits (max lengths, rate limits, file sizes)
- Cover: input validation, auth, data protection, API, client-side, headers

### `<advanced_functionality>`
Features beyond core CRUD. Examples: bulk operations, keyboard shortcuts, smart defaults, notifications, offline support, multi-user.

### `<final_integration_test>`
Numbered test scenarios. Each scenario:

```xml
<test_scenario_N>
  <description>Scenario Title</description>
  <steps>
    1. Action step
    2. Verify expected result
    ...
  </steps>
</test_scenario_N>
```

Rules:
- 8-15 steps per scenario
- Alternate between user actions and verification steps
- Cover the critical user journeys end-to-end
- Include edge cases (empty states, limits, errors)

### `<success_criteria>`
Grouped by dimension:

```xml
<success_criteria>
  <functionality>  <!-- what must work -->
  <user_experience>  <!-- performance, usability -->
  <technical_quality>  <!-- code quality, architecture -->
  <visual_design>  <!-- design consistency -->
  <build>  <!-- deployment, compatibility -->
</success_criteria>
```

Each contains bullet points with specific, measurable criteria.

### `<build_output>`
Build command, output directory, contents description, deployment notes.

### `<deployment_and_operations>`
How the project ships and how it's observed in production. Skip for purely local apps (a one-line `<note>` explaining why is enough).

```xml
<deployment_and_operations>
  <environments>
    - local: docker compose (앱 + PostgreSQL), 시드 데이터 자동 주입
    - staging: main 브랜치 push 시 자동 배포, 프로덕션 동일 구성 + 별도 DB
    - production: 태그(v*) push 시 배포, 수동 승인 게이트 1단계
  </environments>
  <ci_cd>
    - GitHub Actions: lint → typecheck → test → build → deploy
    - PR 필수 체크: 테스트 통과 + 타입 에러 0
    - 롤백: 직전 이미지 태그로 재배포 (원클릭), DB 마이그레이션은 별도 down 스크립트
  </ci_cd>
  <hosting>
    - 앱: Vercel (또는 컨테이너: Fly.io) — 선택 근거 명시
    - DB: Supabase managed PostgreSQL, 일 1회 자동 백업 + 7일 보관
  </hosting>
  <observability>
    <logging>
      - 구조화 JSON 로그 (level, timestamp, requestId, userId)
      - CRITICAL: 로그에 PII/토큰/비밀번호 출력 금지
    </logging>
    <error_tracking>Sentry — 프론트/백 모두, release 태그 연동, 알림: 신규 이슈 발생 시</error_tracking>
    <metrics>
      - 핵심 지표: p95 응답시간, 에러율, 활성 사용자 수
      - 헬스체크: GET /healthz (DB 연결 포함), 배포 게이트로 사용
    </metrics>
  </observability>
  <backups_and_recovery>
    - DB: 일간 스냅샷 7일 + 주간 4주 보관
    - 복구 목표: RPO 24h, RTO 1h (개인 프로젝트 기준 — 프로젝트 성격에 맞게 조정)
  </backups_and_recovery>
</deployment_and_operations>
```

Rules:
- Name concrete services and the rationale for choosing them
- Always define rollback — a deploy pipeline without rollback is half a pipeline
- Logging rules must state what NOT to log (PII, secrets)

### `<key_implementation_notes>`
Technical guidance for the builder:

```xml
<key_implementation_notes>
  <critical_paths>  <!-- what to get right first -->
  <recommended_implementation_order>  <!-- numbered list -->
  <database_schema>  <!-- concrete code if applicable -->
  <performance_considerations>
  <testing_strategy>
  <tool_usage>  <!-- dev tools, screenshots, etc. -->
</key_implementation_notes>
```

---

## Section Applicability by Project Type

| Section | Web App | API/Backend | CLI Tool | Mobile | Library |
|---------|---------|-------------|----------|--------|---------|
| overview | ✅ | ✅ | ✅ | ✅ | ✅ |
| assumptions | ✅ | ✅ | ✅ | ✅ | ✅ |
| open_questions | ✅ | ✅ | ✅ | ✅ | ✅ |
| scope_boundaries | ✅ | ✅ | △ | ✅ | △ |
| technology_stack | ✅ | ✅ | ✅ | ✅ | ✅ |
| prerequisites | ✅ | ✅ | ✅ | ✅ | ✅ |
| environment_variables | ✅ | ✅ | △ | ✅ | ✗ |
| file_structure | ✅ | ✅ | ✅ | ✅ | ✅ |
| core_data_entities | ✅ | ✅ | △ | ✅ | △ |
| authentication | ✅ | ✅ | ✗ | ✅ | ✗ |
| route_definitions | ✅ | ✅ | ✗ | ✅ | ✗ |
| component_hierarchy | ✅ | ✗ | ✗ | ✅ | ✗ |
| pages_and_interfaces | ✅ | ✗ | ✗ | ✅ | ✗ |
| api_endpoints | △¹ | ✅ | ✗ | △¹ | ✗ |
| commands_and_flags | ✗ | ✗ | ✅ | ✗ | ✗ |
| public_api | ✗ | ✗ | ✗ | ✗ | ✅ |
| core_functionality | ✅ | ✅ | ✅ | ✅ | ✅ |
| ai_integration | △² | △² | △² | △² | △² |
| error_handling | ✅ | ✅ | ✅ | ✅ | △ |
| third_party_integrations | ✅ | ✅ | △ | ✅ | △ |
| aesthetic_guidelines | ✅ | ✗ | ✗ | ✅ | ✗ |
| output_formatting | ✗ | ✗ | ✅ | ✗ | ✗ |
| api_design_principles | ✗ | △ | ✗ | ✗ | ✅ |
| internationalization | △³ | △³ | △³ | △³ | ✗ |
| security_considerations | ✅ | ✅ | △ | ✅ | △ |
| advanced_functionality | ✅ | △ | △ | ✅ | △ |
| final_integration_test | ✅ | ✅ | ✅ | ✅ | ✅ |
| success_criteria | ✅ | ✅ | ✅ | ✅ | ✅ |
| build_output | ✅ | ✅ | ✅ | ✅ | ✅ |
| deployment_and_operations | △⁴ | ✅ | ✗ | △ | ✗ |
| key_implementation_notes | ✅ | ✅ | ✅ | ✅ | ✅ |

✅ = Include, △ = Optional, ✗ = Skip

¹ Include when a fullstack app has its own API surface (in addition to pages_and_interfaces)
² Include only if the project has LLM-powered features
³ Include only for multi-locale products
⁴ Include unless the app is purely local/offline (then add a one-line note)

---

## Writing Quality Checklist

- [ ] Every color is a hex code, not a name
- [ ] Every dimension is in px (or rem/% with rationale)
- [ ] Every library version is verified or written as major + "(latest stable)" — no invented minor/patch numbers
- [ ] Every enum lists all possible values
- [ ] Data entities have complete field definitions with types
- [ ] UI specs include hover, active, disabled, empty states
- [ ] Keyboard shortcuts are specified for all key interactions
- [ ] Animations specify duration and easing
- [ ] Success criteria are measurable (numbers, not vague qualities)
- [ ] Implementation order reflects dependency chain
- [ ] Test scenarios cover all critical user journeys
- [ ] Scope boundaries clearly state what is out of scope
- [ ] File structure tree covers all major directories and key files
- [ ] Component hierarchy shows provider wrapping order and shared components
- [ ] Responsive breakpoints defined with mobile layout adaptations
- [ ] Auth flow covers login, signup, session, roles, and protected routes
- [ ] Error handling covers toasts, form validation, error pages, and API errors
- [ ] Security section addresses input validation, data protection, and API security
- [ ] All environment variables listed with required/optional and example values
- [ ] Route definitions cover all pages, guards, and API endpoints
- [ ] Third-party integrations list SDKs, webhooks, and event handlers
- [ ] Unconfirmed decisions recorded in assumptions (decision + rationale + impact if wrong)
- [ ] User-only decisions recorded in open_questions (numbered, with the section each unblocks)
- [ ] AI features (if any) specify model per feature, failure handling, and cost limits
- [ ] API endpoints (if any) define error envelope, pagination, versioning, and per-endpoint error codes
- [ ] CLI commands (if any) define exit codes and non-TTY behavior
- [ ] Deployment section defines rollback and what NOT to log
- [ ] Consistency: routes ↔ pages, UI fields ↔ entities, used colors ↔ palette, mentioned env vars ↔ environment_variables, mentioned libraries ↔ technology_stack
