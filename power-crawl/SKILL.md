---
name: power-crawl
description: Playwright MCP 를 e2e 테스트가 아니라 고속 데이터 수집 엔진으로 쓰는 크롤링 스킬. 페이지 뒤에 숨은 JSON API 를 network 로그로 발굴하고, 단일 도구 호출 안에서 페이지네이션·무한스크롤을 루프로 돌리며, 수집한 데이터를 컨텍스트에 통과시키지 않고 곧바로 파일(JSONL/CSV)로 떨군 뒤 필드 채움률·중복까지 검증한 crawl-report.md 를 남긴다. 사용자가 '크롤링', '스크래핑', '데이터 수집', '사이트에서 목록 긁어와', '상품/가격 정보 모아줘', '전체 페이지 돌면서 뽑아줘', '무한스크롤 끝까지 내려서 수집', '로그인해서 내 데이터 받아와', '이 사이트 API 좀 찾아줘', '결과를 CSV/JSONL 로 저장', '경쟁사/채용공고/리뷰 모니터링' 등을 말하거나, 웹페이지에서 여러 건의 구조화된 데이터를 반복 수집해야 하는 모든 경우에 반드시 이 스킬을 사용할 것. 단일 페이지를 한 번 읽고 요약하는 작업(WebFetch 로 충분)이나 e2e 테스트·QA 자동화·폼 제출 검증은 이 스킬의 범위가 아니다.
---

# Power Crawl

## 왜 기본 사용법으로는 안 되는가

Playwright MCP 의 표준 흐름(`navigate` → `snapshot` → `click` → `snapshot`)은 에이전트가 화면을 **보면서** 조작하라고 설계됐다. 크롤링에 그대로 쓰면 두 가지가 동시에 무너진다.

- **컨텍스트**: 페이지마다 스냅샷 수천 토큰이 쏟아진다. 100페이지면 수십만 토큰이고, 그 대부분은 버릴 마크업이다.
- **속도**: 도구 호출 1회마다 MCP 쪽에서 고정 대기가 붙는다(콜백 완료 후 500ms + 대기 중인 요청에 최대 5초). 모델 왕복까지 더하면 호출 100회는 그 자체로 수 분이다.

그래서 이 스킬은 방향을 뒤집는다.

> **모델은 한 페이지에서 "추출 레시피"만 알아낸다. 실제 수집은 브라우저 안에서 루프로 돌고, 결과는 파일로 직접 떨어진다. 데이터는 모델의 컨텍스트를 통과하지 않는다.**

호출 수를 줄이는 것이 곧 속도다. N페이지를 N번 호출하지 말고, **1번 호출 안에서 N번 돈다.**

## 수집 사다리 — 위에서부터 시도한다

아래로 갈수록 느리고 깨지기 쉽다. **L3 에서 시작하지 마라.** 대부분의 사이트는 L0 나 L1 이고, 정찰에 쓰는 1분이 20분을 아낀다.

| | 층 | 정체 | 판별법 |
|---|---|---|---|
| **L0** | 내부 JSON API | 화면은 껍데기고 데이터는 XHR 로 온다. 이미 구조화돼 있어 파싱이 필요 없다 | `browser_network_requests` 에 `/api`, `/graphql`, `.json` 이 보인다 |
| **L1** | 임베디드 JSON | 초기 HTML 안에 데이터가 통째로 박혀 있다. 렌더링조차 필요 없다 | `__NEXT_DATA__`, `__NUXT__`, `self.__next_f`, `application/ld+json` |
| **L2** | DOM 추출 | HTML 을 받아 셀렉터로 긁는다. 렌더 없이 `fetch`+`DOMParser` 로 충분한 경우가 많다 | 데이터가 초기 HTML 에 있다 |
| **L3** | 실제 렌더·상호작용 | 로그인, 클릭 기반 페이지네이션, 진짜 무한스크롤 | 위 셋이 전부 실패했을 때만 |

L0/L1 을 찾으면 목록·상세를 통틀어 수천 건도 호출 몇 번에 끝난다.

## 도구 3종과 각자의 자리

이 세 개가 엔진이다. **`filename` 파라미터의 의미가 도구마다 다르다** — 여기서 가장 많이 틀린다.

