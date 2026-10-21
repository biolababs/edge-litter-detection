#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const {
  AlignmentType,
  BorderStyle,
  Document,
  Footer,
  HeadingLevel,
  ImageRun,
  LevelFormat,
  Packer,
  PageNumber,
  Paragraph,
  ShadingType,
  Table,
  TableCell,
  TableRow,
  TextRun,
  WidthType,
} = require("docx");

const repoRoot = path.resolve(__dirname, "..");
const HEADER_FILL = "E5E7EB";

function safePath(value) {
  const resolved = path.resolve(value);
  if (resolved !== repoRoot && !resolved.startsWith(`${repoRoot}${path.sep}`)) {
    throw new Error(`Path must remain within the repository: ${value}`);
  }
  return resolved;
}

function parseSvgDimensions(svgPath) {
  const svg = fs.readFileSync(svgPath, "utf8");
  const viewBox = svg.match(
    /viewBox=["']\s*[\d.-]+\s+[\d.-]+\s+([\d.]+)\s+([\d.]+)\s*["']/
  );
  if (viewBox) {
    return { width: Number(viewBox[1]), height: Number(viewBox[2]) };
  }
  const width = svg.match(/\bwidth=["']([\d.]+)["']/);
  const height = svg.match(/\bheight=["']([\d.]+)["']/);
  if (!width || !height) {
    throw new Error(`Cannot determine SVG dimensions: ${svgPath}`);
  }
  return { width: Number(width[1]), height: Number(height[1]) };
}

function imageSource(section) {
  const source = safePath(section.path);
  if (path.extname(source).toLowerCase() !== ".svg") {
    return {
      source,
      dimensions: { width: 1200, height: 675 },
    };
  }
  const png = source.replace(/\.svg$/i, ".png");
  if (!fs.existsSync(png)) {
    throw new Error(`Rendered PNG is missing for ${source}`);
  }
  return { source: png, dimensions: parseSvgDimensions(source) };
}

function makeImage(section) {
  const image = imageSource(section);
  const targetWidth = 600;
  const targetHeight = Math.round(
    targetWidth * image.dimensions.height / image.dimensions.width
  );
  const alt = section.alt || "Publication figure";
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      keepNext: true,
      spacing: { before: 160, after: 80 },
      children: [
        new ImageRun({
          data: fs.readFileSync(image.source),
          type: "png",
          transformation: { width: targetWidth, height: targetHeight },
          altText: {
            title: alt,
            description: alt,
            name: path.basename(image.source),
          },
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 180 },
      children: [
        new TextRun({
          text: section.caption || alt,
          font: "Times New Roman",
          size: 18,
          color: "111111",
        }),
      ],
    }),
  ];
}

function buildNumbering() {
  return {
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
  };
}

function buildStyles() {
  return {
    default: {
      document: {
        run: { font: "Times New Roman", size: 20, color: "111111" },
        paragraph: { spacing: { line: 240, after: 80 } },
      },
    },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: {
          size: 28,
          bold: true,
          font: "Times New Roman",
          color: "111111",
        },
        paragraph: {
          keepNext: true,
          spacing: { before: 220, after: 100 },
          outlineLevel: 0,
        },
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: {
          size: 24,
          bold: true,
          font: "Times New Roman",
          color: "111111",
        },
        paragraph: {
          keepNext: true,
          spacing: { before: 180, after: 80 },
          outlineLevel: 1,
        },
      },
      {
        id: "Heading3",
        name: "Heading 3",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: {
          size: 21,
          bold: true,
          italics: true,
          font: "Times New Roman",
          color: "111111",
        },
        paragraph: {
          keepNext: true,
          spacing: { before: 140, after: 65 },
          outlineLevel: 2,
        },
      },
    ],
  };
}

function makeHeading(section) {
  const levels = {
    1: HeadingLevel.HEADING_1,
    2: HeadingLevel.HEADING_2,
    3: HeadingLevel.HEADING_3,
  };
  return new Paragraph({
    heading: levels[section.level] || HeadingLevel.HEADING_1,
    children: [new TextRun(section.text)],
  });
}

function makeParagraph(section) {
  const lines = (section.text || "").split("\n");
  const children = [];
  lines.forEach((line, index) => {
    children.push(
      new TextRun({ text: line, break: index > 0 ? 1 : undefined })
    );
  });
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 80 },
    children,
  });
}

function makeList(section, reference) {
  return (section.items || []).map(
    item =>
      new Paragraph({
        numbering: { reference, level: 0 },
        spacing: { after: 40 },
        children: [new TextRun(item)],
      })
  );
}

function makeNumberedList(section) {
  return (section.items || []).map(
    (item, index) =>
      new Paragraph({
        indent: { left: 720, hanging: 360 },
        spacing: { after: 40 },
        children: [
          new TextRun({
            text: `${index + 1}.  ${item}`,
            font: "Times New Roman",
            size: 20,
          }),
        ],
      })
  );
}

