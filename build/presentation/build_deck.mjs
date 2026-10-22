import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const WORKSPACE = "C:/Users/Administrator/Desktop/MyEdgeSimPy";
const BUILD_DIR = path.join(WORKSPACE, "build/presentation");
const OUTPUT_DIR = path.join(WORKSPACE, "output/presentation");
const SKILL_DIR =
  "C:/Users/Administrator/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations";
const FINAL_PPTX = path.join(OUTPUT_DIR, "跨边服务状态迁移_overhead_评估_v4.pptx");
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
const FRAME = { left: 72, top: 0, width: 1136 };

function addText(slide, opts) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name: opts.name,
    position: {
      left: opts.left,
      top: opts.top,
      width: opts.width,
      height: opts.height,
    },
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
    lineSpacing: opts.lineSpacing ?? 1.15,
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
    left: FRAME.left,
    top: 40,
    width: FRAME.width,
    height: 22,
    text: `${String(index).padStart(2, "0")}  ${section}`,
    size: 12,
    bold: true,
    color: C.muted,
  });
  addText(slide, {
    left: FRAME.left,
    top: 72,
    width: FRAME.width,
    height: 68,
    text: title,
    size: 30,
    bold: true,
    lineSpacing: 1.05,
  });
  addRule(slide, FRAME.left, 152, 64, 3, C.teal);
}