| 도구 | 실행 위치 | `filename` | 결과 |
|---|---|---|---|
| `browser_evaluate` | **페이지 안** (브라우저 JS) | **출력** 파일 | 지정 시 파일로 저장되고 컨텍스트엔 링크 한 줄만 남는다 ← **벌크 데이터는 전부 이 경로로** |
| `browser_run_code_unsafe` | **Playwright 서버** (Node vm) | **입력** 코드 파일 | 반환값이 **컨텍스트로 그대로 들어온다** ← 요약만 반환할 것 |
| `browser_network_requests` / `_request` | 서버 | **출력** 파일 | API 발굴용 |

### `browser_evaluate` — 주력 엔진

페이지 컨텍스트에서 **async 함수**가 그대로 돈다. 즉 `fetch` 루프, `DOMParser`, `document.querySelectorAll` 을 한 호출 안에서 다 쓸 수 있고, 같은 오리진이면 **로그인 쿠키가 자동으로 실린다**.

```js
// browser_evaluate  { function: <아래>, filename: "data/raw/quotes.json" }
async () => {
  const out = [], errors = [];
  let page = 1, hasNext = true;
  while (hasNext && page <= 200) {              // 폭주 방지 상한은 항상 건다
    const r = await fetch(`/api/quotes?page=${page}`, { credentials: 'include' });
    if (!r.ok) { errors.push({ page, status: r.status }); break; }
    const j = await r.json();
    for (const q of j.quotes) out.push({
      text: q.text, author: q.author.name, tags: q.tags,
      _src: `/api/quotes?page=${page}`, _at: new Date().toISOString()   // 출처 필드는 남긴다
    });
    hasNext = j.has_next;
    page++;
  }
  return { records: out.length, pages: page - 1, errors, data: out };
}
```

이 한 번의 호출로 10페이지 100건이 파일에 떨어지고 컨텍스트에는 링크 한 줄만 남는다.

**제약**: 페이지 안에서 도는 코드라 **same-origin** 만 자유롭다. 크로스 오리진은 CORS 에 막히므로 `run_code_unsafe` + `page.request` 로 간다.

### `browser_run_code_unsafe` — 크로스 오리진·다중 탭·진짜 상호작용

`page` 객체를 통째로 받는다. `page.request.get()` 은 **CORS 를 받지 않고 브라우저 세션 쿠키를 공유**하므로, 로그인 후 인증 API 를 렌더링 없이 HTTP 속도로 때릴 수 있다.

**샌드박스가 매우 좁다 (실측 확인).** vm 컨텍스트에 순수 V8 내장(`Promise`/`JSON`/`Math`/`Date`/`Array`…)과 `page`, `console` 밖에 없다.

```
없음: setTimeout · setInterval · require · fetch · URL · Buffer · process · TextDecoder
```

- 지연 → `await page.waitForTimeout(ms)`
- 상대경로 결합 → `await page.evaluate(u => new URL(u, location.href).href, rel)` 또는 문자열 조합
- **파일 쓰기 불가** → 아래 브리지로 뺀다

**브리지 패턴** — 서버에서 모은 데이터를 페이지에 심고, `browser_evaluate` 로 파일에 떨군다.

```js
// 1) run_code_unsafe
async (page) => {
  const urls = [...];                 // 크로스 오리진 가능
  const results = [];
  let i = 0;
  const worker = async () => {
    while (i < urls.length) {
      const u = urls[i++];
      const r = await page.request.get(u);
      results.push({ url: u, status: r.status(), body: await r.text() });
    }
  };
  await Promise.all(Array.from({ length: 8 }, worker));   // 동시성 8
  await page.evaluate(d => { window.__crawl = d; }, results);
  return { fetched: results.length, statuses: [...new Set(results.map(r => r.status))] };  // 요약만
}

// 2) browser_evaluate  { function: "() => window.__crawl", filename: "data/raw/detail.json" }
```

주의: `window.__crawl` 은 페이지를 이동하면 날아간다. 스태시 후 이동하지 말 것.

## 작업 순서

### 1. 정찰 — 딱 한 페이지

`browser_navigate` 로 목록 페이지 한 장을 연 뒤 `browser_network_requests { static: false }`. 정적 리소스는 자동으로 걸러지고 XHR/fetch 만 번호와 함께 나온다. 후보가 보이면 `browser_network_request { index, part: "response-body", filename }` 로 **한 건만** 엿보고 응답 스키마(레코드 배열 위치, 페이지네이션 키, 총 건수)를 파악한다.

