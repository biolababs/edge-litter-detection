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

function parse(markdown, sourceDirectory) {
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
        type: "code",
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

    const image = line.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (image) {
      flushParagraph();
      let caption = "";
      let captionIndex = index + 1;
      while (
        captionIndex < lines.length &&
        !lines[captionIndex].trim()
      ) {
        captionIndex += 1;
      }
      if (
        captionIndex < lines.length &&
        /^\*Figure\s+\d+\./.test(lines[captionIndex].trim())
      ) {
        const captionLines = [];
        while (captionIndex < lines.length) {
          const captionLine = lines[captionIndex].trim();
          captionLines.push(captionLine);
          if (captionLine.endsWith("*")) break;
          captionIndex += 1;
        }
        const candidate = captionLines.join(" ");
        if (candidate.endsWith("*")) {
          caption = normalizeInline(candidate);
          index = captionIndex;
        }
      }
      sections.push({
        type: "image",
        path: path.resolve(sourceDirectory, image[2]),
        alt: normalizeInline(image[1]),
        caption,
      });
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
        let item = lines[index].trim().slice(2);
        index += 1;
        while (
          index < lines.length &&
          /^\s{2,}\S/.test(lines[index]) &&
          !lines[index].trim().startsWith("- ")
        ) {
          item += ` ${lines[index].trim()}`;
          index += 1;
        }
        items.push(normalizeInline(item));
      }
      index -= 1;
      sections.push({ type: "bullets", items });
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      flushParagraph();
      const items = [];
      while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
        let item = lines[index].trim().replace(/^\d+\.\s+/, "");
        index += 1;
        while (
          index < lines.length &&
          /^\s{2,}\S/.test(lines[index]) &&
          !/^\d+\.\s+/.test(lines[index].trim())
        ) {
          item += ` ${lines[index].trim()}`;
          index += 1;
        }
        items.push(normalizeInline(item));
      }
      index -= 1;
      sections.push({ type: "numbered", items });
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
  const sections = parse(body, path.dirname(input));
  const report = {
    metadata: {
      title:
        "An Open and Reproducible Edge-AI Software Architecture for Litter Detection, Multiclass Classification, Tracking, and Counting",
      subtitle:
        "Preprint version 1.5 — journal format and publication figures",
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
