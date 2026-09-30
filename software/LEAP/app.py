import os
import threading
import json
import shutil
import ast
import difflib
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from bluebook_generator.main import generate_bluebook
from bluebook_generator.kpi_extractor import find_kpis_in_directory
from bluebook_generator.paths import (
    BUSINESS_OVERRIDES_PATH,
    GOVERNANCE_OVERRIDES_PATH as DATA_GOVERNANCE_OVERRIDES_PATH,
    KNOWLEDGE_BASE_DIR,
)

# Add these imports for deep scan
from bluebook_generator.kpi_extractor import (
    _detect_language_by_extension as _dbg_detect_lang,
)  # type: ignore

app = Flask(__name__)

BLUEBOOK_DIR = os.path.join(os.getcwd(), "docs", "_build")
PROJECT_ROOT = Path(__file__).resolve().parent
BLUEBOOK_BUILD_PATH = (PROJECT_ROOT / "docs" / "_build").resolve()
DOCS_STATIC_PATH = (PROJECT_ROOT / "docs" / "_static").resolve()
OVERRIDES_PATH = str(BUSINESS_OVERRIDES_PATH)
KB_OVERRIDES_PATH = str(KNOWLEDGE_BASE_DIR / "overrides.json")
GOVERNANCE_OVERRIDES_PATH = str(DATA_GOVERNANCE_OVERRIDES_PATH)

# --- Global state to track progress ---
status = {"running": False, "output": "Ready to start."}


def _extract_metric_from_index(label: str, text: str) -> str:
    pattern = (
        rf'<span class="metric-indicator-label leap-card-label">{re.escape(label)}</span>'
        rf'<span class="metric-indicator-value leap-card-value">([^<]+)</span>'
    )
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _workspace_stats():
    """Return truthful stats from the generated workspace when available."""
    docs_dir = PROJECT_ROOT / "docs"
    index_path = docs_dir / "index.rst"
    kpi_rst_files = [
        path
        for path in docs_dir.glob("*.rst")
        if path.stem not in {"index", "discovery_report", "raci_directory"}
    ]
    stats = {
        "total_kpis": len(kpi_rst_files),
        "validated_kpis": len(kpi_rst_files),
        "review_items": 0,
        "avg_confidence": "--",
        "workspace_state": "Ready" if kpi_rst_files else "Idle",
    }
    try:
        text = index_path.read_text(encoding="utf-8")
        total = _extract_metric_from_index("KPI Count", text)
        confidence = _extract_metric_from_index("Average Confidence", text)
        validated = _extract_metric_from_index("Validated KPIs", text)
        review = _extract_metric_from_index("Review Items", text)
        if total:
            stats["total_kpis"] = int(float(total.replace(",", "")))
        if confidence:
            stats["avg_confidence"] = confidence
        if validated:
            stats["validated_kpis"] = int(float(validated.replace(",", "")))
        if review:
            stats["review_items"] = int(float(review.replace(",", "")))
        stats["workspace_state"] = "Built" if stats["total_kpis"] else "Idle"
    except Exception:
        pass
    return stats


def _empty_override_ledger():
    return {
        "ledger_name": "LEAP-AXIS-FEEDBACK-SIGNOFF-OVERRIDE-LEDGER",
        "description": "Persistent business-approved KPI overrides checked before generated dossiers are finalized.",
        "kpis": {},
    }


def _read_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return default
    return default


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _source_signature(source_path):
    if not source_path:
        return ""
    try:
        source = Path(str(source_path)).expanduser()
        if not source.is_absolute():
            source = (PROJECT_ROOT / source).resolve()
        else:
            source = source.resolve()
        if not source.exists() or not source.is_file():
            return ""
        return hashlib.sha256(source.read_bytes()).hexdigest()
    except Exception:
        return ""


def _load_override_ledger(path):
    loaded = _read_json(path, _empty_override_ledger())
    if isinstance(loaded, dict):
        ledger = _empty_override_ledger()
        ledger.update(loaded)
        ledger.setdefault("kpis", {})
        return ledger
    return _empty_override_ledger()


def _save_override_ledger_entry(path, kpi_name, fields, payload):
    ledger = _load_override_ledger(path)
    source_path = payload.get("source_path") or payload.get("file_path") or ""
    signature = payload.get("file_signature") or _source_signature(source_path)
    entry = {
        "status": "APPROVED_BY_BUSINESS",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_path": source_path,
        "file_signature": signature,
        "signature_algorithm": "sha256" if signature else "",
        "fields": {k: v for k, v in fields.items() if v is not None},
    }
    ledger.setdefault("kpis", {}).setdefault(kpi_name, {}).update(entry)
    _write_json(path, ledger)