API 가 없으면 L1 확인 — `browser_evaluate` 로 `document.querySelector('#__NEXT_DATA__')?.textContent` 나 JSON-LD 를 찍어본다. 그것도 없으면 `browser_snapshot { filename }` 이나 `browser_find` 로 셀렉터를 잡는다(전체 스냅샷을 컨텍스트로 받지 말 것 — `filename` 으로 저장해 `Read`/`Grep` 으로 본다).

### 2. 레시피 확정 — 소량 스모크 테스트

**전량을 바로 돌리지 마라.** 먼저 2~3페이지만 뽑아 파일로 저장하고, `Read` 나 짧은 python 으로 **실제 값을 눈으로 확인**한다. 셀렉터가 매칭은 되는데 빈 문자열만 채우는 실패가 가장 흔하고, 전량 수집 후에 발견하면 전부 다시 돌려야 한다.

확인할 것: 필드가 비어있지 않은가 · 인코딩이 깨지지 않았는가 · 페이지마다 같은 레코드가 반복되지 않는가(페이지네이션 파라미터가 안 먹는 신호) · **응답이 한 덩어리 JSON 이 맞는가** · **요청한 건수만큼 실제로 왔는가**.

뒤의 둘은 API 를 쓸 때만 나오는 함정이다. 스트리밍 응답(NDJSON)이면 `JSON.parse(전체)` 가 실패하거나 첫 줄만 읽혀 **일부만 조용히 수집된다**(레시피 10-3). 그리고 `count`/`size` 를 서버가 무시하는 API 가 흔하므로, 파라미터를 믿지 말고 **실제 반환 건수를 세서** 루프 종료를 판단한다.

### 3. 벌크 수집 — 호출 수를 줄인다

- 페이지네이션 루프는 **한 호출 안에서** 돈다.
- 총 페이지 수를 미리 알면 순차 대신 **동시 8~16**(워커 풀)으로 간다. 모르면 `has_next`/빈 응답까지 순차로 돌린다.
- 상세 페이지 팬아웃(목록 → 상세 N건)은 워커 풀로 병렬. 레시피는 `references/recipes.md`.
- 결과가 크면 **청크로 나눠 저장**한다(`raw/part-01.json`, `part-02.json`…). 한 번에 직렬화하는 배열이 수천 건을 넘어가면 전송이 느려지고, 중간에 실패하면 전부 잃는다. 대략 5,000건 또는 20MB 마다 끊는다.
- 실패한 URL 은 버리지 말고 `errors` 배열에 담아 같이 저장한다. 재시도의 입력이 된다.

**속도 정책(기본: 최대 속도)**: 지연 없이 동시성 8~16 으로 시작한다. 다만 429/403/캡차가 뜨면 **차단당하는 쪽이 결과적으로 더 느리므로** 즉시 동시성을 반으로 줄이고 요청 간 지연을 넣어 재시도한다. 로그인이 필요한 곳은 계정이 잠길 수 있으니 더 보수적으로 간다.

### 4. 정규화·검증

원본 JSON 을 최종 산출물로 바꾸고 품질을 잰다. 매번 다시 짜지 말고 번들 스크립트를 쓴다.

```bash
python3 ~/.claude/skills/power-crawl/scripts/finalize.py \
  data/raw/*.json --out data/quotes --key text --report
```

JSONL + CSV 를 만들고, 중복 제거 건수와 **필드별 채움률**을 낸다. 채움률은 조용한 실패를 잡는 핵심 지표다 — `price` 가 40% 만 차 있다면 셀렉터가 일부 레이아웃에서 안 먹은 것이다. `--help` 로 전체 옵션 확인.

다만 **낮은 채움률이 전부 버그는 아니다.** 그 필드를 원래 일부 레코드만 갖는 경우가 있다(링크 첨부가 달린 글에만 붙는 `link_url` 등). 모수를 세서 판정한다 — 채움 건수가 그 유형의 개수와 정확히 일치하면 정상이고, **0% 인데 원본에 값이 있으면 경로가 틀린 것**이다. `?? null` 이 오류를 조용히 삼키므로 예외는 나지 않는다. 판정 절차는 `references/troubleshooting.md`.

### 5. 리포트

