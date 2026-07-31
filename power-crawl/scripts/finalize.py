#!/usr/bin/env python3
"""수집 원본(JSON/JSONL) -> JSONL + CSV 변환 및 품질 리포트.

크롤링 결과는 거의 항상 같은 후처리를 거친다: 여러 배치 파일 합치기, 중복 제거,
"셀렉터가 매칭은 됐는데 값이 비었다"는 조용한 실패 잡아내기, 그리고 Excel 에서
안 깨지는 CSV 만들기. 매번 다시 짜지 말고 이걸 쓴다.

사용법:
    finalize.py data/raw/*.json --out data/items --key id --report

입력은 다음을 모두 받는다:
    - JSON 배열                         [{...}, {...}]
    - browser_evaluate 반환 형태        {"records": 100, "errors": [], "data": [{...}]}
    - 흔한 API 응답                     {"items"|"results"|"rows"|... : [{...}]}
    - JSONL                             한 줄에 객체 하나

출력:
    <out>.jsonl   원본 구조 보존 (중첩 유지)
    <out>.csv     CSV 용으로 평탄화 (utf-8-sig, Excel 한글 안전)
    stdout        마크다운 품질 리포트 (--report) -> crawl-report.md 에 그대로 붙여넣는다
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, OrderedDict
from typing import Any

# 레코드 배열이 들어있을 법한 키 (앞쪽 우선)
LIST_KEYS = ("data", "items", "records", "results", "rows", "list", "content",
             "entries", "nodes", "hits", "docs", "products", "posts", "quotes")
# 수집 메타 필드 — 리포트에서 별도 표시
META_FIELDS = ("_src", "_at", "_page", "_url")


def die(msg: str) -> None:
    print(f"finalize.py: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- 입력 파싱

def extract_records(blob: Any, origin: str) -> tuple[list[dict], list]:
    """임의의 파싱 결과에서 (레코드 리스트, 에러 리스트)를 뽑아낸다."""
    errors: list = []

    if isinstance(blob, list):
        return [r for r in blob if isinstance(r, dict)], errors

    if not isinstance(blob, dict):
        return [], errors

    if isinstance(blob.get("errors"), list):
        errors = [{"_from": origin, **e} if isinstance(e, dict) else {"_from": origin, "error": e}
                  for e in blob["errors"]]

    # 알려진 키 우선
    for k in LIST_KEYS:
        v = blob.get(k)
        if isinstance(v, list) and (not v or isinstance(v[0], dict)):
            return [r for r in v if isinstance(r, dict)], errors

    # 없으면 dict 리스트인 값 중 가장 긴 것
    best: list[dict] = []
    for v in blob.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and len(v) > len(best):
            best = [r for r in v if isinstance(r, dict)]
    if best:
        return best, errors

    # 레코드 하나짜리 객체
    return ([blob], errors) if blob else ([], errors)


def load_file(path: str) -> tuple[list[dict], list]:
    if not os.path.exists(path):
        die(f"입력 파일 없음: {path}")
    raw = open(path, encoding="utf-8").read().strip()
    if not raw:
        return [], []

    try:
        return extract_records(json.loads(raw), path)
    except json.JSONDecodeError:
        pass

    # JSONL 시도
    recs, bad = [], 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                recs.append(obj)
        except json.JSONDecodeError:
            bad += 1
    if not recs:
        die(f"JSON 으로도 JSONL 로도 못 읽음: {path}")
    if bad:
        print(f"  경고: {path} — 파싱 실패한 줄 {bad}개 건너뜀", file=sys.stderr)
    return recs, []


# ------------------------------------------------------------ 평탄화/중복제거

def flatten(obj: dict, prefix: str = "", depth: int = 0) -> dict:
    """중첩 dict 를 점 표기로 편다. 리스트는 JSON 문자열로 보존한다."""
    out: dict = {}
    for k, v in obj.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict) and depth < 4:
            out.update(flatten(v, f"{key}.", depth + 1))
        elif isinstance(v, (list, tuple)):
            out[key] = json.dumps(list(v), ensure_ascii=False) if v else ""
        elif v is None:
            out[key] = ""
        elif isinstance(v, bool):
            out[key] = "true" if v else "false"
        else:
            out[key] = v
    return out


def dedupe(records: list[dict], keys: list[str]) -> tuple[list[dict], int]:
    if not keys:
        return records, 0
    seen, kept = set(), []
    for r in records:
        flat = flatten(r)
        sig = tuple(str(r.get(k, flat.get(k, ""))) for k in keys)
        if sig in seen:
            continue
        seen.add(sig)
        kept.append(r)
    return kept, len(records) - len(kept)


def is_empty(v: Any) -> bool:
    return v is None or v == "" or v == [] or v == {}


# ------------------------------------------------------------------- 리포트

def field_stats(records: list[dict]) -> "OrderedDict[str, dict]":
    total = len(records)
    order: "OrderedDict[str, None]" = OrderedDict()
    filled: Counter = Counter()
    types: dict[str, Counter] = {}
    samples: dict[str, Any] = {}

    for r in records:
        for k, v in flatten(r).items():
            order.setdefault(k, None)
            if is_empty(v):
                continue
            filled[k] += 1
            types.setdefault(k, Counter())[type(v).__name__] += 1
            if k not in samples:
                s = str(v).replace("\n", " ").replace("|", "\\|")
                samples[k] = s[:60] + ("…" if len(s) > 60 else "")

    stats: "OrderedDict[str, dict]" = OrderedDict()
    for k in order:
        n = filled[k]
        stats[k] = {
            "filled": n,
            "rate": (n / total * 100) if total else 0.0,
            "type": types.get(k, Counter()).most_common(1)[0][0] if k in types else "-",
            "sample": samples.get(k, ""),
        }
    return stats


TYPE_KO = {"str": "문자열", "int": "정수", "float": "실수", "bool": "불리언", "-": "-"}


def build_report(stats, total, removed, sources, errors, out_prefix, key_fields) -> str:
    L = ["## 수집 품질", ""]
    L.append(f"- 입력 파일: {len(sources)}개")
    L.append(f"- 최종 레코드: **{total:,}건**"
             + (f" (중복 {removed:,}건 제거, 키: `{', '.join(key_fields)}`)" if key_fields
                else " (중복 제거 안 함 — `--key` 미지정)"))
    L.append(f"- 산출물: `{out_prefix}.jsonl`, `{out_prefix}.csv`")
    if errors:
        L.append(f"- **수집 중 실패: {len(errors)}건** → `{out_prefix}-errors.json`")
    L.append("")

    data_fields = [k for k in stats if k not in META_FIELDS]
    L += ["| 필드 | 타입 | 채움률 | 건수 | 예시 |", "|---|---|---:|---:|---|"]
    for k in data_fields:
        s = stats[k]
        mark = "" if s["rate"] >= 95 else (" ⚠️" if s["rate"] >= 50 else " ❌")
        L.append(f"| `{k}`{mark} | {TYPE_KO.get(s['type'], s['type'])} | "
                 f"{s['rate']:.1f}% | {s['filled']:,} | {s['sample']} |")
    meta = [k for k in stats if k in META_FIELDS]
    if meta:
        L.append(f"| _(출처 메타)_ | | | | {', '.join('`' + m + '`' for m in meta)} |")
    L.append("")

    low = [(k, stats[k]["rate"]) for k in data_fields if stats[k]["rate"] < 95]
    if low:
        L.append("**확인 필요** — 채움률이 낮은 필드는 셀렉터가 일부 레이아웃에서 안 맞았을 가능성이 높다:")
        for k, r in sorted(low, key=lambda x: x[1]):
            L.append(f"- `{k}`: {r:.1f}%")
    else:
        L.append("모든 필드 채움률 95% 이상.")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(
        description="크롤 원본 JSON/JSONL -> JSONL + CSV + 품질 리포트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="예: finalize.py data/raw/*.json --out data/items --key id --report")
    ap.add_argument("inputs", nargs="+", help="입력 JSON/JSONL (글롭 가능)")
    ap.add_argument("--out", required=True, help="출력 경로 접두사 (확장자 제외)")
    ap.add_argument("--key", default="", help="중복 제거 키. 쉼표로 복합키: --key title,date")
    ap.add_argument("--report", action="store_true", help="마크다운 품질 리포트를 stdout 에 출력")
    ap.add_argument("--report-file", help="리포트를 파일로도 저장")
    ap.add_argument("--no-csv", action="store_true", help="CSV 생략")
    args = ap.parse_args()

    records: list[dict] = []
    errors: list = []
    for path in args.inputs:
        recs, errs = load_file(path)
        records.extend(recs)
        errors.extend(errs)
        print(f"  {path}: {len(recs):,}건"
              + (f" (실패 {len(errs)}건)" if errs else ""), file=sys.stderr)

    if not records:
        die("레코드를 하나도 못 찾음. 입력 구조를 확인하라 "
            "(배열 / {'data': [...]} / JSONL 을 지원한다).")

    key_fields = [k.strip() for k in args.key.split(",") if k.strip()]
    records, removed = dedupe(records, key_fields)

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)

    jsonl_path = f"{args.out}.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    csv_path = None
    if not args.no_csv:
        flat = [flatten(r) for r in records]
        cols: "OrderedDict[str, None]" = OrderedDict()
        for r in flat:
            for k in r:
                cols.setdefault(k, None)
        csv_path = f"{args.out}.csv"
        # utf-8-sig: Excel 이 한글을 깨지 않게 하는 BOM
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(cols), extrasaction="ignore")
            w.writeheader()
            for r in flat:
                w.writerow(r)

    err_path = None
    if errors:
        err_path = f"{args.out}-errors.json"
        with open(err_path, "w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)

    print(f"\n  -> {jsonl_path} ({len(records):,}건)", file=sys.stderr)
    if csv_path:
        print(f"  -> {csv_path}", file=sys.stderr)
    if err_path:
        print(f"  -> {err_path} (실패 {len(errors)}건)", file=sys.stderr)
    if removed:
        print(f"  중복 {removed:,}건 제거", file=sys.stderr)

    if args.report or args.report_file:
        report = build_report(field_stats(records), len(records), removed,
                              args.inputs, errors, args.out, key_fields)
        if args.report:
            print("\n" + report)
        if args.report_file:
            with open(args.report_file, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"  -> {args.report_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
