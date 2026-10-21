#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

function cells(line) {
  return line
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map(value => value.trim());
}

function normalizeInline(text) {
  return text
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .trim();
}

function parse(markdown) {
  const lines = markdown.split(/\r?\n/);
  const sections = [];
  let paragraph = [];
  let inCode = false;
  let code = [];

  function flushParagraph() {
    if (paragraph.length) {
      sections.push({
        type: "paragraph",
        text: normalizeInline(paragraph.join(" ")),
      });
      paragraph = [];
    }
  }

  function flushCode() {
    if (code.length) {
      sections.push({
        type: "paragraph",
        text: code.join("\n"),
      });
      code = [];
    }
  }

  for (let index = 0; index < lines.length; index += 1) {
    const raw = lines[index];
    const line = raw.trim();

    if (line.startsWith("```")) {
      flushParagraph();
      if (inCode) flushCode();
      inCode = !inCode;
      continue;
    }
    if (inCode) {
      code.push(raw);
      continue;
    }
    if (!line) {
      flushParagraph();
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      if (heading[1].length > 1) {
        sections.push({
          type: "heading",
          level: heading[1].length - 1,
          text: normalizeInline(heading[2]),
        });
      }
      continue;
    }

    if (
      line.startsWith("|") &&
      index + 1 < lines.length &&
      /^\|?[\s:|-]+\|?$/.test(lines[index + 1].trim())
    ) {
      flushParagraph();
      const headers = cells(line).map(normalizeInline);
      index += 2;
      const rows = [];
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        rows.push(cells(lines[index].trim()).map(normalizeInline));
        index += 1;
      }
      index -= 1;
      sections.push({ type: "table", headers, rows });
      continue;
    }

    if (line.startsWith("- ")) {
      flushParagraph();
      const items = [];
      while (index < lines.length && lines[index].trim().startsWith("- ")) {
        items.push(normalizeInline(lines[index].trim().slice(2)));
        index += 1;
      }
      index -= 1;
      sections.push({ type: "bullets", items });
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      flushParagraph();
      while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
        sections.push({
          type: "paragraph",
          text: normalizeInline(lines[index].trim()),
        });
        index += 1;
      }
      index -= 1;
      continue;
    }

    paragraph.push(line);
  }

  flushParagraph();
  flushCode();
  return sections;
}

function main() {
  const input = path.resolve(process.argv[2] || "");
  const output = path.resolve(process.argv[3] || "");
  if (!process.argv[2] || !process.argv[3]) {
    throw new Error(
      "Usage: node scripts/paper_to_report_json.js <paper.md> <report.json>"
    );
  }

  const markdown = fs.readFileSync(input, "utf8");
  const bodyStart = markdown.indexOf("## Abstract");
  const body = bodyStart >= 0 ? markdown.slice(bodyStart) : markdown;
  const sections = parse(body);
  const report = {
    metadata: {
      title:
        "An Open and Reproducible Edge-AI System for Litter Detection, Multiclass Classification, Tracking, and Counting",
      subtitle:
        "Systems and reproducibility preprint — verified software evidence and preliminary engineering validation",
      date: "21 October 2026",
      author: "Abiola A. Babsalaam — Independent Researcher",
      confidential: false,
    },
    sections,
  };
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`, {
    mode: 0o644,
  });
}

main();
