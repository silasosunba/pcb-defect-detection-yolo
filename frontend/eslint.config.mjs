import stylistic from "@stylistic/eslint-plugin";
import tsParser from "@typescript-eslint/parser";

const controlFlow = [
  "if",
  "for",
  "while",
  "do",
  "switch",
  "try",
  "return",
  "throw",
  "break",
  "continue",
  "function",
  "class",
];

export default [
  {
    files: ["**/*.ts", "**/*.tsx", "**/*.mjs"],
    ignores: ["dist/**", "node_modules/**", "test-results/**"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: { "@stylistic": stylistic },
    rules: {
      curly: ["error", "all"],
      "@stylistic/padded-blocks": [
        "error",
        { blocks: "always", classes: "always", switches: "always" },
      ],
      "@stylistic/padding-line-between-statements": [
        "error",
        { blankLine: "always", prev: "*", next: controlFlow },
        { blankLine: "always", prev: controlFlow, next: "*" },
      ],
    },
  },
];
