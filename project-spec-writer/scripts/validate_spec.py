#!/usr/bin/env python3
"""Mechanical validator for project-spec-writer specs.

Usage:
    python3 validate_spec.py <path/to/SPEC.md>

Checks structure (tag balance, known/required sections, empty sections) and
consistency (routes vs pages, hex colors, unresolved markers, env var mentions).
Exit code 0 = no errors (warnings allowed), 1 = errors found, 2 = usage/parse failure.

The validator is intentionally lenient about tags that appear mid-line (e.g.
placeholders like ``?cursor=<opaque>``): only tags at the start of a line, or
inline elements that open and close on the same line, are treated as structure.
"""

import re
import sys
from pathlib import Path

TAG_RE = re.compile(r"<(/?)([a-zA-Z_][\w.-]*)((?:\s+[\w-]+=\"[^\"]*\")*)\s*(/?)>")

ROOT_TAGS = ("project_specification", "feature_specification")

KNOWN_SECTIONS = {
    "project_specification": {
        "project_name", "overview", "assumptions", "open_questions",
        "scope_boundaries", "technology_stack", "prerequisites",
        "environment_variables", "file_structure", "core_data_entities",
        "authentication", "route_definitions", "component_hierarchy",
        "pages_and_interfaces", "api_endpoints", "commands_and_flags",
        "public_api", "core_functionality", "ai_integration", "error_handling",
        "third_party_integrations", "aesthetic_guidelines", "output_formatting",
        "api_design_principles", "internationalization",
        "security_considerations", "advanced_functionality",
        "final_integration_test", "success_criteria", "build_output",
        "deployment_and_operations", "key_implementation_notes",
    },
    "feature_specification": {
        "feature_name", "overview", "assumptions", "open_questions",
        "existing_codebase_context", "scope_boundaries", "data_model_changes",
        "api_changes", "ui_changes", "integration_points", "core_functionality",
        "error_handling", "regression_risks", "migration_plan",
        "final_integration_test", "success_criteria", "implementation_order",
    },
}

RECOMMENDED_SECTIONS = {
    "project_specification": [
        "project_name", "overview", "assumptions", "open_questions",
        "scope_boundaries", "technology_stack", "core_functionality",
        "final_integration_test", "success_criteria",
    ],
    "feature_specification": [
        "feature_name", "overview", "existing_codebase_context",
        "regression_risks", "final_integration_test", "success_criteria",
        "implementation_order",
    ],
}

INTERFACE_SECTIONS = {
    "pages_and_interfaces", "api_endpoints", "commands_and_flags",
    "public_api", "ui_changes", "api_changes",
}

UNRESOLVED_RE = re.compile(r"\b(TODO|TBD|FIXME|XXX)\b|\?\?\?|미정\b")
ENV_MENTION_RE = re.compile(r"process\.env\.([A-Z][A-Z0-9_]+)|os\.environ(?:\.get)?\[?[\"']([A-Z][A-Z0-9_]+)[\"']")
HEX_TOKEN_RE = re.compile(r"#([0-9A-Za-z]{3,8})\b")
PAGE_ATTR_RE = re.compile(r"page=\"([A-Za-z0-9]+)\"")


