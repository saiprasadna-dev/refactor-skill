#!/usr/bin/env python3
"""Trace a Spring endpoint end-to-end through a Java codebase.

Given an endpoint path (e.g. /search), finds the controller handler and
follows the dependency graph through services, repositories, external HTTP
clients, and messaging — producing the "endpoint slice": every class
involved plus the behavior-critical markers (validation, security,
transactions, caching, side effects) that must be preserved during
re-architecture.

Static, heuristic, stdlib-only. It reads source text — it does not compile
or execute anything — so treat the output as a high-confidence map to be
verified, not as ground truth.

Usage:
  python3 scripts/trace_endpoint.py <endpoint-path> [--root DIR] [--format ascii|md|json] [--depth N]

Examples:
  python3 scripts/trace_endpoint.py /search --root ~/projects/shop
  python3 scripts/trace_endpoint.py /api/orders/{id} --root . --format md
  python3 scripts/trace_endpoint.py /search --format json > slice.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {"target", "build", "out", ".git", ".gradle", ".mvn", "node_modules", "generated", "bin"}

MAPPING_RE = re.compile(
    r"@(Get|Post|Put|Delete|Patch|Request)Mapping\s*(\(([^)]*)\))?", re.S)
PATH_ATTR_RE = re.compile(r'(?:path|value)\s*=\s*(\{[^}]*\}|"[^"]*")')
STRING_RE = re.compile(r'"([^"]*)"')
CLASS_RE = re.compile(
    r"(?:public\s+|abstract\s+|final\s+)*(?:class|interface|record|enum)\s+(\w+)"
    r"(?:<[^{]*?>)?(?:\s+extends\s+([\w<>,.\s]+?))?(?:\s+implements\s+([\w<>,.\s]+?))?\s*[{(]")
FIELD_RE = re.compile(r"(?:private|protected|public)\s+(?:final\s+)?([A-Z]\w*(?:<[^;=]*>)?)\s+(\w+)\s*[;=]")
CTOR_PARAM_TYPE_RE = re.compile(r"([A-Z]\w*(?:<[^,()]*>)?)\s+\w+\s*[,)]")

REPO_BASES = ("JpaRepository", "CrudRepository", "PagingAndSortingRepository",
              "MongoRepository", "ReactiveCrudRepository", "ListCrudRepository",
              "JpaSpecificationExecutor", "ElasticsearchRepository")

INFRA_MARKERS = {
    "RestTemplate": "external HTTP call (RestTemplate)",
    "RestClient": "external HTTP call (RestClient)",
    "WebClient": "external HTTP call (WebClient)",
    "HttpClient": "external HTTP call (HttpClient)",
    "KafkaTemplate": "publishes to Kafka",
    "RabbitTemplate": "publishes to RabbitMQ",
    "JmsTemplate": "publishes to JMS",
    "EntityManager": "direct JPA EntityManager usage",
    "JdbcTemplate": "direct SQL (JdbcTemplate)",
    "NamedParameterJdbcTemplate": "direct SQL (NamedParameterJdbcTemplate)",
    "MongoTemplate": "MongoDB template usage",
    "RedisTemplate": "Redis usage",
    "JavaMailSender": "sends email",
}

BEHAVIOR_ANNOTATIONS = {
    "@Transactional": "transaction boundary",
    "@PreAuthorize": "security rule",
    "@PostAuthorize": "security rule",
    "@Secured": "security rule",
    "@RolesAllowed": "security rule",
    "@Valid": "request validation",
    "@Validated": "validation",
    "@Cacheable": "caching",
    "@CacheEvict": "cache eviction",
    "@CachePut": "cache update",
    "@Async": "async execution",
    "@KafkaListener": "consumes Kafka messages",
    "@JmsListener": "consumes JMS messages",
    "@RabbitListener": "consumes RabbitMQ messages",
    "@Scheduled": "scheduled job",
    "@EventListener": "application event listener",
    "@TransactionalEventListener": "transactional event listener",
    "@Retryable": "retry semantics",
    "@CircuitBreaker": "circuit breaker",
    "@RateLimiter": "rate limiting",
    "@Value": "config property",
    "@ConfigurationProperties": "config binding",
}


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def base_type(type_str):
    return re.sub(r"<.*", "", type_str).strip()


def generic_args(type_str):
    m = re.search(r"<(.*)>", type_str)
    return [base_type(a) for a in m.group(1).split(",")] if m else []


class JavaClass:
    def __init__(self, name, path, text):
        self.name = name
        self.path = path
        self.text = text
        m = CLASS_RE.search(text)
        self.extends = []
        self.implements = []
        if m and m.group(1) == name:
            if m.group(2):
                self.extends = [base_type(t) for t in m.group(2).split(",")]
            if m.group(3):
                self.implements = [base_type(t) for t in m.group(3).split(",")]
        self.supertypes_raw = (m.group(2) or "") + "," + (m.group(3) or "") if m else ""
        self.is_test = "/test/" in str(path).replace("\\", "/")

    def annotations(self):
        found = {}
        for ann, meaning in BEHAVIOR_ANNOTATIONS.items():
            if ann + "(" in self.text or re.search(re.escape(ann) + r"\b", self.text):
                found[ann] = meaning
        return found

    def infra(self):
        return {m: d for m, d in INFRA_MARKERS.items()
                if re.search(r"\b" + m + r"\b", self.text)}

    def stereotype(self):
        t = self.text
        if "@RestController" in t or "@Controller" in t:
            return "controller"
        if any(b in self.supertypes_raw for b in REPO_BASES) or "@Repository" in t:
            return "repository"
        if "@FeignClient" in t:
            return "external-client"
        if "@Service" in t:
            return "service"
        if "@Entity" in t or "@Document(" in t or "@Table(" in t:
            return "entity"
        if "@Component" in t:
            return "component"
        if "@Configuration" in t:
            return "configuration"
        if self.is_test:
            return "test"
        return "class"

    def dependencies(self, index):
        deps = set()
        body = strip_comments(self.text)
        for type_str, _name in FIELD_RE.findall(body):
            deps.add(base_type(type_str))
        for m in re.finditer(r"\b" + self.name + r"\s*\(([^)]*)\)", body):
            for type_str in CTOR_PARAM_TYPE_RE.findall(m.group(1) + ")"):
                deps.add(base_type(type_str))
        return sorted(d for d in deps
                      if d != self.name and (d in index or d in INFRA_MARKERS))

    def entity_types(self, index):
        if self.stereotype() != "repository":
            return []
        m = CLASS_RE.search(self.text)
        raw = (m.group(2) or "") if m else ""
        args = generic_args(self.supertypes_raw) or generic_args(raw)
        return [a for a in args if a in index and index[a].stereotype() == "entity"]


def build_index(root):
    index = {}
    for path in root.rglob("*.java"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = CLASS_RE.search(text)
        if m:
            index[m.group(1)] = JavaClass(m.group(1), path, text)
    return index


def mapping_paths(annotation_args):
    if not annotation_args:
        return [""]
    m = PATH_ATTR_RE.search(annotation_args)
    if m:
        return STRING_RE.findall(m.group(1)) or [""]
    return STRING_RE.findall(annotation_args)[:1] or [""]


def normalize(path):
    path = "/" + path.strip("/")
    return "/" if path == "//" else path


def path_matches(query, candidate):
    q, c = normalize(query), normalize(candidate)
    if q == c:
        return True
    pattern = re.sub(r"\{[^/}]+\}", r"[^/]+", re.escape(c).replace(r"\{", "{").replace(r"\}", "}"))
    pattern = re.sub(r"\{[^/}]+\}", r"[^/]+", pattern)
    return re.fullmatch(pattern, q) is not None or re.fullmatch(
        re.sub(r"\{[^/}]+\}", r"\\{[^/}]+\\}", pattern), q) is not None


def find_handlers(index, endpoint):
    handlers = []
    for cls in index.values():
        if cls.stereotype() != "controller":
            continue
        text = cls.text
        class_ann = MAPPING_RE.search(text[:text.find("class ")] if "class " in text else text)
        bases = mapping_paths(class_ann.group(3)) if class_ann else [""]
        for m in MAPPING_RE.finditer(text):
            if class_ann and m.start() == class_ann.start():
                continue
            verb = "ANY" if m.group(1) == "Request" else m.group(1).upper()
            for sub in mapping_paths(m.group(3)):
                for base in bases:
                    full = normalize(base.rstrip("/") + "/" + sub.lstrip("/"))
                    if path_matches(endpoint, full):
                        tail = text[m.end():]
                        sig = re.search(r"(?:public|protected|private)?\s*[\w<>,.\[\]?\s]+\s+(\w+)\s*\(", tail)
                        handlers.append({
                            "controller": cls.name,
                            "file": str(cls.path),
                            "http_method": verb,
                            "path": full,
                            "handler_method": sig.group(1) if sig else "?",
                        })
    return handlers


def walk_slice(index, start, depth):
    slice_classes, queue, seen = {}, [(start, 0)], set()
    while queue:
        name, level = queue.pop(0)
        if name in seen or name not in index:
            continue
        seen.add(name)
        cls = index[name]
        deps = cls.dependencies(index)
        impls = [c.name for c in index.values()
                 if name in c.implements and c.name not in seen]
        slice_classes[name] = {
            "role": cls.stereotype(),
            "file": str(cls.path),
            "behavior_markers": cls.annotations(),
            "infrastructure": cls.infra(),
            "entities": cls.entity_types(index),
            "depends_on": deps,
            "implemented_by": impls,
        }
        if level < depth:
            for nxt in deps + impls + cls.entity_types(index):
                queue.append((nxt, level + 1))
    return slice_classes


def find_tests(index, slice_names):
    tests = {}
    for cls in index.values():
        if not cls.is_test:
            continue
        used = sorted(n for n in slice_names
                      if re.search(r"\b" + n + r"\b", cls.text))
        if used:
            tests[cls.name] = {"file": str(cls.path), "covers": used}
    return tests


def render_ascii(result):
    out = [f"Endpoint slice for {result['endpoint']}  (root: {result['root']})", "=" * 72]
    for h in result["handlers"]:
        out.append(f"HANDLER  {h['http_method']} {h['path']}  ->  "
                   f"{h['controller']}.{h['handler_method']}()  [{h['file']}]")
    out.append("")
    for name, info in result["slice"].items():
        out.append(f"[{info['role']}] {name}  ({info['file']})")
        for ann, meaning in info["behavior_markers"].items():
            out.append(f"    ! {ann}  — {meaning} (must be preserved)")
        for marker, desc in info["infrastructure"].items():
            out.append(f"    ~ {desc}")
        if info["entities"]:
            out.append(f"    # entities: {', '.join(info['entities'])}")
        if info["depends_on"]:
            out.append(f"    -> depends on: {', '.join(info['depends_on'])}")
        if info["implemented_by"]:
            out.append(f"    <- implemented by: {', '.join(info['implemented_by'])}")
    out.append("")
    if result["tests"]:
        out.append("Existing tests touching this slice (your safety net):")
        for t, info in result["tests"].items():
            out.append(f"  {t}  covers {', '.join(info['covers'])}  ({info['file']})")
    else:
        out.append("WARNING: no existing tests reference this slice — write "
                   "characterization tests BEFORE changing anything.")
    return "\n".join(out)


def render_md(result):
    out = [f"# Endpoint slice: `{result['endpoint']}`", ""]
    out.append("| HTTP | Path | Handler | File |")
    out.append("|---|---|---|---|")
    for h in result["handlers"]:
        out.append(f"| {h['http_method']} | {h['path']} | "
                   f"`{h['controller']}.{h['handler_method']}()` | {h['file']} |")
    out += ["", "## Classes in the slice", ""]
    for name, info in result["slice"].items():
        out.append(f"### `{name}` — {info['role']}")
        out.append(f"- file: `{info['file']}`")
        for ann, meaning in info["behavior_markers"].items():
            out.append(f"- **preserve:** `{ann}` — {meaning}")
        for _, desc in info["infrastructure"].items():
            out.append(f"- side effect: {desc}")
        if info["entities"]:
            out.append(f"- entities: {', '.join(f'`{e}`' for e in info['entities'])}")
        if info["depends_on"]:
            out.append(f"- depends on: {', '.join(f'`{d}`' for d in info['depends_on'])}")
        if info["implemented_by"]:
            out.append(f"- implemented by: {', '.join(f'`{i}`' for i in info['implemented_by'])}")
        out.append("")
    out.append("## Existing tests touching the slice")
    out.append("")
    if result["tests"]:
        for t, info in result["tests"].items():
            out.append(f"- `{t}` covers {', '.join(f'`{c}`' for c in info['covers'])}")
    else:
        out.append("**None found — write characterization tests before any change.**")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Trace a Spring endpoint end-to-end.")
    parser.add_argument("endpoint", help="endpoint path, e.g. /search or /api/orders/{id}")
    parser.add_argument("--root", default=".", help="project root to scan (default: cwd)")
    parser.add_argument("--format", choices=["ascii", "md", "json"], default="ascii")
    parser.add_argument("--depth", type=int, default=6, help="dependency depth (default 6)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        sys.exit(2)

    index = build_index(root)
    if not index:
        print(f"error: no Java sources found under {root}", file=sys.stderr)
        sys.exit(2)

    handlers = find_handlers(index, args.endpoint)
    if not handlers:
        print(f"No handler found for '{args.endpoint}'. Check the path (include "
              "any class-level prefix like /api) or search mappings manually.",
              file=sys.stderr)
        sys.exit(1)

    slice_classes = {}
    for h in handlers:
        slice_classes.update(walk_slice(index, h["controller"], args.depth))

    result = {
        "endpoint": args.endpoint,
        "root": str(root),
        "handlers": handlers,
        "slice": slice_classes,
        "tests": find_tests(index, set(slice_classes)),
    }

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.format == "md":
        print(render_md(result))
    else:
        print(render_ascii(result))


if __name__ == "__main__":
    main()
