#!/usr/bin/env python3
"""Universal endpoint tracer — any language, any framework (heuristic).

Given an endpoint path (e.g. /search), finds where it is routed and walks
the dependency graph outward from the handler, producing the "endpoint
slice": every file involved, the behavior-critical markers that must be
preserved (auth, validation, transactions, caching), the side effects
(SQL, external HTTP, messaging, email, storage), and the existing tests
touching the slice.

Route detection support:
  Java/Kotlin  Spring (@GetMapping/@RequestMapping...), JAX-RS (@Path)
  JS/TS        Express / Hono / Koa / Fastify (app.get, router.post,
               app.use/app.route mounting), NestJS (@Controller/@Get),
               Next.js & SvelteKit file-based routes
  Python       FastAPI (@app.get, include_router prefix), Flask
               (@app.route / blueprints), Django (path()/re_path())
  Go           net/http HandleFunc, Gin/Echo/Fiber (.GET/.POST), Chi (.Get)
  C#           ASP.NET Core attributes ([Route], [HttpGet]) & minimal APIs
  Ruby         Rails routes.rb, Sinatra
  PHP          Laravel Route::get, Symfony #[Route]

Static, stdlib-only, heuristic: it reads source text, it does not execute
anything. Treat the output as a high-confidence map to verify, not ground
truth. Nested mounts are resolved two levels deep; aspects/AOP, DI wiring
done in config, and reflection are invisible to it — complete the map by
reading the code.

Usage:
  python3 scripts/trace_endpoint.py <endpoint-path> [--root DIR] [--format ascii|md|json] [--depth N]

Examples:
  python3 scripts/trace_endpoint.py /search --root .
  python3 scripts/trace_endpoint.py /api/orders/{id} --root ~/svc --format md
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {"node_modules", "target", "build", "dist", "out", ".git", ".gradle",
             ".mvn", "vendor", "__pycache__", ".venv", "venv", "env", "bin", "obj",
             ".next", ".svelte-kit", "coverage", ".idea", ".vscode", "generated"}

SOURCE_EXTS = {".java", ".kt", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
               ".py", ".go", ".cs", ".rb", ".php"}

TEST_FILE_RE = re.compile(
    r"(\.test\.|\.spec\.|_test\.(go|py|rb)$|^test_|Test\.java$|Tests?\.cs$|"
    r"Test\.kt$|_spec\.rb$|IT\.java$)", re.I)

# --- behavior markers: (regex, meaning, kind) applied to any slice file ----
MARKERS = [
    # must-preserve semantics
    (r"@Transactional|transaction\.atomic|\.transaction\s*\(|BEGIN TRANSACTION|beginTransaction|\[Transaction|DB::transaction", "transaction boundary", "preserve"),
    (r"@PreAuthorize|@PostAuthorize|@Secured|@RolesAllowed|\[Authorize|@login_required|permission_classes|before_action\s+:authenticate|requireAuth|passport\.authenticate|ensure_signed_in|->middleware\(\s*['\"]auth|jwt_required|get_current_user|@UseGuards", "auth/authorization rule", "preserve"),
    (r"@Valid\b|@Validated|class-validator|zod|joi\.|yup\.|pydantic|validates\s|->validate\(|\$request->validate|FluentValidation|@field_validator|marshmallow", "input validation", "preserve"),
    (r"@Cacheable|@CacheEvict|@CachePut|cache_page|\[ResponseCache|\.remember\(|Cache::|@cached", "caching semantics", "preserve"),
    (r"@Retryable|@CircuitBreaker|@RateLimiter|retry\s*=|Polly\.", "retry/circuit-breaker semantics", "preserve"),
    (r"idempoten", "idempotency handling", "preserve"),
    # side effects
    (r"\bSELECT\s|\bINSERT INTO\b|\bUPDATE\s+\w+\s+SET\b|\bDELETE FROM\b|\.prepare\(|JpaRepository|CrudRepository|EntityManager|JdbcTemplate|prisma\.|knex|sequelize|typeorm|SQLAlchemy|session\.query|objects\.(filter|get|create)|ActiveRecord|Eloquent|gorm\.|sqlx|DbContext|createQueryBuilder|D1Database", "database access", "side-effect"),
    (r"\bfetch\s*\(|axios|httpx|requests\.(get|post|put|delete)|RestTemplate|WebClient|RestClient|HttpClient|Guzzle|http\.Get|http\.Post|Faraday|net/http", "external HTTP call", "side-effect"),
    (r"Kafka|RabbitTemplate|amqp|JmsTemplate|sqs|sns\b|pubsub|celery|sidekiq|bullmq|EventBridge|nats\.", "messaging/queue", "side-effect"),
    (r"nodemailer|JavaMailSender|sendmail|Mailer|send_mail|SendGrid|ses\.|smtp", "sends email", "side-effect"),
    (r"twilio|sms\b|Sms[A-Z(]", "sends SMS", "side-effect"),
    (r"S3Client|bucket\.(put|get|delete)|BlobClient|R2Bucket|storage\.upload|GCS", "object storage", "side-effect"),
    (r"redis|Memcached|memcache", "cache store access", "side-effect"),
    (r"@Scheduled|cron|celery\.beat|Hangfire|whenever", "scheduled job", "side-effect"),
    (r"@KafkaListener|@JmsListener|@RabbitListener|@EventListener|consumer\.subscribe", "message consumer", "side-effect"),
]

ROLE_HINTS = [
    (r"controller", "controller"), (r"handler", "handler"), (r"route", "route"),
    (r"middleware|interceptor|filter", "middleware"),
    (r"service|usecase|use_case", "service"),
    (r"repo|repositor|dao|store|persistence", "repository"),
    (r"model|entity|entities|schema|domain", "model"),
    (r"client|gateway|adapter", "client"), (r"config|settings", "config"),
    (r"migration", "migration"),
]

PARAM_TOKEN_RE = re.compile(r"(\{[^/}]*\}|:[A-Za-z_][\w]*|<[^/>]*>|\[[^/\]]*\])")


def normalize(path):
    path = "/" + (path or "").strip().strip("/")
    return "/" if path == "//" else path


def join_paths(prefix, frag):
    return normalize(prefix.rstrip("/") + "/" + frag.lstrip("/"))


def to_regex(route_path):
    out, last = "", 0
    for m in PARAM_TOKEN_RE.finditer(route_path):
        out += re.escape(route_path[last:m.start()]) + r"[^/]+"
        last = m.end()
    out += re.escape(route_path[last:])
    return out


def paths_match(query, candidate):
    q, c = normalize(query), normalize(candidate)
    if q == c:
        return True
    if re.fullmatch(to_regex(c), q):
        return True
    # allow querying with a literal param placeholder, e.g. /orders/{id}
    return re.fullmatch(to_regex(q), c) is not None


class Repo:
    def __init__(self, root):
        self.root = root
        self.files = {}          # Path -> text
        self.by_stem = {}        # "Name" -> [Path] (basename without ext)
        for p in sorted(root.rglob("*")):
            if p.suffix not in SOURCE_EXTS or not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            self.files[p] = text
            self.by_stem.setdefault(p.stem, []).append(p)
        self.go_module = self._go_module()

    def _go_module(self):
        gm = self.root / "go.mod"
        if gm.is_file():
            m = re.search(r"^module\s+(\S+)", gm.read_text(errors="replace"), re.M)
            return m.group(1) if m else None
        return None

    def rel(self, p):
        try:
            return str(p.relative_to(self.root))
        except ValueError:
            return str(p)


# ---------------------------------------------------------------- imports --
def resolve_js(path, text, repo):
    deps = []
    for m in re.finditer(r"""(?:from\s*|require\s*\(\s*|import\s*\(\s*)['"](\.{1,2}/[^'"]+)['"]""", text):
        base = (path.parent / m.group(1)).resolve()
        for cand in ([base.with_suffix(base.suffix)] if base.suffix in SOURCE_EXTS else []) + \
                    [base.with_name(base.name + ext) for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")] + \
                    [base / ("index" + ext) for ext in (".ts", ".tsx", ".js", ".jsx")]:
            if cand in repo.files:
                deps.append(cand)
                break
    return deps


def resolve_py(path, text, repo):
    deps = []
    for m in re.finditer(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", text, re.M):
        mod = m.group(1) or m.group(2)
        parts = mod.split(".")
        bases = [path.parent] if mod.startswith(".") else [repo.root] + \
            [d for d in path.parents if d != repo.root and repo.root in d.parents]
        if mod.startswith("."):
            dots = len(mod) - len(mod.lstrip("."))
            base = path.parent
            for _ in range(dots - 1):
                base = base.parent
            parts = [p for p in mod.lstrip(".").split(".") if p]
            bases = [base]
        for b in bases:
            cand_file = b.joinpath(*parts).with_suffix(".py") if parts else None
            cand_init = b.joinpath(*parts, "__init__.py") if parts else None
            for cand in (cand_file, cand_init):
                if cand and cand in repo.files:
                    deps.append(cand)
                    break
    return deps


def resolve_by_typename(path, text, repo, exts):
    """Java/Kotlin/C#: match capitalized identifiers against project filenames."""
    deps, body = [], re.sub(r"^\s*(?:import|using|package|namespace)\b.*$", "", text, flags=re.M)
    for name in set(re.findall(r"\b([A-Z][A-Za-z0-9]{2,})\b", body)):
        if name == path.stem:
            continue
        for cand in repo.by_stem.get(name, []):
            if cand.suffix in exts and cand != path:
                deps.append(cand)
    # interface -> implementation
    for cand, txt in repo.files.items():
        if cand.suffix in exts and cand != path and re.search(
                r"(?:implements|:)\s+[^{;]*\b" + re.escape(path.stem) + r"\b", txt):
            deps.append(cand)
    return deps


def resolve_go(path, text, repo):
    deps = [p for p in path.parent.glob("*.go") if p in repo.files and p != path]
    if repo.go_module:
        for m in re.finditer(r'"' + re.escape(repo.go_module) + r'/([\w./-]+)"', text):
            pkg_dir = repo.root / m.group(1)
            deps += [p for p in pkg_dir.glob("*.go") if p in repo.files]
    return deps


def resolve_generic_by_stem(path, text, repo, exts):
    deps = []
    for m in re.finditer(r"""(?:require_relative\s+['"]([^'"]+)|use\s+([\w\\]+);)""", text):
        target = m.group(1) or (m.group(2) or "").split("\\")[-1]
        stem = Path(target).stem
        for cand in repo.by_stem.get(stem, []):
            if cand.suffix in exts:
                deps.append(cand)
    for name in set(re.findall(r"\b([A-Z][A-Za-z0-9]{2,})\b", text)):
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        for cand in repo.by_stem.get(snake, []) + repo.by_stem.get(name, []):
            if cand.suffix in exts and cand != path:
                deps.append(cand)
    return deps


def dependencies(path, repo):
    text = repo.files[path]
    ext = path.suffix
    if ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        return resolve_js(path, text, repo)
    if ext == ".py":
        return resolve_py(path, text, repo)
    if ext in (".java", ".kt"):
        return resolve_by_typename(path, text, repo, {".java", ".kt"})
    if ext == ".cs":
        return resolve_by_typename(path, text, repo, {".cs"})
    if ext == ".go":
        return resolve_go(path, text, repo)
    if ext == ".rb":
        return resolve_generic_by_stem(path, text, repo, {".rb"})
    if ext == ".php":
        return resolve_generic_by_stem(path, text, repo, {".php"})
    return []


# ------------------------------------------------------------------ routes --
def js_mount_prefixes(repo):
    """file -> [prefixes] from app.use('/x', r) / app.route('/x', r) / registerRoutes."""
    mounts = {}
    for path, text in repo.files.items():
        if path.suffix not in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            continue
        imports = {}
        import_res = [
            re.finditer(r"""import\s*(?:\{([^}]*)\}|(\w+))\s*from\s*['"](\.{1,2}/[^'"]+)['"]""", text),
            re.finditer(r"""(?:const|let|var)\s*(?:\{([^}]*)\}|(\w+))\s*=\s*require\(\s*['"](\.{1,2}/[^'"]+)['"]\s*\)""", text),
        ]
        for res in import_res:
            for m in res:
                names = [n.strip().split(" as ")[-1].split(":")[-1].strip()
                         for n in (m.group(1) or "").split(",") if n.strip()]
                if m.group(2):
                    names.append(m.group(2))
                for cand in resolve_js(path, f'import x from "{m.group(3)}"', repo):
                    for n in names:
                        imports[n] = cand
        for m in re.finditer(r"""\.\s*(?:use|route)\(\s*['"]([^'"]+)['"]\s*,\s*(\w+)""", text):
            prefix, var = m.group(1), m.group(2)
            if var in imports:
                mounts.setdefault(imports[var], []).append((path, prefix))
    # resolve up to two levels of nesting
    resolved = {}
    for target, entries in mounts.items():
        prefixes = []
        for parent, prefix in entries:
            parent_prefixes = [p for _, p in mounts.get(parent, [])] or [""]
            prefixes += [join_paths(pp, prefix) for pp in parent_prefixes]
        resolved[target] = prefixes
    return resolved


def py_mount_prefixes(repo):
    mounts = {}
    for path, text in repo.files.items():
        if path.suffix != ".py":
            continue
        for m in re.finditer(r"include_router\(\s*([\w.]+)[^)]*?prefix\s*=\s*['\"]([^'\"]+)['\"]", text, re.S):
            var, prefix = m.group(1).split(".")[-1], m.group(2)
            for im in re.finditer(r"from\s+([\w.]+)\s+import\s+([\w ,]+)", text):
                if re.search(r"\b" + re.escape(var) + r"\b", im.group(2)) or var == im.group(1).split(".")[-1]:
                    for cand in resolve_py(path, im.group(0), repo):
                        mounts.setdefault(cand, []).append(prefix)
        for m in re.finditer(r"Blueprint\(\s*['\"]\w+['\"][^)]*url_prefix\s*=\s*['\"]([^'\"]+)['\"]", text):
            mounts.setdefault(path, []).append(m.group(1))
    return mounts


def find_routes(repo):
    """Yield dicts: {method, path, file, evidence, line}."""
    routes = []
    js_mounts = js_mount_prefixes(repo)
    py_mounts = py_mount_prefixes(repo)

    def add(method, full, path, m, text):
        routes.append({"method": method.upper(), "path": normalize(full),
                       "file": path, "line": text.count("\n", 0, m.start()) + 1,
                       "evidence": m.group(0).strip()[:120]})

    for path, text in repo.files.items():
        ext = path.suffix
        if TEST_FILE_RE.search(path.name):
            continue

        if ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            prefixes = js_mounts.get(path, [""])
            for m in re.finditer(r"""\.\s*(get|post|put|delete|patch|all)\(\s*['"`]([^'"`]*)['"`]""", text):
                for pre in prefixes:
                    add(m.group(1), join_paths(pre, m.group(2)), path, m, text)
            ctrl = re.search(r"@Controller\(\s*['\"]([^'\"]*)['\"]?\s*\)?", text)
            if "@Controller" in text:
                base = ctrl.group(1) if ctrl else ""
                for m in re.finditer(r"@(Get|Post|Put|Delete|Patch)\(\s*['\"]?([^'\")]*)['\"]?\s*\)", text):
                    add(m.group(1), join_paths("/" + base, m.group(2)), path, m, text)
            rel = repo.rel(path).replace("\\", "/")
            fb = re.match(r"(?:src/)?(?:app|pages)/(.*?)(?:/route|/index)?\.(ts|js|tsx|jsx)$", rel)
            if fb and ("export" in text) and ("app/" in rel or "pages/" in rel):
                route = "/" + re.sub(r"\(([^)]*)\)/?", "", fb.group(1))
                for verb in re.findall(r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)", text) or (["GET"] if "pages/" in rel else []):
                    routes.append({"method": verb, "path": normalize(route), "file": path,
                                   "line": 1, "evidence": f"file-based route {rel}"})

        elif ext == ".py":
            prefixes = py_mounts.get(path, [""])
            for m in re.finditer(r"@[\w.]+\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]", text):
                for pre in prefixes:
                    add(m.group(1), join_paths(pre, m.group(2)), path, m, text)
            for m in re.finditer(r"@[\w.]+\.route\(\s*['\"]([^'\"]+)['\"](?:[^)]*methods\s*=\s*\[([^\]]*)\])?", text):
                methods = re.findall(r"['\"](\w+)['\"]", m.group(2) or "") or ["GET"]
                for verb in methods:
                    for pre in prefixes:
                        add(verb, join_paths(pre, m.group(1)), path, m, text)
            for m in re.finditer(r"\b(?:path|re_path)\(\s*r?['\"]([^'\"]+)['\"]", text):
                add("ANY", "/" + m.group(1).lstrip("^").rstrip("$"), path, m, text)

        elif ext in (".java", ".kt"):
            head = text.split("class ", 1)[0] if "class " in text else text
            cm = re.search(r"@RequestMapping\s*\(([^)]*)\)", head)
            bases = re.findall(r'"([^"]*)"', cm.group(1)) if cm else [""]
            for m in re.finditer(r"@(Get|Post|Put|Delete|Patch|Request)Mapping\s*(\(([^)]*)\))?", text):
                if cm and m.start() == cm.start():
                    continue
                verb = "ANY" if m.group(1) == "Request" else m.group(1)
                subs = re.findall(r'"([^"]*)"', m.group(3) or "") or [""]
                for base in bases:
                    for sub in subs:
                        add(verb, join_paths("/" + base, sub), path, m, text)
            cp = re.search(r'@Path\("([^"]*)"\)', text)
            if cp:
                for m in re.finditer(r"@(GET|POST|PUT|DELETE|PATCH)\b(?:.*?@Path\(\"([^\"]*)\"\))?", text, re.S):
                    add(m.group(1), join_paths("/" + cp.group(1), m.group(2) or ""), path, m, text)
            for m in re.finditer(r"""\b(get|post|put|delete|patch)\(\s*"([^"]+)"\s*\)\s*\{""", text):
                add(m.group(1), m.group(2), path, m, text)  # Ktor

        elif ext == ".go":
            for m in re.finditer(r'\.\s*(GET|POST|PUT|DELETE|PATCH|Get|Post|Put|Delete|Patch)\(\s*"([^"]+)"', text):
                add(m.group(1), m.group(2), path, m, text)
            for m in re.finditer(r'HandleFunc\(\s*"([^"]+)"', text):
                add("ANY", m.group(1), path, m, text)

        elif ext == ".cs":
            croute = re.search(r'\[Route\("([^"]*)"\)\]', text)
            base = croute.group(1) if croute else ""
            cls = re.search(r"class\s+(\w+?)Controller\b", text)
            base = base.replace("[controller]", (cls.group(1).lower() if cls else ""))
            for m in re.finditer(r'\[Http(Get|Post|Put|Delete|Patch)(?:\("([^"]*)"\))?\]', text):
                add(m.group(1), join_paths("/" + base, m.group(2) or ""), path, m, text)
            for m in re.finditer(r'Map(Get|Post|Put|Delete|Patch)\(\s*"([^"]+)"', text):
                add(m.group(1), m.group(2), path, m, text)

        elif ext == ".rb":
            for m in re.finditer(r"^\s*(get|post|put|delete|patch)\s+['\"]([^'\"]+)['\"]", text, re.M):
                add(m.group(1), m.group(2), path, m, text)

        elif ext == ".php":
            for m in re.finditer(r"Route::(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]", text):
                add(m.group(1), m.group(2), path, m, text)
            for m in re.finditer(r"#\[Route\(\s*['\"]([^'\"]+)['\"][^\]]*?(?:methods:\s*\[([^\]]*)\])?", text):
                methods = re.findall(r"['\"](\w+)['\"]", m.group(2) or "") or ["ANY"]
                for verb in methods:
                    add(verb, m.group(1), path, m, text)
    return routes


# ------------------------------------------------------------------- slice --
def classify(path, repo):
    rel = repo.rel(path).lower()
    for pattern, role in ROLE_HINTS:
        if re.search(pattern, rel):
            return role
    return "source"


def scan_markers(text):
    preserve, effects = {}, {}
    for pattern, meaning, kind in MARKERS:
        m = re.search(pattern, text)
        if m:
            (preserve if kind == "preserve" else effects)[meaning] = m.group(0).strip()[:60]
    return preserve, effects


def walk(start_files, repo, depth):
    slice_files, queue, seen = {}, [(f, 0) for f in start_files], set()
    while queue:
        path, level = queue.pop(0)
        if path in seen or path not in repo.files:
            continue
        seen.add(path)
        if TEST_FILE_RE.search(path.name):
            continue
        text = repo.files[path]
        preserve, effects = scan_markers(text)
        deps = sorted(set(dependencies(path, repo)) - {path})
        slice_files[path] = {"role": classify(path, repo), "preserve": preserve,
                             "side_effects": effects,
                             "depends_on": [repo.rel(d) for d in deps if d in repo.files]}
        if level < depth:
            queue += [(d, level + 1) for d in deps]
    return slice_files


def find_tests(repo, slice_paths):
    stems = {p.stem for p in slice_paths} | {p.stem.replace("Controller", "").replace("Service", "") for p in slice_paths}
    stems = {s for s in stems if len(s) > 3}
    tests = {}
    for path, text in repo.files.items():
        if not TEST_FILE_RE.search(path.name):
            continue
        covers = sorted(s for s in stems if re.search(r"\b" + re.escape(s) + r"\b", text))
        if covers:
            tests[repo.rel(path)] = covers
    return tests


# ------------------------------------------------------------------ output --
def render_ascii(result):
    out = [f"Endpoint slice for {result['endpoint']}  (root: {result['root']})", "=" * 72]
    for h in result["handlers"]:
        out.append(f"HANDLER  {h['method']} {h['path']}  ->  {h['file']}:{h['line']}   {h['evidence']}")
    out.append("")
    for rel, info in result["slice"].items():
        out.append(f"[{info['role']}] {rel}")
        for meaning, ev in info["preserve"].items():
            out.append(f"    ! preserve: {meaning}   ({ev})")
        for meaning, ev in info["side_effects"].items():
            out.append(f"    ~ side effect: {meaning}   ({ev})")
        if info["depends_on"]:
            out.append(f"    -> {', '.join(info['depends_on'])}")
    out.append("")
    if result["tests"]:
        out.append("Existing tests touching this slice (your safety net):")
        for t, covers in result["tests"].items():
            out.append(f"  {t}  covers {', '.join(covers)}")
    else:
        out.append("WARNING: no tests reference this slice — write characterization "
                   "tests BEFORE changing anything.")
    return "\n".join(out)


def render_md(result):
    out = [f"# Endpoint slice: `{result['endpoint']}`", "",
           "| Method | Path | Where | Evidence |", "|---|---|---|---|"]
    for h in result["handlers"]:
        out.append(f"| {h['method']} | `{h['path']}` | `{h['file']}:{h['line']}` | `{h['evidence']}` |")
    out += ["", "## Files in the slice", ""]
    for rel, info in result["slice"].items():
        out.append(f"### `{rel}` — {info['role']}")
        for meaning, ev in info["preserve"].items():
            out.append(f"- **preserve:** {meaning} (`{ev}`)")
        for meaning, ev in info["side_effects"].items():
            out.append(f"- side effect: {meaning} (`{ev}`)")
        if info["depends_on"]:
            out.append(f"- depends on: {', '.join(f'`{d}`' for d in info['depends_on'])}")
        out.append("")
    out.append("## Existing tests touching the slice\n")
    if result["tests"]:
        out += [f"- `{t}` covers {', '.join(covers)}" for t, covers in result["tests"].items()]
    else:
        out.append("**None found — write characterization tests before any change.**")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Universal endpoint tracer.")
    parser.add_argument("endpoint", help="endpoint path, e.g. /search or /api/orders/{id}")
    parser.add_argument("--root", default=".", help="project root to scan (default: cwd)")
    parser.add_argument("--format", choices=["ascii", "md", "json"], default="ascii")
    parser.add_argument("--depth", type=int, default=6, help="dependency depth (default 6)")
    parser.add_argument("--list-routes", action="store_true",
                        help="list every route detected instead of tracing one")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        sys.exit(2)
    repo = Repo(root)
    if not repo.files:
        print(f"error: no source files found under {root}", file=sys.stderr)
        sys.exit(2)

    routes = find_routes(repo)
    if args.list_routes:
        for r in sorted(routes, key=lambda r: (r["path"], r["method"])):
            print(f"{r['method']:6} {r['path']:40} {repo.rel(r['file'])}:{r['line']}")
        return

    handlers = [r for r in routes if paths_match(args.endpoint, r["path"])]
    if not handlers:
        print(f"No route found matching '{args.endpoint}'. "
              f"Run with --list-routes to see the {len(routes)} detected routes; "
              "the mapping may use a mount prefix or a framework this tracer "
              "doesn't parse — locate it manually in that case.", file=sys.stderr)
        sys.exit(1)

    slice_files = walk({h["file"] for h in handlers}, repo, args.depth)
    result = {
        "endpoint": args.endpoint,
        "root": str(root),
        "handlers": [{**h, "file": repo.rel(h["file"])} for h in handlers],
        "slice": {repo.rel(p): info for p, info in slice_files.items()},
        "tests": find_tests(repo, set(slice_files)),
    }

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.format == "md":
        print(render_md(result))
    else:
        print(render_ascii(result))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