def pascal_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def find_spec_lines(lines):
    """Return (root_tag, start_idx, end_idx) of the spec region, or None."""
    for root in ROOT_TAGS:
        start = end = None
        for i, line in enumerate(lines):
            if f"<{root}>" in line and start is None:
                start = i
            if f"</{root}>" in line:
                end = i
        if start is not None:
            return root, start, end
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"error: file not found: {path}")
        return 2

    lines = path.read_text(encoding="utf-8").splitlines()
    errors, warnings = [], []

    region = find_spec_lines(lines)
    if region is None:
        print("error: no <project_specification> or <feature_specification> root tag found")
        return 1
    root, start, end = region
    if end is None:
        errors.append((start + 1, f"<{root}> is never closed"))
        end = len(lines) - 1

    # ---- structural scan ------------------------------------------------
    stack = []           # [(tag, line_no)]
    sections = {}        # top-level section -> first line_no
    section_of_line = {} # line idx -> current top-level section name
    empty_candidates = {}  # tag -> (line_no, had_content)
    in_fence = False

    for i in range(start, end + 1):
        raw = lines[i]
        if raw.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            # code blocks inside the spec are opaque to structure
            section_of_line[i] = stack[1][0] if len(stack) > 1 else None
            continue

        section_of_line[i] = stack[1][0] if len(stack) > 1 else None

        # cancel inline elements (<x>...</x> on one line) by processing pairs
        tokens = list(TAG_RE.finditer(raw))
        line_stack = []
        structural = []
        for m in tokens:
            closing, name, _attrs, selfclose = m.group(1), m.group(2), m.group(3), m.group(4)
            if selfclose:
                continue
            if not closing:
                line_stack.append((name, m))
            else:
                if line_stack and line_stack[-1][0] == name:
                    open_name, open_m = line_stack.pop()  # inline element, balanced on this line
                    # an inline element that is a direct child of the root is still a section
                    if len(stack) == 1 and not raw[: open_m.start()].strip():
                        if open_name in sections:
                            warnings.append((i + 1, f"duplicate top-level section <{open_name}> (first at line {sections[open_name]})"))
                        else:
                            sections[open_name] = i + 1
                        has_text = bool(raw[open_m.end(): m.start()].strip())
                        empty_candidates[open_name] = [i + 1, has_text]
                else:
                    structural.append(("close", name, m))
        structural.extend(("open", name, m) for name, m in line_stack)
        structural.sort(key=lambda t: t[2].start())

        for kind, name, m in structural:
            # mid-line leftover tags (e.g. <opaque> placeholders) are not structure
            if raw[: m.start()].strip() and kind == "open":
                continue
            if kind == "open":
                if len(stack) == 1:  # direct child of root
                    if name in sections:
                        warnings.append((i + 1, f"duplicate top-level section <{name}> (first at line {sections[name]})"))
                    else:
                        sections[name] = i + 1
                    empty_candidates[name] = [i + 1, False]
                stack.append((name, i + 1))
            else:
                if stack and stack[-1][0] == name:
                    stack.pop()
                elif any(t == name for t, _ in stack):
                    while stack and stack[-1][0] != name:
                        t, ln = stack.pop()
                        errors.append((ln, f"<{t}> opened here but closed out of order (found </{name}> at line {i + 1})"))
                    if stack:
                        stack.pop()
                elif name != root:
                    errors.append((i + 1, f"stray closing tag </{name}> with no matching open tag"))

        # track content for empty-section detection (self-closing tags like
        # <route ... /> count as content)
        stripped = TAG_RE.sub("", raw).strip()
        has_selfclosing = any(m.group(4) for m in tokens)
        if (stripped or has_selfclosing) and len(stack) > 1:
            top = stack[1][0]
            if top in empty_candidates:
                empty_candidates[top][1] = True

        if not stack and i == start:
            stack.append((root, i + 1))

    for tag, ln in stack:
        if tag != root:
            errors.append((ln, f"<{tag}> is never closed"))

    # ---- section-level checks -------------------------------------------
    known = KNOWN_SECTIONS[root]
    for name, ln in sections.items():
        if name not in known:
            warnings.append((ln, f"unknown top-level section <{name}> — custom sections are allowed, but double-check the name against the schema reference"))

    for name in RECOMMENDED_SECTIONS[root]:
        if name not in sections:
            warnings.append((start + 1, f"recommended section <{name}> is missing"))

    if not INTERFACE_SECTIONS & set(sections):
        warnings.append((start + 1, "no interface section found (pages_and_interfaces / api_endpoints / commands_and_flags / public_api)"))

    for name, (ln, had_content) in empty_candidates.items():
        if not had_content:
            errors.append((ln, f"section <{name}> is empty"))

    # ---- content checks ---------------------------------------------------
    def section_text(name):
        return "\n".join(lines[i] for i in range(start, end + 1) if section_of_line.get(i) == name)

    body_by_section = {}
    for i in range(start, end + 1):
        sec = section_of_line.get(i)
        body_by_section.setdefault(sec, []).append((i + 1, lines[i]))

    # unresolved markers outside open_questions
    for sec, entries in body_by_section.items():
        if sec == "open_questions":
            continue
        for ln, text in entries:
            if UNRESOLVED_RE.search(text):
                warnings.append((ln, f"unresolved marker in <{sec}> — move undecided items to <open_questions>"))

    # hex color sanity
    for ln, text in ((i + 1, lines[i]) for i in range(start, end + 1)):
        for m in HEX_TOKEN_RE.finditer(text):
            tok = m.group(1)
            if len(tok) in (3, 6, 8) and re.fullmatch(r"[0-9A-Fa-f]+", tok):
                continue
            if len(tok) in (4, 5, 7) and re.fullmatch(r"[0-9A-Fa-f]+", tok):
                warnings.append((ln, f"suspicious hex color #{tok} (unusual length {len(tok)})"))
            elif re.fullmatch(r"[0-9A-Fa-f]*[G-Zg-z][0-9A-Za-z]*", tok) and len(tok) == 6:
                warnings.append((ln, f"#{tok} looks like a hex color but contains non-hex characters"))

    # routes ↔ pages cross-reference
    if "route_definitions" in sections and "pages_and_interfaces" in sections:
        pages_text = section_text("pages_and_interfaces")
        for ln, text in body_by_section.get("route_definitions", []):
            for m in PAGE_ATTR_RE.finditer(text):
                snake = pascal_to_snake(m.group(1))
                base = re.sub(r"_(page|view)$", "", snake)
                if snake not in pages_text and base not in pages_text and m.group(1) not in pages_text:
                    warnings.append((ln, f'route page="{m.group(1)}" has no matching section in <pages_and_interfaces>'))

    # env var mentions ↔ environment_variables
    declared = set(re.findall(r"<name>([A-Z][A-Z0-9_]+)</name>", section_text("environment_variables")))
    for sec, entries in body_by_section.items():
        if sec == "environment_variables":
            continue
        for ln, text in entries:
            for m in ENV_MENTION_RE.finditer(text):
                var = m.group(1) or m.group(2)
                if var and var not in declared:
                    warnings.append((ln, f"env var {var} referenced but not declared in <environment_variables>"))

    # ---- report -----------------------------------------------------------
    for ln, msg in sorted(errors):
        print(f"ERROR   line {ln}: {msg}")
    for ln, msg in sorted(warnings):
        print(f"WARNING line {ln}: {msg}")
    print(f"\n{path.name}: {len(errors)} error(s), {len(warnings)} warning(s), "
          f"{len(sections)} top-level section(s) [{root}]")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
