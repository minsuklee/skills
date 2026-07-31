# Playwright MCP 실측 동작

@playwright/mcp v0.0.78 (playwright-core 1.62 번들) 기준. **추측이 아니라 소스 확인 + 실행으로 검증한 내용**이다. 도구가 예상과 다르게 동작하면 여기부터 본다.

## 1. `filename` 의 의미가 도구마다 다르다

| 도구 | `filename` | 비고 |
|---|---|---|
| `browser_evaluate` | **출력** | 지정 시 결과 JSON 이 파일로, 컨텍스트엔 링크 한 줄 |
| `browser_network_requests` | **출력** | 요청 목록 |
| `browser_network_request` | **출력** | 헤더/바디 |
| `browser_snapshot` | **출력** | 접근성 트리 |
| `browser_take_screenshot` | **출력** | 이미지 |
| `browser_console_messages` | **출력** | 콘솔 로그 |
| `browser_run_code_unsafe` | **입력** | 실행할 코드를 파일에서 읽는다. 출력 옵션은 **없다** |

`run_code_unsafe` 의 반환값은 `JSON.stringify` 되어 **컨텍스트로 직행**한다. 벌크 데이터를 반환하면 이 스킬의 목적이 통째로 무너진다.

내부 동작(`addResult`): `filename` 이 있으면 파일에 쓰고 링크만 남기고, 없으면 전문을 컨텍스트에 넣는다. 즉 **`filename` 을 빼먹는 것 = 데이터를 컨텍스트에 쏟는 것.**

## 2. 파일 경로 규칙

- `filename` 을 **주면** 작업 디렉터리(cwd) 기준으로 해석된다. → `filename: "data/raw/x.json"` 이면 `<cwd>/data/raw/x.json`.
- `filename` 을 **생략하면** `<cwd>/.playwright-mcp/` 아래 자동 이름으로 저장된다.
- cwd 또는 출력 디렉터리 **밖의 경로는 거부**된다(`File access denied`).
- **하위 디렉터리를 자동 생성하지 않는다.** 없으면 그대로 실패한다:

```
ENOENT: no such file or directory, open '/…/data/raw/x.json'
```

수집 시작 전에 `mkdir -p data/raw` 를 반드시 먼저 실행한다. 이 한 줄을 빼먹어 몇 분짜리 수집이 통째로 날아가는 게 가장 흔한 사고다.

## 3. `browser_evaluate` 실행 모델

- `page.evaluate` 로 페이지 컨텍스트에서 돈다. 브라우저 전역이 전부 있다: `fetch`, `DOMParser`, `document`, `location`, `localStorage`, `URL`, `TextDecoder`.
- **async 함수를 지원한다.** 반환된 프로미스를 await 한 뒤 결과를 직렬화한다. → `fetch` 루프를 한 호출에 담을 수 있다.
- 결과는 `JSON.stringify(result, null, 2)`. 구조화 복제가 아니라 JSON 직렬화이므로 `Map`/`Set`/`undefined`/함수/순환 참조는 사라지거나 실패한다. **평범한 배열·객체·문자열·숫자·null 로만 반환**한다.
- `target` 을 주면 특정 엘리먼트에 바인딩되고, 함수는 `(element) => …` 형태가 된다.
- 같은 오리진 요청에는 세션 쿠키가 실린다(`credentials: 'include'`). 크로스 오리진은 CORS 정책을 그대로 받는다.

## 4. `run_code_unsafe` 샌드박스 — 매우 좁다

`vm.createContext({ page, __end__ })` 로 만든 컨텍스트에서 실행된다. 전역에는 **순수 V8 내장과 `page`, `console` 뿐**이다.

실행으로 확인한 결과:

```
있음: Promise · JSON · Math · Date · Array · Object · String · Number · RegExp
      Error 계열 · Intl · ArrayBuffer · 타입드 배열 · console · page
없음(ReferenceError): setTimeout · setInterval · require · fetch · URL
                      Buffer · process · TextDecoder · module · __dirname
```

결과적으로:

