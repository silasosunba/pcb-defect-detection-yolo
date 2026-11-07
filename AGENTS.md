# Project coding style

Follow the user's preference for spacious, readable code throughout Python,
TypeScript, React, tests, scripts, and generated notebook code cells.

- Put a blank line after each compound block header, including `if`, `elif`,
  `else`, `try`, `except`/`catch`, and `finally`, before its first statement.
- Separate control-flow sections from surrounding statements with blank lines.
- Leave a blank line around exit/error statements such as `return`, `raise`,
  `throw`, `break`, and `continue` where another statement or block follows.
- Use full, multi-line control-flow bodies. Do not compress branches or exception
  handlers onto a single line. Always use braces for TypeScript control flow.
- Put separate variable declarations on separate statements. Keep related
  operations grouped, and separate distinct phases with a blank line.
- Wrap long argument lists and expressions. Preserve SQL text and already
  applied migration contents when making formatting-only changes.
- Keep formatting changes free of business-logic changes.

Use `uv run python scripts/format_code.py` for Python and the training notebook.
Use `npm run format` inside `frontend/` for TypeScript, React, CSS, and config.
Their `--check` / `format:check` modes verify the same style without writing.
Do not run standalone Ruff or Prettier as the final formatting step: they remove
the blank lines inside blocks that the user explicitly wants. The project
commands apply the user's spacing after the standard formatter.

Edit notebook code in `scripts/build_notebook.py` and `training/prepare.py`, then
regenerate `notebooks/pcb_yolo_kaggle.ipynb`. Do not reformat the unrelated legacy
regression notebook or CSV as part of application work.