def run_generation_in_background(path):
    """Wrapper to run our main logic and update status."""
    global status
    try:
        for message in generate_bluebook(path):
            status["output"] += f"\n{message}"
        status["output"] += "\n\n--- Bluebook Generation Complete! ---"
    except Exception as e:
        status["output"] += f"\n\nAn error occurred: {e}"
    finally:
        status["stats"] = _workspace_stats()
        status["running"] = False


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")

@app.route("/api/stats")
def get_stats():
    """Return aggregated stats from the generated KPI workspace."""
    stats = _workspace_stats()
    stats.update(status.get("stats") or {})
    return jsonify(stats)


@app.route("/start", methods=["POST"])
def start_generation():
    """Start the bluebook generation process."""
    global status
    if status["running"]:
        return jsonify({"status": "Already running."}), 400

    path = request.form.get("path")
    if not path or not os.path.isdir(path):
        return jsonify({"status": "Invalid or missing folder path."}), 400

    status = {"running": True, "output": "Starting generation..."}

    thread = threading.Thread(target=run_generation_in_background, args=(path,))
    thread.start()

    return jsonify({"status": "Generation started."})


@app.route("/status")
def get_status():
    """Provide real-time status updates to the frontend."""
    return jsonify(status)


@app.route("/api/workspace/purge", methods=["POST"])
def handle_workspace_purge():
    """
    Administrative local endpoint: clears docs/_build so the next run starts
    from a genuinely clean Sphinx output directory.
    """
    global status

    if request.remote_addr not in {"127.0.0.1", "::1", "localhost"}:
        return jsonify({"status": "rejected", "message": "Local requests only."}), 403

    if status.get("running"):
        return (
            jsonify(
                {
                    "status": "rejected",
                    "message": "A Bluebook generation is currently running.",
                }
            ),
            409,
        )

    try:
        build_dir = BLUEBOOK_BUILD_PATH
        expected_parent = (PROJECT_ROOT / "docs").resolve()
        if build_dir.parent != expected_parent or build_dir.name != "_build":
            return jsonify({"status": "rejected", "message": "Unsafe build path."}), 400

        if build_dir.exists():
            for item in build_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        else:
            build_dir.mkdir(parents=True, exist_ok=True)

        status = {"running": False, "output": "Build workspace cleared. Ready for a fresh scan."}
        return jsonify({"status": "success", "message": "Docs _build cleared successfully."})
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


# --- ADD THIS NEW ROUTE ---
@app.route("/bluebook/<path:filename>")
def serve_bluebook(filename):
    """Serves the generated HTML files from the docs/_build directory."""
    if filename.startswith("_static/"):
        static_filename = filename.removeprefix("_static/")
        built_static = BLUEBOOK_BUILD_PATH / "_static" / static_filename
        if built_static.exists():
            return send_from_directory(BLUEBOOK_BUILD_PATH / "_static", static_filename)
        return send_from_directory(DOCS_STATIC_PATH, static_filename)

    requested = BLUEBOOK_BUILD_PATH / filename
    if requested.suffix == "":
        html_filename = f"{filename}.html"
        if (BLUEBOOK_BUILD_PATH / html_filename).exists():
            return send_from_directory(BLUEBOOK_DIR, html_filename)
    return send_from_directory(BLUEBOOK_DIR, filename)


@app.route("/overrides/<kpi_name>", methods=["GET"])
def get_overrides(kpi_name):
    """Return saved overrides for a KPI (if any)."""
    try:
        if os.path.exists(OVERRIDES_PATH):
            with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            existing = data.get(kpi_name, {})
            if existing:
                return jsonify(existing)
        for ledger_path in (KB_OVERRIDES_PATH,):
            data = _load_override_ledger(ledger_path)
            kpi_block = data.get("kpis", {}).get(kpi_name, {}) if isinstance(data, dict) else {}
            fields = kpi_block.get("fields", {}) if isinstance(kpi_block, dict) else {}
            if fields:
                return jsonify(fields)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({})


