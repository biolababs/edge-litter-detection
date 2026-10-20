#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");

function resolveDocx() {
  try {
    return require("docx");
  } catch (_) {
    const root = path.join(os.homedir(), ".toolbox", "tools", "uno-nodedeps");
    if (!fs.existsSync(root)) throw _;
    const versions = fs.readdirSync(root).filter(v => /^\d+(\.\d+)+$/.test(v)).sort().reverse();
    for (const version of versions) {
      const modules = path.join(
        root,
        version,
        "lib",
        "commonjs",
        "@amzn",
        "uno-node-deps",
        "node_modules"
      );
      if (fs.existsSync(modules)) {
        module.paths.unshift(modules);
        return require("docx");
      }
    }
    throw _;
  }
}

const {
  AlignmentType,
  BorderStyle,
  Document,
  Footer,
  HeadingLevel,
  LevelFormat,
  Packer,
  PageBreak,
  PageNumber,
  Paragraph,
  Table,
  TableCell,
  TableOfContents,
  TableRow,
  TextRun,
  WidthType,
} = resolveDocx();

const repoRoot = path.resolve(__dirname, "..");

function safePath(value) {
  const resolved = path.resolve(repoRoot, value);
  if (resolved !== repoRoot && !resolved.startsWith(repoRoot + path.sep)) {
    throw new Error(`Path must remain within repository: ${value}`);
  }
  return resolved;
}

function cells(line) {
  return line
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map(value => value.trim());
}

function parseMarkdown(markdown) {
  const lines = markdown.split(/\r?\n/);
  const blocks = [];
  let paragraph = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: "paragraph", text: paragraph.join(" ") });
      paragraph = [];
    }
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (!line) {
      flushParagraph();
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2] });
      continue;
    }
    if (line.startsWith("- ")) {
      flushParagraph();
      const items = [];
      while (index < lines.length && lines[index].trim().startsWith("- ")) {
        items.push(lines[index].trim().slice(2));
        index += 1;
      }
      index -= 1;
      blocks.push({ type: "bullets", items });
      continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      flushParagraph();
      const items = [];
      while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^\d+\.\s+/, ""));
        index += 1;
      }
      index -= 1;
      blocks.push({ type: "numbered", items });
      continue;
    }
    if (
      line.startsWith("|") &&
      index + 1 < lines.length &&
      /^\|?[\s:|-]+\|?$/.test(lines[index + 1].trim())
    ) {
      flushParagraph();
      const headers = cells(line);
      index += 2;
      const rows = [];
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        rows.push(cells(lines[index].trim()));
        index += 1;
      }
      index -= 1;
      blocks.push({ type: "table", headers, rows });
      continue;
    }
    paragraph.push(line);
  }
  flushParagraph();
  return blocks;
}

function paragraph(text, options = {}) {
  return new Paragraph({
    spacing: { after: 140, line: 330 },
    ...options,
    children: [new TextRun({ text, font: "Arial", size: 22 })],
  });
}

function table(block) {
  const border = { style: BorderStyle.SINGLE, size: 1, color: "B7B7B7" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const width = Math.floor(9360 / Math.max(1, block.headers.length));
  const row = (values, header = false) =>
    new TableRow({
      children: values.map(
        value =>
          new TableCell({
            borders,
            width: { size: width, type: WidthType.DXA },
            margins: { top: 60, bottom: 60, left: 70, right: 70 },
            children: [
              new Paragraph({
                children: [
                  new TextRun({
                    text: String(value),
                    font: "Arial",
                    size: 18,
                    bold: header,
                  }),
                ],
              }),
            ],
          })
      ),
    });
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: Array(block.headers.length).fill(width),
    rows: [row(block.headers, true), ...block.rows.map(values => row(values))],
  });
}

async function main() {
  const input = safePath(process.argv[2] || "thesis/manuscript.md");
  const output = safePath(process.argv[3] || "thesis/Jetson_Litter_Detection_Thesis_Draft.docx");
  const blocks = parseMarkdown(fs.readFileSync(input, "utf8"));
  const title = blocks.find(block => block.type === "heading" && block.level === 1)?.text || "Thesis";
  const children = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 1200, after: 400 },
      children: [new TextRun({ text: title, bold: true, font: "Arial", size: 44 })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 160 },
      children: [new TextRun({ text: "Abiola A. Babsalaam", font: "Arial", size: 26 })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 900 },
      children: [
        new TextRun({
          text: "Prospective research manuscript — results pending",
          italics: true,
          font: "Arial",
          size: 22,
        }),
      ],
    }),
    new Paragraph({ children: [new PageBreak()] }),
    new Paragraph({
      spacing: { after: 180 },
      children: [
        new TextRun({
          text: "⚠️ AI & Data Notice: All output is AI-generated and must be independently verified before sharing with customers or taking action.",
          bold: true,
          color: "A65E00",
          font: "Arial",
          size: 22,
        }),
      ],
    }),
    new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
    new Paragraph({ children: [new PageBreak()] }),
  ];

  for (const block of blocks) {
    if (block.type === "heading") {
      if (block.level === 1) continue;
      children.push(
        new Paragraph({
          heading: block.level === 2 ? HeadingLevel.HEADING_1 : HeadingLevel.HEADING_2,
          children: [new TextRun(block.text)],
        })
      );
    } else if (block.type === "paragraph") {
      children.push(paragraph(block.text));
    } else if (block.type === "bullets") {
      children.push(
        ...block.items.map(item =>
          paragraph(item, { numbering: { reference: "bullets", level: 0 } })
        )
      );
    } else if (block.type === "numbered") {
      children.push(
        ...block.items.map(item =>
          paragraph(item, { numbering: { reference: "numbers", level: 0 } })
        )
      );
    } else if (block.type === "table") {
      children.push(table(block), new Paragraph({ spacing: { after: 160 } }));
    }
  }

  const doc = new Document({
    numbering: {
      config: [
        {
          reference: "bullets",
          levels: [
            {
              level: 0,
              format: LevelFormat.BULLET,
              text: "•",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 720, hanging: 360 } } },
            },
          ],
        },
        {
          reference: "numbers",
          levels: [
            {
              level: 0,
              format: LevelFormat.DECIMAL,
              text: "%1.",
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 720, hanging: 360 } } },
            },
          ],
        },
      ],
    },
    styles: {
      default: { document: { run: { font: "Arial", size: 22 } } },
      paragraphStyles: [
        {
          id: "Heading1",
          name: "Heading 1",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: { font: "Arial", size: 34, bold: true },
          paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0 },
        },
        {
          id: "Heading2",
          name: "Heading 2",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: { font: "Arial", size: 28, bold: true },
          paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 },
        },
      ],
    },
    sections: [
      {
        properties: {
          page: {
            size: { width: 11906, height: 16838 },
            margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
          },
        },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [
                  new TextRun({ text: "Page ", size: 18 }),
                  new TextRun({ children: [PageNumber.CURRENT], size: 18 }),
                ],
              }),
            ],
          }),
        },
        children,
      },
    ],
  });

  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, await Packer.toBuffer(doc));
  console.log(`DOCX generated: ${output}`);
}

main().catch(error => {
  console.error(error.message);
  process.exit(1);
});

