"""Format Python while preserving the project's spacious control-flow style."""

import argparse
import ast
import io
import subprocess
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ("backend", "training", "scripts", "tests")
SUITE_KEYWORDS = {
    "if",
    "elif",
    "else",
    "try",
    "except",
    "finally",
    "for",
    "while",
    "with",
    "async",
    "def",
    "class",
    "match",
    "case",
}
CONTROL_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.ExceptHandler,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
)
EXIT_NODES = (ast.Raise, ast.Return, ast.Break, ast.Continue)


def signature(source):

    tree = ast.parse(source)
    # Notebook cell strings may change whitespace; their Python AST must not.

    for node in ast.walk(tree):

        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "code"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):

            node.args[0].value = ast.dump(
                ast.parse(node.args[0].value), include_attributes=False
            )

    return ast.dump(tree, include_attributes=False)



def format_python(source, filename="notebook_cell.py"):

    formatted = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--stdin-filename",
            str(filename),
            "-",
        ],
        input=source,
        text=True,
        capture_output=True,
        check=True,
        cwd=ROOT,
    ).stdout
    lines = formatted.splitlines()
    before, after = set(), set()
    logical = []
    ignored = {
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.NL,
        tokenize.COMMENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
    }

    for token in tokenize.generate_tokens(io.StringIO(formatted).readline):

        if token.type == tokenize.NEWLINE:

            if (
                logical
                and logical[0].string in SUITE_KEYWORDS
                and logical[-1].string == ":"
            ):

                after.add(logical[-1].end[0])

                if logical[0].string in {"else", "elif", "except", "finally", "case"}:

                    before.add(logical[0].start[0])

            logical = []

        elif token.type not in ignored:

            logical.append(token)

    for node in ast.walk(ast.parse(formatted)):

        if isinstance(node, CONTROL_NODES + EXIT_NODES):

            decorators = getattr(node, "decorator_list", [])
            before.add(min([node.lineno, *(item.lineno for item in decorators)]))
            after.add(node.end_lineno)

    output = []

    for number, line in enumerate(lines, 1):

        if number in before and output and output[-1].strip():

            output.append("")

        output.append(line)

        if number in after and line.strip():

            output.append("")

    result = "\n".join(output).rstrip() + "\n"

    if signature(source) != signature(result):

        raise RuntimeError(f"Formatting would change Python behavior: {filename}")

    return result



def format_embedded_cells(source):

    """Keep the notebook generator's visible code samples readable as well."""
    lines = source.splitlines(keepends=True)
    offsets = [0]

    for line in lines:

        offsets.append(offsets[-1] + len(line))

    replacements = []

    for node in ast.walk(ast.parse(source)):

        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "code"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):

            continue

        literal = node.args[0]
        formatted = format_python(literal.value)
        replacement = (
            '"""\n' + formatted.replace("\\", "\\\\").replace('"""', '\\"""') + '"""'
        )
        start = offsets[literal.lineno - 1] + len(
            lines[literal.lineno - 1].encode()[: literal.col_offset].decode()
        )
        end = offsets[literal.end_lineno - 1] + len(
            lines[literal.end_lineno - 1].encode()[: literal.end_col_offset].decode()
        )
        replacements.append((start, end, replacement))

    for start, end, replacement in sorted(replacements, reverse=True):

        source = source[:start] + replacement + source[end:]

    return source



def main():

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = []

    for directory in SOURCE_DIRS:

        for path in sorted((ROOT / directory).rglob("*.py")):

            original = path.read_text()
            source = (
                format_embedded_cells(original)
                if path.name == "build_notebook.py"
                else original
            )
            formatted = format_python(source, path)

            if signature(original) != signature(formatted):

                raise RuntimeError(f"Formatting would change Python behavior: {path}")

            if formatted != original:

                changed.append(str(path.relative_to(ROOT)))

                if not args.check:

                    path.write_text(formatted)

    if args.check and changed:

        raise SystemExit("Formatting needed:\n" + "\n".join(changed))

    command = [sys.executable, str(ROOT / "scripts/build_notebook.py")]

    if args.check:

        command.append("--check")

    subprocess.run(command, check=True, cwd=ROOT)
    print(
        "Python and notebook formatting checked."
        if args.check
        else f"Formatted {len(changed)} Python files and regenerated the notebook."
    )



if __name__ == "__main__":

    main()
