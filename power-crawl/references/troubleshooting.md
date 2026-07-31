# 증상별 대응

## 수집 결과가 비었다 / 필드가 전부 null

채움률이 0%거나 배열이 비었다면 순서대로 확인한다.

1. **셀렉터가 실제로 매칭되는가** — `browser_evaluate` 로 `document.querySelectorAll(SEL).length` 를 찍는다. 0이면 셀렉터 문제.
2. **`fetch` 로 받은 HTML 과 화면이 다른가** — 이게 가장 흔하다. 화면은 JS 로 그려졌는데 `fetch` 는 빈 껍데기 HTML 을 받는다. 확인:

```js
async () => {
  const html = await (await fetch(location.href, { credentials: 'include' })).text();
  const d = new DOMParser().parseFromString(html, 'text/html');
  return { fetched: d.querySelectorAll('.item').length, live: document.querySelectorAll('.item').length };
}
```

`fetched: 0, live: 40` 이면 클라이언트 렌더링이다. → **L0(API) 을 다시 찾아라.** 데이터가 어디선가 XHR 로 오고 있다는 확실한 증거다. 그래도 없으면 레시피 7·8로 실제 렌더를 쓴다.

3. **자동 생성 클래스명** — `css-1a2b3c` 같은 해시 클래스는 배포마다 바뀐다. `data-*` 속성, `id`, 텍스트 기반(`browser_find`), 구조적 위치로 바꾼다.
4. **iframe 안에 있는가** — `document` 로는 안 잡힌다. `run_code_unsafe` 에서 `page.frameLocator()` 또는 `page.frames()` 로 접근한다.

## 채움률이 낮다 — 셀렉터 실패인가, 원래 없는 값인가

`finalize.py` 가 `❌`/`⚠️` 를 붙였다고 전부 버그는 아니다. **모수를 세서 판정한다.** 둘을 구분하지 못하면 멀쩡한 수집을 다시 돌리거나, 진짜 버그를 정상이라고 넘긴다.

| 판정 | 신호 | 실측 예 |
|---|---|---|
| **정상** — 해당 유형의 레코드가 원래 적다 | 채움 건수가 그 유형의 개수와 **정확히 일치** | `link_url` 10% = 60건 중 링크 첨부 글이 딱 6건 |
| **버그** — 경로가 틀렸다 | 0% 인데 원본에는 값이 **분명히 있다** | `attachment_desc` 0% — 축약판 경로를 봤다 |

확인 방법은 하나뿐이다. **원본 응답 한 건을 열어 그 값이 실제로 있는지 본다.**

```python
rows = json.load(open('data/raw/part-01.json'))['data']
print('링크형:', sum(1 for r in rows if r['link_url']), '/ 전체:', len(rows))   # 모수 대조
```

0% 는 거의 항상 진짜 버그다. **경로가 틀렸는데 예외는 안 난다** — `?? null` 이 조용히 삼키기 때문이다. GraphQL 이라면 같은 필드의 완전판이 다른 경로에 있을 가능성이 높다(레시피 10-4).

## 응답이 `JSON.parse` 에 실패한다 / 요청한 건수의 일부만 들어온다

NDJSON 스트리밍 응답이다. `@stream`/`@defer` 를 쓰는 GraphQL(Relay 계열)에서 나온다. 한 덩어리 JSON 이 아니라 **줄마다 독립된 JSON** 이고, 첫 줄에는 레코드가 1건만 있다.

```js
const lines = t.split('\n').filter(l => l.trim());
console.log(lines.length, lines.map(l => JSON.parse(l).label));
// [null, '…$stream$…', '…$stream$…', '…$defer$…page_info']
```

`label` 과 `path` 가 붙은 줄이 보이면 확정이다. 줄 단위로 파싱해 병합한다(레시피 10-3). 특히 **`page_info` 는 마지막 줄에 있다** — 첫 줄만 읽고 커서를 못 찾아 한 페이지에서 루프가 끝나는 사고가 흔하다.

## 모든 페이지가 같은 데이터를 준다

페이지네이션 파라미터가 안 먹는 것이다. 중복률 100%로 나타난다.

- 파라미터 이름 확인: `page` / `p` / `offset` / `start` / `cursor` / `pageNo` / `_page`
- offset 방식인데 page 를 보내고 있을 수 있다 → `offset = (page-1) * size`
- POST 바디로 페이지를 받는 API 일 수 있다 → `browser_network_request { part: "request-body" }` 로 원본 요청을 확인해 그대로 흉내낸다
- 정찰 때 **2페이지를 실제로 눌러보고** 그때 나가는 요청을 보는 게 가장 확실하다

