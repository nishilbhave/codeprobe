#!/usr/bin/env python3
"""
dependency_mapper.py — Import/dependency graph builder for code-review-claude.

Builds an import/dependency graph from source files and detects circular
dependencies. Outputs JSON to stdout.
Read-only: only reads files, never writes anything.
Dependencies: Python 3.8+ standard library only.

Usage:
    python3 dependency_mapper.py /path/to/project
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Directories to skip during traversal
SKIP_DIRS: Set[str] = {
    "node_modules",
    "vendor",
    ".git",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".venv",
    "venv",
    "env",
}

# Recognized source file extensions
RECOGNIZED_EXTENSIONS: Set[str] = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".php", ".java", ".rb", ".go", ".rs",
    ".vue", ".svelte", ".sql", ".sh",
    ".css", ".scss", ".html",
}

# Extensions that contain importable code (subset we parse for imports)
IMPORTABLE_EXTENSIONS: Set[str] = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".php", ".go",
}

# Common extensions to try when resolving an import path to a file
JS_RESOLVE_EXTENSIONS: List[str] = [
    ".js", ".ts", ".jsx", ".tsx",
    "/index.js", "/index.ts",
]

PY_RESOLVE_EXTENSIONS: List[str] = [".py", "/__init__.py"]

PHP_RESOLVE_EXTENSIONS: List[str] = [".php"]

# --- Import patterns by language ---

# PHP: use Namespace\Class; require/include variants
PHP_USE_PATTERN: re.Pattern = re.compile(
    r"^\s*use\s+([\w\\]+)\s*;", re.MULTILINE
)
PHP_REQUIRE_PATTERN: re.Pattern = re.compile(
    r"^\s*(?:require|include|require_once|include_once)\s*"
    r"(?:\(\s*)?['\"]([^'\"]+)['\"]\s*(?:\)\s*)?;",
    re.MULTILINE,
)

# JavaScript / TypeScript: import ... from '...', require('...')
JS_IMPORT_FROM_PATTERN: re.Pattern = re.compile(
    r"""(?:import\s+(?:[\w{},*\s]+)\s+from|import)\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)
JS_REQUIRE_PATTERN: re.Pattern = re.compile(
    r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE,
)

# Python: from X import Y, import X
PY_FROM_IMPORT_PATTERN: re.Pattern = re.compile(
    r"^\s*from\s+([\w.]+)\s+import", re.MULTILINE
)
PY_IMPORT_PATTERN: re.Pattern = re.compile(
    r"^\s*import\s+([\w.]+)", re.MULTILINE
)

# Go: import "path" or import ( "path" ... )
GO_IMPORT_SINGLE_PATTERN: re.Pattern = re.compile(
    r'^\s*import\s+"([^"]+)"', re.MULTILINE
)
GO_IMPORT_BLOCK_PATTERN: re.Pattern = re.compile(
    r"import\s*\((.*?)\)", re.DOTALL
)
GO_IMPORT_LINE_PATTERN: re.Pattern = re.compile(r'"([^"]+)"')

# Well-known Python stdlib top-level modules (partial list for filtering)
PYTHON_STDLIB_TOP: Set[str] = {
    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
    "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
    "binhex", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb",
    "chunk", "cmath", "cmd", "code", "codecs", "codeop", "collections",
    "colorsys", "compileall", "concurrent", "configparser", "contextlib",
    "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv",
    "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
    "difflib", "dis", "distutils", "doctest", "email", "encodings",
    "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
    "fnmatch", "formatter", "fractions", "ftplib", "functools", "gc",
    "getopt", "getpass", "gettext", "glob", "grp", "gzip", "hashlib",
    "heapq", "hmac", "html", "http", "idlelib", "imaplib", "imghdr",
    "imp", "importlib", "inspect", "io", "ipaddress", "itertools",
    "json", "keyword", "lib2to3", "linecache", "locale", "logging",
    "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes",
    "mmap", "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
    "numbers", "operator", "optparse", "os", "ossaudiodev", "parser",
    "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil",
    "platform", "plistlib", "poplib", "posix", "posixpath", "pprint",
    "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr",
    "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
    "selectors", "shelve", "shlex", "shutil", "signal", "site",
    "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "sqlite3",
    "ssl", "stat", "statistics", "string", "stringprep", "struct",
    "subprocess", "sunau", "symtable", "sys", "sysconfig", "syslog",
    "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "test",
    "textwrap", "threading", "time", "timeit", "tkinter", "token",
    "tokenize", "trace", "traceback", "tracemalloc", "tty", "turtle",
    "turtledemo", "types", "typing", "unicodedata", "unittest", "urllib",
    "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc",
    "zipapp", "zipfile", "zipimport", "zlib", "_thread",
}


