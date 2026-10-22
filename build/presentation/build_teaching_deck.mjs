import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const WORKSPACE = "C:/Users/Administrator/Desktop/MyEdgeSimPy";
const BUILD_DIR = path.join(WORKSPACE, "build/presentation");
const OUTPUT_DIR = path.join(WORKSPACE, "output/presentation");
const SKILL_DIR =
  "C:/Users/Administrator/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations";
const FINAL_PPTX = path.join(OUTPUT_DIR, "跨边服务状态迁移_教学版_v5.pptx");
const FONT = "Microsoft YaHei";

const C = {
  bg: "#F7F7F4",
  paper: "#FFFFFF",
  white: "#FFFFFF",
  ink: "#1B1B19",
  muted: "#5F5F58",
  rule: "#D9D9D1",
  teal: "#0F5B5B",
  tealSoft: "#E7F0EE",
  rust: "#B84A24",
  rustSoft: "#F7E8E2",
};

const SIZE = { width: 1280, height: 720 };

function addText(slide, opts) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name: opts.name,
    position: { left: opts.left, top: opts.top, width: opts.width, height: opts.height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = opts.text;
  shape.text.style = {
    typeface: FONT,
    fontSize: opts.size ?? 18,
    bold: opts.bold ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "top",
    lineSpacing: opts.lineSpacing ?? 1.2,
    insets: 0,
    wrap: "square",
    autoFit: "none",
  };
  return shape;
}

function addRule(slide, left, top, width, height, color = C.rule) {
  return slide.shapes.add({
    geometry: "rect",
    position: { left, top, width, height },
    fill: color,
    line: { style: "solid", fill: "none", width: 0 },
  });
}

function addPanel(slide, left, top, width, height, fill = C.paper, line = C.rule, lineWidth = 1) {
  return slide.shapes.add({
    geometry: "roundRect",
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: lineWidth },
    borderRadius: "rounded-lg",
  });
}

function header(slide, index, section, title) {
  addText(slide, {
    left: 72,
    top: 38,
    width: 1136,
    height: 22,
    text: `${String(index).padStart(2, "0")}  ${section}`,
    size: 12,
    bold: true,
    color: C.muted,
  });
  addText(slide, {
    left: 72,
    top: 68,
    width: 1136,
    height: 72,
    text: title,
    size: 28,
    bold: true,
    lineSpacing: 1.08,
  });
  addRule(slide, 72, 150, 64, 3, C.teal);
}

function takeaway(slide, text) {
  addRule(slide, 72, 606, 1136, 1, C.rule);
  addText(slide, {
    left: 72,
    top: 620,
    width: 1040,
    height: 40,
    text,
    size: 18,
    bold: true,
    color: C.teal,
  });
}

function pageNumber(slide, number) {
  addText(slide, {
    left: 1180,
    top: 686,
    width: 36,
    height: 16,
    text: String(number),
    size: 10,
    color: C.muted,
    align: "right",
  });
}

function addTable(slide, opts) {
  const values = opts.values;
  const rows = values.length;
  const columns = values[0].length;
  const table = slide.tables.add({
    rows,
    columns,
    left: opts.left,
    top: opts.top,
    width: opts.width,
    height: opts.height,
    columnWidths: opts.columnWidths,
    values,
  });
  table.styleOptions = { headerRow: false, bandedRows: false };
  table.borders.assign({ style: "solid", fill: C.rule, width: 1 });
  const rowHeight = opts.rowHeight ?? Math.floor(opts.height / rows);
  for (let r = 0; r < rows; r += 1) {
    table.rows[r].height = rowHeight;
  }
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < columns; c += 1) {
      const cell = table.getCell(r, c);
      const isHeader = r === 0;
      cell.fill = isHeader ? C.teal : r % 2 === 0 ? "#FBFBF8" : C.white;
      const range = table.cells.block({ row: r, column: c, rowCount: 1, columnCount: 1 });
      range.textStyle.typeface = FONT;
      range.textStyle.fontSize = isHeader ? 13 : (opts.fontSize ?? 14);
      range.textStyle.bold = isHeader || (opts.boldFirstColumn && c === 0);
      range.textStyle.color = isHeader ? C.white : C.ink;
      range.textStyle.alignment = c === 0 ? "left" : "center";
    }
  }
  return table;
}

function notes(slide, text) {
  slide.speakerNotes.text = text;
  slide.speakerNotes.setVisible(true);
}

function newSlide(presentation, background = C.bg) {
  const slide = presentation.slides.add();
  slide.background.fill = background;
  return slide;
}