function takeaway(slide, text) {
  addRule(slide, FRAME.left, 610, FRAME.width, 1, C.rule);
  addText(slide, {
    left: FRAME.left,
    top: 626,
    width: 1040,
    height: 36,
    text,
    size: 19,
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
      if (isHeader) {
        cell.text.color = C.white;
        cell.text.fill = C.white;
      }
      const range = table.cells.block({ row: r, column: c, rowCount: 1, columnCount: 1 });
      range.textStyle.typeface = FONT;
      range.textStyle.fontSize = isHeader ? 14 : (opts.fontSize ?? 14);
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
  const renders = path.join(BUILD_DIR, "renders");
  await fs.mkdir(renders, { recursive: true });

  const presentation = Presentation.create({ slideSize: SIZE });
  presentation.theme.defaultFont = FONT;
  presentation.theme.colorScheme = {
    name: "Storage Systems Editorial",
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
      top: 214,
      width: 1040,
      height: 128,
      text: "跨边服务状态迁移的 overhead 评估",
      size: 46,
      bold: true,
      color: "#FFFFFF",
      lineSpacing: 1.08,
    });
    addRule(slide, 72, 360, 96, 3, "#8FB8B2");
    addText(slide, {
      left: 72,
      top: 390,
      width: 980,
      height: 40,
      text: "面向云边存储的数据安全缩减技术研究",
      size: 22,
      color: "#D6E5E2",
    });
    addText(slide, {
      left: 72,
      top: 470,
      width: 980,
      height: 64,
      text: "先把 base、delta、restore 和预测的系统账算清，再谈安全机制。",
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
      "各位老师好。我汇报的是项目里跨边状态迁移的子课题。今天先讲系统怎么实现，再讲做了哪些实验，结论会贯穿每一页。"
    );
  }

  // 2. Position in the project
  {
    const slide = newSlide(presentation);
    header(slide, 2, "项目位置", "本子课题对应项目里的第二条和第三条挑战");
    const rows = [
      ["01", "缓存优化与访问隐私难兼顾", "缓存调度依赖访问规律，调度请求可能暴露访问模式。", false],
      ["02", "常规加密妨碍增量识别与传输", "加密隐藏相似性，节点难以识别重复内容与差异。", true],
      ["03", "跨边状态同步可能泄露移动轨迹", "同步时刻与通信端点可能暴露终端移动规律。", true],
    ];
    rows.forEach(([num, title, desc, highlight], i) => {
      const top = 192 + i * 118;
      if (highlight) {
        addPanel(slide, 64, top - 8, 1152, 100, C.tealSoft, C.tealSoft);
        addRule(slide, 64, top - 8, 4, 100, C.teal);
      }
      addText(slide, {
        left: 88,
        top,
        width: 54,
        height: 40,
        text: num,
        size: 24,
        bold: true,
        color: highlight ? C.teal : C.muted,
      });
      addText(slide, {
        left: 156,
        top: top + 2,
        width: 464,
        height: 64,
        text: title,
        size: 20,
        bold: true,
      });
      addText(slide, {
        left: 648,
        top: top + 4,
        width: 520,
        height: 58,
        text: desc,
        size: 15,
        color: C.muted,
      });
      if (highlight) {
        addText(slide, {
          left: 1104,
          top: top + 6,
          width: 96,
          height: 24,
          text: "本子课题",
          size: 12,
          bold: true,
          color: C.teal,
          align: "right",
        });
      }
    });
    takeaway(slide, "当前阶段不做加密，先把跨边迁移的系统开销算清楚，给后续安全机制提供对照。");
    pageNumber(slide, 2);
    notes(
      slide,
      "老师项目里有三条挑战。我对应的是第二条和第三条：加密后的增量识别，以及跨边同步的隐私。当前阶段先不做加密，先把系统开销算清楚，否则后面安全机制的代价没有对照。"
    );
  }

  // 3. System topology
  {
    const slide = newSlide(presentation);
    header(slide, 3, "系统实现", "系统拓扑与迁移路径");

    const x0 = 64;
    const y0 = 198;
    const cellW = 96;
    const cellH = 78;
    const gap = 14;
    const rows = 3;
    const cols = 4;
    const cellPos = (row, col) => ({
      left: x0 + col * (cellW + gap),
      top: y0 + row * (cellH + gap),
    });
    const center = (row, col) => ({
      x: x0 + col * (cellW + gap) + cellW / 2,
      y: y0 + row * (cellH + gap) + cellH / 2,
    });
    const pathPoint = (row, col) => {
      const pos = cellPos(row, col);
      return { x: pos.left + 24, y: pos.top + 36 };
    };

    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        if (c < cols - 1) {
          addRule(slide, x0 + c * (cellW + gap) + cellW, y0 + r * (cellH + gap) + cellH / 2, gap, 1, "#C9C9C1");
        }
        if (r < rows - 1) {
          addRule(slide, x0 + c * (cellW + gap) + cellW / 2, y0 + r * (cellH + gap) + cellH, 1, gap, "#C9C9C1");
        }
      }
    }

    const current = { row: 1, col: 2 };
    const target = { row: 0, col: 3 };
    let currentEdge;
    let targetEdge;

    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        const pos = cellPos(r, c);
        addPanel(slide, pos.left, pos.top, cellW, cellH, C.paper, C.rule, 1);
        slide.shapes.add({
          geometry: "ellipse",
          position: { left: pos.left + 10, top: pos.top + 10, width: 8, height: 8 },
          fill: C.teal,
          line: { style: "solid", fill: "none", width: 0 },
        });
        addText(slide, {
          left: pos.left + 22,
          top: pos.top + 4,
          width: 42,
          height: 16,
          text: "gNB",
          size: 9,
          color: C.muted,
        });
        const edge = addPanel(slide, pos.left + cellW - 46, pos.top + cellH - 24, 38, 16, C.tealSoft, C.teal, 1);
        addText(slide, {
          left: pos.left + cellW - 44,
          top: pos.top + cellH - 22,
          width: 34,
          height: 12,
          text: "edge",
          size: 8,
          bold: true,
          color: C.teal,
        });
        if (r === current.row && c === current.col) {
          addPanel(slide, pos.left, pos.top, cellW, cellH, "none", C.teal, 3);
          currentEdge = edge;
        }
        if (r === target.row && c === target.col) {
          addPanel(slide, pos.left, pos.top, cellW, cellH, "none", C.rust, 3);
          targetEdge = edge;
        }
      }
    }

    const path = [[2, 0], [2, 1], [1, 1], [1, 2], [1, 3], [0, 3]];
    for (const point of path) {
      const p = pathPoint(...point);
      slide.shapes.add({
        geometry: "ellipse",
        position: { left: p.x - 3, top: p.y - 3, width: 6, height: 6 },
        fill: C.teal,
        line: { style: "solid", fill: "none", width: 0 },
      });
    }

    const startX = cellPos(current.row, current.col).left + cellW;
    const startY = cellPos(current.row, current.col).top + cellH / 2;
    const endX = cellPos(target.row, target.col).left + cellW / 2;
    const endY = cellPos(target.row, target.col).top;
    const turnX = 510;
    const bendY = 178;
    slide.shapes.add({
      geometry: "connector",
      kind: "straight",
      position: { left: startX, top: startY, width: turnX - startX, height: 1 },
      line: { style: "solid", fill: C.rust, width: 3 },
    });
    slide.shapes.add({
      geometry: "connector",
      kind: "straight",
      position: { left: turnX, top: bendY, width: 1, height: startY - bendY },
      line: { style: "solid", fill: C.rust, width: 3 },
    });
    slide.shapes.add({
      geometry: "connector",
      kind: "straight",
      position: { left: endX, top: bendY, width: turnX - endX, height: 1 },
      line: { style: "solid", fill: C.rust, width: 3 },
    });
    slide.shapes.add({
      geometry: "connector",
      kind: "straight",
      position: { left: endX, top: bendY, width: 1, height: endY - bendY },
      line: { style: "solid", fill: C.rust, width: 3 },
      tail: { type: "arrow", width: "lg", length: "lg" },
    });
    addText(slide, {
      left: 292,
      top: 150,
      width: 220,
      height: 22,
      text: "state migration",
      size: 12,
      bold: true,
      color: C.rust,
    });

    addRule(slide, 560, 198, 2, 244, C.teal);
    const steps = [
      "1  车跨 cell，触发 handover",
      "2  当前 edge server 持有 base",
      "3  迁移 delta 或全量状态",
      "4  目标 edge server apply + restore",
    ];
    steps.forEach((text, i) => {
      addText(slide, {
        left: 584,
        top: 206 + i * 58,
        width: 600,
        height: 30,
        text,
        size: 17,
      });
    });
    addText(slide, {
      left: 584,
      top: 452,
      width: 600,
      height: 24,
      text: "状态 3–200 MB，镜像 205–540 MB",
      size: 14,
      color: C.muted,
    });
    addText(slide, {
      left: 584,
      top: 490,
      width: 600,
      height: 44,
      text: "青框：当前 cell    橙框：目标 cell\n青点：车辆路径    橙箭头：状态迁移",
      size: 13,
      color: C.muted,
    });
    addText(slide, {
      left: 584,
      top: 552,
      width: 600,
      height: 22,
      text: "DATA7：30 个 gNB，62 条链路",
      size: 12,
      color: C.muted,
    });

    takeaway(slide, "切换是“车换 cell”，迁移是“状态换 edge server”。");
    pageNumber(slide, 3);
    notes(
      slide,
      "这是系统拓扑。每个格子是一个 cell，里面一个 gNB 和一个 edge server。车跨 cell 触发 handover，状态从当前 edge server 迁到目标 edge server。虚线是车辆路径，橙箭头是这次状态迁移。"
    );
  }

  // 4. State model
  {
    const slide = newSlide(presentation);
    header(slide, 4, "状态模型", "base、delta 与 restore");
    const aPanel = addPanel(slide, 72, 220, 260, 132, C.paper, C.rule);
    addText(slide, { left: 94, top: 240, width: 216, height: 26, text: "节点 A", size: 18, bold: true });
    addText(slide, { left: 94, top: 280, width: 216, height: 52, text: "base snapshot\n上次同步的完整状态", size: 14, color: C.muted });

    const bPanel = addPanel(slide, 432, 220, 320, 132, C.tealSoft, C.teal);
    addText(slide, { left: 454, top: 240, width: 276, height: 26, text: "传输", size: 18, bold: true, color: C.teal });
    addText(slide, { left: 454, top: 280, width: 276, height: 52, text: "delta = 当前状态 − base", size: 15, color: C.ink });

    const cPanel = addPanel(slide, 852, 220, 260, 132, C.paper, C.rule);
    addText(slide, { left: 874, top: 240, width: 216, height: 26, text: "节点 B", size: 18, bold: true });
    addText(slide, { left: 874, top: 280, width: 216, height: 52, text: "apply + restart\n恢复时间也计入开销", size: 14, color: C.muted });

    slide.shapes.connect(aPanel, bPanel, {
      kind: "straight",
      fromSide: "right",
      toSide: "left",
      line: { style: "solid", fill: C.teal, width: 2 },
      tail: { type: "arrow", width: "med", length: "med" },
    });
    slide.shapes.connect(bPanel, cPanel, {
      kind: "straight",
      fromSide: "right",
      toSide: "left",
      line: { style: "solid", fill: C.teal, width: 2 },
      tail: { type: "arrow", width: "med", length: "med" },
    });

    addPanel(slide, 432, 420, 680, 96, C.rustSoft, C.rust);
    addText(slide, {
      left: 456,
      top: 438,
      width: 632,
      height: 28,
      text: "冷目标：目标节点没有 base",
      size: 17,
      bold: true,
      color: C.rust,
    });
    addText(slide, {
      left: 456,
      top: 472,
      width: 632,
      height: 28,
      text: "不能只发 delta，必须回退全量状态。",
      size: 15,
      color: C.ink,
    });
    addText(slide, {
      left: 72,
      top: 548,
      width: 1136,
      height: 26,
      text: "恢复开销 = 应用状态 + 重启服务，按 5 ms/MB 计入迁移时长。",
      size: 16,
      color: C.muted,
    });
    takeaway(slide, "增量不是免费的。delta 能不能用，取决于目标节点有没有 base。");
    pageNumber(slide, 4);
    notes(
      slide,
      "每个节点可以保存一份 base snapshot。目标有 base 就传 delta，没有就回退全量。传完还要 apply 和 restart。所以增量不是免费的，收益取决于 base 在不在。"
    );
  }

  // 5. Real vs assumed
  {
    const slide = newSlide(presentation);
    header(slide, 5, "仿真实现", "真实数据与可控假设分开");
    addTable(slide, {
      left: 72,
      top: 196,
      width: 1136,
      height: 322,
      columnWidths: [568, 568],
      rowHeight: 54,
      boldFirstColumn: true,
      values: [
        ["真实数据", "可控假设"],
        ["DATA7：30 个真实 gNB", "链路带宽 100 Mbps 至 1 Gbps"],
        ["SF / Rome：真实出租车轨迹", "状态增长率"],
        ["4 类 MEC 服务的数据流", "恢复速率 5 ms/MB"],
        ["网络时延 5 ms/跳", "镜像层大小"],
        ["DATA7 车辆：SUMO 轨迹", "服务算力与内存"],
      ],
    });
    addText(slide, {
      left: 72,
      top: 540,
      width: 1136,
      height: 24,
      text: "DATA7 的基站位置来自 OpenCellID，车辆轨迹由 SUMO 生成。",
      size: 14,
      color: C.muted,
    });
    takeaway(slide, "拓扑和移动来自真实数据，网络与服务参数是可控假设。");
    pageNumber(slide, 5);
    notes(
      slide,
      "拓扑和移动来自真实数据。DATA7 是真实 gNB 加 SUMO 轨迹，SF 和 Rome 是真实出租车。带宽、状态大小、恢复速率是可控假设。这样既能贴近现实，又能做参数扫描。"
    );
  }

  // 6. Metrics
  {
    const slide = newSlide(presentation);
    header(slide, 6, "指标", "开销不能只看一个字节数");
    const items = [
      ["数据量", "state + image + base sync", "GB"],
      ["带宽-时间", "传输字节 × 占用步数", "MB·s"],
      ["恢复", "apply state + restart service", "steps"],
      ["用户侧", "interruption + post-arrival lag", "% / steps"],
    ];
    items.forEach(([label, formula, unit], i) => {
      const top = 196 + i * 92;
      addText(slide, { left: 72, top, width: 220, height: 32, text: label, size: 21, bold: true, color: C.teal });
      addText(slide, { left: 330, top: top + 2, width: 700, height: 30, text: formula, size: 18 });
      addText(slide, { left: 1060, top: top + 3, width: 148, height: 26, text: unit, size: 14, color: C.muted, align: "right" });
      addRule(slide, 72, top + 54, 1136, 1, C.rule);
    });
    addText(slide, {
      left: 72,
      top: 556,
      width: 1136,
      height: 34,
      text: "同一个 100 GB，占用 10 秒和占用 100 秒，代价不同。",
      size: 18,
      color: C.ink,
    });
    takeaway(slide, "只看 GB，会低估迁移对链路和用户的实际占用。");
    pageNumber(slide, 6);
    notes(
      slide,
      "开销我分四层看：数据量、带宽-时间、恢复、用户侧中断。只看 GB 会漏掉传输占用了多久、恢复要多久、用户等了多久。"
    );
  }

  // 7. Baseline
  {
    const slide = newSlide(presentation);
    header(slide, 7, "基线", "follow-me 在 DATA7 上有多贵");
    const kpis = [
      ["48.8%", "服务中断"],
      ["345 GB", "迁移数据"],
      ["48.2×", "开销比"],
    ];
    kpis.forEach(([value, label], i) => {
      const left = 72 + i * 384;
      addText(slide, { left, top: 182, width: 340, height: 58, text: value, size: 40, bold: true, color: C.rust });
      addText(slide, { left, top: 242, width: 340, height: 24, text: label, size: 14, color: C.muted });
    });
    addTable(slide, {
      left: 72,
      top: 300,
      width: 1136,
      height: 250,
      columnWidths: [536, 280, 320],
      rowHeight: 50,
      values: [
        ["服务", "中断率", "迁移数据"],
        ["信息娱乐", "47.9%", "215 GB"],
        ["交通分析", "33.2%", "108 GB"],
        ["导航", "5.5%", "15.6 GB"],
        ["上下文告警", "4.0%", "5.7 GB"],
      ],
    });
    takeaway(slide, "大状态服务主导开销，信息娱乐一个服务就占 215 GB。");
    pageNumber(slide, 7);
    notes(
      slide,
      "DATA7 上 follow-me 全量迁移，40 km/h 就有 48.8% 中断，345 GB，开销比 48 倍。信息娱乐一个服务占 215 GB。这解释了为什么不能把所有服务一视同仁。"
    );
  }

  // 8. Delta and base
  {
    const slide = newSlide(presentation);
    header(slide, 8, "增量", "增量收益取决于 base 命中");
    addTable(slide, {
      left: 72,
      top: 196,
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
      top: 540,
      width: 1136,
      height: 30,
      text: "冷目标越多，delta 越接近全量。合成数据 93% 是冷目标，增量几乎没有收益。",
      size: 16,
      color: C.muted,
    });
    takeaway(slide, "delta 的核心不是“增量”两个字，而是 base locality。");
    pageNumber(slide, 8);
    notes(
      slide,
      "换增量以后，DATA7 冷目标只有 17%，省 74% 字节。但合成数据 93% 是冷目标，只省 2.4%。所以 delta 的收益不是一个固定倍数，取决于 base 命中。"
    );
  }

  // 9. Stress matrix
  {
    const slide = newSlide(presentation);
    header(slide, 9, "压力矩阵", "需求除以容量决定临界速度");
    addTable(slide, {
      left: 72,
      top: 196,
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
      top: 556,
      width: 1136,
      height: 28,
      text: "同一策略在不同带宽和负载下，可能从“可接受”直接变成“不可用”。",
      size: 16,
      color: C.muted,
    });
    takeaway(slide, "速度是放大器。带宽和负载才是决定系统能不能撑住的底数。");
    pageNumber(slide, 9);
    notes(
      slide,
      "压力矩阵跑了五个场景、四种策略、四个速度。100 Mbps 12 车 20 km/h 就崩，500 Mbps 30 车 40 km/h 崩，1 Gbps 12 车到 90 还没崩。速度是放大器，带宽和负载是底数。"
    );
  }

  // 10. Predictors
  {
    const slide = newSlide(presentation);
    header(slide, 10, "预测器", "proactive 只有在预测准时才划算");
    addTable(slide, {
      left: 72,
      top: 196,
      width: 1136,
      height: 320,
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
      top: 540,
      width: 1136,
      height: 30,
      text: "预测差会让迁移数据从 140 GB 涨到 214 GB，比不预测更贵。",
      size: 16,
      color: C.muted,
    });
    takeaway(slide, "预测质量决定 proactive 是省钱还是烧钱。oracle 只能当上限。");
    pageNumber(slide, 10);
    notes(
      slide,
      "预测器对比很关键。oracle 100%，一阶马尔可夫 49%，last-direction 21%。差预测会让迁移数据从 140 GB 涨到 214 GB，比不预测更贵。pre-copy 能掩盖中断，但掩盖不了状态落后。"
    );
  }

  // 11. Conclusions
  {
    const slide = newSlide(presentation);
    header(slide, 11, "结论", "三条系统结论");
    const conclusions = [
      ["01", "overhead 不是单一字节数", "要把传输量、占用时间和恢复成本一起算。"],
      ["02", "delta 是 base locality 问题", "目标有没有 base，决定了增量能省多少。"],
      ["03", "proactive 是预测质量问题", "预测不准时，提前迁移会比不迁移更贵。"],
    ];
    conclusions.forEach(([num, title, desc], i) => {
      const top = 188 + i * 124;
      addText(slide, { left: 72, top, width: 64, height: 42, text: num, size: 24, bold: true, color: C.teal });
      addText(slide, { left: 156, top: top + 1, width: 620, height: 30, text: title, size: 21, bold: true });
      addText(slide, { left: 156, top: top + 38, width: 900, height: 28, text: desc, size: 16, color: C.muted });
    });
    addText(slide, {
      left: 72,
      top: 556,
      width: 1136,
      height: 32,
      text: "没有单一最优策略。按带宽、负载、速度的组合选择。",
      size: 19,
      color: C.ink,
    });
    takeaway(slide, "这些正是项目里密文增量与同步机制要付的系统成本。");
    pageNumber(slide, 11);
    notes(
      slide,
      "三条结论。第一，overhead 要按 bytes 加 time 加 restore 算。第二，delta 是 base locality 问题。第三，proactive 是预测质量问题。没有单一最优策略。"
    );
  }

  // 12. Next
  {
    const slide = newSlide(presentation);
    header(slide, 12, "下一步", "base placement 与隐私");
    const items = [
      ["base placement", "哪些节点值得预热，复制间隔多长。"],
      ["隐私侧信道", "迁移时刻与通信端点会泄露移动轨迹。"],
      ["小规模 testbed", "用真实节点验证仿真结论。"],
    ];
    items.forEach(([title, desc], i) => {
      const left = 72 + i * 384;
      addRule(slide, left, 196, 48, 3, C.teal);
      addText(slide, { left, top: 216, width: 330, height: 34, text: title, size: 21, bold: true });
      addText(slide, { left, top: 262, width: 330, height: 90, text: desc, size: 16, color: C.muted });
    });
    addText(slide, {
      left: 72,
      top: 470,
      width: 1136,
      height: 54,
      text: "先系统，后安全。两者共用同一套开销账。",
      size: 28,
      bold: true,
      color: C.teal,
    });
    takeaway(slide, "下一步把 base 放置与隐私保护放进同一个评估框架。");
    pageNumber(slide, 12);
    notes(
      slide,
      "下一步做 base placement 和隐私侧信道。先系统后安全，两者共用同一套开销账。"
    );
  }

  // Render every slide.
  for (let i = 0; i < presentation.slides.items.length; i += 1) {
    const slide = presentation.slides.items[i];
    const blob = await presentation.export({ slide, format: "png", scale: 1 });
    const stem = `slide-${String(i + 1).padStart(2, "0")}.png`;
    await fs.writeFile(path.join(renders, stem), new Uint8Array(await blob.arrayBuffer()));
  }

  const draftPath = path.join(BUILD_DIR, "draft.pptx");
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(draftPath);
  console.log(`draft: ${draftPath}`);
  console.log(`renders: ${renders}`);

  if (process.argv.includes("--finalize")) {
    const { finalizePresentation } = await import(
      pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href
    );
    const stagingDir = path.join(WORKSPACE, ".codex-finalizer");
    await fs.mkdir(stagingDir, { recursive: true });
    await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
    const candidatePath = path.join(stagingDir, "candidate.pptx");
    await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
    const result = await finalizePresentation({
      explicitTotalSlideCount: 12,
      requiredNativeTableOwnerSlides: [5, 7, 8, 9, 10],
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
        ...[5, 7, 8, 9, 10].flatMap((n) => ["--require-native-table-slide", String(n)]),
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
