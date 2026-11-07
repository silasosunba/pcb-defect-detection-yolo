import { readFile, readdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { ESLint } from "eslint";
import * as prettier from "prettier";
import ts from "typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const check = process.argv.includes("--check");
const eslint = new ESLint({ cwd: root, fix: true });

async function filesIn(directory) {

  const entries = await readdir(directory, { withFileTypes: true });
  const groups = await Promise.all(
    entries.map((entry) => {

      const target = path.join(directory, entry.name);

      return entry.isDirectory() ? filesIn(target) : [target];
    
}),
  );

  return groups.flat();

}

function separateDeclarations(source, filename) {

  if (!/\.tsx?$/.test(filename)) {

    return source;
  
}

  const tree = ts.createSourceFile(
    filename,
    source,
    ts.ScriptTarget.Latest,
    true,
    filename.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const replacements = [];

  function visit(node) {

    if (
      ts.isVariableStatement(node) &&
      node.declarationList.declarations.length > 1
    ) {

      const kind =
        node.declarationList.flags & ts.NodeFlags.Const
          ? "const"
          : node.declarationList.flags & ts.NodeFlags.Let
            ? "let"
            : "var";
      const modifiers =
        node.modifiers?.map((item) => item.getText(tree)).join(" ") || "";
      const prefix = `${modifiers ? modifiers + " " : ""}${kind}`;
      replacements.push({
        start: node.getStart(tree),
        end: node.end,
        text: node.declarationList.declarations
          .map((item) => `${prefix} ${item.getText(tree)};`)
          .join("\n"),
      });
    
}

    ts.forEachChild(node, visit);
  
}

  visit(tree);

  for (const item of replacements.sort(
    (left, right) => right.start - left.start,
  )) {

    source = source.slice(0, item.start) + item.text + source.slice(item.end);
  
}

  return source;

}

const files = (
  await Promise.all(
    ["src", "e2e", "scripts"].map((directory) =>
      filesIn(path.join(root, directory)),
    ),
  )
).flat();

for (const entry of await readdir(root)) {

  if (/\.(ts|mjs|json|html)$/.test(entry)) {

    files.push(path.join(root, entry));
  
}

}

let changed = 0;

for (const filename of files
  .filter((filename) => /\.(ts|tsx|mjs|css|json|html)$/.test(filename))
  .sort()) {

  const original = await readFile(filename, "utf8");
  const options = await prettier.resolveConfig(filename);
  let formatted = await prettier.format(
    separateDeclarations(original, filename),
    { ...options, filepath: filename },
  );

  if (/\.(ts|tsx|mjs)$/.test(filename)) {

    let result = (await eslint.lintText(formatted, { filePath: filename }))[0];

    if (result.fatalErrorCount) {

      throw new Error(result.messages.map((item) => item.message).join("\n"));
    
}

    formatted = await prettier.format(result.output || formatted, {
      ...options,
      filepath: filename,
    });
    result = (await eslint.lintText(formatted, { filePath: filename }))[0];

    if (result.errorCount) {

      throw new Error(result.messages.map((item) => item.message).join("\n"));
    
}

    formatted = result.output || formatted;
  
}

  if (formatted !== original) {

    changed += 1;

    if (check) {

      console.error(`Formatting needed: ${path.relative(root, filename)}`);
    
} else {

      await writeFile(filename, formatted);
    
}
  
}

}

if (check && changed) {

  process.exitCode = 1;

}

console.log(
  check
    ? `Formatting checked (${changed} files need changes).`
    : `Formatted ${changed} frontend files.`,
);