def is_binary(filepath: str) -> bool:
    """Detect binary files by checking for null bytes in the first 1024 bytes."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except (OSError, IOError):
        return True


def collect_files(root_dir: str) -> List[str]:
    """Walk the directory tree and collect recognized source files."""
    files: List[str] = []
    root = os.path.abspath(root_dir)

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out skip directories (modifying dirnames in-place prunes the walk)
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        ]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in RECOGNIZED_EXTENSIONS:
                continue

            full_path = os.path.join(dirpath, filename)

            # Skip binary files
            if is_binary(full_path):
                continue

            # Store as relative path from root_dir
            rel_path = os.path.relpath(full_path, root)
            files.append(rel_path)

    return sorted(files)


def read_file_content(filepath: str) -> Optional[str]:
    """Read a file and return its text content, or None on failure."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, IOError, PermissionError):
        return None


def resolve_path(base_dir: str, candidate: str, extensions: List[str],
                 root: str) -> Optional[str]:
    """Try to resolve a candidate path to an actual file relative to root.

    Tries the candidate as-is first, then appends each extension.
    Returns a root-relative path if found, otherwise None.
    """
    # Normalise to absolute
    abs_candidate = os.path.normpath(os.path.join(base_dir, candidate))

    # Try exact path first
    if os.path.isfile(abs_candidate):
        return os.path.relpath(abs_candidate, root)

    # Try with extensions
    for ext in extensions:
        attempt = abs_candidate + ext
        if os.path.isfile(attempt):
            return os.path.relpath(attempt, root)

    return None


# --- Language-specific import extractors ---

def extract_php_imports(content: str, file_rel: str,
                        root: str) -> List[str]:
    """Extract imports from a PHP file."""
    imports: List[str] = []
    file_dir = os.path.join(root, os.path.dirname(file_rel))

    # use Namespace\Class;  ->  resolve namespace to path
    for match in PHP_USE_PATTERN.finditer(content):
        namespace = match.group(1)
        # Convert namespace separators to path separators
        candidate = namespace.replace("\\", os.sep)
        resolved = resolve_path(root, candidate, PHP_RESOLVE_EXTENSIONS, root)
        if resolved:
            imports.append(resolved)

    # require/include with string literal
    for match in PHP_REQUIRE_PATTERN.finditer(content):
        path_str = match.group(1)
        resolved = resolve_path(file_dir, path_str, PHP_RESOLVE_EXTENSIONS, root)
        if resolved:
            imports.append(resolved)

    return imports


def extract_js_imports(content: str, file_rel: str,
                       root: str) -> List[str]:
    """Extract imports from a JavaScript/TypeScript file."""
    imports: List[str] = []
    file_dir = os.path.join(root, os.path.dirname(file_rel))

    for pattern in (JS_IMPORT_FROM_PATTERN, JS_REQUIRE_PATTERN):
        for match in pattern.finditer(content):
            path_str = match.group(1)

            # Skip non-relative (node_modules / bare specifiers)
            if not path_str.startswith("."):
                continue

            resolved = resolve_path(
                file_dir, path_str, JS_RESOLVE_EXTENSIONS, root,
            )
            if resolved:
                imports.append(resolved)

    return imports


def extract_python_imports(content: str, file_rel: str,
                           root: str) -> List[str]:
    """Extract imports from a Python file."""
    imports: List[str] = []

    for pattern in (PY_FROM_IMPORT_PATTERN, PY_IMPORT_PATTERN):
        for match in pattern.finditer(content):
            module_path = match.group(1)
            top_level = module_path.split(".")[0]

            # Skip stdlib modules
            if top_level in PYTHON_STDLIB_TOP:
                continue

            # Convert dotted path to filesystem path
            candidate = module_path.replace(".", os.sep)
            resolved = resolve_path(root, candidate, PY_RESOLVE_EXTENSIONS, root)
            if resolved:
                imports.append(resolved)

    return imports


def extract_go_imports(content: str, file_rel: str,
                       root: str) -> List[str]:
    """Extract imports from a Go file."""
    imports: List[str] = []
    raw_paths: List[str] = []

    # Single-line imports
    for match in GO_IMPORT_SINGLE_PATTERN.finditer(content):
        raw_paths.append(match.group(1))

    # Block imports
    for block_match in GO_IMPORT_BLOCK_PATTERN.finditer(content):
        block = block_match.group(1)
        for line_match in GO_IMPORT_LINE_PATTERN.finditer(block):
            raw_paths.append(line_match.group(1))

    for imp in raw_paths:
        # Skip external modules (contain a domain with a dot)
        if "." in imp.split("/")[0]:
            continue

        # Treat as project-relative path
        resolved = resolve_path(root, imp, [".go"], root)
        if resolved:
            imports.append(resolved)

    return imports


# Mapping of extension to extractor function
EXTRACTOR_MAP = {
    ".php": extract_php_imports,
    ".js": extract_js_imports,
    ".jsx": extract_js_imports,
    ".ts": extract_js_imports,
    ".tsx": extract_js_imports,
    ".py": extract_python_imports,
    ".go": extract_go_imports,
}


