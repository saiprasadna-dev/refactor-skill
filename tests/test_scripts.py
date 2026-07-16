"""Regression tests for the skill scripts, run against committed fixtures.

    python3 -m unittest discover tests -v

Stdlib only. Each test invokes the script CLIs the way users do, so the
whole surface (arg parsing, exit codes, output formats) is covered.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
TRACER = ROOT / "skills" / "endpoint-rearchitect" / "scripts" / "trace_endpoint.py"
PLANNER = ROOT / "skills" / "endpoint-rearchitect" / "scripts" / "plan_refactor.py"
SPRING_TRACER = ROOT / "skills" / "java-modernization" / "scripts" / "trace_endpoint.py"
KB_SEARCH = ROOT / "skills" / "java-modernization" / "scripts" / "search.py"


def run(script, *args):
    proc = subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True, timeout=120)
    return proc.returncode, proc.stdout, proc.stderr


def run_json(script, *args):
    code, out, err = run(script, *args, "--format", "json")
    assert code == 0, err
    return json.loads(out)


class UniversalTracerTests(unittest.TestCase):
    def test_hono_mount_prefix_and_slice(self):
        data = run_json(TRACER, "/listings", "--root", str(FIXTURES / "hono-app"))
        methods = {h["method"] for h in data["handlers"]}
        self.assertEqual(methods, {"GET", "POST"})
        slice_files = set(data["slice"])
        self.assertIn("src/controllers/listingController.ts", slice_files)
        self.assertIn("src/services/listingRepo.ts", slice_files)
        route = data["slice"]["src/routes/listings.ts"]
        self.assertIn("auth/authorization rule", route["preserve"])
        repo = data["slice"]["src/services/listingRepo.ts"]
        self.assertIn("database access", repo["side_effects"])
        self.assertEqual(data["tests"], {})

    def test_hono_context_get_is_not_a_route(self):
        # c.get('user') in the controller must not be detected as a route
        code, out, _ = run(TRACER, "/", "--list-routes",
                           "--root", str(FIXTURES / "hono-app"))
        self.assertEqual(code, 0)
        detected = {tuple(line.split()[:2]) for line in out.strip().splitlines()}
        self.assertEqual(detected, {("GET", "/listings"), ("POST", "/listings")})

    def test_express_commonjs_mounting(self):
        data = run_json(TRACER, "/api/search", "--root", str(FIXTURES / "express-app"))
        self.assertEqual(data["handlers"][0]["file"], "src/routes/search.js")
        svc = data["slice"]["src/services/searchService.js"]
        self.assertIn("database access", svc["side_effects"])

    def test_java_spring_interface_to_impl(self):
        data = run_json(TRACER, "/api/search", "--root", str(FIXTURES / "java-app"))
        slice_files = set(data["slice"])
        self.assertTrue(any(f.endswith("SearchServiceImpl.java") for f in slice_files))
        impl = next(v for k, v in data["slice"].items()
                    if k.endswith("SearchServiceImpl.java"))
        self.assertIn("transaction boundary", impl["preserve"])
        self.assertIn("caching semantics", impl["preserve"])
        self.assertTrue(data["tests"])  # SearchControllerTest is found

    def test_python_fastapi_include_router_prefix(self):
        data = run_json(TRACER, "/api/search", "--root", str(FIXTURES / "py-app"))
        self.assertEqual(data["handlers"][0]["file"], "app/routers/search.py")
        svc = data["slice"]["app/services/search_service.py"]
        self.assertIn("external HTTP call", svc["side_effects"])
        self.assertTrue(data["tests"])

    def test_go_gin_route(self):
        data = run_json(TRACER, "/search", "--root", str(FIXTURES / "go-app"))
        self.assertEqual(data["handlers"][0]["method"], "GET")
        self.assertIn("search.go", data["slice"])

    def test_unknown_route_exits_1(self):
        code, _, err = run(TRACER, "/nope", "--root", str(FIXTURES / "go-app"))
        self.assertEqual(code, 1)
        self.assertIn("--list-routes", err)


class BatchPlannerTests(unittest.TestCase):
    def test_hotspot_inventory(self):
        rows = run_json(PLANNER, "--root", str(FIXTURES / "godfile-app"))
        self.assertEqual(rows[0]["file"], "server.js")
        self.assertEqual(rows[0]["endpoints"], 9)
        self.assertTrue(rows[0]["hotspot"])

    def test_godfile_plan_clusters_and_phases(self):
        plan = run_json(PLANNER, "--root", str(FIXTURES / "godfile-app"),
                        "--file", "server.js")
        names = {c["cluster"]: c for c in plan["clusters"]}
        self.assertEqual(set(names), {"users", "orders", "search", "reports"})
        self.assertEqual(len(names["users"]["endpoints"]), 4)
        self.assertTrue(names["search"]["read_only"])
        # safest-first: phase 1 is a read-only cluster
        first = next(c for c in plan["clusters"]
                     if c["cluster"] == plan["phases"][0]["cluster"])
        self.assertTrue(first["read_only"])
        self.assertIn("auth/authorization rule", plan["preserve_markers"])
        self.assertEqual(plan["tests"], {})

    def test_single_resource_file_subclusters(self):
        plan = run_json(PLANNER, "--root", str(FIXTURES / "singleres-app"),
                        "--file", "api.js")
        self.assertGreater(len(plan["clusters"]), 1)
        self.assertTrue(any("account/" in c["cluster"] for c in plan["clusters"]))


class SpringTracerTests(unittest.TestCase):
    def test_spring_slice_with_entities(self):
        data = run_json(SPRING_TRACER, "/api/search",
                        "--root", str(FIXTURES / "java-app"))
        self.assertEqual(data["handlers"][0]["controller"], "SearchController")
        repo = data["slice"]["ProductRepository"]
        self.assertEqual(repo["role"], "repository")
        self.assertEqual(repo["entities"], ["Product"])


class KnowledgeBaseTests(unittest.TestCase):
    def test_compat_lookup(self):
        code, out, err = run(KB_SEARCH, "junit", "--domain", "compat",
                             "--format", "json")
        self.assertEqual(code, 0, err)
        hits = json.loads(out)
        self.assertEqual(hits[0]["component"], "JUnit")

    def test_jakarta_keep_package(self):
        code, out, err = run(KB_SEARCH, "javax.sql", "--domain", "jakarta",
                             "--format", "json")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)[0]["action"], "KEEP")


if __name__ == "__main__":
    unittest.main()
