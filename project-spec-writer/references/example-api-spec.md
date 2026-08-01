# Example Spec: LinkHub (API/Backend Project, Korean Content)

This example shows two things at once: (1) how a backend API spec uses `<api_endpoints>` instead of `pages_and_interfaces`, and (2) the default language policy in action — prose in Korean, all identifiers/code/paths in English.

---

```xml
<project_specification>

<project_name>LinkHub - 사내 URL 단축 서비스 API</project_name>

<overview>
LinkHub는 사내 구성원이 긴 URL을 짧은 링크로 변환하고 클릭 통계를 확인할 수 있는 REST API 서비스다. 사내 위키·메신저에서 공유되는 긴 링크를 짧고 기억하기 쉬운 형태로 관리하는 것이 핵심 가치다.

주요 기능: 단축 링크 생성(커스텀 slug 지원), 리다이렉트, 링크별 클릭 통계 집계, 만료 일시 설정, 소유자 기반 링크 관리.

CRITICAL: 이 프로젝트는 API 서버만 포함한다. 웹 UI는 별도 프로젝트이며 이 스펙의 범위가 아니다. 모든 응답은 JSON이고, 리다이렉트 엔드포인트(GET /{slug})만 예외적으로 302를 반환한다.
</overview>

<assumptions>
  - 인증: 사내 SSO(OIDC)가 이미 존재한다고 가정하고 JWT 검증만 구현. SSO가 없다면 authentication 섹션 재설계 필요.
  - 트래픽 규모: 일 10만 리다이렉트 이하 가정 → 단일 인스턴스 + Redis 캐시로 충분. 초과 시 수평 확장 검토.
  - slug 충돌 정책: 자동 생성 slug는 재시도 3회로 충돌 해소 가능하다고 가정 (7자 base62 = 3.5조 조합).
</assumptions>

<open_questions>
  - Q1. 링크 만료 후 slug 재사용 허용 여부? → core_data_entities의 unique 제약 및 삭제 정책에 영향
  - Q2. 클릭 통계에 리퍼러/기기 정보까지 수집할지, 카운트만 할지? → 개인정보 검토 필요, click_event 스키마에 영향
  - Q3. 관리자 권한(타인 링크 삭제)이 필요한가? → authorization rules에 영향
</open_questions>

<scope_boundaries>
  <in_scope>
    - 단축 링크 CRUD (생성, 조회, 목록, 수정, 삭제)
    - slug 리다이렉트 (302) + 클릭 카운트
    - 링크별 일 단위 클릭 통계 조회
    - 만료 일시(expiresAt) 지원 — 만료 링크는 410 Gone
    - JWT 기반 인증, 소유자만 자기 링크 수정/삭제
    - Rate limiting (생성 60 req/min, 리다이렉트 무제한)
  </in_scope>
  <out_of_scope>
    - 웹 UI (별도 프로젝트)
    - QR 코드 생성
    - 커스텀 도메인 (go.company.com 단일 도메인만)
    - 링크 미리보기(OG 태그 파싱)
    - 실시간 통계 스트리밍
  </out_of_scope>
  <future_considerations>
    - 팀 단위 링크 네임스페이스 (Phase 2)
    - Slack 봇 연동 (Phase 2)
  </future_considerations>
</scope_boundaries>

<technology_stack>
  <backend>
    <runtime>Python 3.12 + uvicorn</runtime>
    <framework>FastAPI (latest stable) — 자동 OpenAPI 문서 생성이 사내 공유에 유리</framework>
    <orm>SQLAlchemy 2.x (async) + Alembic (마이그레이션)</orm>
    <validation>Pydantic v2 (FastAPI 내장)</validation>
  </backend>
  <data_layer>
    <database>PostgreSQL 16 — 링크/통계 저장</database>
    <cache>Redis 7 — slug→URL 캐시(리다이렉트 경로), rate limit 카운터</cache>
    <note>CRITICAL: 리다이렉트 경로는 DB를 거치지 않고 Redis 캐시 우선. 캐시 미스 시에만 DB 조회 후 캐시 적재 (TTL 1h).</note>
  </data_layer>
  <libraries>
    <jwt>PyJWT (latest stable) — SSO 발급 JWT 검증</jwt>
    <ids>base62 인코딩 자체 구현 (의존성 불필요, ~20줄)</ids>
  </libraries>
</technology_stack>

<prerequisites>
  <environment_setup>
    - Python 3.12+, Docker + docker compose (로컬 PostgreSQL/Redis 구동)
    - uv (패키지 관리) — 사내 표준
  </environment_setup>
  <build_configuration>
    - pyproject.toml 단일 설정, ruff (lint+format), mypy strict
    - docker compose: app + postgres:16 + redis:7, 헬스체크 포함
  </build_configuration>
</prerequisites>

<environment_variables>
  <variable>
    <name>DATABASE_URL</name>
    <description>PostgreSQL 연결 문자열 (asyncpg driver)</description>
    <required>true</required>
    <example>postgresql+asyncpg://linkhub:linkhub@localhost:5432/linkhub</example>
  </variable>
  <variable>
    <name>REDIS_URL</name>
    <description>Redis 연결 문자열</description>
    <required>true</required>
    <example>redis://localhost:6379/0</example>
  </variable>
  <variable>
    <name>JWT_PUBLIC_KEY</name>
    <description>SSO가 서명한 JWT 검증용 공개키 (PEM, base64 인코딩)</description>
    <required>true</required>
    <example>LS0tLS1CRUdJTi...</example>
  </variable>
  <variable>
    <name>BASE_URL</name>
    <description>단축 링크의 공개 도메인</description>
    <required>true</required>
    <example>https://go.company.com</example>
  </variable>
</environment_variables>

<file_structure>
src/
├── main.py                     # FastAPI 앱 생성, 라우터 등록, lifespan(DB/Redis 연결)
├── config.py                   # pydantic-settings 기반 환경변수 로딩
├── api/
│   ├── links.py                # /links CRUD 라우터
│   ├── redirect.py             # GET /{slug} 리다이렉트 라우터
│   └── stats.py                # /links/{id}/stats 라우터
├── core/
│   ├── auth.py                 # JWT 검증 dependency (get_current_user)
│   ├── rate_limit.py           # Redis 기반 rate limit dependency
│   └── errors.py               # ApiError 계층 + 전역 exception handler
├── db/
│   ├── models.py               # SQLAlchemy 모델 (Link, ClickEvent)
│   ├── session.py              # async session factory
│   └── migrations/             # Alembic
├── services/
│   ├── links.py                # slug 생성/충돌 처리, CRUD 로직
│   ├── redirect.py             # 캐시 조회 → DB 폴백 → 클릭 기록(비동기)
│   └── stats.py                # 일 단위 집계 쿼리
└── tests/
    ├── test_links.py
    ├── test_redirect.py
    └── test_stats.py
</file_structure>

<core_data_entities>
  <link>
    - id: UUID (pk, server-generated)
    - slug: string (unique, 3-32자, [a-z0-9-], 자동 생성 시 7자 base62)
    - targetUrl: string (required, http/https만, max 2048자)
    - ownerId: string (JWT sub 클레임, 사번)
    - clickCount: integer (default 0, 비정규화 캐시 — 정확한 값은 click_event 집계)
    - expiresAt: timestamptz | null (null = 무기한)
    - createdAt / updatedAt: timestamptz
    Indexes: [slug] (unique), [ownerId, createdAt]
  </link>

  <click_event>
    - id: bigserial (pk)
    - linkId: UUID (FK → link.id, onDelete: CASCADE)
    - clickedAt: timestamptz (default now())
    Indexes: [linkId, clickedAt] — 일 단위 집계 쿼리용
    비고: Q2 확정 전까지 카운트만 저장 (리퍼러/기기 정보 없음)
  </click_event>
</core_data_entities>

<authentication>
  <strategy>사내 SSO가 발급한 JWT(RS256)를 Authorization: Bearer 헤더로 수신, 공개키로 검증만 수행. 토큰 발급/갱신은 이 서비스 범위 밖.</strategy>
  <validation>
    - 서명, exp, iss(사내 SSO issuer) 검증 — 하나라도 실패 시 401
    - sub 클레임(사번)을 ownerId로 사용
  </validation>
  <authorization>
    - 링크 수정/삭제: owner 본인만 (불일치 시 403)
    - 링크 목록: 본인 소유만 반환
    - 리다이렉트(GET /{slug}): 인증 불필요 (공개)
  </authorization>
</authentication>

<api_endpoints>
  <base_url>/api/v1 (리다이렉트만 루트 경로)</base_url>
  <content_type>application/json</content_type>

  <resource name="links">
    <endpoint>
      <route>POST /api/v1/links</route>
      <purpose>단축 링크 생성</purpose>
      <auth>Bearer JWT 필수</auth>
      <request>
        {
          "targetUrl": "string (required, http/https, max 2048자)",
          "slug": "string (optional, 3-32자 [a-z0-9-], 미지정 시 7자 자동 생성)",
          "expiresAt": "ISO 8601 (optional, 미래 시각만)"
        }
      </request>
      <response status="201">
        { "id": "uuid", "slug": "q4-okr", "shortUrl": "https://go.company.com/q4-okr",
          "targetUrl": "...", "expiresAt": null, "clickCount": 0, "createdAt": "..." }
      </response>
      <errors>
        - 400 INVALID_URL: targetUrl 형식/길이 위반
        - 400 INVALID_SLUG: slug 형식 위반
        - 409 SLUG_TAKEN: slug 중복
        - 422 EXPIRY_IN_PAST: expiresAt이 과거
      </errors>
      <rate_limit>60 req/min per user</rate_limit>
    </endpoint>
    <endpoint>
      <route>GET /api/v1/links</route>
      <purpose>내 링크 목록 (최신순)</purpose>
      <auth>Bearer JWT 필수</auth>
      <request>?cursor=<opaque>&limit=20 (max 100) — cursor 기반 페이지네이션</request>
      <response status="200">{ "items": [Link...], "nextCursor": "..." | null }</response>
    </endpoint>
    <endpoint>
      <route>PATCH /api/v1/links/{id}</route>
      <purpose>targetUrl / expiresAt 수정 (slug는 불변)</purpose>
      <auth>Bearer JWT + owner 본인</auth>
      <errors>- 403 NOT_OWNER, 404 LINK_NOT_FOUND</errors>
      <side_effect>수정 성공 시 Redis 캐시 즉시 무효화 (DEL slug 키)</side_effect>
    </endpoint>
    <endpoint>
      <route>DELETE /api/v1/links/{id}</route>
      <purpose>링크 삭제 (click_event cascade 삭제)</purpose>
      <auth>Bearer JWT + owner 본인</auth>
      <response status="204">본문 없음</response>
      <side_effect>Redis 캐시 즉시 무효화</side_effect>
    </endpoint>
  </resource>

  <resource name="redirect">
    <endpoint>
      <route>GET /{slug}</route>
      <purpose>원본 URL로 302 리다이렉트 + 클릭 기록</purpose>
      <auth>불필요 (공개)</auth>
      <response status="302">Location: targetUrl</response>
      <errors>
        - 404 (JSON 아닌 최소 HTML): slug 없음
        - 410 (최소 HTML): 만료된 링크
      </errors>
      <performance>CRITICAL: p95 20ms 이하. Redis 캐시 우선, 클릭 기록은 응답 후 비동기 처리 (BackgroundTasks) — 기록 실패가 리다이렉트를 막으면 안 됨.</performance>
    </endpoint>
  </resource>

  <resource name="stats">
    <endpoint>
      <route>GET /api/v1/links/{id}/stats</route>
      <purpose>일 단위 클릭 통계</purpose>
      <auth>Bearer JWT + owner 본인</auth>
      <request>?from=2026-07-01&to=2026-07-28 (기본: 최근 30일, 최대 범위 90일)</request>
      <response status="200">
        { "total": 1204, "daily": [ { "date": "2026-07-01", "clicks": 42 }, ... ] }
      </response>
      <errors>- 400 RANGE_TOO_WIDE: 90일 초과 요청</errors>
    </endpoint>
  </resource>

  <error_response_format>
    모든 에러(리다이렉트 404/410 제외)는 { "error": { "code": "SLUG_TAKEN", "message": "..." } }.
    code는 SCREAMING_SNAKE_CASE로 클라이언트 분기용, message는 한국어 설명.
  </error_response_format>
  <pagination>cursor 기반 (createdAt+id 인코딩한 opaque 문자열). offset 페이지네이션 금지.</pagination>
  <versioning>URL prefix /api/v1. 브레이킹 체인지 시 /api/v2 신설.</versioning>
</api_endpoints>

<core_functionality>
  <slug_generation>
    - 자동 생성: 7자 base62 (crypto random), 충돌 시 재생성 최대 3회 후 500
    - 커스텀 slug: 예약어 차단 목록 (api, docs, healthz, metrics 등 라우트 충돌 방지)
  </slug_generation>
  <click_tracking>
    - 리다이렉트 성공 시 click_event INSERT + link.clickCount 증가 (단일 트랜잭션, 비동기)
    - 만료/404 접근은 기록하지 않음
  </click_tracking>
  <expiry>
    - 만료 판정은 요청 시점 비교 (expiresAt < now() → 410) — 배치 삭제 없음
    - 만료 링크도 목록/통계에서는 조회 가능 (상태 "expired" 표시)
  </expiry>
</core_functionality>

<error_handling>
  <api_errors>
    - 모든 예외는 core/errors.py의 전역 핸들러가 error envelope으로 변환
    - 미처리 예외: 500 INTERNAL_ERROR + requestId 반환, 상세는 로그로만 (스택 노출 금지)
    - Redis 다운: 리다이렉트는 DB 직접 조회로 폴백 (성능 저하 감수), rate limit은 통과 처리 (가용성 우선)
    - DB 다운: 503 SERVICE_UNAVAILABLE + Retry-After: 5
  </api_errors>
</error_handling>

<security_considerations>
  <input_validation>
    - CRITICAL: targetUrl은 http/https 스킴만 허용 — javascript:, data: 차단 (open redirect 무기화 방지)
    - 사내 IP 대역/localhost로의 리다이렉트 차단 (SSRF 우회 방지): 생성 시 호스트 검증
    - slug 정규식 검증: ^[a-z0-9-]{3,32}$
  </input_validation>
  <api_security>
    - Rate limit: 생성 60/min, 수정·삭제 30/min, 통계 120/min (Redis sliding window, 키: user+route)
    - 초과 시 429 + Retry-After 헤더
  </api_security>
  <data_protection>
    - 클릭 이벤트에 IP/UA 저장하지 않음 (Q2 확정 전) — 개인정보 최소 수집
    - 로그에 JWT 토큰 원문 출력 금지
  </data_protection>
</security_considerations>

<final_integration_test>
  <test_scenario_1>
    <description>링크 생성부터 리다이렉트, 통계까지 핵심 경로</description>
    <steps>
      1. POST /api/v1/links (JWT 포함, targetUrl만) → 201, 7자 slug 확인
      2. GET /{slug} (인증 없이) → 302, Location이 targetUrl과 일치
      3. 같은 slug로 3회 추가 접근
      4. GET /api/v1/links/{id}/stats → total 4, 오늘 날짜에 4 확인
      5. PATCH로 targetUrl 변경 → 200
      6. GET /{slug} → 302, 새 targetUrl로 이동 (캐시 무효화 검증)
      7. DELETE → 204, GET /{slug} → 404
    </steps>
  </test_scenario_1>
  <test_scenario_2>
    <description>커스텀 slug, 충돌, 만료</description>
    <steps>
      1. POST slug="team-wiki" → 201
      2. 다른 사용자 JWT로 POST slug="team-wiki" → 409 SLUG_TAKEN
      3. POST slug="api" → 400 INVALID_SLUG (예약어)
      4. POST expiresAt=+1초 → 201, 2초 대기 후 GET /{slug} → 410
      5. 만료 링크가 목록에 "expired" 상태로 조회되는지 확인
    </steps>
  </test_scenario_2>
  <test_scenario_3>
    <description>권한과 악성 입력 차단</description>
    <steps>
      1. JWT 없이 POST /api/v1/links → 401
      2. 사용자 A의 링크를 사용자 B가 PATCH → 403 NOT_OWNER
      3. POST targetUrl="javascript:alert(1)" → 400 INVALID_URL
      4. POST targetUrl="http://169.254.169.254/" → 400 INVALID_URL (내부 대역 차단)
      5. 생성 API 61회 연속 호출 → 61번째 429 + Retry-After
    </steps>
  </test_scenario_3>
</final_integration_test>

<success_criteria>
  <functionality>
    - 전 시나리오 통과, OpenAPI 문서(/docs)에 모든 엔드포인트 노출
  </functionality>
  <performance>
    - 리다이렉트 p95 20ms 이하 (캐시 히트), 100ms 이하 (캐시 미스)
    - 생성 API p95 100ms 이하
  </performance>
  <technical_quality>
    - mypy strict 0 에러, ruff 0 경고, 테스트 커버리지 서비스 레이어 90%+
  </technical_quality>
</success_criteria>

<build_output>
  <build_command>docker build -t linkhub:latest .</build_command>
  <output_directory>단일 컨테이너 이미지 (multi-stage, 최종 이미지 200MB 이하)</output_directory>
  <contents>uvicorn 구동, /healthz 헬스체크 (DB+Redis 연결 확인 포함)</contents>
</build_output>

<deployment_and_operations>
  <environments>
    - local: docker compose (app + postgres + redis)
    - production: 사내 K8s, 초기 replica 2
  </environments>
  <ci_cd>
    - GitHub Actions: ruff → mypy → pytest → docker build → 이미지 push
    - 배포: 태그 push 시 K8s rolling update, 롤백은 직전 이미지 태그 재배포
    - 마이그레이션: 배포 전 Job으로 alembic upgrade 실행 (앱보다 먼저)
  </ci_cd>
  <observability>
    <logging>구조화 JSON (level, requestId, path, latency). CRITICAL: JWT/targetUrl 쿼리스트링 내 토큰 로그 금지</logging>
    <metrics>리다이렉트 latency p50/p95/p99, 캐시 히트율, 429 발생 수 — /metrics (Prometheus)</metrics>
    <alerts>5xx 비율 1% 초과 5분 지속 시 알림, 캐시 히트율 80% 미만 시 경고</alerts>
  </observability>
</deployment_and_operations>

<key_implementation_notes>
  <critical_paths>
    1. 리다이렉트 경로의 캐시 전략 — 서비스 성능의 전부
    2. open redirect / SSRF 방어 — 보안 사고 직결
    3. slug 유니크 제약과 충돌 처리 — 데이터 정합성의 기반
  </critical_paths>
  <recommended_implementation_order>
    1. 프로젝트 셋업 (FastAPI + docker compose + Alembic 초기 마이그레이션)
    2. Link 모델 + POST/GET /links (인증 포함)
    3. 리다이렉트 (DB 직조회 버전) + 클릭 기록
    4. Redis 캐시 레이어 + 무효화
    5. PATCH/DELETE + 권한 검사
    6. 통계 집계 API
    7. Rate limiting
    8. 보안 검증 (URL 스킴/내부 대역 차단)
    9. 관측성 (구조화 로그, /metrics, /healthz)
  </recommended_implementation_order>
</key_implementation_notes>

</project_specification>
```