`crawl-report.md` 를 남긴다. 목적은 "이 데이터를 믿어도 되는가"와 "어떻게 다시 돌리는가"에 답하는 것이다.

```markdown
# 크롤 리포트: <대상>

## 요약
- 대상 / 수집 일시
- 전략: L0 내부 API `GET /api/quotes?page=N`
- 수집: 100건 (중복 제거 후 100건) · 도구 호출 4회 · 약 12초
- 산출물: `data/quotes.jsonl`, `data/quotes.csv`

## 수집 경로
발굴한 엔드포인트, 쿼리 파라미터, 페이지네이션 방식(`has_next`/offset/cursor), 인증 방식.
→ 다음 사람이 이 절만 읽고 재현할 수 있어야 한다.

## 스키마와 품질
| 필드 | 타입 | 채움률 | 비고 |

## 누락·실패
실패한 URL, 건너뛴 범위, 수집하지 못한 필드와 그 이유.

## 제약과 주의
robots/ToS 상 확인한 사항, 레이트 리밋 반응, 재수집 시 주의점.
```

건수·채움률을 **추정하지 말고** finalize.py 출력값을 그대로 옮긴다.

## 반드시 지킬 것

- **출력 디렉터리를 미리 만든다.** `filename` 은 하위 디렉터리를 자동 생성하지 않는다(실측 확인). 없으면 `ENOENT` 로 수집이 통째로 날아간다. 크롤 시작 전 `mkdir -p data/raw`.
- **`filename` 경로는 작업 디렉터리(cwd) 기준**이며 cwd 밖은 거부된다. `filename` 을 생략하면 `.playwright-mcp/` 에 자동 이름으로 저장된다.
- **벌크 데이터를 반환값으로 받지 않는다.** `browser_evaluate` 는 반드시 `filename` 과 함께 쓰고, `run_code_unsafe` 는 건수·상태코드 같은 요약만 반환한다.
- **각 레코드에 출처를 심는다.** `_src`(URL), `_at`(수집 시각). 나중에 검증·증분 수집·디버깅이 전부 이것에 의존한다.
- **루프에 상한을 건다.** `while (hasNext)` 만 두면 페이지네이션이 무한히 같은 페이지를 주는 사이트에서 멈추지 않는다.

## 경계

로그인은 **사용자 본인이 브라우저에서** 하게 한다. 자격증명을 대신 받아 입력하지 말고, **2FA·본인확인 화면이 뜨면 대신 처리하지 않고** 사용자에게 넘긴다. 로그인 완료 후 같은 세션을 재사용해 수집한다(쿠키가 `fetch`/`page.request` 에 자동으로 실린다).

**Playwright MCP 브라우저는 사용자의 평소 브라우저와 별개 프로필**이다. "이미 로그인돼 있다"는 말이 이쪽 세션을 뜻하지 않을 수 있으므로, 수집 전에 세션을 실제로 확인한다(레시피 9). 로그인 벽에 막힌 페이지는 에러 대신 **0건 또는 공개분 일부만** 조용히 내주므로, 확인 없이 진행하면 "수집은 됐는데 대부분 비어 있는" 결과가 나온다. 접근 권한이 없는 영역을 우회하거나 캡차·봇 차단을 무력화하는 방향으로는 가지 않는다 — 차단이 반복되면 사용자에게 알리고 방법을 함께 정한다. robots.txt/ToS 상 명시적으로 금지된 대상은 수집 전에 사용자에게 알린다.

## 참조 파일

- `references/recipes.md` — 상황별 코드 레시피(API 페이지네이션·병렬 팬아웃·무한스크롤·임베디드 JSON·로그인 세션·증분 수집, GraphQL 은 Relay 요청 캡처·스트리밍 응답까지). **코드를 짜기 전에 해당 절을 읽으면 대부분 그대로 쓸 수 있다.**
- `references/mechanics.md` — Playwright MCP 도구별 실측 동작(파일 경로 규칙, vm 샌드박스 전역 목록, 호출 오버헤드, 네트워크 인덱스 규칙). 도구가 예상과 다르게 굴 때 여기부터 본다.
- `references/troubleshooting.md` — 빈 결과·낮은 채움률 판정·스트리밍 응답·CORS·중복·차단·타임아웃 증상별 대응.
- `scripts/finalize.py` — 원본 JSON → JSONL/CSV + 품질 통계.