## CORS 에러

```
Access to fetch at '…' from origin '…' has been blocked by CORS policy
```

페이지 안의 `fetch` 는 브라우저 정책을 그대로 받는다. → `run_code_unsafe` + `page.request`(레시피 6). 또는 해당 오리진으로 `browser_navigate` 한 뒤 same-origin 으로 `fetch` 한다.

## 401 / 403 이 중간부터 나온다

세션 만료다. **그때까지 모은 것을 먼저 저장**하고(데이터 손실이 가장 비싸다) 사용자에게 재로그인을 요청한다. 토큰 기반이면 `localStorage` 에서 새로 읽어 다시 시작한다.

처음부터 403 이면 인증이 아니라 봇 차단일 수 있다. 아래로.

## 429 / 봇 차단 / 캡차

최대 속도가 기본이지만, **차단당하면 결과적으로 더 느리다.** 순서대로 완화한다.

1. 동시성을 절반으로 (`CONC: 10 → 5 → 2`)
2. 요청 간 지연 추가 — 페이지 안에서는 `await new Promise(r => setTimeout(r, 300))`, 서버 쪽에서는 `await page.waitForTimeout(300)`
3. 429 를 만나면 지수 백오프로 재시도하되 **재시도 횟수 상한**을 둔다
4. `Retry-After` 헤더가 있으면 그 값을 따른다

캡차가 뜨거나 차단이 반복되면 우회하지 말고 **사용자에게 알리고 방향을 함께 정한다**. 수집 속도를 낮출지, 공식 API 를 쓸지, 범위를 줄일지는 사용자의 판단이다.

## 수집 도중 실패해 전부 날렸다

배치로 쪼개지 않은 것이다(레시피 11). 앞으로는:

- 5,000건/20MB 마다 별도 파일로 저장
- `errors` 배열을 데이터와 **같은 파일에** 담는다 — 무엇을 못 받았는지가 데이터만큼 중요하다
- 각 배치의 범위(`range: [start, end]`)를 결과에 넣어두면 재시도 지점이 명확해진다

## `ENOENT: no such file or directory`

출력 디렉터리가 없다. `filename` 은 하위 디렉터리를 만들어주지 않는다. 크롤 전에 `mkdir -p data/raw`.

## `ReferenceError: setTimeout is not defined`

`run_code_unsafe` 안이다. 이 샌드박스에는 `setTimeout`·`require`·`fetch`·`URL`·`Buffer` 가 없다. `page.waitForTimeout(ms)` 로 바꾼다. 전체 목록은 `mechanics.md` 4절.

## 결과가 컨텍스트에 통째로 쏟아졌다

`browser_evaluate` 에 `filename` 을 안 줬거나, `run_code_unsafe` 가 데이터를 반환했다. 후자는 출력 파일 옵션이 없으므로 **브리지 패턴**(레시피 6)으로 빼야 한다.

## 호출이 오래 걸려 끊긴다

단일 호출을 2분 이내로 유지한다. 페이지 범위를 나눠 여러 번 호출하면(레시피 11) 각 호출이 짧아지고 중간 결과도 안전하게 남는다. MCP 서버 자체는 콜백에 타임아웃을 걸지 않지만 클라이언트 쪽 한계는 별개다.

## 한글이 깨진다

`fetch` 는 응답 헤더의 charset 을 따른다. EUC-KR/CP949 사이트는 `r.text()` 가 깨진다.

```js
const buf = await (await fetch(url)).arrayBuffer();
const html = new TextDecoder('euc-kr').decode(buf);   // 페이지 안에는 TextDecoder 가 있다
```

`run_code_unsafe` 쪽에는 `TextDecoder` 가 없으므로 이 처리는 반드시 `browser_evaluate` 안에서 한다.

## CSV 에서 숫자·날짜가 이상하다

`finalize.py` 는 값을 문자열로 보존한다. 가공은 수집 이후 단계의 일이다 — **원본을 보존**해야 나중에 다시 파싱할 수 있다. 변환이 필요하면 JSONL 을 입력으로 별도 처리한다.

## 중복이 많다

`--key` 로 안정적인 식별자를 지정한다. `id` 가 없으면 URL, 그것도 없으면 내용 조합(`--key title,date`). 페이지네이션 중복(1페이지가 반복됨)과 원본 자체의 중복은 다른 문제이므로, 중복률이 높으면 먼저 페이지네이션부터 의심한다.
