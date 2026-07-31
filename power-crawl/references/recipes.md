# 크롤 레시피

상황을 고르고 코드를 가져다 고쳐 쓴다. 전부 실제 도구 동작에 맞춰 검증된 형태다.

| # | 상황 | 도구 |
|---|---|---|
| [1](#1-api-페이지네이션--hasnext-순차) | 내부 API, 총 페이지 모름 | `browser_evaluate` |
| [2](#2-api-페이지네이션--총-페이지-아는-경우-병렬) | 내부 API, 총 페이지 앎 | `browser_evaluate` |
| [3](#3-dom-추출--fetch--domparser) | API 없음, 데이터는 초기 HTML | `browser_evaluate` |
| [4](#4-임베디드-json--nextdata--json-ld) | Next/Nuxt/JSON-LD | `browser_evaluate` |
| [5](#5-목록--상세-팬아웃) | 목록에서 URL 뽑아 상세 N건 | `browser_evaluate` |
| [6](#6-크로스-오리진--pagerequest-워커-풀) | 다른 도메인 섞임 | `run_code_unsafe` |
| [7](#7-무한스크롤) | 진짜 스크롤이 필요할 때 | `run_code_unsafe` |
| [8](#8-클릭-기반-페이지네이션더-보기) | 다음 버튼·더보기 | `run_code_unsafe` |
| [9](#9-로그인-세션-재사용) | 인증 필요 | 사용자 로그인 + 1·6 |
| [10](#10-graphql) | GraphQL 엔드포인트 (Relay·스트리밍 응답 포함) | `browser_evaluate` |
| [11](#11-청크-저장과-재시도) | 대량·실패 복구 | 공통 |
| [12](#12-증분-수집) | 정기 재수집 | 공통 |

핵심 규칙 두 가지만 기억하면 된다. `browser_evaluate` 는 **페이지 안**에서 돌고 `filename` 이 **출력**이다. `run_code_unsafe` 는 **서버**에서 돌고 반환값이 **컨텍스트로 들어온다**(요약만 반환).

---

## 1. API 페이지네이션 — has_next 순차

가장 흔한 경우. 마지막 페이지를 미리 알 수 없으니 종료 신호를 따라간다.

```js
// browser_evaluate { function: ..., filename: "data/raw/items.json" }
async () => {
  const out = [], errors = [];
  let p = 1, hasNext = true;
  const MAX = 500;                                   // 폭주 방지
  while (hasNext && p <= MAX) {
    const url = `/api/items?page=${p}&size=100`;
    const r = await fetch(url, { credentials: 'include' });
    if (!r.ok) { errors.push({ page: p, status: r.status }); break; }
    const j = await r.json();
    const rows = j.items ?? j.data ?? j.results ?? [];
    if (!rows.length) break;                         // 종료 신호가 없는 API 대비
    const at = new Date().toISOString();
    for (const it of rows) out.push({ id: it.id, name: it.name, price: it.price, _src: url, _at: at });
    hasNext = j.has_next ?? j.hasMore ?? (rows.length === 100);
    p++;
  }
  return { records: out.length, pages: p - 1, errors, data: out };
}
```

종료 조건은 **세 겹**으로 둔다: 서버가 주는 신호 · 빈 결과 · 상한. 하나만 믿으면 무한 루프에 빠지는 API 가 실제로 많다.

cursor 방식이면 `let cursor = null` 로 두고 `j.next_cursor` 를 따라가되, **같은 커서가 두 번 나오면 중단**한다.

## 2. API 페이지네이션 — 총 페이지 아는 경우 (병렬)

첫 응답의 `total`/`totalPages` 로 페이지 수를 계산할 수 있으면 병렬로 간다.

```js
// browser_evaluate { function: ..., filename: "data/raw/items.json" }
async () => {
  const SIZE = 100, CONC = 10;
  const first = await (await fetch(`/api/items?page=1&size=${SIZE}`, { credentials: 'include' })).json();
  const totalPages = Math.ceil(first.total / SIZE);

  const pages = Array.from({ length: totalPages - 1 }, (_, i) => i + 2);
  const buckets = [], errors = [];
  let i = 0;
  const worker = async () => {
    while (i < pages.length) {
      const p = pages[i++];
      const url = `/api/items?page=${p}&size=${SIZE}`;
      try {
        const r = await fetch(url, { credentials: 'include' });
        if (!r.ok) { errors.push({ page: p, status: r.status }); continue; }
        buckets.push({ p, rows: (await r.json()).items, url });
      } catch (e) { errors.push({ page: p, error: String(e) }); }
    }
  };
  await Promise.all(Array.from({ length: CONC }, worker));

  buckets.push({ p: 1, rows: first.items, url: `/api/items?page=1&size=${SIZE}` });
  buckets.sort((a, b) => a.p - b.p);                          // 순서 복원
  const at = new Date().toISOString();
  const out = buckets.flatMap(b => b.rows.map(it => ({ ...it, _src: b.url, _at: at })));
  return { records: out.length, totalPages, errors, data: out };
}
```

워커 풀은 `Promise.all(urls.map(fetch))` 보다 낫다. 후자는 수백 개를 동시에 던져 서버와 브라우저를 동시에 무너뜨린다. 풀은 동시 개수를 `CONC` 로 고정한다.

## 3. DOM 추출 — fetch + DOMParser

API 가 없어도 데이터가 초기 HTML 에 있으면 **렌더링 없이** 긁는다. 페이지마다 navigate 하는 것보다 훨씬 빠르다.

```js
// browser_evaluate { function: ..., filename: "data/raw/quotes.json" }
async () => {
  const out = [], errors = [];
  for (let p = 1; p <= 10; p++) {
    const url = `/page/${p}/`;
    const r = await fetch(url, { credentials: 'include' });
    if (!r.ok) { errors.push({ page: p, status: r.status }); continue; }
    const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
    const cards = doc.querySelectorAll('.quote');
    if (!cards.length) { errors.push({ page: p, note: 'no rows' }); break; }
    const at = new Date().toISOString();
    for (const q of cards) out.push({
      text: q.querySelector('.text')?.textContent?.trim() ?? null,
      author: q.querySelector('.author')?.textContent?.trim() ?? null,
      tags: [...q.querySelectorAll('.tag')].map(t => t.textContent.trim()),
      href: q.querySelector('a')?.getAttribute('href') ?? null,
      _src: url, _at: at
    });
  }
  return { records: out.length, errors, data: out };
}
```

`?? null` 을 쓰는 이유: 빈 문자열보다 `null` 이 낫다. finalize.py 의 채움률이 "셀렉터가 안 맞았다"를 정확히 잡아준다.

상대경로 링크는 `new URL(href, location.href).href` 로 절대화한다(**페이지 안에서는 `URL` 이 있다** — 서버 vm 에는 없다).

## 4. 임베디드 JSON — __NEXT_DATA__ / JSON-LD

Next.js·Nuxt·상거래 사이트는 완성된 JSON 을 HTML 에 그대로 박아둔다. 셀렉터보다 훨씬 안정적이고 필드도 풍부하다. **DOM 을 긁기 전에 항상 먼저 확인한다.**

정찰:

```js
// browser_evaluate { function: ..., filename: "data/probe/embedded.json" }
() => ({
  next: !!document.querySelector('#__NEXT_DATA__'),
  nuxt: typeof window.__NUXT__ !== 'undefined',
  nextFlight: typeof self.__next_f !== 'undefined',
  ldTypes: [...document.querySelectorAll('script[type="application/ld+json"]')]
    .map(s => { try { return JSON.parse(s.textContent)['@type']; } catch { return 'PARSE_ERROR'; } }),
  apollo: typeof window.__APOLLO_STATE__ !== 'undefined',
  nextKeys: (() => {
    const el = document.querySelector('#__NEXT_DATA__');
    if (!el) return null;
    try { return Object.keys(JSON.parse(el.textContent).props.pageProps); } catch { return 'PARSE_ERROR'; }
  })()
})
```

수집(페이지별로 HTML 만 받아 파싱 — 렌더 불필요):

```js
// browser_evaluate { function: ..., filename: "data/raw/products.json" }
async () => {
  const out = [], errors = [];
  for (let p = 1; p <= 20; p++) {
    const url = `/products?page=${p}`;
    const r = await fetch(url, { credentials: 'include' });
    const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
    const el = doc.querySelector('#__NEXT_DATA__');
    if (!el) { errors.push({ page: p, note: '__NEXT_DATA__ 없음' }); break; }
    const props = JSON.parse(el.textContent).props.pageProps;
    const rows = props.products ?? [];
    if (!rows.length) break;
    const at = new Date().toISOString();
    for (const it of rows) out.push({ ...it, _src: url, _at: at });
  }
  return { records: out.length, errors, data: out };
}
```

JSON-LD 는 `@type` 이 `Product`/`JobPosting`/`Article` 인 블록을 골라 쓴다. 스키마가 표준이라 사이트가 바뀌어도 잘 버틴다.

## 5. 목록 → 상세 팬아웃

목록에서 URL 을 모으고 상세 N건을 병렬로 받는다. 같은 오리진이면 `browser_evaluate` 하나로 끝난다.

```js
// browser_evaluate { function: ..., filename: "data/raw/details.json" }
async () => {
  // 1단계: 목록에서 URL 수집
  const links = new Set();
  for (let p = 1; p <= 10; p++) {
    const r = await fetch(`/list?page=${p}`, { credentials: 'include' });
    const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
    const found = [...doc.querySelectorAll('a.item-link')]
      .map(a => new URL(a.getAttribute('href'), location.origin).href);
    if (!found.length) break;
    found.forEach(u => links.add(u));
  }

  // 2단계: 상세 병렬 수집
  const urls = [...links], out = [], errors = [];
  let i = 0;
  const worker = async () => {
    while (i < urls.length) {
      const u = urls[i++];
      try {
        const r = await fetch(u, { credentials: 'include' });
        if (!r.ok) { errors.push({ url: u, status: r.status }); continue; }
        const d = new DOMParser().parseFromString(await r.text(), 'text/html');
        out.push({
          url: u,
          title: d.querySelector('h1')?.textContent?.trim() ?? null,
          price: d.querySelector('[data-price]')?.getAttribute('data-price') ?? null,
          desc: d.querySelector('.description')?.textContent?.trim() ?? null,
          _at: new Date().toISOString()
        });
      } catch (e) { errors.push({ url: u, error: String(e) }); }
    }
  };
  await Promise.all(Array.from({ length: 10 }, worker));
  return { listed: urls.length, records: out.length, errors, data: out };
}
```

`Set` 으로 URL 을 모으면 목록 중복이 자동으로 걸러진다.

## 6. 크로스 오리진 — page.request 워커 풀

다른 도메인이 섞이면 페이지 안의 `fetch` 는 CORS 에 막힌다. 서버 쪽 `page.request` 는 CORS 를 받지 않고 브라우저 쿠키를 공유한다.

```js
// run_code_unsafe — 반환은 요약만
async (page) => {
  const urls = [ /* 크로스 오리진 포함 */ ];
  const results = [], errors = [];
  let i = 0;
  const worker = async () => {
    while (i < urls.length) {
      const u = urls[i++];
      try {
        const r = await page.request.get(u, { timeout: 20000 });
        if (r.status() !== 200) { errors.push({ url: u, status: r.status() }); continue; }
        results.push({ url: u, html: await r.text() });
      } catch (e) { errors.push({ url: u, error: String(e) }); }
    }
  };
  await Promise.all(Array.from({ length: 8 }, worker));
  await page.evaluate(d => { window.__crawl = d; }, { results, errors });
  return { ok: results.length, failed: errors.length };
}
```

파싱은 페이지 안에서 하고 바로 파일로 뺀다:

```js
// browser_evaluate { function: ..., filename: "data/raw/cross.json" }
() => {
  const { results, errors } = window.__crawl;
  const out = results.map(({ url, html }) => {
    const d = new DOMParser().parseFromString(html, 'text/html');
    return { url, title: d.querySelector('h1')?.textContent?.trim() ?? null };
  });
  return { records: out.length, errors, data: out };
}
```

`page.request` 는 브라우저 렌더링을 거치지 않으므로 JS 로 그려지는 내용은 안 잡힌다. 그런 페이지는 레시피 7·8 로 간다.

## 7. 무한스크롤

**먼저 레시피 1을 시도하라.** 무한스크롤 UI 는 거의 항상 뒤에 페이지네이션 API 가 있고, 그쪽이 수십 배 빠르다. 스크롤은 API 를 못 찾았을 때만.

```js
// run_code_unsafe
async (page) => {
  const SEL = '.item-card';
  let prev = 0, stable = 0, rounds = 0;
  while (stable < 3 && rounds < 200) {              // 3회 연속 변화 없으면 종료
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(700);                 // setTimeout 없음 — 이걸 쓴다
    const n = await page.evaluate(s => document.querySelectorAll(s).length, SEL);
    stable = (n === prev) ? stable + 1 : 0;
    prev = n;
    rounds++;
  }
  return { items: prev, rounds };
}
```

그 다음 DOM 을 한 번에 파일로:

```js
// browser_evaluate { function: ..., filename: "data/raw/scrolled.json" }
() => {
  const at = new Date().toISOString();
  const out = [...document.querySelectorAll('.item-card')].map(c => ({
    title: c.querySelector('.title')?.textContent?.trim() ?? null,
    price: c.querySelector('.price')?.textContent?.trim() ?? null,
    href: c.querySelector('a')?.href ?? null,
    _src: location.href, _at: at
  }));
  return { records: out.length, data: out };
}
```

"더 이상 늘지 않음"을 **연속 3회** 확인하는 게 중요하다. 한 번만 보면 로딩 지연을 끝으로 오인해 절반만 수집한다. 가상 스크롤(윈도잉) 사이트는 DOM 에서 지나간 항목이 사라지므로, 스크롤 도중 라운드마다 수집해 누적해야 한다.

## 8. 클릭 기반 페이지네이션(더 보기)

```js
// run_code_unsafe
async (page) => {
  const collected = [];
  for (let i = 0; i < 100; i++) {
    const rows = await page.evaluate(() =>
      [...document.querySelectorAll('.row')].map(r => ({
        name: r.querySelector('.name')?.textContent?.trim() ?? null,
        val: r.querySelector('.val')?.textContent?.trim() ?? null
      })));
    collected.push(...rows);

    const next = page.locator('a.next:not([disabled])').first();
    if (!(await next.count())) break;
    await next.click();
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(300);
  }
  await page.evaluate(d => { window.__crawl = d; }, collected);
  return { records: collected.length };
}
```

이후 `browser_evaluate { function: "() => window.__crawl", filename: "..." }` 로 파일에 떨군다.

## 9. 로그인 세션 재사용

자격증명을 대신 받지 않는다. **사용자가 직접 로그인**하게 하고 그 세션을 재사용한다.

**Playwright MCP 브라우저는 사용자의 평소 브라우저와 다른 프로필이다.** "이미 로그인돼 있다"는 말이 이쪽 세션을 뜻하지 않는 경우가 많으므로, 수집 전에 반드시 확인한다.

1. `browser_navigate` 로 로그인 페이지를 연다.
2. 사용자에게 열린 브라우저 창에서 로그인(2FA 포함)을 마치고 알려달라고 요청한다. **2FA 화면은 대신 처리하지 않는다.**
3. 로그인 확인: `browser_evaluate` 로 사용자 전용 엔드포인트를 찔러본다.

```js
// browser_evaluate — 세션 확인
async () => {
  const r = await fetch('/api/me', { credentials: 'include' });
  return { status: r.status, body: r.ok ? await r.json() : null };
}
```

전용 엔드포인트를 모르면 **쿠키·로그인 폼·임베디드 사용자 ID** 를 함께 본다. 하나만 보면 오판한다:

```js
// browser_evaluate — 엔드포인트를 모를 때
() => {
  const html = document.documentElement.innerHTML;
  return {
    sessionCookie: (document.cookie.match(/c_user=(\d+)/) || [])[1] || null,   // 사이트별 쿠키명으로 교체
    hasLoginForm: !!document.querySelector('input[type="password"], input[name="pass"]'),
    embeddedUserId: (html.match(/"USER_ID":"(\d+)"/) || [])[1] || null,        // "0" 이면 로그아웃
    recordCount: document.querySelectorAll('div[role="article"]').length       // 실제 콘텐츠가 그려졌는가
  };
}
```

**로그인 벽은 에러를 주지 않는다.** 401 대신 로그인 폼이 섞인 200 페이지가 오고, 공개분 일부만 렌더링된다. 확인 없이 진행하면 "수집은 성공했는데 대부분 비어 있는" 결과가 나오고, 그 원인을 셀렉터 문제로 오진하기 쉽다.

4. 이후 레시피 1·2·5 를 그대로 쓴다. `credentials: 'include'` 는 same-origin 쿠키를 자동으로 싣고, `page.request` 도 같은 세션을 공유한다.

`Authorization: Bearer` 토큰을 쓰는 API 라면 정찰 단계의 `browser_network_request { part: "request-headers" }` 로 헤더를 확인하고, 페이지 안에서 토큰 출처(`localStorage`)를 읽어 붙인다.

```js
async () => {
  const token = localStorage.getItem('access_token');
  const r = await fetch('/api/items?page=1', { headers: { Authorization: `Bearer ${token}` } });
  return await r.json();
}
```

세션은 만료된다. 긴 수집 중 401 이 나오면 즉시 멈추고 **그때까지 모은 것을 저장한 뒤** 사용자에게 재로그인을 요청한다.

## 10. GraphQL

세 가지가 동시에 어려울 수 있다. **요청을 재현하기 어렵고**, **응답이 한 덩어리 JSON 이 아닐 수 있으며**, **같은 필드가 여러 경로에 서로 다른 완전도로 존재한다.** 아래 10-1 부터 순서대로 확인한다.

### 10-1. 기본 — 쿼리를 그대로 재사용

정찰에서 `/graphql` POST 가 보이면 `browser_network_request { part: "request-body" }` 로 쿼리와 변수를 그대로 가져와 재사용한다.

```js
// browser_evaluate { function: ..., filename: "data/raw/gql.json" }
async () => {
  const QUERY = `query Items($page:Int!){ items(page:$page){ nodes{ id name price } pageInfo{ hasNextPage } } }`;
  const out = [], errors = [];
  let p = 1, hasNext = true;
  while (hasNext && p <= 200) {
    const r = await fetch('/graphql', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ query: QUERY, variables: { page: p } })
    });
    const j = await r.json();
    if (j.errors) { errors.push({ page: p, errors: j.errors }); break; }
    const conn = j.data.items;
    out.push(...conn.nodes.map(n => ({ ...n, _src: `graphql:page=${p}`, _at: new Date().toISOString() })));
    hasNext = conn.pageInfo.hasNextPage;
    p++;
  }
  return { records: out.length, errors, data: out };
}
```

GraphQL 은 HTTP 200 으로도 에러를 반환한다. `r.ok` 가 아니라 **`j.errors` 를 봐야** 한다. 스키마에 없는 필드를 요청하면 전체 쿼리가 실패하므로, 원본 요청의 필드 집합에서 출발해 늘려간다.

### 10-2. 요청을 손으로 조립할 수 없을 때 — 후킹으로 원본 본문을 훔친다

Relay 기반 사이트(페이스북·인스타그램 등)는 쿼리 문자열 대신 **`doc_id`** 를 보내고, 본문에 CSRF 토큰(`fb_dtsg`)·세션 필드·`__relay_internal__pv__*` 프로바이더 플래그가 **수십 개** 붙는다. 하나라도 빠지면 실패하고 `doc_id` 는 배포마다 바뀐다.

수기 조립은 포기한다. **실제 요청을 통째로 캡처해 `variables` 만 교체한다.**

1단계 — 후킹 설치 (`fetch` 와 `XMLHttpRequest` 둘 다):

```js
// browser_evaluate — filename 없이 (반환값이 작다)
() => {
  window.__raw = [];
  const WANT = 'ProfileCometTimelineFeedRefetchQuery';     // 노리는 쿼리 이름
  const grab = (body) => {
    try {
      if (new URLSearchParams(body).get('fb_api_req_friendly_name') === WANT) window.__raw.push(body);
    } catch (e) {}
  };
  const of = window.fetch;
  window.fetch = function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url);
    if (url && url.includes('/api/graphql') && init && typeof init.body === 'string') grab(init.body);
    return of.apply(this, arguments);
  };
  const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) { this.__u = u; return oo.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function (body) {
    if (this.__u && String(this.__u).includes('/api/graphql') && typeof body === 'string') grab(body);
    return os.apply(this, arguments);
  };
  return { hooked: true };
}
```

2단계 — 실제 요청을 유발한다. 페이지네이션 요청은 스크롤·클릭으로만 나간다:

```js
// run_code_unsafe
async (page) => {
  for (let i = 0; i < 3; i++) {
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(2000);
  }
  return await page.evaluate(() => ({ captured: (window.__raw || []).length }));
}
```

3단계 — 캡처한 본문에서 `variables` 만 갈아끼운다:

```js
const base = new URLSearchParams(window.__raw[0]);
const baseVars = JSON.parse(base.get('variables'));
const v = Object.assign({}, baseVars, { cursor, count: 10 });
const p = new URLSearchParams(base.toString());
p.set('variables', JSON.stringify(v));
const r = await fetch('/api/graphql/', {
  method: 'POST',
  headers: { 'content-type': 'application/x-www-form-urlencoded' },
  credentials: 'include',
  body: p.toString()
});
```

`browser_network_request { part: "request-body" }` 로도 본문을 볼 수 있다. 후킹이 나은 점은 **스크롤·클릭으로 뒤늦게 나가는 요청까지 자동으로 쌓이고**, 그 결과가 페이지 안에 남아 다음 `browser_evaluate` 에서 바로 재사용된다는 것이다. 도구 호출 왕복이 줄어든다.

**페이지를 이동하면 후킹도 `window.__raw` 도 날아간다.** 캡처 후 navigate 하지 말 것.

### 10-3. 스트리밍 응답 — 한 덩어리 JSON 이 아니다

`@stream`/`@defer` 지시자를 쓰는 응답은 **NDJSON** 으로 온다. `JSON.parse(전체응답)` 은 실패하고, 첫 줄만 읽으면 **요청한 건수의 일부만** 수집된다. 조용한 실패라 더 위험하다.

실측한 페이스북 타임라인 응답(요청 1회, 3건):

| 줄 | `label` | `path` | 내용 |
|---|---|---|---|
| 1 | 없음 | — | `…edges` — **edges[0] 단 1건** |
| 2 | `…$stream$…` | `["node","timeline_list_feed_units","edges",1]` | edges[1] |
| 3 | `…$stream$…` | `[…,"edges",2]` | edges[2] |
| 4 | `…$defer$…page_info` | `["node","timeline_list_feed_units"]` | `page_info` |

즉 **첫 줄만 파싱하면 1/3만 건진다.** 줄마다 따로 파싱해 병합한다:

```js
const pick = (o, path) => path.split('.').reduce((a, k) => {
  if (a == null) return null;
  return (/^\d+$/.test(k) && Array.isArray(a)) ? a[+k] : a[k];
}, o);

let got = 0, nextCursor = null, sawPageInfo = false;
for (const line of t.split('\n')) {
  if (!line.trim()) continue;
  let j;
  try { j = JSON.parse(line); } catch { errors.push({ page, note: 'line parse fail' }); continue; }
  if (j.errors) errors.push({ page, gqlErrors: j.errors.map(e => e.message).slice(0, 2) });
  const d = j.data || {};

  const edges = pick(d, 'node.timeline_list_feed_units.edges');   // 초기 줄
  if (Array.isArray(edges)) { for (const e of edges) if (pushNode(e && e.node)) got++; }
  else if (d.node && d.node.__typename === 'Story') { if (pushNode(d.node)) got++; }   // stream 줄

  const pi = d.page_info || pick(d, 'node.timeline_list_feed_units.page_info');        // defer 줄
  if (pi) { sawPageInfo = true; nextCursor = pi.end_cursor ?? null; hasNext = !!pi.has_next_page; }
}
```

스트림 줄은 `edges` 배열이 아니라 **노드 하나가 `data.node` 로 바로 온다.** 두 형태를 모두 받아야 한다. `page_info` 는 보통 **마지막 줄**에 있으므로, 커서를 읽기 전에 루프를 빠져나가면 페이지네이션이 한 페이지에서 멈춘다.

### 10-4. 같은 필드가 여러 경로에 있다 — 완전판을 고른다

GraphQL 응답은 같은 데이터를 렌더링 위치별로 여러 번 담는다. 이름이 같아도 **완전도가 다르다.**

실측 예 — 첨부(attachment):

```
node.attachments[0]                              → { media, styles }          축약판
node.comet_sections.content.story.attachments[0] → { …, comet_footer_renderer, all_subattachments, … }   완전판
```

축약판 경로로 링크 설명을 뽑으면 **채움률 0%** 가 나온다. 셀렉터는 "매칭"되는데 값이 없는, 가장 잡기 어려운 실패다. 완전판 우선 + 축약판 폴백으로 체인을 만든다:

```js
const story = pick(n, 'comet_sections.content.story') || {};
const att    = pick(story, 'attachments.0') || pick(n, 'attachments.0') || {};   // 완전판 우선
const footer = pick(att, 'comet_footer_renderer.attachment') || {};
const link   = pick(att, 'styles.attachment.story_attachment_link_renderer.attachment')
            || pick(footer, 'story_attachment_link_renderer.attachment') || {};
```

경로를 추측하지 말고 **응답 한 건을 파일로 떨군 뒤 재귀 탐색으로 실제 경로를 찾는다**(스모크 테스트 단계에서 한 번만 하면 된다):

```python
def walk(o, path='', d=0, hits=None):
    if hits is None: hits = []
    if d > 9: return hits
    if isinstance(o, dict):
        for k, v in o.items():
            p = f'{path}.{k}'
            if k in ('creation_time', 'wwwURL', 'post_id') and not isinstance(v, (dict, list)):
                hits.append((p, repr(v)[:90]))
            if k == 'text' and isinstance(v, str) and len(v) > 25:
                hits.append((p, v[:70].replace('\n', ' ')))
            walk(v, p, d + 1, hits)
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            walk(v, f'{path}[{i}]', d + 1, hits)
    return hits
```

### 10-5. 페이지 크기와 병렬화

- **`count` 를 서버가 무시할 수 있다.** 페이스북 타임라인은 `count: 10` 을 보내도 응답당 **3건 고정**이었다. 페이지 크기 파라미터를 믿지 말고 **실제 반환 건수를 세서** 루프 종료를 판단한다.
- **커서 체인은 병렬화할 수 없다.** 다음 커서를 알아야 다음 요청을 만들 수 있으므로 레시피 2(총 페이지 선계산 후 병렬)를 쓸 수 없다. 순차 루프가 유일한 방법이고, 이때는 **한 호출 안에서 도는 것**이 유일한 속도 수단이다.
- 그래서 종료 조건을 4겹으로 둔다: `has_next_page` · 새 레코드 0건 · **커서 반복** · `MAX_PAGES` 상한.

```js
if (!got) { errors.push({ page, note: 'no new stories' }); break; }
if (!sawPageInfo || !nextCursor) { errors.push({ page, note: 'no page_info/cursor' }); break; }
if (seenCursors.has(nextCursor)) { errors.push({ page, note: 'cursor repeated' }); break; }
seenCursors.add(nextCursor);
cursor = nextCursor;
```

### 10-6. 검증된 사례 — 페이스북 프로필 타임라인

로그인 세션에서 실측(2026-07). 같은 접근이 인스타그램 등 다른 Relay 기반 서비스에도 적용된다.

| 항목 | 값 |
|---|---|
| 엔드포인트 | `POST /api/graphql/` |
| `fb_api_req_friendly_name` | `ProfileCometTimelineFeedRefetchQuery` |
| `doc_id` | 배포마다 변함 — **하드코딩 금지**, 매번 후킹으로 캡처 |
| 레코드 경로 | `data.node.timeline_list_feed_units.edges[].node` |
| 페이지네이션 | `page_info.end_cursor` / `has_next_page` (마지막 줄) |
| 응답당 건수 | 3건 고정 (`count` 무시) |
| 본문 | `node.comet_sections.content.story.message.text` |
| 작성시각 | `node.creation_time` (unix seconds) |
| permalink | `node.comet_sections.content.story.wwwURL` |
| 이미지 | `story.attachments` 아래 `uri`/`src` 중 `scontent` 포함 값 |

결과: 60건 / 20페이지 / 요청 간 250ms 지연 / 에러 0건 / 중복 0건. 채움률은 `post_id`·`created_at`·`permalink` 100%, `message` 98.3%(사진 전용 글 1건), `images` 83.3%.

주의할 점:

- **로그인 필수.** 로그아웃 상태에서는 `USER_ID: 0` 이 되고 게시물이 0건 잡힌다. 확인은 `document.cookie` 의 `c_user` 로 한다. 로그인은 사용자가 직접 하게 하고(2FA 포함) 그 세션을 재사용한다.
- **이미지 URL 에 서명·만료가 붙는다**(`scontent-*.fbcdn.net`). 보관하려면 수집 직후 내려받아야 한다.
- 커서 체인 + 3건 고정이라 200건이면 약 67회 요청 ≈ 1분이다. 이 비용을 미리 알려두면 범위 협의가 쉽다.

## 11. 청크 저장과 재시도

대량 수집은 한 파일에 몰지 않는다. 중간에 실패하면 전부 잃는다.

```js
// browser_evaluate — 배치마다 filename 을 바꿔 호출 (part-01, part-02 …)
async () => {
  const START = 1, END = 50;                   // 호출마다 이 범위만 조정
  const out = [], errors = [];
  for (let p = START; p <= END; p++) {
    try {
      const r = await fetch(`/api/items?page=${p}`, { credentials: 'include' });
      if (!r.ok) { errors.push({ page: p, status: r.status }); continue; }
      out.push(...(await r.json()).items);
    } catch (e) { errors.push({ page: p, error: String(e) }); }
  }
  return { range: [START, END], records: out.length, errors, data: out };
}
```

`finalize.py` 는 여러 파일을 한꺼번에 받아 합치고 중복을 제거한다:

```bash
python3 ~/.claude/skills/power-crawl/scripts/finalize.py data/raw/part-*.json --out data/items --key id --report
```

실패 목록만 모아 재시도할 때는 URL 배열을 코드에 직접 박고 레시피 5의 2단계만 돌린다.

## 12. 증분 수집

정기 재수집이라면 이미 가진 키를 페이지 안으로 넘겨 새 것만 받는다.

```js
// browser_evaluate — 기존 id 목록을 코드 안에 박아 넣는다
async () => {
  const KNOWN = new Set([/* 기존 id 들 */]);
  const out = [];
  let p = 1, done = false;
  while (!done && p <= 100) {
    const j = await (await fetch(`/api/items?page=${p}&sort=created_desc`, { credentials: 'include' })).json();
    for (const it of j.items) {
      if (KNOWN.has(it.id)) { done = true; break; }     // 최신순이면 첫 중복에서 멈춘다
      out.push({ ...it, _at: new Date().toISOString() });
    }
    p++;
  }
  return { newRecords: out.length, data: out };
}
```

기존 키는 `python3 -c "import json;print([r['id'] for r in map(json.loads,open('data/items.jsonl'))])"` 로 뽑는다. 수만 개면 코드에 박지 말고 마지막 수집 시각 기준 필터(`?since=`)를 쓴다.