| 하고 싶은 것 | 안 되는 방법 | 되는 방법 |
|---|---|---|
| 지연 | `setTimeout` | `await page.waitForTimeout(ms)` |
| 상대 URL 결합 | `new URL(rel, base)` | `page.evaluate(u => new URL(u, location.href).href, rel)` 또는 문자열 조합 |
| 파일 쓰기 | `require('fs')` | 페이지에 스태시 후 `browser_evaluate` + `filename` |
| HTTP 요청 | `fetch` | `page.request.get/post` |

`page` 는 완전한 Playwright Page 다. `page.context()`, `page.request`, `page.locator`, `page.mouse`, `page.keyboard`, `page.waitForLoadState` 전부 쓸 수 있다.

`page.request` 의 가치: **CORS 를 받지 않고**, 브라우저 컨텍스트의 **쿠키를 공유**하며, 렌더링을 건너뛴다. 로그인 후 인증 API 를 HTTP 속도로 대량 호출하는 유일한 경로다.

## 5. 호출당 고정 오버헤드

모든 도구 호출은 `waitForCompletion` 으로 감싸여 있다:

1. 콜백 실행 (**타임아웃 없음** — 긴 루프도 중간에 잘리지 않는다)
2. `waitForTimeout(500)` — 무조건 0.5초
3. 네비게이션이 발생했으면 `load` 대기 (최대 10초)
4. 아니면 대기 중인 xhr/fetch 완료 대기 (최대 5초) + 요청이 있었으면 다시 0.5초

즉 **호출 1회당 0.5~5.5초의 고정 비용**이 붙고, 여기에 모델 왕복이 더해진다. 100페이지를 100번 호출하면 대기만 몇 분이다. 같은 100페이지를 1번 호출 안의 루프로 돌리면 고정 비용은 한 번뿐이다. 이것이 "호출 수 = 속도"의 근거다.

MCP 클라이언트 쪽 타임아웃은 별개로 존재할 수 있다. 단일 호출이 2분을 넘길 것 같으면 배치로 쪼갠다(레시피 11).

## 6. 네트워크 도구

- `browser_network_requests { static: false }` (기본값)는 **성공한 정적 리소스를 자동으로 숨긴다.** 이미지·폰트·CSS 를 걸러낸 XHR/fetch 목록이 바로 나오므로 API 발굴에 이상적이다. 숨겨진 개수는 하단에 알려준다.
- `filter` 는 URL 정규식이다. 예: `"/api/|graphql"`. `/pattern/i` 형태로 플래그도 준다.
- **번호는 필터링 후에도 전체 목록 기준의 절대 인덱스**다. 필터 결과에서 본 번호를 `browser_network_request { index }` 에 그대로 넘기면 된다.
- 기록 범위는 **현재 페이지 로드 이후**다. 늦게 뜨는 XHR 은 `browser_wait_for { time: 2 }` 로 조금 기다렸다 조회한다.
- `part: "response-body"` 는 텍스트 MIME 이면 본문을, 아니면 바이너리를 파일로 저장한다.

## 7. 스냅샷을 컨텍스트로 받지 않기

`browser_navigate` 는 이 버전에서 스냅샷을 `.playwright-mcp/*.yml` 로 저장하고 링크만 돌려준다. 셀렉터를 찾을 때는:

- `browser_find { text | regex }` — 매칭 노드와 주변 몇 줄만. 가장 싸다.
- `browser_snapshot { filename, depth }` — 파일로 저장 후 `Grep`/`Read`.

목록 페이지 하나의 전체 스냅샷도 수천 토큰이다. 크롤링에서 필요한 건 "레코드 하나의 셀렉터 구조"뿐이므로 `browser_find` 나 `depth` 제한으로 충분하다.

## 8. 데이터 크기 한계

`browser_evaluate` 결과는 CDP 를 통해 JSON 으로 넘어온다. 수만 건 배열도 동작은 하지만 직렬화가 느려지고 메모리를 먹는다. **5,000건 또는 20MB 근처에서 배치를 끊는다**(레시피 11). 끊어두면 중간 실패 시 그 배치만 다시 돌리면 된다.