function makeCode(section) {
  const lines = (section.text || "").split("\n");
  const children = [];
  lines.forEach((line, index) => {
    children.push(
      new TextRun({
        text: line || " ",
        break: index > 0 ? 1 : undefined,
        font: "Courier New",
        size: 16,
      })
    );
  });
  return new Paragraph({
    shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
    indent: { left: 180, right: 180 },
    spacing: { before: 60, after: 100, line: 220 },
    children,
  });
}

function makeTable(section) {
  const border = { style: BorderStyle.SINGLE, size: 1, color: "B8B8B8" };
  const borders = {
    top: border,
    bottom: border,
    left: border,
    right: border,
  };
  const headers = section.headers || [];
  const columnWidth =
    headers.length > 0 ? Math.floor(9360 / headers.length) : 2000;

  function row(values, header = false) {
    return new TableRow({
      tableHeader: header,
      cantSplit: true,
      children: values.map(
        value =>
          new TableCell({
            borders,
            width: { size: columnWidth, type: WidthType.DXA },
            shading: header
              ? { fill: HEADER_FILL, type: ShadingType.CLEAR }
              : undefined,
            margins: { top: 42, bottom: 42, left: 72, right: 72 },
            children: [
              new Paragraph({
                spacing: { after: 0 },
                children: [
                  new TextRun({
                    text: String(value),
                    bold: header,
                    color: "111111",
                    font: "Times New Roman",
                    size: 17,
                  }),
                ],
              }),
            ],
          })
      ),
    });
  }

  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: Array(headers.length).fill(columnWidth),
    rows: [row(headers, true), ...(section.rows || []).map(values => row(values))],
  });
}

function buildContent(data) {
  const children = [];
  for (const section of data.sections || []) {
    switch (section.type) {
      case "heading":
        children.push(makeHeading(section));
        break;
      case "paragraph":
        children.push(makeParagraph(section));
        break;
      case "bullets":
        children.push(...makeList(section, "bullets"));
        break;
      case "numbered":
        children.push(...makeNumberedList(section));
        break;
      case "code":
        children.push(makeCode(section));
        break;
      case "table":
        children.push(
          makeTable(section),
          new Paragraph({ spacing: { after: 120 }, children: [] })
        );
        break;
      case "image":
        children.push(...makeImage(section));
        break;
      default:
        throw new Error(`Unsupported report section: ${section.type}`);
    }
  }
  return children;
}

async function main() {
  if (process.argv.length < 4) {
    throw new Error(
      "Usage: node scripts/generate_paper_docx.js <report.json> <paper.docx>"
    );
  }
  const input = safePath(process.argv[2]);
  const output = safePath(process.argv[3]);
  const data = JSON.parse(fs.readFileSync(input, "utf8"));
  const metadata = data.metadata || {};

  const titlePage = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 40, after: 160 },
      children: [
        new TextRun({
          text: metadata.title || "Preprint",
          bold: true,
          size: 36,
          font: "Times New Roman",
          color: "111111",
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 70 },
      children: [
        new TextRun({
          text: metadata.author || "",
          size: 22,
          font: "Times New Roman",
          color: "111111",
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 55 },
      children: [
        new TextRun({
          text: metadata.subtitle || "",
          size: 18,
          font: "Times New Roman",
          color: "333333",
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 35 },
      children: [
        new TextRun({
          text: metadata.date || "",
          size: 18,
          font: "Times New Roman",
          color: "333333",
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 180 },
      children: [
        new TextRun({
          text: "Code: github.com/biolababs/edge-litter-detection",
          size: 18,
          font: "Times New Roman",
          color: "333333",
        }),
      ],
    }),
  ];

  const document = new Document({
    creator: "Abiola A. Babsalaam",
    lastModifiedBy: "Abiola A. Babsalaam",
    title: metadata.title || "",
    subject: "Edge-AI software architecture and reproducibility preprint",
    description:
      "Preprint reporting public-data accuracy, edge deployment design, and warmed Jetson Orin Nano profiling.",
    numbering: buildNumbering(),
    styles: buildStyles(),
    sections: [
      {
        properties: {
          page: {
            size: { width: 12240, height: 15840 },
            margin: { top: 1080, right: 1440, bottom: 1080, left: 1440 },
          },
        },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [
                  new TextRun({
                    text: "Page ",
                    size: 17,
                    font: "Times New Roman",
                  }),
                  new TextRun({
                    children: [PageNumber.CURRENT],
                    size: 17,
                    font: "Times New Roman",
                  }),
                ],
              }),
            ],
          }),
        },
        children: [...titlePage, ...buildContent(data)],
      },
    ],
  });

  const buffer = await Packer.toBuffer(document);
  fs.writeFileSync(output, buffer, { mode: 0o644 });
  console.log(`DOCX generated: ${output}`);
}

main().catch(error => {
  console.error(error.stack || error.message);
  process.exit(1);
});