def build_dependency_graph(
    file_paths: List[str], root: str,
) -> Dict[str, List[str]]:
    """Build an adjacency list of file -> [imported files]."""
    graph: Dict[str, List[str]] = {}
    file_set: Set[str] = set(file_paths)

    for rel_path in file_paths:
        ext = os.path.splitext(rel_path)[1].lower()
        extractor = EXTRACTOR_MAP.get(ext)
        if extractor is None:
            continue

        full_path = os.path.join(root, rel_path)
        content = read_file_content(full_path)
        if content is None:
            continue

        raw_imports = extractor(content, rel_path, root)

        # Deduplicate while preserving order, and keep only project files
        seen: Set[str] = set()
        resolved: List[str] = []
        for imp in raw_imports:
            normalised = imp.replace(os.sep, "/")
            if normalised not in seen:
                seen.add(normalised)
                resolved.append(normalised)

        if resolved:
            graph[rel_path.replace(os.sep, "/")] = resolved

    return graph


def detect_cycles(graph: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """Run DFS cycle detection on the dependency graph.

    Returns a list of cycle descriptors, each with a 'chain' (list of nodes
    forming the cycle, starting and ending with the same node) and a 'severity'
    ('direct' for 2-node cycles, 'transitive' for 3+ nodes).
    """
    WHITE, GREY, BLACK = 0, 1, 2
    colour: Dict[str, int] = {node: WHITE for node in graph}
    parent_chain: Dict[str, List[str]] = {}
    cycles: List[List[str]] = []
    seen_cycle_keys: Set[str] = set()

    def dfs(node: str, path: List[str]) -> None:
        colour[node] = GREY
        parent_chain[node] = list(path)

        for neighbour in graph.get(node, []):
            if neighbour not in colour:
                # Node not in graph keys — skip (leaf dependency)
                continue

            if colour[neighbour] == GREY:
                # Found a cycle: extract the cycle portion from the path
                cycle_start_idx = path.index(neighbour) if neighbour in path else -1
                if cycle_start_idx >= 0:
                    cycle = path[cycle_start_idx:] + [neighbour]
                else:
                    cycle = [node, neighbour]

                # Normalise: rotate so the smallest node is first
                min_node = min(cycle[:-1])
                min_idx = cycle[:-1].index(min_node)
                normalised = cycle[min_idx:] + cycle[1:min_idx + 1]
                key = " -> ".join(normalised)

                if key not in seen_cycle_keys:
                    seen_cycle_keys.add(key)
                    cycles.append(normalised)

            elif colour[neighbour] == WHITE:
                dfs(neighbour, path + [neighbour])

        colour[node] = BLACK

    for node in list(colour.keys()):
        if colour[node] == WHITE:
            dfs(node, [node])

    results: List[Dict[str, Any]] = []
    for cycle in cycles:
        # Number of unique nodes is len(cycle) - 1 (last repeats the first)
        unique_count = len(cycle) - 1
        severity = "direct" if unique_count <= 2 else "transitive"
        results.append({"chain": cycle, "severity": severity})

    return results


def compute_summary(
    graph: Dict[str, List[str]],
    circular: List[Dict[str, Any]],
    total_files: int,
) -> Dict[str, Any]:
    """Compute aggregate summary statistics from the dependency graph."""
    total_edges = sum(len(deps) for deps in graph.values())

    # Count how many times each file is imported
    import_counts: Dict[str, int] = {}
    for deps in graph.values():
        for dep in deps:
            import_counts[dep] = import_counts.get(dep, 0) + 1

    # Most imported file
    if import_counts:
        most_imported_file = max(import_counts, key=import_counts.get)  # type: ignore[arg-type]
        most_imported = {
            "file": most_imported_file,
            "imported_by": import_counts[most_imported_file],
        }
    else:
        most_imported = {"file": "", "imported_by": 0}

    # File with most outgoing dependencies
    if graph:
        most_deps_file = max(graph, key=lambda k: len(graph[k]))
        most_dependencies = {
            "file": most_deps_file,
            "depends_on": len(graph[most_deps_file]),
        }
    else:
        most_dependencies = {"file": "", "depends_on": 0}

    return {
        "total_files": total_files,
        "total_edges": total_edges,
        "circular_count": len(circular),
        "most_imported": most_imported,
        "most_dependencies": most_dependencies,
    }


def main() -> None:
    if len(sys.argv) < 2:
        json.dump(
            {"error": "Usage: python3 dependency_mapper.py /path/to/project"},
            sys.stdout,
            indent=2,
        )
        sys.exit(1)

    target_dir = sys.argv[1]

    if not os.path.isdir(target_dir):
        json.dump(
            {"error": f"Directory not found: {target_dir}"},
            sys.stdout,
            indent=2,
        )
        sys.exit(1)

    # Collect source files
    file_paths = collect_files(target_dir)
    root = os.path.abspath(target_dir)

    # Build the dependency graph
    graph = build_dependency_graph(file_paths, root)

    # Detect circular dependencies
    circular = detect_cycles(graph)

    # Compute summary
    summary = compute_summary(graph, circular, total_files=len(file_paths))

    output = {
        "graph": graph,
        "circular_dependencies": circular,
        "summary": summary,
    }

    json.dump(output, sys.stdout, indent=2)
    print()  # trailing newline


if __name__ == "__main__":
    main()