@app.route("/overrides", methods=["POST"])
def save_overrides():
    """
    Body JSON:
    {
      "kpi_name": "Some KPI",
      "fields": {
        "description": "...",
        "objective": "...",
        "input_measure": "...",
        "unit_of_measure": "...",
        "reporting_source": "...",
        "comments": "..."
      }
    }
    """
    try:
        payload = request.get_json(force=True)
        kpi_name = payload.get("kpi_name")
        fields = payload.get("fields", {})
        if not kpi_name or not isinstance(fields, dict):
            return jsonify({"error": "Invalid payload"}), 400

        data = {}
        if os.path.exists(OVERRIDES_PATH):
            with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        data.setdefault(kpi_name, {}).update(
            {k: v for k, v in fields.items() if v is not None}
        )

        os.makedirs(os.path.dirname(OVERRIDES_PATH), exist_ok=True)
        with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        _save_override_ledger_entry(KB_OVERRIDES_PATH, kpi_name, fields, payload)

        return jsonify({"status": "saved"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/governance-overrides/<kpi_name>", methods=["GET"])
def get_governance_overrides(kpi_name):
    """Return saved RACI overrides for a KPI."""
    try:
        if os.path.exists(GOVERNANCE_OVERRIDES_PATH):
            with open(GOVERNANCE_OVERRIDES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            kpi_overrides = data.get("kpis", {}) if isinstance(data, dict) else {}
            return jsonify(kpi_overrides.get(kpi_name, {}))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({})


@app.route("/governance-overrides", methods=["POST"])
def save_governance_overrides():
    """
    Body JSON:
    {
      "kpi_name": "Some KPI",
      "fields": {
        "responsible": "...",
        "accountable": "...",
        "consulted": "...",
        "informed": "...",
        "confidence": "High",
        "basis": "..."
      }
    }
    """
    try:
        payload = request.get_json(force=True)
        kpi_name = payload.get("kpi_name")
        fields = payload.get("fields", {})
        if not kpi_name or not isinstance(fields, dict):
            return jsonify({"error": "Invalid payload"}), 400

        data = {"kpis": {}}
        if os.path.exists(GOVERNANCE_OVERRIDES_PATH):
            with open(GOVERNANCE_OVERRIDES_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
        data.setdefault("kpis", {}).setdefault(kpi_name, {}).update(
            {k: v for k, v in fields.items() if v is not None}
        )

        os.makedirs(os.path.dirname(GOVERNANCE_OVERRIDES_PATH), exist_ok=True)
        with open(GOVERNANCE_OVERRIDES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "saved"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


class _ScopedAstRewrite(ast.NodeTransformer):
    def __init__(self, function_name, replacement):
        self.function_name = function_name or ""
        self.replacement = replacement
        self.in_scope = not bool(self.function_name)
        self.changed = False

    def visit_FunctionDef(self, node):
        previous = self.in_scope
        if self.function_name and node.name == self.function_name:
            self.in_scope = True
            node = self.generic_visit(node)
            self.in_scope = previous
            return node
        return self.generic_visit(node) if not self.function_name else node

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)

    def visit_BinOp(self, node):
        node = self.generic_visit(node)
        if not self.in_scope:
            return node
        operator_map = {
            "add": ast.Add,
            "+": ast.Add,
            "sub": ast.Sub,
            "-": ast.Sub,
            "mult": ast.Mult,
            "*": ast.Mult,
            "div": ast.Div,
            "/": ast.Div,
        }
        new_operator = str(self.replacement.get("operator") or "").lower()
        operator_cls = operator_map.get(new_operator)
        if operator_cls and not isinstance(node.op, operator_cls):
            node.op = operator_cls()
            self.changed = True
        return node

    def visit_Constant(self, node):
        if not self.in_scope:
            return node
        old_value = self.replacement.get("old_value")
        new_value = self.replacement.get("new_value")
        if old_value is None or new_value is None:
            return node
        if str(node.value) == str(old_value):
            try:
                if isinstance(node.value, int):
                    node.value = int(new_value)
                elif isinstance(node.value, float):
                    node.value = float(new_value)
                else:
                    node.value = new_value
                self.changed = True
            except Exception:
                node.value = new_value
                self.changed = True
        return node


@app.route("/api/no-code/ast-rewrite", methods=["POST"])
def no_code_ast_rewrite():
    """
    Deterministic local no-code edit bridge for Python source files.
    Default behavior is dry-run preview. Set {"apply": true} to write the patch.
    """
    try:
        payload = request.get_json(force=True)
        source_path = Path(str(payload.get("source_path") or "")).expanduser()
        if not source_path.is_absolute():
            source_path = (PROJECT_ROOT / source_path).resolve()
        else:
            source_path = source_path.resolve()
        if not source_path.exists() or source_path.suffix != ".py":
            return jsonify({"error": "Only existing Python .py files are supported."}), 400
        try:
            source_path.relative_to(PROJECT_ROOT)
        except ValueError:
            if not payload.get("allow_external_project_file"):
                return jsonify({"error": "Refusing to modify files outside the LEAP workspace without explicit allow flag."}), 400

        original = source_path.read_text(encoding="utf-8")
        tree = ast.parse(original)
        rewriter = _ScopedAstRewrite(
            payload.get("function_name") or "",
            payload.get("replacement") or {},
        )
        new_tree = rewriter.visit(tree)
        ast.fix_missing_locations(new_tree)
        if not rewriter.changed:
            return jsonify({"status": "unchanged", "message": "No matching AST element found."})
        rewritten = ast.unparse(new_tree) + "\n"
        diff = "\n".join(
            difflib.unified_diff(
                original.splitlines(),
                rewritten.splitlines(),
                fromfile=str(source_path),
                tofile=str(source_path),
                lineterm="",
            )
        )
        if payload.get("apply") is True:
            source_path.write_text(rewritten, encoding="utf-8")
            return jsonify({"status": "applied", "file_signature": _source_signature(source_path), "diff": diff})
        return jsonify({"status": "preview", "file_signature": _source_signature(source_path), "diff": diff})
    except SyntaxError as e:
        return jsonify({"error": f"Python parse failed: {e}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/edit")
def edit_page():
    """
    Simple edit page for a KPI. Usage: /edit?kpi=<KPI Name>
    This page loads existing overrides (if any) and lets the user save updates.
    """
    kpi_name = request.args.get("kpi", "").strip()
    if not kpi_name:
        kpi_name = ""
    return render_template("edit.html", kpi_name=kpi_name)


@app.route("/debug-scan")
def debug_scan():
    """
    Quick diagnostic: scan a folder and return the KPIs that would be found.
    Usage:
      /debug-scan?path=/absolute/path/to/folder
      /debug-scan?path=relative/path/from/cwd
    """
    raw = (request.args.get("path") or "").strip()
    if not raw:
        return jsonify({"error": "Provide a folder path via ?path="}), 400

    candidate = os.path.expanduser(raw)
    if not os.path.isabs(candidate):
        candidate = os.path.abspath(os.path.join(os.getcwd(), candidate))

    if not os.path.isdir(candidate):
        return jsonify(
            {
                "error": "Folder not found",
                "received": raw,
                "resolved": candidate,
                "cwd": os.getcwd(),
            }
        ), 400

    # Run the scanner safely and handle any unexpected errors
    try:
        kpis = find_kpis_in_directory(candidate)
    except Exception as e:
        return jsonify(
            {
                "error": "Scanner raised an exception",
                "resolved": candidate,
                "message": str(e),
            }
        ), 500

    # Normalize None -> []
    if kpis is None:
        kpis = []

    return jsonify(
        {
            "path": candidate,
            "count": len(kpis),
            "items": [
                {
                    "name": k.get("name"),
                    "file_path": k.get("file_path"),
                    "file_line": k.get("file_line"),
                }
                for k in kpis
            ],
        }
    )


@app.route("/debug-scan-deep")
def debug_scan_deep():
    """
    Deep diagnostic: walk the folder, show every file, the language hint,
    and any KPIs detected per file. Uses public scanner to avoid internal helper errors.
    """
    raw = (request.args.get("path") or "").strip()
    if not raw:
        return jsonify({"error": "Provide a folder path via ?path="}), 400

    base = os.path.expanduser(raw)
    if not os.path.isabs(base):
        base = os.path.abspath(os.path.join(os.getcwd(), base))

    if not os.path.isdir(base):
        return jsonify(
            {
                "error": "Folder not found",
                "received": raw,
                "resolved": base,
                "cwd": os.getcwd(),
            }
        ), 400

    # Run the public scanner once
    try:
        all_kpis = find_kpis_in_directory(base) or []
    except Exception as e:
        return jsonify(
            {"error": "scanner-error", "message": str(e), "resolved": base}
        ), 500

    # Index by file
    by_file = {}
    for k in all_kpis:
        fp = k.get("file_path")
        by_file.setdefault(fp, []).append(k)

    # Walk the directory to list every file, then attach KPIs from by_file
    per_file = []
    total_kpis = 0
    for dirpath, _, filenames in os.walk(base):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            p_lower = path.lower()
            lang = _dbg_detect_lang(p_lower)
            items = by_file.get(path, [])
            total_kpis += len(items)
            per_file.append(
                {
                    "file": path,
                    "lang": lang,
                    "kpi_count": len(items),
                    "kpis": [
                        {"name": i.get("name"), "line": i.get("file_line")}
                        for i in items[:5]
                    ],
                }
            )

    return jsonify(
        {
            "path": base,
            "total_kpis": total_kpis,
            "files_scanned": len(per_file),
            "files": per_file,
        }
    )


if __name__ == "__main__":
    if not os.path.exists("docs/_build"):
        os.makedirs("docs/_build")
    app.run(debug=True)