async function main() {
  await fs.mkdir(BUILD_DIR, { recursive: true });
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  const renders = path.join(BUILD_DIR, "renders_teaching");
  await fs.mkdir(renders, { recursive: true });

  const presentation = Presentation.create({ slideSize: SIZE });
  presentation.theme.defaultFont = FONT;
  presentation.theme.colorScheme = {
    name: "Storage Systems Teaching",
    themeColors: {
      accent1: C.teal,
      accent2: C.rust,
      accent3: "#7A8F8B",
      accent4: "#9C6B4E",
      accent5: "#4C6B78",
      accent6: "#6E7F5C",
      bg1: C.bg,
      bg2: C.paper,
      tx1: C.ink,
      tx2: C.muted,
      dk1: "#000000",
      dk2: "#123F3F",
      lt1: "#FFFFFF",
      lt2: "#E7F0EE",
      hlink: C.teal,
      folHlink: C.rust,
    },
  };

  // 1. Cover
  {
    const slide = newSlide(presentation, "#0E3A3A");
    addText(slide, {
      left: 72,
      top: 52,
      width: 900,
      height: 24,
      text: "子课题汇报  /  2026年10月",
      size: 13,
      bold: true,
      color: "#BFD6D2",
    });
    addText(slide, {
      left: 72,
      top: 200,
      width: 1040,
      height: 140,
      text: "跨边服务状态迁移：\n从一个生活例子讲起",
      size: 44,
      bold: true,
      color: "#FFFFFF",
      lineSpacing: 1.12,
    });
    addRule(slide, 72, 372, 96, 3, "#8FB8B2");
    addText(slide, {
      left: 72,
      top: 400,
      width: 980,
      height: 34,
      text: "面向云边存储的数据安全缩减技术研究",
      size: 22,
      color: "#D6E5E2",
    });
    addText(slide, {
      left: 72,
      top: 456,
      width: 980,
      height: 64,
      text: "先讲清楚系统，再讲实验，最后落到开销。",
      size: 18,
      color: "#BFD6D2",
    });
    addText(slide, {
      left: 72,
      top: 640,
      width: 700,
      height: 22,
      text: "汇报人：________",
      size: 13,
      color: "#A9C6C1",
    });
    notes(
      slide,
      "各位老师好。今天我不先讲公式，先从一个生活例子讲起。先让老师明白车、服务、状态和迁移分别在说什么，再讲我们做了什么实验。"
    );
  }

  // 2. Life example
  {
    const slide = newSlide(presentation);
    header(slide, 2, "生活例子", "车在移动，服务也要跟着走");
    const panels = [
      { left: 72, title: "车在 A 区", lines: "服务在 A 区机房\n离得近，延迟低" },
      { left: 440, title: "车开到 B 区", lines: "服务还在 A 区\n路变远，延迟变高" },
      { left: 808, title: "把服务搬到 B 区", lines: "服务恢复本地\n但搬家有成本" },
    ];
    const shapes = [];
    panels.forEach((panel) => {
      shapes.push(addPanel(slide, panel.left, 210, 320, 150, C.paper, C.rule));
      addText(slide, { left: panel.left + 24, top: 230, width: 272, height: 30, text: panel.title, size: 20, bold: true });
      addText(slide, { left: panel.left + 24, top: 274, width: 272, height: 66, text: panel.lines, size: 16, color: C.muted });
    });
    slide.shapes.connect(shapes[0], shapes[1], {
      kind: "straight", fromSide: "right", toSide: "left",
      line: { style: "solid", fill: C.teal, width: 2 },
      tail: { type: "arrow", width: "med", length: "med" },
    });
    slide.shapes.connect(shapes[1], shapes[2], {
      kind: "straight", fromSide: "right", toSide: "left",
      line: { style: "solid", fill: C.teal, width: 2 },
      tail: { type: "arrow", width: "med", length: "med" },
    });
    addText(slide, {
      left: 72,
      top: 400,
      width: 1136,
      height: 54,
      text: "服务不是一个空壳。它带着“状态”：视频播放到哪、导航走到哪、缓存了什么。",
      size: 18,
    });
    addText(slide, {
      left: 72,
      top: 470,
      width: 1136,
      height: 54,
      text: "所以服务迁移不是“把程序复制过去”，而是“把程序连同记忆一起搬过去”。",
      size: 18,
      color: C.muted,
    });
    takeaway(slide, "服务迁移 = 把服务和它的状态一起搬家。");
    pageNumber(slide, 2);
    notes(
      slide,
      "先看一个生活场景。车在 A 区，服务也在 A 区，离得近，延迟低。车开到 B 区，服务还在 A 区，路变远，延迟就高了。把服务搬到 B 区，延迟恢复，但搬家要花时间和流量。服务还带着状态，比如视频播放到哪、导航路线、缓存。所以迁移不是复制程序，是连记忆一起搬。"
    );
  }

  // 3. Cloud vs edge
  {
    const slide = newSlide(presentation);
    header(slide, 3, "背景知识", "为什么要有边缘计算：因为“近”很重要");
    addPanel(slide, 72, 206, 500, 244, C.paper, C.rule);
    addText(slide, { left: 100, top: 228, width: 440, height: 30, text: "云计算", size: 22, bold: true });
    addText(slide, {
      left: 100,
      top: 274,
      width: 440,
      height: 140,
      text: "机房在城市外，像一个大仓库。\n容量大，但离用户远。\n好处是便宜，坏处是延迟高。",
      size: 16,
      color: C.muted,
    });
    addPanel(slide, 700, 206, 508, 244, C.tealSoft, C.teal);
    addText(slide, { left: 728, top: 228, width: 452, height: 30, text: "边缘计算", size: 22, bold: true, color: C.teal });
    addText(slide, {
      left: 728,
      top: 274,
      width: 452,
      height: 140,
      text: "把一小部分机房放到基站旁边。\n像小区门口的小仓库。\n离用户近，延迟低。",
      size: 16,
      color: C.ink,
    });
    addRule(slide, 572, 328, 128, 2, C.rule);
    addText(slide, { left: 574, top: 340, width: 36, height: 24, text: "远", size: 13, color: C.muted });
    addText(slide, { left: 664, top: 340, width: 36, height: 24, text: "近", size: 13, color: C.teal });
    addText(slide, {
      left: 72,
      top: 490,
      width: 1136,
      height: 52,
      text: "边缘节点的好处是近，代价是每个节点容量小。用户一移动，就可能要换节点。",
      size: 18,
    });
    takeaway(slide, "边缘计算用“近”换“快”，但“近”带来了迁移问题。");
    pageNumber(slide, 3);
    notes(
      slide,
      "云计算像城市外的大仓库，容量大但离得远。边缘计算像小区门口的小仓库，离得近、延迟低，但每个仓库容量小。用户在移动，一换区域就可能要换仓库，这就产生了服务迁移。"
    );
  }

  // 4. Cell anatomy
  {
    const slide = newSlide(presentation);
    header(slide, 4, "背景知识", "一个 cell 里到底有什么");
    addPanel(slide, 72, 196, 620, 330, "#FBFBF8", C.teal, 2);
    addText(slide, { left: 96, top: 214, width: 400, height: 28, text: "cell（一片服务区域）", size: 18, bold: true, color: C.teal });
    addPanel(slide, 108, 262, 220, 68, C.paper, C.rule);
    addText(slide, { left: 126, top: 278, width: 184, height: 26, text: "基站 gNB", size: 17, bold: true });
    addText(slide, { left: 126, top: 306, width: 184, height: 18, text: "负责无线接入", size: 12, color: C.muted });
    addPanel(slide, 108, 348, 220, 68, C.paper, C.rule);
    addText(slide, { left: 126, top: 364, width: 184, height: 26, text: "交换机", size: 17, bold: true });
    addText(slide, { left: 126, top: 392, width: 184, height: 18, text: "负责回程网络", size: 12, color: C.muted });
    addPanel(slide, 108, 434, 220, 68, C.paper, C.rule);
    addText(slide, { left: 126, top: 450, width: 184, height: 26, text: "边缘服务器", size: 17, bold: true });
    addText(slide, { left: 126, top: 478, width: 184, height: 18, text: "运行服务、保存状态", size: 12, color: C.muted });
    addText(slide, { left: 430, top: 250, width: 80, height: 26, text: "车", size: 18, bold: true });
    slide.shapes.add({
      geometry: "ellipse",
      position: { left: 470, top: 296, width: 10, height: 10 },
      fill: C.teal,
      line: { style: "solid", fill: "none", width: 0 },
    });
    slide.shapes.add({
      geometry: "connector",
      kind: "straight",
      position: { left: 328, top: 300, width: 142, height: 1 },
      line: { style: "dashed", fill: C.teal, width: 2 },
    });
    addText(slide, { left: 350, top: 270, width: 90, height: 20, text: "无线连接", size: 11, color: C.muted });
    addText(slide, {
      left: 730,
      top: 214,
      width: 478,
      height: 30,
      text: "三句话记住 cell",
      size: 20,
      bold: true,
    });
    addText(slide, {
      left: 730,
      top: 264,
      width: 478,
      height: 190,
      text: "1. 车在哪个 cell，就连哪个基站。\n\n2. 服务跑在这个 cell 的边缘服务器上。\n\n3. cell 不是“只是一个基站”，而是服务归属单元。",
      size: 17,
      lineSpacing: 1.2,
    });
    takeaway(slide, "cell = 服务区域 + 基站 + 交换机 + 边缘服务器。");
    pageNumber(slide, 4);
    notes(
      slide,
      "这一页解释 cell。cell 不是只有一个基站，它是一片服务区域。区域里有一个基站负责无线接入，一个交换机负责回程网络，一个边缘服务器负责运行服务和保存状态。车在哪个 cell，就连哪个基站，用哪个边缘服务器。"
    );
  }

  // 5. Handover vs migration
  {
    const slide = newSlide(presentation);
    header(slide, 5, "背景知识", "车换 cell 时，发生了两件事");
    addPanel(slide, 72, 208, 300, 220, C.paper, C.teal, 2);
    addText(slide, { left: 94, top: 226, width: 256, height: 26, text: "cell A", size: 18, bold: true, color: C.teal });
    addText(slide, { left: 94, top: 268, width: 256, height: 22, text: "基站 A", size: 15 });
    addText(slide, { left: 94, top: 300, width: 256, height: 22, text: "边缘服务器 A", size: 15 });
    addText(slide, { left: 94, top: 332, width: 256, height: 22, text: "状态在 A", size: 15, color: C.rust });

    addPanel(slide, 620, 208, 300, 220, C.paper, C.rust, 2);
    addText(slide, { left: 642, top: 226, width: 256, height: 26, text: "cell B", size: 18, bold: true, color: C.rust });
    addText(slide, { left: 642, top: 268, width: 256, height: 22, text: "基站 B", size: 15 });
    addText(slide, { left: 642, top: 300, width: 256, height: 22, text: "边缘服务器 B", size: 15 });
    addText(slide, { left: 642, top: 332, width: 256, height: 22, text: "状态要搬到这里", size: 15, color: C.rust });

    addText(slide, { left: 430, top: 270, width: 80, height: 26, text: "车", size: 18, bold: true });
    slide.shapes.add({
      geometry: "connector", kind: "straight",
      position: { left: 470, top: 310, width: 150, height: 1 },
      line: { style: "solid", fill: C.teal, width: 2 },
      tail: { type: "arrow", width: "med", length: "med" },
    });
    addText(slide, { left: 452, top: 318, width: 190, height: 22, text: "handover：车换基站", size: 12, color: C.teal });
    slide.shapes.add({
      geometry: "connector", kind: "straight",
      position: { left: 372, top: 340, width: 248, height: 1 },
      line: { style: "solid", fill: C.rust, width: 2 },
      tail: { type: "arrow", width: "med", length: "med" },
    });
    addText(slide, { left: 400, top: 348, width: 220, height: 22, text: "migration：状态换服务器", size: 12, color: C.rust });

    addText(slide, {
      left: 72,
      top: 470,
      width: 1136,
      height: 56,
      text: "这两件事不是一回事。车可能已经连到 B，但服务状态还在 A。",
      size: 18,
    });
    takeaway(slide, "handover 是“车换基站”，migration 是“状态换服务器”。");
    pageNumber(slide, 5);
    notes(
      slide,
      "车从 A 到 B，会发生两件事。第一，车换基站，这叫 handover。第二，服务状态从 A 的边缘服务器搬到 B，这叫 migration。这两件事可以不同步：车已经连到 B，但状态还在 A。"
    );
  }

  // 6. State / base / delta / restore
  {
    const slide = newSlide(presentation);
    header(slide, 6, "背景知识", "服务里到底要搬什么：base、delta、restore");
    addText(slide, { left: 72, top: 190, width: 420, height: 30, text: "状态 = 服务的“记忆”", size: 20, bold: true, color: C.teal });
    addText(slide, {
      left: 72,
      top: 232,
      width: 420,
      height: 130,
      text: "视频播放到第几分钟。\n导航当前走到哪条路。\n缓存了哪些地图和视频。\n这些都要跟着车走。",
      size: 16,
      color: C.muted,
      lineSpacing: 1.35,
    });
    addPanel(slide, 500, 208, 220, 120, C.paper, C.rule);
    addText(slide, { left: 522, top: 226, width: 176, height: 24, text: "节点 A", size: 17, bold: true });
    addText(slide, { left: 522, top: 260, width: 176, height: 50, text: "base snapshot\n上次保存的完整状态", size: 13, color: C.muted });
    addPanel(slide, 760, 208, 220, 120, C.tealSoft, C.teal);
    addText(slide, { left: 782, top: 226, width: 176, height: 24, text: "delta", size: 17, bold: true, color: C.teal });
    addText(slide, { left: 782, top: 260, width: 176, height: 50, text: "从上次快照之后\n变化的部分", size: 13, color: C.ink });
    addPanel(slide, 1030, 208, 180, 120, C.paper, C.rust);
    addText(slide, { left: 1050, top: 226, width: 140, height: 24, text: "节点 B", size: 17, bold: true });
    addText(slide, { left: 1050, top: 260, width: 140, height: 50, text: "apply + restore\n恢复成可运行", size: 13, color: C.muted });
    slide.shapes.add({
      geometry: "connector",
      kind: "straight",
      position: { left: 720, top: 268, width: 40, height: 1 },
      line: { style: "solid", fill: C.teal, width: 2 },
      tail: { type: "arrow", width: "med", length: "med" },
    });
    slide.shapes.add({
      geometry: "connector",
      kind: "straight",
      position: { left: 980, top: 268, width: 50, height: 1 },
      line: { style: "solid", fill: C.teal, width: 2 },
      tail: { type: "arrow", width: "med", length: "med" },
    });
    addPanel(slide, 500, 366, 710, 86, C.rustSoft, C.rust);
    addText(slide, { left: 522, top: 382, width: 666, height: 26, text: "如果目标节点没有 base：只能搬全量。", size: 16, bold: true, color: C.rust });
    addText(slide, { left: 522, top: 412, width: 666, height: 24, text: "这叫 cold target，是增量策略最大的风险。", size: 14, color: C.ink });
    addText(slide, {
      left: 72,
      top: 486,
      width: 1136,
      height: 54,
      text: "目标节点有 base，就只传 delta；没有 base，就要传全量。恢复也要时间。",
      size: 17,
      color: C.muted,
    });
    takeaway(slide, "增量不是免费的，它依赖目标节点有没有 base。");
    pageNumber(slide, 6);
    notes(
      slide,
      "状态就是服务的记忆：视频播放到哪、导航走到哪、缓存了什么。base 是上次保存的完整快照，delta 是之后变化的部分。目标节点有 base，就只传 delta；没有 base，就要传全量。传完还要 apply 和 restore，才能继续服务。"
    );
  }

  // 7. Overhead
  {
    const slide = newSlide(presentation);
    header(slide, 7, "背景知识", "搬家不只看箱子多少，还要看占用时间");
    const items = [
      ["数据量", "搬了多少 MB 或 GB", "像箱子总重量"],
      ["带宽-时间", "占用了网络多久", "像电梯被占了几分钟"],
      ["恢复", "到了之后整理、重启多久", "像拆箱、摆货"],
      ["用户侧", "服务断了多久、还要等多久", "像顾客排队时间"],
    ];
    items.forEach(([label, desc, analogy], i) => {
      const top = 190 + i * 92;
      addText(slide, { left: 72, top, width: 170, height: 30, text: label, size: 20, bold: true, color: C.teal });
      addText(slide, { left: 270, top: top + 2, width: 520, height: 28, text: desc, size: 17 });
      addText(slide, { left: 810, top: top + 3, width: 390, height: 26, text: analogy, size: 14, color: C.muted });
      addRule(slide, 72, top + 54, 1136, 1, C.rule);
    });
    addText(slide, {
      left: 72,
      top: 540,
      width: 1136,
      height: 30,
      text: "同一个 100 GB，占用 10 秒和占用 100 秒，代价完全不同。",
      size: 17,
    });
    takeaway(slide, "只看 GB，会低估迁移对链路和用户的实际占用。");
    pageNumber(slide, 7);
    notes(
      slide,
      "搬家不只看箱子多少。还要看电梯被占用多久，到了之后整理多久，顾客等了多久。对应到系统里，就是数据量、带宽-时间、恢复时间、用户中断时间。只看 GB 会低估开销。"
    );
  }

  // 8. Topology
  {
    const slide = newSlide(presentation);
    header(slide, 8, "系统实现", "系统拓扑：两张图不要混在一起");
    const x0 = 64;
    const y0 = 196;
    const cellW = 96;
    const cellH = 78;
    const gap = 14;
    const rows = 3;
    const cols = 4;
    const cellPos = (row, col) => ({ left: x0 + col * (cellW + gap), top: y0 + row * (cellH + gap) });
    const pathPoint = (row, col) => {
      const pos = cellPos(row, col);
      return { x: pos.left + 24, y: pos.top + 36 };
    };
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        if (c < cols - 1) addRule(slide, x0 + c * (cellW + gap) + cellW, y0 + r * (cellH + gap) + cellH / 2, gap, 1, "#C9C9C1");
        if (r < rows - 1) addRule(slide, x0 + c * (cellW + gap) + cellW / 2, y0 + r * (cellH + gap) + cellH, 1, gap, "#C9C9C1");
      }
    }
    const current = { row: 1, col: 2 };
    const target = { row: 0, col: 3 };
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        const pos = cellPos(r, c);
        addPanel(slide, pos.left, pos.top, cellW, cellH, C.paper, C.rule, 1);
        slide.shapes.add({ geometry: "ellipse", position: { left: pos.left + 10, top: pos.top + 10, width: 8, height: 8 }, fill: C.teal, line: { style: "solid", fill: "none", width: 0 } });
        addText(slide, { left: pos.left + 22, top: pos.top + 4, width: 42, height: 16, text: "gNB", size: 9, color: C.muted });
        addPanel(slide, pos.left + cellW - 46, pos.top + cellH - 24, 38, 16, C.tealSoft, C.teal, 1);
        addText(slide, { left: pos.left + cellW - 44, top: pos.top + cellH - 22, width: 34, height: 12, text: "edge", size: 8, bold: true, color: C.teal });
        if (r === current.row && c === current.col) addPanel(slide, pos.left, pos.top, cellW, cellH, "none", C.teal, 3);
        if (r === target.row && c === target.col) addPanel(slide, pos.left, pos.top, cellW, cellH, "none", C.rust, 3);
      }
    }
    const path = [[2, 0], [2, 1], [1, 1], [1, 2], [1, 3], [0, 3]];
    for (const point of path) {
      const p = pathPoint(...point);
      slide.shapes.add({ geometry: "ellipse", position: { left: p.x - 3, top: p.y - 3, width: 6, height: 6 }, fill: C.teal, line: { style: "solid", fill: "none", width: 0 } });
    }
    const startX = cellPos(current.row, current.col).left + cellW;
    const startY = cellPos(current.row, current.col).top + cellH / 2;
    const endX = cellPos(target.row, target.col).left + cellW / 2;
    const endY = cellPos(target.row, target.col).top;
    const turnX = 510;
    const bendY = 176;
    slide.shapes.add({ geometry: "connector", kind: "straight", position: { left: startX, top: startY, width: turnX - startX, height: 1 }, line: { style: "solid", fill: C.rust, width: 3 } });
    slide.shapes.add({ geometry: "connector", kind: "straight", position: { left: turnX, top: bendY, width: 1, height: startY - bendY }, line: { style: "solid", fill: C.rust, width: 3 } });
    slide.shapes.add({ geometry: "connector", kind: "straight", position: { left: endX, top: bendY, width: turnX - endX, height: 1 }, line: { style: "solid", fill: C.rust, width: 3 } });
    slide.shapes.add({ geometry: "connector", kind: "straight", position: { left: endX, top: bendY, width: 1, height: endY - bendY }, line: { style: "solid", fill: C.rust, width: 3 }, tail: { type: "arrow", width: "lg", length: "lg" } });
    addText(slide, { left: 300, top: 146, width: 220, height: 22, text: "状态迁移", size: 12, bold: true, color: C.rust });

    addRule(slide, 556, 196, 2, 250, C.teal);
    addText(slide, { left: 580, top: 198, width: 620, height: 30, text: "两张图要分开看", size: 20, bold: true });
    addText(slide, {
      left: 580,
      top: 244,
      width: 620,
      height: 150,
      text: "移动图：车经过哪些 cell。\n网络图：交换机之间怎么连。\n\n4 连通是网络连法，不是车的行驶限制。",
      size: 16,
      color: C.muted,
      lineSpacing: 1.3,
    });
    addText(slide, {
      left: 580,
      top: 410,
      width: 620,
      height: 60,
      text: "DATA7：30 个真实 gNB，62 条链路。\nSF / Rome：16×16 网格。",
      size: 14,
      color: C.ink,
    });
    addText(slide, {
      left: 580,
      top: 490,
      width: 620,
      height: 44,
      text: "青框：当前 cell    橙框：目标 cell\n青点：车辆路径    橙箭头：状态迁移",
      size: 12,
      color: C.muted,
    });
    takeaway(slide, "cell 归属和网络路由是两张图，不能混在一起。");
    pageNumber(slide, 8);
    notes(
      slide,
      "这是系统拓扑。左边一格是一个 cell，里面有 gNB 和 edge server。青框是当前 cell，橙框是目标 cell，青点是车经过的 cell，橙箭头是状态迁移。右边要强调：移动图和网络图是两张图。4 连通是交换机之间的连法，不是车的行驶限制。"
    );
  }

  // 9. Simulation setup
  {
    const slide = newSlide(presentation);
    header(slide, 9, "仿真实现", "为什么用仿真：真实城市做上千次切换不现实");
    addText(slide, {
      left: 72,
      top: 190,
      width: 440,
      height: 210,
      text: "仿真能做什么：\n\n1. 控制变量：带宽、速度、车辆数。\n2. 重复实验：同一个场景跑很多次。\n3. 覆盖真实轨迹：DATA7、SF、Rome。",
      size: 16,
      lineSpacing: 1.3,
    });
    addTable(slide, {
      left: 540,
      top: 190,
      width: 668,
      height: 320,
      columnWidths: [320, 348],
      rowHeight: 53,
      values: [
        ["真实数据", "可控假设"],
        ["DATA7：30 个真实 gNB", "链路带宽"],
        ["SF / Rome：出租车轨迹", "状态增长率"],
        ["4 类服务的数据流", "恢复速率"],
        ["网络时延", "镜像层大小"],
        ["SUMO 车流（DATA7）", "服务算力与内存"],
      ],
    });
    addText(slide, {
      left: 72,
      top: 528,
      width: 1136,
      height: 50,
      text: "注意：DATA7 的基站位置是真实的，车辆轨迹是 SUMO 生成的，不是真实 GPS。",
      size: 15,
      color: C.muted,
    });
    takeaway(slide, "真实拓扑与轨迹，加上可控的网络和服务参数。");
    pageNumber(slide, 9);
    notes(
      slide,
      "为什么用仿真？真实城市里做上千次切换不现实。仿真可以控制带宽、速度、车辆数，也可以重复跑。我们用 DATA7 的真实 gNB 位置和 SUMO 车流，用 SF 和 Rome 的真实出租车轨迹。带宽、状态大小、恢复速率是可控假设。"
    );
  }

  // 10. Four services
  {
    const slide = newSlide(presentation);
    header(slide, 10, "服务模型", "四类 MEC 服务：它们搬的东西不一样");
    addTable(slide, {
      left: 72,
      top: 190,
      width: 1136,
      height: 330,
      columnWidths: [200, 280, 320, 336],
      rowHeight: 66,
      fontSize: 13,
      values: [
        ["服务", "终端传什么", "边缘算什么", "状态 / 镜像"],
        ["导航", "GPS、航向", "路径重规划", "5 MB / 370 MB"],
        ["信息娱乐", "播放位置、码率", "转码、选片", "200 MB / 540 MB"],
        ["上下文告警", "传感器、遥测", "上下文匹配", "3 MB / 205 MB"],
        ["交通分析", "探针、雷达", "时空聚合", "80 MB / 295 MB"],
      ],
    });
    addText(slide, {
      left: 72,
      top: 540,
      width: 1136,
      height: 46,
      text: "这些是代表性参数，大小差两个数量级。不是运营商实测分布。",
      size: 15,
      color: C.muted,
    });
    takeaway(slide, "服务不是一样大的，迁移策略不能一刀切。");
    pageNumber(slide, 10);
    notes(
      slide,
      "四类服务搬的东西不一样。导航状态很小，信息娱乐很大，告警最小，交通分析中等。镜像也有大有小。这些是代表性参数，不是运营商实测。重点不是具体数字，而是服务之间差两个数量级。"
    );
  }

  // 11. Baseline
  {
    const slide = newSlide(presentation);
    header(slide, 11, "实验一", "最直接的做法：车到哪，服务搬到哪");
    const kpis = [["48.8%", "服务中断"], ["345 GB", "迁移数据"], ["48.2×", "开销比"]];
    kpis.forEach(([value, label], i) => {
      const left = 72 + i * 384;
      addText(slide, { left, top: 178, width: 340, height: 58, text: value, size: 38, bold: true, color: C.rust });
      addText(slide, { left, top: 236, width: 340, height: 24, text: label, size: 14, color: C.muted });
    });
    addTable(slide, {
      left: 72,
      top: 292,
      width: 1136,
      height: 240,
      columnWidths: [536, 280, 320],
      rowHeight: 48,
      values: [
        ["服务", "中断率", "迁移数据"],
        ["信息娱乐", "47.9%", "215 GB"],
        ["交通分析", "33.2%", "108 GB"],
        ["导航", "5.5%", "15.6 GB"],
        ["上下文告警", "4.0%", "5.7 GB"],
      ],
    });
    takeaway(slide, "大状态服务主导开销：信息娱乐一个服务就占 215 GB。");
    pageNumber(slide, 11);
    notes(
      slide,
      "这是最直接的做法：车到哪，就把服务全量搬到哪。DATA7 上 40 km/h 就有 48.8% 中断，345 GB，开销比 48 倍。信息娱乐一个服务占 215 GB。所以不能把所有服务一视同仁。"
    );
  }

  // 12. Delta and base
  {
    const slide = newSlide(presentation);
    header(slide, 12, "实验二", "少搬一点：增量到底能省多少");
    addTable(slide, {
      left: 72,
      top: 190,
      width: 1136,
      height: 320,
      columnWidths: [236, 210, 230, 230, 230],
      rowHeight: 54,
      values: [
        ["数据", "冷目标", "字节节省", "中断（全量）", "中断（增量）"],
        ["DATA7", "17%", "74%", "48.8%", "11.5%"],
        ["SF", "42%", "47%", "13.2%", "4.8%"],
        ["Rome", "55%", "28%", "9.0%", "4.2%"],
        ["合成", "93%", "2.4%", "5.9%", "5.7%"],
      ],
    });
    addText(slide, {
      left: 72,
      top: 536,
      width: 1136,
      height: 50,
      text: "冷目标 = 目标节点没有 base。冷目标越多，增量越接近全量。",
      size: 16,
      color: C.muted,
    });
    takeaway(slide, "增量收益取决于 base 命中，不是一个固定倍数。");
    pageNumber(slide, 12);
    notes(
      slide,
      "增量能不能省，取决于目标节点有没有 base。DATA7 只有 17% 冷目标，省 74% 字节；合成数据 93% 冷目标，只省 2.4%。所以增量不是固定收益，它是一个 base locality 问题。"
    );
  }

  // 13. Stress matrix
  {
    const slide = newSlide(presentation);
    header(slide, 13, "实验三", "车更快、网更差，会发生什么");
    addTable(slide, {
      left: 72,
      top: 190,
      width: 1136,
      height: 340,
      columnWidths: [286, 220, 220, 410],
      rowHeight: 56,
      values: [
        ["场景", "20 km/h", "90 km/h", "中断 ≥ 50% 起点"],
        ["100 Mbps / 12 车", "65.7%", "92.3%", "20 km/h"],
        ["500 Mbps / 12 车", "17.0%", "72.3%", "90 km/h"],
        ["1 Gbps / 12 车", "8.7%", "39.2%", "90 km/h 以上"],
        ["500 Mbps / 30 车", "36.8%", "89.0%", "40 km/h"],
        ["100 Mbps / 30 车", "71.9%", "93.1%", "20 km/h"],
      ],
    });
    addText(slide, {
      left: 72,
      top: 550,
      width: 1136,
      height: 40,
      text: "同一策略，带宽和负载一变，可能从“可接受”直接变成“不可用”。",
      size: 16,
      color: C.muted,
    });
    takeaway(slide, "需求除以容量，决定系统什么时候撑不住。速度只是放大器。");
    pageNumber(slide, 13);
    notes(
      slide,
      "压力矩阵跑了五个场景、四种策略、四个速度。100 Mbps 12 车 20 km/h 就崩，500 Mbps 30 车 40 km/h 崩，1 Gbps 12 车到 90 还没崩。所以决定成败的是需求除以容量，速度只是放大器。"
    );
  }

  // 14. Predictors
  {
    const slide = newSlide(presentation);
    header(slide, 14, "实验四", "提前搬：预测准了才划算");
    addText(slide, {
      left: 72,
      top: 180,
      width: 1136,
      height: 40,
      text: "预测器 = 在车到边界之前，猜它下一个会去哪个 cell。",
      size: 17,
      color: C.muted,
    });
    addTable(slide, {
      left: 72,
      top: 232,
      width: 1136,
      height: 300,
      columnWidths: [290, 190, 190, 233, 233],
      rowHeight: 54,
      values: [
        ["预测器", "准确率", "中断", "迁移数据", "到达后滞后"],
        ["oracle（上限）", "100%", "7.4%", "139 GB", "1.7 步"],
        ["一阶马尔可夫", "49%", "8.2%", "192 GB", "5.9 步"],
        ["last-direction", "21%", "9.8%", "214 GB", "10.9 步"],
        ["reactive 全量", "—", "39.0%", "140 GB", "7.8 步"],
      ],
    });
    addText(slide, {
      left: 72,
      top: 548,
      width: 1136,
      height: 40,
      text: "预测错就会搬到错误节点，再重迁一次。迁移数据反而比不预测更多。",
      size: 16,
      color: C.muted,
    });
    takeaway(slide, "预测质量决定 proactive 是省钱还是烧钱。oracle 只能当上限。");
    pageNumber(slide, 14);
    notes(
      slide,
      "提前搬需要预测。oracle 看真实未来，是上限；一阶马尔可夫用其他车辆学转移概率，49%；last-direction 按方向猜，21%。预测差会搬到错误节点，再重迁一次，迁移数据反而更多。"
    );
  }

  // 15. Conclusions
  {
    const slide = newSlide(presentation);
    header(slide, 15, "总结", "三句话总结");
    const items = [
      ["01", "开销不是单一字节数", "要同时看数据量、占用时间、恢复时间和用户中断。"],
      ["02", "增量的关键是 base 在不在", "目标节点有 base 才便宜，没有 base 就要回退全量。"],
      ["03", "提前搬的关键是预测准不准", "预测错会比不预测更贵，oracle 只能当上限。"],
    ];
    items.forEach(([num, title, desc], i) => {
      const top = 188 + i * 120;
      addText(slide, { left: 72, top, width: 64, height: 42, text: num, size: 24, bold: true, color: C.teal });
      addText(slide, { left: 156, top: top + 1, width: 900, height: 30, text: title, size: 21, bold: true });
      addText(slide, { left: 156, top: top + 38, width: 940, height: 28, text: desc, size: 16, color: C.muted });
    });
    addText(slide, {
      left: 72,
      top: 540,
      width: 1136,
      height: 34,
      text: "没有单一最优策略。要按带宽、负载、速度的组合来选择。",
      size: 18,
    });
    takeaway(slide, "这些正是项目里密文增量与同步机制要付的系统成本。");
    pageNumber(slide, 15);
    notes(
      slide,
      "三句话。第一，开销不是单一字节数，要看数据量、时间、恢复和中断。第二，增量的关键是 base 在不在。第三，提前搬的关键是预测准不准。没有单一最优策略。"
    );
  }

  // 16. Next
  {
    const slide = newSlide(presentation);
    header(slide, 16, "下一步", "把 base 和隐私一起考虑");
    const items = [
      ["base placement", "哪些节点值得预热，复制间隔多长。"],
      ["隐私侧信道", "迁移时刻与通信端点会泄露移动轨迹。"],
      ["小规模 testbed", "用真实节点验证仿真结论。"],
    ];
    items.forEach(([title, desc], i) => {
      const left = 72 + i * 384;
      addRule(slide, left, 200, 48, 3, C.teal);
      addText(slide, { left, top: 220, width: 330, height: 34, text: title, size: 21, bold: true });
      addText(slide, { left, top: 266, width: 330, height: 90, text: desc, size: 16, color: C.muted });
    });
    addText(slide, {
      left: 72,
      top: 440,
      width: 1136,
      height: 54,
      text: "先系统，后安全。两者共用同一套开销账。",
      size: 28,
      bold: true,
      color: C.teal,
    });
    takeaway(slide, "下一步把 base 放置与隐私保护放进同一个评估框架。");
    pageNumber(slide, 16);
    notes(
      slide,
      "下一步做 base placement 和隐私侧信道。先系统后安全，两者共用同一套开销账。"
    );
  }

  for (let i = 0; i < presentation.slides.items.length; i += 1) {
    const slide = presentation.slides.items[i];
    const blob = await presentation.export({ slide, format: "png", scale: 1 });
    const stem = `slide-${String(i + 1).padStart(2, "0")}.png`;
    await fs.writeFile(path.join(renders, stem), new Uint8Array(await blob.arrayBuffer()));
  }

  const draftPath = path.join(BUILD_DIR, "draft_teaching.pptx");
  await (await PresentationFile.exportPptx(presentation)).save(draftPath);
  console.log(`draft: ${draftPath}`);
  console.log(`renders: ${renders}`);

  if (process.argv.includes("--finalize")) {
    const { finalizePresentation } = await import(
      pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href
    );
    const stagingDir = path.join(WORKSPACE, ".codex-finalizer");
    await fs.mkdir(stagingDir, { recursive: true });
    await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
    const candidatePath = path.join(stagingDir, "candidate_teaching.pptx");
    await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
    const result = await finalizePresentation({
      explicitTotalSlideCount: 16,
      requiredNativeTableOwnerSlides: [9, 10, 11, 12, 13, 14],
      requiredNativeChartOwnerSlides: [],
      workspaceDir: WORKSPACE,
      candidatePath,
      finalPath: FINAL_PPTX,
      pythonExecutable:
        "C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe",
      integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
      layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
      layoutArgs: [
        "--expected-slide-size-emu",
        "12192000,6858000",
        "--validate-bullet-geometry",
        "--validate-heading-fit",
        ...[9, 10, 11, 12, 13, 14].flatMap((n) => ["--require-native-table-slide", String(n)]),
      ],
      fontPolicy: { basis: "design", families: [FONT] },
      verifyArtifactToolImport: true,
      receiptPath: path.join(stagingDir, `${path.basename(FINAL_PPTX)}.validation.json`),
    });
    console.log(JSON.stringify(result, null, 2));
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
