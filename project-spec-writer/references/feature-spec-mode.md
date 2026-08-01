# Feature Spec Mode — Specs for Existing Codebases

Use this mode when the user wants to spec a feature (or a set of changes) for a codebase that already exists, rather than a greenfield project. The core difference: a greenfield spec invents everything; a feature spec must **discover and respect what already exists**. Most feature-spec failures come from specifying things that contradict the codebase's actual conventions.

## Workflow

### 1. Analyze the Codebase First

Never write a feature spec from the user's description alone. Before drafting, establish:

- **Stack & versions**: read `package.json` / `pyproject.toml` / `go.mod` etc. — the spec must reference the versions actually installed, not ideal ones
- **Conventions**: file organization, naming patterns, state management approach, error handling idioms, test framework and patterns
- **Relevant modules**: the files/components/tables the feature will touch or extend
- **Existing patterns to reuse**: if the codebase already has a modal system, a form validation pattern, or an API client wrapper, the spec must use them — introducing a parallel pattern is a defect

Use subagents (e.g., an Explore agent) for broad codebase survey when available; read key files directly for the parts the feature touches.

### 2. Interview for the Feature Intent

Same what/who/how questions as greenfield, plus:

- Where does this feature live in the existing UI/API surface?
- What existing behavior must NOT change? (regression boundary)
- Is there a migration concern (existing data, existing users)?

Technology choices are usually inherited, not chosen — only raise stack questions when the feature genuinely needs something new (a new library, a new service). Confirm any new dependency with the user.

### 3. Draft the Feature Spec

Root tag is `<feature_specification>`. Section order:

```
feature_name → overview → assumptions → open_questions →
existing_codebase_context → scope_boundaries →
data_model_changes → api_changes → ui_changes →
integration_points → core_functionality → error_handling →
regression_risks → migration_plan →
final_integration_test → success_criteria → implementation_order
```

Reuse section formats from [xml-schema.md](xml-schema.md) where they overlap (`assumptions`, `open_questions`, `scope_boundaries`, `error_handling`, `final_integration_test`, `success_criteria`). The feature-specific sections:

### `<existing_codebase_context>`
What the builder must know about the codebase before touching it. This is the section that prevents convention violations.

```xml
<existing_codebase_context>
  <stack>Next.js 14.2 (App Router) + TypeScript 5.4 + Prisma 5.10 + PostgreSQL — package.json 기준 실측</stack>
  <conventions>
    - API: src/app/api/*/route.ts, zod로 요청 검증, 에러는 lib/api-error.ts의 ApiError로 throw
    - 컴포넌트: src/components/{feature}/ 폴더, named export만 사용
    - 상태: 서버 상태는 TanStack Query, 클라이언트 상태는 useState (전역 스토어 없음 — 도입 금지)
    - 테스트: Vitest + Testing Library, *.test.tsx 동일 폴더 배치
  </conventions>
  <relevant_modules>
    - src/components/comments/ — 이번 기능(대댓글)이 확장할 기존 댓글 UI
    - prisma/schema.prisma의 Comment 모델 — parentId 필드 추가 대상
    - src/app/api/comments/route.ts — 목록/생성 API, 트리 조회로 변경 필요
  </relevant_modules>
  <reuse_do_not_reinvent>
    - 확인 다이얼로그: components/ui/confirm-dialog.tsx 사용 (새 모달 만들지 말 것)
    - 상대 시간 표시: lib/format.ts의 timeAgo() 사용
  </reuse_do_not_reinvent>
</existing_codebase_context>
```

### `<data_model_changes>`
Only the delta — new tables/fields/indexes, altered constraints. For each change: the migration and its backward compatibility.

```xml
<data_model_changes>
  <change entity="Comment">
    - ADD parentId: String? (nullable FK → Comment.id, onDelete: Cascade)
    - ADD INDEX [postId, parentId]
    - 기존 데이터: 전부 parentId = null (최상위 댓글) — 백필 불필요
  </change>
  <migration>
    - prisma migrate로 단일 마이그레이션, 롤백: parentId 컬럼 drop
    - CRITICAL: 배포 순서 — 마이그레이션 먼저, 앱 배포 나중 (nullable이므로 구버전 앱과 호환)
  </migration>
</data_model_changes>
```

### `<api_changes>` / `<ui_changes>`
Same formats as `<api_endpoints>` / `<pages_and_interfaces>` in the main schema, but split into **modified** vs **added**. For modified endpoints/views, state exactly what changes and what stays identical — "응답에 replies 필드 추가, 기존 필드는 모두 불변" beats re-describing the whole endpoint.

### `<integration_points>`
Where the feature connects to existing code — the seams. Each entry: file/module, what hooks in, and the contract at that seam.

### `<regression_risks>`
What existing behavior could break, and how the builder verifies it didn't.

```xml
<regression_risks>
  - 댓글 수 카운트: Post.commentCount가 대댓글 포함인지 정의 필요 (포함으로 결정 → 기존 카운트 로직 수정) — 기존 게시글 목록 화면에서 검증
  - 댓글 삭제: cascade로 대댓글 동반 삭제 — 삭제 확인 문구에 명시, 기존 삭제 테스트 업데이트
  - 알림: 기존 "내 글에 댓글" 알림이 대댓글에도 발화하는지 — 발화하도록 확장하되 중복 알림 금지
</regression_risks>
```

### `<migration_plan>`
Include when existing data or users are affected: data backfill, feature flags, staged rollout, deploy ordering. Skip (with a one-line note) when the feature is purely additive.

### `<implementation_order>`
Numbered steps respecting dependencies, each mapped to the files it touches. Start with the migration/data layer, end with polish.

## Review

Run the same consistency pass as greenfield mode, plus feature-specific checks:

- Every convention stated in `existing_codebase_context` is actually followed by the rest of the spec
- Every modified file mentioned in the spec exists in the codebase (verify paths — don't spec edits to imagined files)
- Every regression risk has a verification step in `final_integration_test`
- New dependencies (if any) were explicitly confirmed by the user

Then run `python3 scripts/validate_spec.py <SPEC.md>` (it accepts `<feature_specification>` roots).

## Output

Filename: `FEATURE_NAME_FEATURE_SPEC.md` (e.g., `NESTED_COMMENTS_FEATURE_SPEC.md`), saved to the repo root or a `docs/specs/` directory if one exists. Language policy follows SKILL.md (Korean content by default, identifiers in English).
