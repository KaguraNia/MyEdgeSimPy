import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const WORKSPACE = "C:/Users/Administrator/Desktop/MyEdgeSimPy";
const BUILD_DIR = path.join(WORKSPACE, "build/presentation");
const OUTPUT_DIR = path.join(WORKSPACE, "output/presentation");
const SKILL_DIR =
  "C:/Users/Administrator/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations";
const FINAL_PPTX = path.join(OUTPUT_DIR, "跨边服务状态迁移_教学详版_v6.pptx");
const FONT = "Microsoft YaHei";

const C = {
  bg: "#F7F7F4",
  paper: "#FFFFFF",
  ink: "#1B1B19",
  muted: "#5F5F58",
  quiet: "#7A7A72",
  rule: "#D9D9D1",
  teal: "#0F5B5B",
  teal2: "#2E7774",
  tealSoft: "#E7F0EE",
  rust: "#B84A24",
  rustSoft: "#F7E8E2",
  amber: "#A56A00",
  amberSoft: "#F6EEDC",
  green: "#547248",
  greenSoft: "#EBF1E7",
};

const SIZE = { width: 1280, height: 720 };
const CONTENT = { left: 72, top: 176, width: 1136, bottom: 590 };

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
    fontSize: opts.size ?? 17,
    bold: opts.bold ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "top",
    lineSpacing: opts.lineSpacing ?? 1.28,
    insets: opts.insets ?? 0,
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

function addPanel(
  slide,
  left,
  top,
  width,
  height,
  fill = C.paper,
  line = C.rule,
  lineWidth = 1
) {
  return slide.shapes.add({
    geometry: "roundRect",
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: lineWidth },
    borderRadius: "rounded-lg",
  });
}

function addCircle(slide, left, top, size, fill) {
  return slide.shapes.add({
    geometry: "ellipse",
    position: { left, top, width: size, height: size },
    fill,
    line: { style: "solid", fill: "none", width: 0 },
  });
}

function addArrow(slide, left, top, width, height, color = C.teal, vertical = false) {
  return slide.shapes.add({
    geometry: "connector",
    kind: "straight",
    position: { left, top, width, height },
    line: { style: "solid", fill: color, width: 2 },
    tail: { type: "arrow", width: "med", length: "med" },
  });
}

function header(slide, index, section, title) {
  addText(slide, {
    left: 72,
    top: 36,
    width: 1136,
    height: 20,
    text: `${String(index).padStart(2, "0")}  ${section}`,
    size: 12,
    bold: true,
    color: C.muted,
  });
  addText(slide, {
    left: 72,
    top: 66,
    width: 1136,
    height: 64,
    text: title,
    size: 28,
    bold: true,
    lineSpacing: 1.08,
  });
  addRule(slide, 72, 143, 64, 3, C.teal);
}

function takeaway(slide, text, top = 620) {
  addRule(slide, 72, top - 14, 1136, 1, C.rule);
  addText(slide, {
    left: 72,
    top,
    width: 1040,
    height: 38,
    text,
    size: 17,
    bold: true,
    color: C.teal,
  });
}

function pageNumber(slide, number) {
  addText(slide, {
    left: 1178,
    top: 686,
    width: 40,
    height: 16,
    text: String(number),
    size: 10,
    color: C.muted,
    align: "right",
  });
}

function addNotes(slide, text) {
  slide.speakerNotes.text = text;
  slide.speakerNotes.setVisible(true);
}

function addTable(slide, opts) {
  const rows = opts.values.length;
  const columns = opts.values[0].length;
  const table = slide.tables.add({
    rows,
    columns,
    left: opts.left,
    top: opts.top,
    width: opts.width,
    height: opts.height,
    columnWidths: opts.columnWidths,
    values: opts.values,
  });
  table.styleOptions = { headerRow: false, bandedRows: false };
  table.borders.assign({ style: "solid", fill: C.rule, width: 1 });
  const rowHeight = opts.rowHeight ?? Math.floor(opts.height / rows);
  for (let r = 0; r < rows; r += 1) {
    table.rows[r].height = rowHeight;
    for (let c = 0; c < columns; c += 1) {
      const cell = table.getCell(r, c);
      const isHeader = r === 0;
      cell.fill = isHeader ? C.teal : r % 2 === 0 ? "#FBFBF8" : C.white;
      const range = table.cells.block({
        row: r,
        column: c,
        rowCount: 1,
        columnCount: 1,
      });
      range.textStyle.typeface = FONT;
      range.textStyle.fontSize = isHeader ? 12.5 : (opts.fontSize ?? 13);
      range.textStyle.bold = isHeader || (opts.boldFirstColumn && c === 0);
      range.textStyle.color = isHeader ? C.white : C.ink;
      range.textStyle.alignment =
        c === 0 || opts.alignLeftColumns?.includes(c) ? "left" : "center";
    }
  }
  return table;
}

function newSlide(presentation, background = C.bg) {
  const slide = presentation.slides.add();
  slide.background.fill = background;
  return slide;
}

function bulletColumn(slide, left, top, width, title, body, accent = C.teal) {
  addRule(slide, left, top, 38, 3, accent);
  addText(slide, {
    left,
    top: top + 16,
    width,
    height: 32,
    text: title,
    size: 19,
    bold: true,
  });
  addText(slide, {
    left,
    top: top + 58,
    width,
    height: 126,
    text: body,
    size: 15.5,
    color: C.muted,
    lineSpacing: 1.38,
  });
}

async function main() {
  await fs.mkdir(BUILD_DIR, { recursive: true });
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  const renderDir = path.join(BUILD_DIR, "renders_teaching_v6");
  await fs.mkdir(renderDir, { recursive: true });

  const presentation = Presentation.create({ slideSize: SIZE });
  presentation.theme.defaultFont = FONT;
  presentation.theme.colorScheme = {
    name: "MEC Teaching Detailed",
    themeColors: {
      accent1: C.teal,
      accent2: C.rust,
      accent3: C.teal2,
      accent4: C.amber,
      accent5: C.green,
      accent6: "#6A6A63",
      bg1: C.bg,
      bg2: C.paper,
      tx1: C.ink,
      tx2: C.muted,
      dk1: "#000000",
      dk2: "#123F3F",
      lt1: "#FFFFFF",
      lt2: C.tealSoft,
      hlink: C.teal,
      folHlink: C.rust,
    },
  };

  // 1. Cover
  {
    const slide = newSlide(presentation, "#0E3A3A");
    addText(slide, {
      left: 72,
      top: 50,
      width: 900,
      height: 24,
      text: "子课题汇报  /  2026年10月",
      size: 13,
      bold: true,
      color: "#BFD6D2",
    });
    addText(slide, {
      left: 72,
      top: 178,
      width: 1060,
      height: 155,
      text: "车辆移动后，服务如何\n不中断地跟过去",
      size: 45,
      bold: true,
      color: "#FFFFFF",
      lineSpacing: 1.12,
    });
    addRule(slide, 72, 362, 96, 3, "#8FB8B2");
    addText(slide, {
      left: 72,
      top: 392,
      width: 1020,
      height: 32,
      text: "MEC 服务状态迁移的仿真、开销评估与优化方向",
      size: 22,
      color: "#D6E5E2",
    });
    addText(slide, {
      left: 72,
      top: 448,
      width: 1020,
      height: 58,
      text: "今天先解释系统，再解释实验；每一页都回答“为什么测这个”。",
      size: 17,
      color: "#BFD6D2",
    });
    addText(slide, {
      left: 72,
      top: 640,
      width: 780,
      height: 22,
      text: "面向云边存储的数据安全缩减技术研究",
      size: 13,
      color: "#A9C6C1",
    });
    addNotes(
      slide,
      "各位老师好。今天的重点不是先讲一个复杂算法，而是把车辆移动后为什么需要迁移、迁移到底搬什么、开销从哪里来这三件事讲清楚。每讲一个概念，我都会说明它在后面的实验里对应哪个指标，最后再把结论和下一步接起来。"
    );
  }

  // 2. Roadmap
  {
    const slide = newSlide(presentation);
    header(slide, 2, "汇报结构", "这份汇报回答三个问题");
    const items = [
      ["问题一", "为什么必须迁移", "车换了服务区域以后，原来的服务器会变远。"],
      ["问题二", "迁移到底搬什么", "程序镜像、会话状态，以及目标节点恢复服务的时间。"],
      ["问题三", "怎样判断值不值", "用户中断、传输字节、链路占用和恢复时间。"],
    ];
    items.forEach(([label, title, body], i) => {
      const left = 72 + i * 384;
      addText(slide, {
        left,
        top: 190,
        width: 330,
        height: 22,
        text: label,
        size: 12,
        bold: true,
        color: C.teal,
      });
      addText(slide, {
        left,
        top: 220,
        width: 330,
        height: 40,
        text: title,
        size: 21,
        bold: true,
      });
      addText(slide, {
        left,
        top: 270,
        width: 330,
        height: 102,
        text: body,
        size: 15.5,
        color: C.muted,
        lineSpacing: 1.4,
      });
      addRule(slide, left, 382, 330, 1, C.rule);
    });
    addPanel(slide, 72, 412, 1136, 124, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 96,
      top: 430,
      width: 1088,
      height: 28,
      text: "当前结论先说一遍",
      size: 17,
      bold: true,
      color: C.teal,
    });
    addText(slide, {
      left: 96,
      top: 466,
      width: 1088,
      height: 48,
      text:
        "节省迁移字节主要靠“只搬变化部分”；减少用户中断主要靠“提前搬并在最后短暂切换”；两者都依赖目标节点是否已有 base，以及预测是否足够准。",
      size: 16,
      lineSpacing: 1.35,
    });
    takeaway(slide, "系统优化不是追求某一个数字最小，而是在中断、字节和时间之间选可接受的位置。");
    pageNumber(slide, 2);
    addNotes(
      slide,
      "这份汇报围绕三个问题展开。第一，车辆换区域后为什么不能继续用原来的服务器。第二，服务迁移到底搬的是哪些数据。第三，怎样才能说明一个方案真的更好。页面下方是本次汇报的总结论：只搬变化部分可以减少字节，提前搬可以减少中断，但这两个优化都依赖 base 和预测。后面每一组实验都是在验证这句话的不同部分。"
    );
  }

  // 3. Everyday example
  {
    const slide = newSlide(presentation);
    header(slide, 3, "生活例子", "一个每天都在发生的例子");
    const panels = [
      ["车在 A 区", "服务也在 A 区。\n车离服务器很近，\n导航和视频响应很快。"],
      ["车开到 B 区", "无线已经连到 B 区，\n但服务仍留在 A 区。\n数据要绕更远的路。"],
      ["服务搬到 B 区", "服务重新变近。\n但搬家要传数据、\n占用网络，还会短暂停顿。"],
    ];
    const shapes = [];
    panels.forEach(([title, body], i) => {
      const left = 72 + i * 384;
      shapes.push(addPanel(slide, left, 196, 320, 176, C.paper, C.rule));
      addText(slide, {
        left: left + 24,
        top: 218,
        width: 272,
        height: 30,
        text: title,
        size: 19,
        bold: true,
        color: i === 2 ? C.teal : C.ink,
      });
      addText(slide, {
        left: left + 24,
        top: 264,
        width: 272,
        height: 84,
        text: body,
        size: 15,
        color: C.muted,
        lineSpacing: 1.38,
      });
    });
    addArrow(slide, 392, 282, 48, 1);
    addArrow(slide, 776, 282, 48, 1);
    addText(slide, {
      left: 72,
      top: 416,
      width: 545,
      height: 112,
      text:
        "服务不是一个空壳。\n视频要知道播放到第几分钟；导航要知道目的地和当前路线；交通分析还要保留近期统计。",
      size: 16.5,
      lineSpacing: 1.42,
    });
    addText(slide, {
      left: 660,
      top: 416,
      width: 548,
      height: 112,
      text:
        "这些“记住上次做到哪里”的数据叫状态。\n迁移不是把程序再安装一遍，而是让新节点接过同一份工作，并接着原来的进度继续。",
      size: 16.5,
      lineSpacing: 1.42,
      color: C.muted,
    });
    takeaway(slide, "服务迁移 = 把程序、状态和继续工作的能力一起交给新节点。");
    pageNumber(slide, 3);
    addNotes(
      slide,
      "先用一个生活例子。车在 A 区时，服务也在 A 区，离得近。车开到 B 区以后，无线网络已经换了，但如果服务器还在 A 区，请求就要绕远路。把服务搬到 B 区可以重新变近，可搬家要传数据。关键点是：服务有自己的记忆，包括视频进度、导航路线和缓存。迁移要保证新节点能接着做，而不只是把程序启动起来。"
    );
  }

  // 4. Cloud vs edge
  {
    const slide = newSlide(presentation);
    header(slide, 4, "背景知识", "移动边缘计算（MEC）把计算放到离用户更近的地方");
    addPanel(slide, 72, 194, 500, 240, C.paper, C.rule);
    addText(slide, {
      left: 98,
      top: 216,
      width: 448,
      height: 30,
      text: "云计算",
      size: 22,
      bold: true,
    });
    addText(slide, {
      left: 98,
      top: 260,
      width: 448,
      height: 130,
      text:
        "可以想成城市外的大仓库。\n资源多、成本低，适合长期保存和大规模计算。\n但用户发出的请求要经过更长的网络路径。",
      size: 16,
      color: C.muted,
      lineSpacing: 1.42,
    });
    addText(slide, {
      left: 476,
      top: 220,
      width: 70,
      height: 22,
      text: "远 · 慢",
      size: 11.5,
      bold: true,
      color: C.muted,
      align: "right",
    });
    addPanel(slide, 700, 194, 508, 240, C.tealSoft, C.teal);
    addText(slide, {
      left: 726,
      top: 216,
      width: 456,
      height: 30,
      text: "边缘计算",
      size: 22,
      bold: true,
      color: C.teal,
    });
    addText(slide, {
      left: 726,
      top: 260,
      width: 456,
      height: 130,
      text:
        "可以想成每个街区旁边的小仓库。\n每个仓库不大，但离用户很近。\n导航、告警这类要求快速响应的服务更适合放在这里。",
      size: 16,
      lineSpacing: 1.42,
    });
    addText(slide, {
      left: 1124,
      top: 220,
      width: 60,
      height: 22,
      text: "近 · 快",
      size: 11.5,
      bold: true,
      color: C.teal,
      align: "right",
    });
    addPanel(slide, 72, 466, 1136, 84, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 96,
      top: 485,
      width: 1088,
      height: 46,
      text:
        "但“近”不是免费的：每个边缘节点容量有限，服务不能同时在所有节点完整运行。车一移动，服务就可能需要换地方。",
      size: 17,
      lineSpacing: 1.35,
    });
    takeaway(slide, "边缘计算用“近”换“快”，代价是用户移动时服务要跟着移动。");
    pageNumber(slide, 4);
    addNotes(
      slide,
      "边缘计算可以理解成把云计算的一小部分能力放到离用户很近的位置。离得近，网络往返时间短，适合导航、告警和实时视频。但是每个边缘节点容量有限，不可能把所有服务都复制到所有地方。因此车一移动，就可能需要把服务从原来的节点交给新节点。这正是本课题要解决的问题。"
    );
  }

  // 5. Cell anatomy
  {
    const slide = newSlide(presentation);
    header(slide, 5, "背景知识", "cell 是一片服务区域，而不是一个孤立的基站");
    addPanel(slide, 72, 188, 620, 354, "#FBFBF8", C.teal, 2);
    addText(slide, {
      left: 96,
      top: 207,
      width: 510,
      height: 28,
      text: "一个 cell 的简化组成",
      size: 18,
      bold: true,
      color: C.teal,
    });
    const labels = [
      ["基站 gNB", "负责车辆的无线接入，也就是车和网络之间的第一段连接。"],
      ["交换机", "把本地流量送进更方便的边缘服务器，也连接不同节点。"],
      ["边缘服务器", "真正运行导航、视频和告警服务，并保存服务状态。"],
    ];
    labels.forEach(([title, body], i) => {
      const top = 252 + i * 86;
      addPanel(slide, 106, top, 354, 64, C.paper, C.rule);
      addText(slide, {
        left: 124,
        top: top + 10,
        width: 318,
        height: 22,
        text: title,
        size: 16.5,
        bold: true,
      });
      addText(slide, {
        left: 124,
        top: top + 35,
        width: 318,
        height: 22,
        text: body,
        size: 11.5,
        color: C.muted,
      });
    });
    addText(slide, {
      left: 505,
      top: 255,
      width: 54,
      height: 22,
      text: "车辆",
      size: 15,
      bold: true,
      align: "center",
    });
    addCircle(slide, 530, 302, 10, C.teal);
    addText(slide, {
      left: 468,
      top: 326,
      width: 132,
      height: 40,
      text: "无线连接\n到本 cell",
      size: 11,
      color: C.muted,
      align: "center",
    });
    addText(slide, {
      left: 730,
      top: 194,
      width: 478,
      height: 30,
      text: "仿真里为什么要抽象成 cell",
      size: 20,
      bold: true,
    });
    addText(slide, {
      left: 730,
      top: 240,
      width: 478,
      height: 238,
      text:
        "第一，仿真关心的是“服务应该归哪个节点管”，不需要复现每一根天线和每一条街道。\n\n第二，真实数据提供的是基站位置和车辆经过的区域，cell 正好能把二维移动和计算节点对应起来。\n\n第三，抽象后可以清楚区分车辆的移动图和节点之间的网络图，后面才能单独测带宽和路由的影响。",
      size: 15.2,
      color: C.muted,
      lineSpacing: 1.42,
    });
    addText(slide, {
      left: 730,
      top: 492,
      width: 478,
      height: 40,
      text: "所以：cell = 服务区域 + 无线接入 + 网络连接 + 边缘服务器。",
      size: 14,
      bold: true,
      color: C.teal,
    });
    takeaway(slide, "cell 是仿真中的服务归属单元，不等同于只画一个基站图标。");
    pageNumber(slide, 5);
    addNotes(
      slide,
      "这一页解释 cell。真实网络由基站、回传网络、核心网和服务器共同组成。仿真不可能把所有硬件都画出来，因此我们把一片服务区域、一个无线接入点、连到边缘服务器的网络路径合在一起，抽象成一个 cell。这样车辆经过哪个区域，就对应到哪个服务节点。这个抽象不会改变核心问题，反而让问题边界更清楚。"
    );
  }

  // 6. Mobility graph vs network graph
  {
    const slide = newSlide(presentation);
    header(slide, 6, "系统模型", "车辆走哪条路，和网络怎么连，是两张图");
    const x0 = 68;
    const y0 = 204;
    const cw = 82;
    const ch = 70;
    const gap = 12;
    const rows = 3;
    const cols = 4;
    const pos = (r, c) => ({
      left: x0 + c * (cw + gap),
      top: y0 + r * (ch + gap),
    });
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        const p = pos(r, c);
        addPanel(slide, p.left, p.top, cw, ch, C.paper, C.rule);
        addText(slide, {
          left: p.left + 10,
          top: p.top + 8,
          width: 60,
          height: 16,
          text: "cell",
          size: 9,
          bold: true,
          color: C.muted,
        });
        addCircle(slide, p.left + 10, p.top + 32, 7, C.teal);
        addPanel(slide, p.left + cw - 34, p.top + ch - 22, 25, 13, C.tealSoft, C.teal, 1);
        addText(slide, {
          left: p.left + cw - 33,
          top: p.top + ch - 21,
          width: 24,
          height: 10,
          text: "edge",
          size: 6.5,
          color: C.teal,
          align: "center",
        });
        if (c < cols - 1) {
          addRule(slide, p.left + cw, p.top + ch / 2, gap, 1, "#BDBDB5");
        }
        if (r < rows - 1) {
          addRule(slide, p.left + cw / 2, p.top + ch, 1, gap, "#BDBDB5");
        }
      }
    }
    const route = [
      [2, 0],
      [2, 1],
      [1, 1],
      [1, 2],
      [0, 2],
      [0, 3],
    ];
    for (let i = 0; i < route.length - 1; i += 1) {
      const a = pos(route[i][0], route[i][1]);
      const b = pos(route[i + 1][0], route[i + 1][1]);
      const ax = a.left + 41;
      const ay = a.top + 41;
      const bx = b.left + 41;
      const by = b.top + 41;
      addRule(
        slide,
        Math.min(ax, bx),
        Math.min(ay, by),
        Math.abs(ax - bx) || 2,
        Math.abs(ay - by) || 2,
        "#7AA7A2"
      );
    }
    route.forEach(([r, c], i) => {
      const p = pos(r, c);
      addCircle(slide, p.left + 36, p.top + 36, i === route.length - 1 ? 12 : 10, i === route.length - 1 ? C.rust : C.teal);
    });
    addText(slide, {
      left: 68,
      top: 456,
      width: 420,
      height: 24,
      text: "青色圆点：车辆实际经过的 cell",
      size: 12,
      color: C.muted,
    });
    addText(slide, {
      left: 68,
      top: 482,
      width: 420,
      height: 24,
      text: "灰线：网络节点之间允许的四方向连接",
      size: 12,
      color: C.muted,
    });
    addText(slide, {
      left: 540,
      top: 194,
      width: 668,
      height: 30,
      text: "为什么要分成两张图",
      size: 20,
      bold: true,
    });
    addText(slide, {
      left: 540,
      top: 240,
      width: 668,
      height: 198,
      text:
        "移动图回答：车下一秒会去哪个 cell，服务要迁到哪里。\n\n网络图回答：两个服务器之间有哪些链路，迁移要走几跳，链路有多快。\n\n车辆在真实道路上可以斜着走，但仿真中的网络只在上下左右相邻的节点之间连边。4 连通是对网络路由的简化，不是限制车辆轨迹。",
      size: 15.3,
      color: C.muted,
      lineSpacing: 1.42,
    });
    addPanel(slide, 540, 456, 668, 76, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 562,
      top: 471,
      width: 624,
      height: 48,
      text:
        "DATA7 使用 30 个真实 gNB 位置；SF 和 Rome 使用 16×16 的服务归属网格。不同数据集不是严格同尺度的对照。",
      size: 13.5,
      lineSpacing: 1.3,
    });
    takeaway(slide, "车辆轨迹提供移动序列，网络图决定迁移路径和传输成本。");
    pageNumber(slide, 6);
    addNotes(
      slide,
      "这里要特别消除一个误解。车辆轨迹和网络拓扑不是同一张图。车辆可以沿着任意真实道路走，我们只需要把每一秒的位置映射到它所在的 cell。网络图则说明边缘服务器之间哪些链相连、一条迁移要经过几跳。数据库里有真实轨迹时，轨迹形状不会被网格限制。四连通只是网络路由的简化。"
    );
  }

  // 7. Handover vs migration
  {
    const slide = newSlide(presentation);
    header(slide, 7, "核心概念", "同一次跨区移动里，实际发生了两个动作");
    addPanel(slide, 72, 202, 300, 224, C.paper, C.teal, 2);
    addText(slide, {
      left: 96,
      top: 222,
      width: 252,
      height: 28,
      text: "cell A",
      size: 19,
      bold: true,
      color: C.teal,
    });
    addText(slide, {
      left: 96,
      top: 270,
      width: 252,
      height: 112,
      text: "基站 A\n边缘服务器 A\n服务状态仍在 A",
      size: 15.5,
      lineSpacing: 1.55,
      color: C.muted,
    });
    addPanel(slide, 620, 202, 300, 224, C.paper, C.rust, 2);
    addText(slide, {
      left: 644,
      top: 222,
      width: 252,
      height: 28,
      text: "cell B",
      size: 19,
      bold: true,
      color: C.rust,
    });
    addText(slide, {
      left: 644,
      top: 270,
      width: 252,
      height: 112,
      text: "基站 B\n边缘服务器 B\n需要接手服务和状态",
      size: 15.5,
      lineSpacing: 1.55,
      color: C.muted,
    });
    addText(slide, {
      left: 418,
      top: 224,
      width: 156,
      height: 24,
      text: "无线连接变化",
      size: 13,
      bold: true,
      color: C.teal,
      align: "center",
    });
    addArrow(slide, 390, 258, 212, 1, C.teal);
    addText(slide, {
      left: 392,
      top: 274,
      width: 208,
      height: 52,
      text: "handover\n车辆从 A 的基站切到 B 的基站",
      size: 12,
      color: C.teal,
      align: "center",
      lineSpacing: 1.3,
    });
    addText(slide, {
      left: 418,
      top: 338,
      width: 156,
      height: 24,
      text: "服务归属变化",
      size: 13,
      bold: true,
      color: C.rust,
      align: "center",
    });
    addArrow(slide, 390, 372, 212, 1, C.rust);
    addText(slide, {
      left: 392,
      top: 388,
      width: 208,
      height: 52,
      text: "migration\n服务和状态从 A 的服务器搬到 B",
      size: 12,
      color: C.rust,
      align: "center",
      lineSpacing: 1.3,
    });
    addPanel(slide, 72, 460, 848, 94, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 96,
      top: 478,
      width: 800,
      height: 58,
      text:
        "这两件事可以不同步。车已经连到 B，但服务状态还在 A，就会出现“网络换了、服务没跟上”的窗口。用户看到卡顿或失败，本质上就是服务连续性被破坏。",
      size: 16,
      lineSpacing: 1.4,
    });
    addText(slide, {
      left: 952,
      top: 470,
      width: 256,
      height: 72,
      text: "我们分别记录\nhandover 与 migration，\n避免把两个时间点混为一谈。",
      size: 13.5,
      color: C.muted,
      lineSpacing: 1.35,
    });
    takeaway(slide, "handover 是“车换基站”，migration 是“服务换服务器”。");
    pageNumber(slide, 7);
    addNotes(
      slide,
      "车跨过区域时，第一件事是无线连接从 A 的基站切到 B 的基站，这叫 handover。第二件事才是服务和状态从 A 的服务器搬到 B，这叫 migration。两者可以不同步。最坏情况是车已经在 B，导航请求也发到了 B，但 B 还没有状态，只能等或回退到 A。用户感受到的中断就是从这个不同步窗口来的。"
    );
  }

  // 8. Migration timeline
  {
    const slide = newSlide(presentation);
    header(slide, 8, "核心概念", "一次迁移包含四个阶段，中断只出现在后半段");
    const barLeft = 82;
    const barTop = 226;
    const widths = [238, 272, 160, 332];
    const labels = [
      ["1  建立快照", "确定要从源节点搬哪些状态。"],
      ["2  批量传输", "源节点继续服务，后台把主体数据送过去。"],
      ["3  最后切换", "短暂停止服务，冻结最后的小变化。"],
      ["4  应用与恢复", "目标节点装载状态、重启组件，真正接手。"],
    ];
    let cursor = barLeft;
    widths.forEach((w, i) => {
      addRule(slide, cursor, barTop, w, 54, i === 2 || i === 3 ? C.rust : C.teal);
      addText(slide, {
        left: cursor + 12,
        top: barTop + 14,
        width: w - 24,
        height: 30,
        text: labels[i][0],
        size: 14,
        bold: true,
        color: C.white,
        align: "center",
      });
      addText(slide, {
        left: cursor,
        top: barTop + 72,
        width: w - 12,
        height: 74,
        text: labels[i][1],
        size: 13,
        color: C.muted,
        lineSpacing: 1.35,
      });
      cursor += w;
    });
    addText(slide, {
      left: 82,
      top: 382,
      width: 220,
      height: 28,
      text: "用户侧是否可用",
      size: 15,
      bold: true,
    });
    addRule(slide, 82, 420, 510, 30, C.tealSoft);
    addText(slide, {
      left: 104,
      top: 425,
      width: 466,
      height: 20,
      text: "源节点继续提供服务",
      size: 13,
      bold: true,
      color: C.teal,
      align: "center",
    });
    addRule(slide, 592, 420, 492, 30, C.rustSoft);
    addText(slide, {
      left: 614,
      top: 425,
      width: 448,
      height: 20,
      text: "最后切换 + 恢复：不可用窗口",
      size: 13,
      bold: true,
      color: C.rust,
      align: "center",
    });
    addText(slide, {
      left: 82,
      top: 470,
      width: 530,
      height: 92,
      text:
        "所以在预复制（pre-copy）方案里，批量传输并不会让服务马上停掉。真正的中断来自最后冻结数据和目标节点恢复。仿真把这一刻计为最后切换，并把恢复时间继续计入不可用窗口。",
      size: 15.5,
      lineSpacing: 1.42,
    });
    addPanel(slide, 650, 470, 558, 92, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 672,
      top: 486,
      width: 514,
      height: 60,
      text:
        "为什么不在传输期间直接让两边都接请求？因为两边会同时修改状态，产生冲突。最后切换就是保证只有一个“正式版本”的边界。",
      size: 14.4,
      lineSpacing: 1.38,
    });
    takeaway(slide, "预复制（pre-copy）减少中断，但最后切换和恢复仍然要付出用户等待。");
    pageNumber(slide, 8);
    addNotes(
      slide,
      "这页回答之前一个疑问：源节点在批量传输时不是还在服务吗，为什么还会有中断。答案是批量传输阶段确实可以继续服务，但传完以后必须冻结最后的小变化，再把状态交给目标节点并恢复组件。这个最后窗口是一次性的，通常比整份状态全程停机短，但不能消失。我们统计的中断就是用户无法正常获得服务的那些秒。"
    );
  }

  // 9. State
  {
    const slide = newSlide(presentation);
    header(slide, 9, "状态模型", "服务状态是“继续工作的记忆”，不只是日志文件");
    addText(slide, {
      left: 72,
      top: 188,
      width: 460,
      height: 200,
      text:
        "如果把服务理解成一个人：\n\n程序代码像这个人的技能，镜像像工作手册；状态像他刚才做到哪里、已经处理了哪些请求、桌面上摆着什么材料。\n\n换一个工位后，只把工作手册拿过去还不够，还要把当前进度也带过去。",
      size: 16.3,
      lineSpacing: 1.48,
    });
    addPanel(slide, 576, 194, 632, 278, C.paper, C.rule);
    addText(slide, {
      left: 600,
      top: 214,
      width: 584,
      height: 28,
      text: "仿真中每类服务都保存三类内容",
      size: 18,
      bold: true,
    });
    const rows = [
      ["会话状态", "当前进度和上下文，例如播放位置、路线、聚合窗口。"],
      ["增长状态", "服务运行越久，状态会按配置持续增长。"],
      ["程序镜像", "只读的运行环境。目标节点没缓存时才需要拉取。"],
    ];
    rows.forEach(([title, body], i) => {
      const top = 260 + i * 62;
      addText(slide, {
        left: 602,
        top,
        width: 120,
        height: 24,
        text: title,
        size: 14,
        bold: true,
        color: C.teal,
      });
      addText(slide, {
        left: 730,
        top,
        width: 450,
        height: 42,
        text: body,
        size: 14,
        color: C.muted,
      });
      addRule(slide, 602, top + 48, 578, 1, C.rule);
    });
    addPanel(slide, 72, 426, 1136, 122, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 96,
      top: 444,
      width: 1088,
      height: 78,
      text:
        "这也解释了为什么“状态大小”不能只写一个固定数字。状态会随运行时间增长；同一服务在不同数据集上的停留时间不同，最后一次同步之后积累的变化也不同。仿真把这些变化按秒累加，再用 base 计算增量。",
      size: 16,
      lineSpacing: 1.42,
    });
    takeaway(slide, "只搬程序镜像不够，能把用户正在进行的会话接过去才算迁移完成。");
    pageNumber(slide, 9);
    addNotes(
      slide,
      "状态不是普通的日志。日志主要供事后查看，状态是服务继续工作必须依赖的上下文。比如视频要知道播放位置，导航要知道目的地和已经算出的路线，交通分析要知道统计窗口。镜像则是程序运行环境，通常可以共享缓存。状态会随时间增长，所以迁移大小不是一个固定常数。"
    );
  }

  // 10. Four services
  {
    const slide = newSlide(presentation);
    header(slide, 10, "服务模型", "四类 MEC 服务：用户怎么用，数据怎么流动");
    addTable(slide, {
      left: 72,
      top: 186,
      width: 1136,
      height: 352,
      columnWidths: [150, 280, 310, 396],
      rowHeight: 70.4,
      fontSize: 12.4,
      alignLeftColumns: [0, 1, 2, 3],
      values: [
        ["服务", "用户与终端做什么", "边缘侧算什么，返回什么", "必须保留的状态"],
        [
          "导航",
          "车辆发送位置、速度、航向和目的地。",
          "结合路况重新规划路径，返回下一步路线和提示。",
          "目的地、当前路线、最近一次规划结果。",
        ],
        [
          "信息娱乐",
          "乘客选择内容，终端报告播放进度和清晰度。",
          "选片、转码、缓存，返回视频或音频数据块。",
          "播放位置、码率、缓冲区、个性化列表。",
        ],
        [
          "上下文告警",
          "车辆上传传感器、车速、附近事件等遥测。",
          "匹配区域规则，返回碰撞、限速或风险告警。",
          "最近的事件上下文和已触发规则，状态最小。",
        ],
        [
          "实时交通分析",
          "多辆车上传探针、雷达和路段观测。",
          "按时间和空间聚合，返回拥堵图或预测结果。",
          "滑动窗口、局部模型和近期聚合数据。",
        ],
      ],
    });
    addText(slide, {
      left: 72,
      top: 556,
      width: 1136,
      height: 34,
      text:
        "这四类服务覆盖了不同状态规模：告警很小，导航较小，交通分析中等，信息娱乐最大。参数是代表性设定，不是运营商实测分布。",
      size: 14.5,
      color: C.muted,
    });
    takeaway(slide, "迁移研究的对象不是“一个应用”，而是一组状态规模差异很大的服务。");
    pageNumber(slide, 10);
    addNotes(
      slide,
      "四类服务不是四个随便写的名字。导航接收位置和目的地，在边缘重新算路，再把下一步路线返回。信息娱乐要保存播放位置和缓冲数据，通常状态最大。告警接收传感器，在边缘做规则匹配，状态很小。实时交通分析把很多车的数据聚合成拥堵图。它们的状态大小差两个数量级，所以不能用同一个迁移策略一刀切。"
    );
  }

  // 11. Service size consequences
  {
    const slide = newSlide(presentation);
    header(slide, 11, "服务模型", "服务大小不同，优化重点也不同");
    addTable(slide, {
      left: 72,
      top: 188,
      width: 1136,
      height: 300,
      columnWidths: [190, 190, 190, 566],
      rowHeight: 60,
      fontSize: 13,
      alignLeftColumns: [0, 3],
      values: [
        ["服务", "初始状态", "镜像大小", "这个服务最值得优化什么"],
        ["导航", "5 MB", "370 MB", "镜像预热；状态很小，重点通常是让目标节点提前有运行环境。"],
        ["信息娱乐", "200 MB", "540 MB", "大状态分块、压缩和增量传输；很可能主导总迁移字节。"],
        ["上下文告警", "3 MB", "205 MB", "尽量避免为很小的状态付出完整启停成本。"],
        ["交通分析", "80 MB", "295 MB", "共享区域模型，减少多辆车重复搬运相同数据。"],
      ],
    });
    addPanel(slide, 72, 516, 552, 64, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 94,
      top: 530,
      width: 508,
      height: 34,
      text: "同一个优化不会对所有服务同样有效。",
      size: 16,
      bold: true,
      color: C.teal,
    });
    addPanel(slide, 656, 516, 552, 64, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 678,
      top: 530,
      width: 508,
      height: 34,
      text: "因此实验必须报告每服务指标，不能只看总量。",
      size: 16,
      bold: true,
    });
    takeaway(slide, "系统的“平均值”可能掩盖某一个大状态服务造成的绝大部分成本。");
    pageNumber(slide, 11);
    addNotes(
      slide,
      "这张表强调服务之间的差异。导航的状态很小，但镜像比较大，所以镜像预热很重要。信息娱乐状态最大，往往是总迁移字节的主要来源。告警状态非常小，为它做复杂迁移可能不划算。交通分析适合共享区域模型。后面实验会单独看每个服务的中断和字节，而不是只看总平均。"
    );
  }

  // 12. Base delta restore
  {
    const slide = newSlide(presentation);
    header(slide, 12, "状态迁移优化", "base、delta 和 restore 是三种不同的成本");
    const boxes = [
      ["base", "目标节点以前保存的完整快照", "像一份旧底稿", C.paper, C.rule],
      ["delta", "从底稿到现在发生变化的部分", "像只交修改页", C.tealSoft, C.teal],
      ["restore", "目标节点读取状态并恢复服务", "像在新工位重新摆好桌面", C.rustSoft, C.rust],
    ];
    boxes.forEach(([title, body, analogy, fill, line], i) => {
      const left = 72 + i * 384;
      addPanel(slide, left, 192, 320, 138, fill, line, 1.5);
      addText(slide, {
        left: left + 22,
        top: 210,
        width: 276,
        height: 28,
        text: title,
        size: 20,
        bold: true,
        color: line === C.rule ? C.ink : line,
      });
      addText(slide, {
        left: left + 22,
        top: 248,
        width: 276,
        height: 38,
        text: body,
        size: 14.2,
      });
      addText(slide, {
        left: left + 22,
        top: 294,
        width: 276,
        height: 22,
        text: analogy,
        size: 12,
        color: C.muted,
      });
    });
    addArrow(slide, 392, 258, 48, 1);
    addArrow(slide, 776, 258, 48, 1);
    addText(slide, {
      left: 72,
      top: 360,
      width: 1136,
      height: 28,
      text: "仿真中的 base 不是预制常量，而是随服务移动不断更新的每节点快照。",
      size: 17,
      bold: true,
      color: C.teal,
    });
    const origins = [
      ["1  初始节点", "服务一开始所在的节点保存初始状态。"],
      ["2  离开节点", "服务迁走后，旧节点保留离开时的快照。"],
      ["3  新节点接手", "迁移完成后，目标节点把它收到的状态作为新 base。"],
    ];
    origins.forEach(([title, body], i) => {
      const left = 72 + i * 384;
      addRule(slide, left, 410, 330, 1, C.rule);
      addText(slide, {
        left,
        top: 426,
        width: 330,
        height: 26,
        text: title,
        size: 15,
        bold: true,
      });
      addText(slide, {
        left,
        top: 460,
        width: 330,
        height: 70,
        text: body,
        size: 13.6,
        color: C.muted,
        lineSpacing: 1.35,
      });
    });
    addText(slide, {
      left: 72,
      top: 548,
      width: 1136,
      height: 34,
      text: "恢复成本按 5 ms/MB 计入：每传 1 MB，目标节点还要多花约 5 ms 应用到可运行状态。",
      size: 14.2,
      color: C.muted,
    });
    takeaway(slide, "增量减少的是 delta 和恢复，不等于网络传输免费；base 本身也有放置与维护成本。");
    pageNumber(slide, 12);
    addNotes(
      slide,
      "base 可以理解成旧底稿，delta 是最近修改的内容。目标节点如果以前保存过这个服务的 base，只需要传修改部分；如果没有，就只能传完整状态。迁移完成以后还要恢复，恢复时间按传输量线性估算。base 不是凭空出现的，我们记录三类来源：初始节点、服务离开时旧节点留下的快照，以及迁移完成后目标节点更新的快照。"
    );
  }

  // 13. Cold target
  {
    const slide = newSlide(presentation);
    header(slide, 13, "状态迁移优化", "目标节点没有 base 时，增量会退化成全量");
    addPanel(slide, 72, 196, 536, 238, C.tealSoft, C.teal, 1.5);
    addText(slide, {
      left: 96,
      top: 216,
      width: 488,
      height: 28,
      text: "情况 A：目标节点已有 base",
      size: 19,
      bold: true,
      color: C.teal,
    });
    addText(slide, {
      left: 96,
      top: 262,
      width: 488,
      height: 118,
      text:
        "当前状态 = 完整快照 + 最近发生的变化\n\n只传“最近变化”这一小块。\n数据少，传输和恢复通常都更快。",
      size: 15.5,
      lineSpacing: 1.42,
    });
    addPanel(slide, 672, 196, 536, 238, C.rustSoft, C.rust, 1.5);
    addText(slide, {
      left: 696,
      top: 216,
      width: 488,
      height: 28,
      text: "情况 B：目标节点是 cold target",
      size: 19,
      bold: true,
      color: C.rust,
    });
    addText(slide, {
      left: 696,
      top: 262,
      width: 488,
      height: 118,
      text:
        "目标节点没有旧底稿，只剩“当前状态”可传。\n\n只能传完整状态。\n即使策略名字叫增量，这一次也会接近全量迁移。",
      size: 15.5,
      lineSpacing: 1.42,
    });
    addPanel(slide, 72, 452, 1136, 110, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 96,
      top: 466,
      width: 1088,
      height: 80,
      text:
        "所以，增量迁移的核心并不是压缩算法，而是 base 的位置：\n服务经常回到哪些节点，哪些节点最容易提前保存快照。\n这个结论直接连到存储系统里的放置、缓存和复制问题。",
      size: 16,
      lineSpacing: 1.32,
    });
    takeaway(slide, "delta 的收益取决于“目标节点以前有没有见过这个服务”。");
    pageNumber(slide, 13);
    addNotes(
      slide,
      "cold target 是目标节点没有 base 的情况。此时增量策略没有旧底稿可以比较，只能发送完整状态。所以同一个“增量迁移”算法，在不同移动轨迹上收益会差很多。如果车辆总在城市里循环，同一个节点可能以前见过这个服务，增量就便宜；如果车辆总去新区域，目标节点经常是冷的，增量就接近全量。这自然把问题连接到存储系统里的数据放置和缓存。"
    );
  }

  // 14. Overhead taxonomy
  {
    const slide = newSlide(presentation);
    header(slide, 14, "指标设计", "迁移开销有四层，不能只看搬了多少 GB");
    const items = [
      ["数据量", "搬了多少 MB 或 GB", "像箱子总重量", C.teal],
      ["带宽-时间", "占用链路多久，也就是“占用率 × 时间”", "像电梯被占用了几分钟", C.amber],
      ["恢复", "到了新节点后整理、装载、重启多久", "像到新工位重新摆货", C.rust],
      ["用户侧", "用户多久没有服务，或到达后还要等多久", "像顾客排队时间", C.green],
    ];
    items.forEach(([title, body, analogy, color], i) => {
      const top = 184 + i * 82;
      addText(slide, {
        left: 72,
        top,
        width: 170,
        height: 32,
        text: title,
        size: 19,
        bold: true,
        color,
      });
      addText(slide, {
        left: 258,
        top: top + 3,
        width: 560,
        height: 34,
        text: body,
        size: 15.5,
      });
      addText(slide, {
        left: 846,
        top: top + 4,
        width: 362,
        height: 30,
        text: analogy,
        size: 13.2,
        color: C.muted,
      });
      addRule(slide, 72, top + 56, 1136, 1, C.rule);
    });
    addPanel(slide, 72, 516, 1136, 64, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 96,
      top: 530,
      width: 1088,
      height: 34,
      text: "开销比 = 迁移产生的总字节 ÷ 同期服务真正返回给用户的业务字节。",
      size: 16.2,
      bold: true,
      color: C.teal,
    });
    takeaway(slide, "相同的 GB，占用 10 秒和占用 100 秒，对系统的影响完全不同。");
    pageNumber(slide, 14);
    addNotes(
      slide,
      "迁移开销不能只看总字节。第一层是搬了多少数据。第二层是这些数据占用了链路多长时间，可以用带宽乘持续时间衡量。第三层是目标节点恢复要多久。第四层是用户实际等了多久。开销比是迁移字节和服务业务字节的比例，它适合比较不同服务规模，但仍然不能代替时间指标。"
    );
  }

  // 15. Metrics table
  {
    const slide = newSlide(presentation);
    header(slide, 15, "指标设计", "七个观察指标分别回答一个具体问题");
    addTable(slide, {
      left: 72,
      top: 184,
      width: 1136,
      height: 382,
      columnWidths: [230, 580, 326],
      rowHeight: 47.75,
      fontSize: 11.8,
      alignLeftColumns: [0, 1, 2],
      values: [
        ["指标", "怎么定义", "它回答什么问题"],
        ["每服务中断率", "该服务不可用的车辆秒数 ÷ 该服务全部车辆秒数。", "用户受影响的范围有多大？"],
        ["切换前就绪率", "迁移在对应 handover 之前完成的次数 ÷ 迁移总次数。", "预迁移是不是真的赶上了？"],
        ["到达后滞后", "handover 完成后，又经过多少步迁移才完成。", "车到了以后还要等多久？"],
        ["迁移提前量", "迁移开始步 − handover 步。负数表示提前开始。", "什么时候发起迁移？"],
        ["迁移字节", "状态、缺失镜像和其它同步产生的总字节。", "传输成本有多高？"],
        ["迁移时长 ÷ 停留时间", "一次迁移耗时 ÷ 车辆在该 cell 停留时长。", "还没搬完，车是不是又要走了？"],
        ["冗余迁移率", "未完成就反向迁移，或到达下一格后才完成的迁移占比。", "有没有做无用功？"],
      ],
    });
    addText(slide, {
      left: 72,
      top: 572,
      width: 1136,
      height: 30,
      text: "总中断率在一辆车有多个服务时，只要至少一个服务不可用，就记这一秒为中断。",
      size: 13.8,
      color: C.muted,
    });
    takeaway(slide, "这组指标把“快”“省”“稳”拆开，避免一个平均数掩盖问题。");
    pageNumber(slide, 15);
    addNotes(
      slide,
      "这张表是后面对照实验的读表规则。每服务中断率告诉我们是哪个服务影响用户。切换前就绪率告诉我们应该提前做的迁移有没有赶上。到达后滞后告诉用户还要等多久。迁移提前量描述策略什么时候开始。迁移字节描述搬了多少。迁移时长除以停留时间描述是否追不上车。冗余迁移描述是否做了无效往返。"
    );
  }

  // 16. Simulator loop
  {
    const simSlide = newSlide(presentation);
    header(simSlide, 16, "仿真实现", "仿真每秒做一次判断，最后把所有事件记成指标");
    const steps = [
      ["读轨迹", "读取每辆车这一秒的位置，映射到所属 cell。"],
      ["查切换", "如果所属 cell 变了，记录一次 handover。"],
      ["选迁移", "根据策略决定哪些服务迁移、迁到哪个节点。"],
      ["搬状态", "拉取缺失镜像、传状态，并计算恢复和不可用窗口。"],
      ["记指标", "每秒记录延迟、可用性、链路占用和迁移进度。"],
    ];
    let cursor = 72;
    steps.forEach(([title, body], i) => {
      addPanel(simSlide, cursor, 200, 202, 174, i === 0 ? C.tealSoft : C.paper, i === 0 ? C.teal : C.rule);
      addText(simSlide, {
        left: cursor + 18,
        top: 218,
        width: 166,
        height: 26,
        text: `${i + 1}  ${title}`,
        size: 17,
        bold: true,
        color: i === 0 ? C.teal : C.ink,
      });
      addText(simSlide, {
        left: cursor + 18,
        top: 258,
        width: 166,
        height: 90,
        text: body,
        size: 13.2,
        color: C.muted,
        lineSpacing: 1.35,
      });
      if (i < steps.length - 1) addArrow(simSlide, cursor + 204, 278, 22, 1);
      cursor += 226;
    });
    addText(simSlide, {
      left: 72,
      top: 408,
      width: 548,
      height: 128,
      text:
        "EdgeSimPy 负责离散时间推进、服务器资源、链路容量、网络时延和流调度。我们的控制器负责车辆移动后的 handover、服务选择、base 管理和迁移状态机。",
      size: 15.5,
      lineSpacing: 1.42,
    });
    addText(simSlide, {
      left: 660,
      top: 408,
      width: 548,
      height: 128,
      text:
        "每辆车的四类服务都单独记录，输出包括 handover、migration、逐秒服务状态和汇总结果。\n\n因此同一场景可以同时分析用户影响、传输成本和可观测行为。",
      size: 15.5,
      lineSpacing: 1.42,
      color: C.muted,
    });
    takeaway(simSlide, "仿真不是只算最终总量，而是保留每秒状态，才能解释结果从何而来。");
    pageNumber(simSlide, 16);
    addNotes(
      simSlide,
      "仿真每秒推进一次。先读车辆位置，映射到 cell；位置跨区就记 handover；然后控制器决定哪些服务要迁移；接着模拟镜像、状态、链路和恢复；最后记录这一秒的指标。EdgeSimPy 提供网络和资源模型，我们的代码补充了迁移控制和服务层。保存每秒数据的好处是，后续可以解释中断到底发生在什么时候、哪个服务上。"
    );
  }

  // 17. Data provenance
  {
    const slide = newSlide(presentation);
    header(slide, 17, "数据来源", "实验里哪些是真实数据，哪些是可控假设");
    addTable(slide, {
      left: 72,
      top: 190,
      width: 1136,
      height: 330,
      columnWidths: [230, 420, 486],
      rowHeight: 55,
      fontSize: 12.8,
      alignLeftColumns: [0, 1, 2],
      values: [
        ["内容", "使用方式", "需要怎样理解"],
        ["San Francisco", "真实出租车轨迹，映射到 16×16 服务网格。", "轨迹真实，网格和 cell 大小是仿真抽象。"],
        ["Rome", "真实出租车轨迹，映射到 16×16 服务网格。", "轨迹真实，网格和 cell 大小是仿真抽象。"],
        ["DATA7", "30 个真实 gNB 位置、62 条候选链路，车辆由 SUMO 生成。", "基站位置真实，不是全城真实 GPS 车流。"],
        ["服务与网络参数", "四类服务的状态/镜像大小、带宽、5 ms/MB 恢复。", "代表性假设，用来做受控比较，不是现场测量。"],
        ["链路与无线时延", "链路 5 ms/跳，无线 2 ms。", "用于仿真，结果应关注趋势和机制，不宜当作运营商 SLA。"],
      ],
    });
    addPanel(slide, 72, 542, 1136, 42, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 92,
      top: 552,
      width: 1096,
      height: 24,
      text: "当前 SF、Rome、DATA7 的 cell 尺度和数量不同，因此跨数据集结果适合看机制方向，不是严格同条件排名。",
      size: 13.4,
    });
    takeaway(slide, "真实拓扑和轨迹提供外部有效性，可控参数负责隔离变量。");
    pageNumber(slide, 17);
    addNotes(
      slide,
      "这一页特别说明数据边界。SF 和 Rome 提供了真实出租车轨迹，但服务区域网格是仿真抽象。DATA7 提供了真实基站位置和链路关系，但车辆轨迹是 SUMO 生成的，不是真实车辆 GPS。来源包括 Zenodo 10.5281/zenodo.7806928 的 DATA7，以及 San Francisco Cabspotting 和 Rome taxi 轨迹。服务大小和恢复速率是代表性假设。"
    );
  }

  // 18. Controlled experiment
  {
    const slide = newSlide(presentation);
    header(slide, 18, "实验设置", "先固定一组统一条件，再逐项改变变量");
    const values = [
      ["运行时长", "1800 秒"],
      ["车辆数", "12 辆"],
      ["每车服务数", "4 类，共 48 个服务实例"],
      ["速度", "基线 40 km/h；压力测试扫 20/40/60/90"],
      ["链路带宽", "基线 500 Mbps；压力测试扫 100 Mbps/1 Gbps"],
      ["恢复成本", "5 ms/MB"],
      ["提前量", "接近边界前 12 步触发预迁移"],
      ["中断口径", "至少一个服务不可用的车辆秒数占比"],
    ];
    addTable(slide, {
      left: 72,
      top: 190,
      width: 724,
      height: 352,
      columnWidths: [250, 474],
      rowHeight: 44,
      fontSize: 13,
      alignLeftColumns: [0, 1],
      values: [["变量", "基线设置"], ...values],
    });
    addPanel(slide, 840, 190, 368, 352, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 864,
      top: 212,
      width: 320,
      height: 30,
      text: "为什么先固定？",
      size: 18,
      bold: true,
      color: C.teal,
    });
    addText(slide, {
      left: 864,
      top: 258,
      width: 320,
      height: 248,
      text:
        "如果同时改变速度、带宽、服务规模和轨迹，就无法判断变化由谁造成。\n\n因此先做同一条件下的策略对照，再做速度、带宽和车辆数的压力矩阵。\n\n当前提前量是 12 步，后续应扫描 5/12/30/60。",
      size: 14.3,
      lineSpacing: 1.42,
    });
    takeaway(slide, "实验设计的目标是能归因，而不只是得到一张更大的结果表。");
    pageNumber(slide, 18);
    addNotes(
      slide,
      "基线实验固定 12 辆车、1800 秒和 40 公里每小时。每个服务每秒都参与可用性统计。预迁移在距离边界约 12 步时触发。为什么先固定这些？因为如果所有变量一起变，最后无法知道收益来自增量、提前量还是带宽。压力测试再单独扫速度和负载。12 步只是当前参数，正式论文里应该做提前量的敏感性分析。"
    );
  }

  // 19. Follow-me baseline
  {
    const slide = newSlide(presentation);
    header(slide, 19, "实验一", "follow-me：车到哪，服务就把全部状态搬到哪");
    const kpis = [
      ["48.8%", "车辆秒发生服务中断"],
      ["345 GB", "1800 秒累计迁移字节"],
      ["48.2×", "迁移字节 ÷ 业务字节"],
    ];
    kpis.forEach(([value, label], i) => {
      const left = 72 + i * 384;
      addText(slide, {
        left,
        top: 184,
        width: 340,
        height: 58,
        text: value,
        size: 38,
        bold: true,
        color: C.rust,
      });
      addText(slide, {
        left,
        top: 242,
        width: 340,
        height: 30,
        text: label,
        size: 13.5,
        color: C.muted,
      });
    });
    addText(slide, {
      left: 72,
      top: 292,
      width: 548,
      height: 160,
      text:
        "读法：在 12 辆车、1800 秒、500 Mbps 下，48.8% 的车辆秒至少有一个服务不可用。也就是说，接近一半的时间里，用户会感到某个服务不可用。\n\n345 GB 是迁移总字节，约为业务流量的 48 倍。\n搬服务本身已经成为主要网络负担。",
      size: 15.2,
      lineSpacing: 1.42,
    });
    addPanel(slide, 660, 292, 548, 176, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 684,
      top: 310,
      width: 500,
      height: 28,
      text: "问题出在哪里",
      size: 17,
      bold: true,
    });
    addText(slide, {
      left: 684,
      top: 348,
      width: 500,
      height: 102,
      text:
        "follow-me 只有在车切换之后才开始搬。\n\n传输、拉取镜像和恢复都发生在用户移动之后，用户必须等它完成。",
      size: 14.8,
      lineSpacing: 1.4,
    });
    addText(slide, {
      left: 72,
      top: 478,
      width: 1136,
      height: 70,
      text:
        "这不是说 follow-me 没有意义。它是文献里最直接、最容易解释的基线，回答“如果完全不做优化会怎样”。后面所有改进都要和它放在同一条件下比较。",
      size: 15.8,
      lineSpacing: 1.4,
      color: C.muted,
    });
    takeaway(slide, "最晚开始搬，能保证服务一定被发现需要搬，但无法给用户留出提前量。");
    pageNumber(slide, 19);
    addNotes(
      slide,
      "follow-me 就是车到哪、服务才搬到哪。它是很自然的基线。在这组 DATA7 条件里，48.8% 的车辆秒至少有一个服务不可用，累计迁移 345 GB，开销比 48.2 倍。为什么中断这么高？因为迁移从 handover 之后才开始，用户先到了新节点，再等迁移、镜像和恢复完成。这个结果说明优化传输和时机都有空间。"
    );
  }

  // 20. Service breakdown
  {
    const slide = newSlide(presentation);
    header(slide, 20, "实验一", "把总量拆开后，信息娱乐主导了迁移成本");
    addTable(slide, {
      left: 72,
      top: 190,
      width: 676,
      height: 300,
      columnWidths: [230, 210, 236],
      rowHeight: 60,
      fontSize: 13.2,
      values: [
        ["服务", "中断率", "迁移字节"],
        ["信息娱乐", "47.9%", "215 GB"],
        ["实时交通分析", "33.2%", "108 GB"],
        ["导航", "5.5%", "15.6 GB"],
        ["上下文告警", "4.0%", "5.7 GB"],
      ],
    });
    addPanel(slide, 780, 190, 428, 300, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 804,
      top: 212,
      width: 380,
      height: 28,
      text: "这张表如何解释",
      size: 18,
      bold: true,
      color: C.teal,
    });
    addText(slide, {
      left: 804,
      top: 254,
      width: 380,
      height: 212,
      text:
        "信息娱乐状态大，单次传输时间长，所以既贡献大量字节，也更容易在传输期间被用户感知。\n\n导航和告警状态小，虽然不代表完全无成本，但不应该和视频使用同一种全量迁移策略。\n\n这也是后面做服务级策略而不是“整车统一策略”的依据。",
      size: 14.5,
      lineSpacing: 1.42,
    });
    addText(slide, {
      left: 72,
      top: 520,
      width: 1136,
      height: 44,
      text:
        "信息娱乐一项占约 62% 的迁移字节，接近其他三类之和；把四个服务相加会发现总中断不是各服务中断的简单平均。",
      size: 15,
      color: C.muted,
      lineSpacing: 1.35,
    });
    takeaway(slide, "服务级差异是优化空间：大状态服务优先增量，小状态服务优先避免启停。");
    pageNumber(slide, 20);
    addNotes(
      slide,
      "把总量拆开后，信息娱乐迁移 215 GB，占整体约六成；交通分析 108 GB；导航和告警小很多。中断率也是信息娱乐最高。这里要解释一个容易误读的地方：总中断率不是四个服务中断率的平均值，而是一辆车只要至少一个服务不可用就算中断，所以总中断会高于告警和导航的单项中断。"
    );
  }

  // 21. Incremental across datasets
  {
    const slide = newSlide(presentation);
    header(slide, 21, "实验二", "增量迁移能省多少，取决于 base locality");
    addTable(slide, {
      left: 72,
      top: 186,
      width: 786,
      height: 298,
      columnWidths: [186, 200, 200, 200],
      rowHeight: 59.6,
      fontSize: 13,
      values: [
        ["数据", "冷目标比例", "字节节省", "中断：全量 → 增量"],
        ["DATA7", "17%", "74%", "48.8% → 11.5%"],
        ["SF", "42%", "47%", "13.2% → 4.8%"],
        ["Rome", "55%", "28%", "9.0% → 4.2%"],
        ["合成网格", "93%", "2.4%", "5.9% → 5.7%"],
      ],
    });
    addPanel(slide, 892, 186, 316, 298, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 916,
      top: 207,
      width: 268,
      height: 28,
      text: "最值得记住的对照",
      size: 17,
      bold: true,
    });
    addText(slide, {
      left: 916,
      top: 250,
      width: 268,
      height: 198,
      text:
        "DATA7 冷目标只有 17%，所以增量省 74%。\n\n合成数据冷目标 93%，增量只省 2.4%，几乎退化为全量。\n\n换了移动模式，收益就会不同。",
      size: 14.3,
      lineSpacing: 1.42,
    });
    addText(slide, {
      left: 72,
      top: 512,
      width: 1136,
      height: 54,
      text:
        "注意：四个数据集的服务区域尺度和轨迹来源不同，因此这不是严格同尺度的排名。它更适合回答“为什么增量收益不稳定”，而不是“哪个城市更好”。",
      size: 14.5,
      color: C.muted,
      lineSpacing: 1.35,
    });
    takeaway(slide, "推进量优化的正确问题不是“能省几倍”，而是“哪些目标节点经常是热的”。");
    pageNumber(slide, 21);
    addNotes(
      slide,
      "这张表是 base locality 的证据。DATA7 只有 17% 的迁移遇到冷目标，所以增量节省 74% 字节，同时中断从 48.8% 降到 11.5%。合成网格里 93% 的迁移目标都没有 base，增量只省 2.4%，几乎和全量一样。这里不能把四个城市当作严格排名，因为 cell 尺度不同。它说明的是机制：目标节点是否以前有快照，决定了增量能不能发挥作用。"
    );
  }

  // 22. Stress matrix
  {
    const slide = newSlide(presentation);
    header(slide, 22, "实验三", "速度、带宽和车辆数共同决定系统何时撑不住");
    addTable(slide, {
      left: 72,
      top: 186,
      width: 1136,
      height: 340,
      columnWidths: [286, 220, 220, 410],
      rowHeight: 56.6,
      fontSize: 12.8,
      values: [
        ["场景", "20 km/h", "90 km/h", "中断首次达到 50% 的速度"],
        ["100 Mbps / 12 车", "65.7%", "92.3%", "20 km/h"],
        ["500 Mbps / 12 车", "17.0%", "72.3%", "90 km/h"],
        ["1 Gbps / 12 车", "8.7%", "39.2%", "90 km/h 以上仍未达到"],
        ["500 Mbps / 30 车", "36.8%", "89.0%", "40 km/h"],
        ["100 Mbps / 30 车", "71.9%", "93.1%", "20 km/h"],
      ],
    });
    addText(slide, {
      left: 72,
      top: 544,
      width: 550,
      height: 48,
      text:
        "速度变快会让车更频繁跨区，也会缩短每次迁移可用的时间窗口。",
      size: 14.6,
      color: C.muted,
    });
    addText(slide, {
      left: 660,
      top: 544,
      width: 548,
      height: 48,
      text:
        "但速度不是唯一变量：带宽越低、并发车越多，同一速度下也更容易中断。",
      size: 14.6,
      color: C.muted,
    });
    takeaway(slide, "核心关系是“迁移需求 ÷ 可用容量”；速度只是把需求更快地压到一个节点上。");
    pageNumber(slide, 22);
    addNotes(
      slide,
      "压力测试同时改变带宽、车辆数和速度。100 Mbps 12 车在 20 公里每小时就已经超过一半中断；500 Mbps 12 车要到 90 公里每小时；1 Gbps 12 车到 90 仍低于一半。500 Mbps 但 30 车时，40 公里每小时就达到边界。这张表要说明的是，速度是放大器，根本上还是迁移需求超过了带宽和处理能力。"
    );
  }

  // 23. Predictors
  {
    const slide = newSlide(presentation);
    header(slide, 23, "实验四", "预测器的任务只是猜测下一个 cell");
    const items = [
      ["last-direction", "沿着车辆最近一段方向继续外推。", "简单、便宜；转弯就很容易错。"],
      ["一阶马尔可夫", "用其他车辆学到的 cell 转移概率猜下一格。", "CPU 可以训练；不需要 GPU。"],
      ["oracle", "直接读取车辆真实未来轨迹。", "实验上限，现实中不可获得。"],
    ];
    items.forEach(([title, body, note], i) => {
      const left = 72 + i * 384;
      addPanel(slide, left, 196, 320, 194, i === 2 ? C.amberSoft : C.paper, i === 2 ? "#D7B56A" : C.rule);
      addText(slide, {
        left: left + 22,
        top: 216,
        width: 276,
        height: 30,
        text: title,
        size: 18.5,
        bold: true,
        color: i === 2 ? C.amber : C.teal,
      });
      addText(slide, {
        left: left + 22,
        top: 260,
        width: 276,
        height: 54,
        text: body,
        size: 14.2,
        lineSpacing: 1.36,
      });
      addText(slide, {
        left: left + 22,
        top: 326,
        width: 276,
        height: 40,
        text: note,
        size: 12.5,
        color: C.muted,
      });
    });
    addPanel(slide, 72, 428, 1136, 118, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 96,
      top: 446,
      width: 1088,
      height: 28,
      text: "预测错了会发生什么",
      size: 16.5,
      bold: true,
      color: C.teal,
    });
    addText(slide, {
      left: 96,
      top: 480,
      width: 1088,
      height: 50,
      text:
        "服务被搬到错误节点，车辆真正到达后还要再迁一次。结果可能是中断没有完全消失，迁移字节反而增加。所以 proactive 不是天然优于 follow-me。",
      size: 15,
      lineSpacing: 1.4,
    });
    takeaway(slide, "预迁移的收益不是“提前”本身带来的，而是“提前且猜对”带来的。");
    pageNumber(slide, 23);
    addNotes(
      slide,
      "预测器只做一件事：在车还没到边界时，猜它下一个 cell。last-direction 沿最近方向外推，最便宜但转弯就错。一阶马尔可夫用历史路线学习转移概率，CPU 可以跑。oracle 是直接看真实未来，只能做上限。预测器的名字听起来高级，但判断仍然要回到两个问题：猜得准不准，猜错以后多做多少迁移。"
    );
  }

  // 24. Predictor results
  {
    const slide = newSlide(presentation);
    header(slide, 24, "实验四", "预测越差，中断仍可下降，但无谓字节会明显增加");
    addTable(slide, {
      left: 72,
      top: 186,
      width: 794,
      height: 300,
      columnWidths: [220, 150, 160, 132, 132],
      rowHeight: 60,
      fontSize: 12.3,
      values: [
        ["预测器", "准确率", "中断", "迁移数据", "到达后滞后"],
        ["oracle（上限）", "100%", "7.4%", "139 GB", "1.7 步"],
        ["一阶马尔可夫", "49%", "8.2%", "192 GB", "5.9 步"],
        ["last-direction", "21%", "9.8%", "214 GB", "10.9 步"],
        ["reactive（follow-me）", "—", "39.0%", "140 GB", "7.8 步"],
      ],
    });
    addPanel(slide, 900, 186, 308, 300, C.rustSoft, C.rust, 1);
    addText(slide, {
      left: 922,
      top: 208,
      width: 264,
      height: 26,
      text: "关键对照",
      size: 17,
      bold: true,
      color: C.rust,
    });
    addText(slide, {
      left: 922,
      top: 246,
      width: 264,
      height: 214,
      text:
        "last-direction 的迁移数据是 214 GB，比 reactive 全量的 140 GB 还多。\n\n提前搬确实把中断从 39.0% 降到 9.8%，但付出了更高的字节成本。\n\noracle 只能说明“如果完全猜对会怎样”，不能作为现实方案。",
      size: 13.7,
      lineSpacing: 1.38,
    });
    addText(slide, {
      left: 72,
      top: 514,
      width: 1136,
      height: 52,
      text:
        "所以必须同时报告中断、迁移字节和到达后滞后。只报中断，会把“频繁搬错再重搬”的方案说成成功。",
      size: 15,
      color: C.muted,
      lineSpacing: 1.35,
    });
    takeaway(slide, "提前迁移（proactive）的价值取决于预测质量，必须在同样的中断目标下比较总字节。");
    pageNumber(slide, 24);
    addNotes(
      slide,
      "预测结果很说明问题。oracle 中断最低、字节也相对少，但现实中拿不到真实未来。一阶马尔可夫准确率约 49%，字节 192 GB。last-direction 只有 21%，中断仍比不预测低，但迁移字节 214 GB，比 reactive 全量还多。也就是说，它通过多搬几次来换取提前量。研究上必须把中断和字节一起报，否则会高估提前搬的收益。"
    );
  }

  // 25. Optimization map
  {
    const slide = newSlide(presentation);
    header(slide, 25, "系统优化", "降低迁移开销可以从四个层次下手");
    const layers = [
      [
        "1  决策层",
        "何时迁、迁哪个服务",
        "小状态服务可远程访问；大状态服务优先迁移。",
        "风险：延迟和一致性要求不同。",
        C.teal,
      ],
      [
        "2  放置层",
        "哪些节点提前保存 base",
        "沿常见路线预热快照和镜像，提高 base 命中率。",
        "风险：维护流量和存储占用增加。",
        C.amber,
      ],
      [
        "3  传输层",
        "一次迁移怎样搬得更少",
        "分块增量、压缩、去重、共享区域模型。",
        "风险：CPU、兼容性、冷目标回退。",
        C.rust,
      ],
      [
        "4  恢复层",
        "到了以后怎样更快可用",
        "镜像预热、并行拉层、状态应用加速。",
        "风险：并发会争抢带宽和 CPU。",
        C.green,
      ],
    ];
    layers.forEach(([title, question, action, risk, color], i) => {
      const top = 184 + i * 94;
      addText(slide, {
        left: 72,
        top,
        width: 170,
        height: 28,
        text: title,
        size: 18,
        bold: true,
        color,
      });
      addText(slide, {
        left: 252,
        top: top + 2,
        width: 262,
        height: 50,
        text: question,
        size: 14.5,
      });
      addText(slide, {
        left: 530,
        top: top + 2,
        width: 390,
        height: 50,
        text: action,
        size: 14,
      });
      addText(slide, {
        left: 940,
        top: top + 2,
        width: 268,
        height: 50,
        text: risk,
        size: 12.7,
        color: C.muted,
      });
      addRule(slide, 72, top + 64, 1136, 1, C.rule);
    });
    addText(slide, {
      left: 72,
      top: 556,
      width: 1136,
      height: 32,
      text:
        "优先级建议：先量化“搬什么”，再做 base placement，最后决定是否需要更复杂的迁移策略。",
      size: 15.4,
      color: C.muted,
    });
    takeaway(slide, "这四个层次共同决定中断和成本，不能用单一的“迁移算法更好”概括。");
    pageNumber(slide, 25);
    addNotes(
      slide,
      "系统优化可以拆成四层。第一，决策层决定迁不迁、迁哪个服务。第二，放置层决定哪些节点提前有 base 和镜像。第三，传输层决定一次迁移怎么压缩、分块和去重。第四，恢复层决定目标节点多快能真正接手。每一层都能降低开销，但都会带来新的代价。建议先做传输层和放置层，因为它们和存储背景最贴近，也能独立测量收益。"
    );
  }

  // 26. Conclusions
  {
    const slide = newSlide(presentation);
    header(slide, 26, "结论", "目前的实验支持四条判断");
    const conclusions = [
      [
        "01",
        "用户连续性必须有明确口径",
        "中断不是 handover 次数，而是用户无法获得服务的车辆秒占比。还要看切换前就绪和到达后滞后。",
      ],
      [
        "02",
        "迁移字节不是唯一开销",
        "同一份状态，传得更久就会占用更多链路；恢复慢则会把中断继续拉长。",
      ],
      [
        "03",
        "增量的上限由 base locality 决定",
        "DATA7 冷目标 17%，增量省 74%；合成数据冷目标 93%，只省 2.4%。",
      ],
      [
        "04",
        "提前搬需要把预测错误计费",
        "last-direction 把中断降到 9.8%，却产生 214 GB，超过 reactive 的 140 GB。",
      ],
    ];
    conclusions.forEach(([num, title, body], i) => {
      const top = 178 + i * 92;
      addText(slide, {
        left: 72,
        top,
        width: 56,
        height: 36,
        text: num,
        size: 22,
        bold: true,
        color: C.teal,
      });
      addText(slide, {
        left: 148,
        top,
        width: 1040,
        height: 28,
        text: title,
        size: 18.5,
        bold: true,
      });
      addText(slide, {
        left: 148,
        top: top + 34,
        width: 1040,
        height: 44,
        text: body,
        size: 14.3,
        color: C.muted,
        lineSpacing: 1.35,
      });
    });
    addPanel(slide, 72, 550, 1136, 32, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 92,
      top: 556,
      width: 1096,
      height: 22,
      text: "这四条正对老师项目里的“跨边状态同步/密文增量”挑战：优化收益必须连恢复与同步成本一起算。",
      size: 13.4,
      bold: true,
      color: C.teal,
    });
    takeaway(slide, "没有单一最优策略；应按服务、速度、带宽和 base 命中情况组合选择。");
    pageNumber(slide, 26);
    addNotes(
      slide,
      "结论有四点。第一，先把用户连续性说清楚，不能用切换次数代替中断。第二，成本要同时看字节、带宽时间和恢复。第三，增量的上限由 base 命中率决定。第四，提前搬必须把预测错误带来的额外迁移算进去。这四点和项目里的跨边状态同步、密文增量直接相关，因为任何安全和缩减机制都不能只报压缩率，还要报恢复和同步开销。"
    );
  }

  // 27. Limits and next steps
  {
    const slide = newSlide(presentation);
    header(slide, 27, "边界与下一步", "先补齐系统评估，再把安全机制叠上去");
    addPanel(slide, 72, 188, 548, 286, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 96,
      top: 208,
      width: 500,
      height: 28,
      text: "现在还不能直接下论文结论的地方",
      size: 18,
      bold: true,
    });
    addText(slide, {
      left: 96,
      top: 250,
      width: 500,
      height: 202,
      text:
        "1. 三类数据的 cell 尺度不同，不能当严格同条件排名。\n\n2. 12 步提前量是固定参数，还没做 5/12/30/60 的扫描。\n\n3. 暂未加入“完全不迁移、远程访问”的对照。\n\n4. 恢复模型是线性的，真实系统还要考虑启动、依赖和 I/O 抖动。",
      size: 14.2,
      lineSpacing: 1.4,
    });
    addPanel(slide, 660, 188, 548, 286, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 684,
      top: 208,
      width: 500,
      height: 28,
      text: "下一步实验与安全扩展",
      size: 18,
      bold: true,
      color: C.teal,
    });
    addText(slide, {
      left: 684,
      top: 250,
      width: 500,
      height: 202,
      text:
        "1. 做 base 放置与预热间隔的敏感性分析。\n\n2. 扫描提前量，观察收益和冗余迁移的拐点。\n\n3. 建一个小规模 testbed 校准 5 ms/MB 恢复模型。\n\n4. 在迁移时刻、源/目标、字节数上加入隐私机制，再复用同一套开销指标。",
      size: 14.2,
      lineSpacing: 1.4,
    });
    addText(slide, {
      left: 72,
      top: 508,
      width: 1136,
      height: 54,
      text:
        "安全机制为什么可以接在后面：加密、填充、批处理和诱饵迁移都会改变可观测时间与流量，但不会绕过“迁移字节、恢复时间、用户中断”这笔账。",
      size: 15.6,
      lineSpacing: 1.4,
    });
    takeaway(slide, "先建立可解释的系统基线，再证明安全机制带来的额外开销是可以接受的。");
    pageNumber(slide, 27);
    addNotes(
      slide,
      "最后列清楚边界。当前数据尺度和 cell 抽象不同，不能把四个数据集的数字当作严格排行。提前量、不迁移对照和小规模实测还需要补。下一步先做 base 放置和提前量敏感性，再尝试真实 testbed。安全机制可以后叠加，因为它仍然要回答同样三个问题：增加了多少字节、延长了多少恢复时间、让用户多等了多少秒。"
    );
  }

  for (let i = 0; i < presentation.slides.items.length; i += 1) {
    const slide = presentation.slides.items[i];
    const blob = await presentation.export({ slide, format: "png", scale: 1 });
    const stem = `slide-${String(i + 1).padStart(2, "0")}.png`;
    await fs.writeFile(path.join(renderDir, stem), new Uint8Array(await blob.arrayBuffer()));
  }

  const draftPath = path.join(BUILD_DIR, "draft_teaching_v6.pptx");
  await (await PresentationFile.exportPptx(presentation)).save(draftPath);
  console.log(`draft: ${draftPath}`);
  console.log(`renders: ${renderDir}`);

  if (process.argv.includes("--finalize")) {
    const { finalizePresentation } = await import(
      pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href
    );
    const stagingDir = path.join(WORKSPACE, ".codex-finalizer");
    await fs.mkdir(stagingDir, { recursive: true });
    await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
    const candidatePath = path.join(stagingDir, "candidate_teaching_v6.pptx");
    await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
    const tableSlides = [10, 11, 15, 17, 18, 20, 21, 22, 24];
    const result = await finalizePresentation({
      explicitTotalSlideCount: 27,
      requiredNativeTableOwnerSlides: tableSlides,
      requiredNativeChartOwnerSlides: [],
      workspaceDir: WORKSPACE,
      candidatePath,
      finalPath: FINAL_PPTX,
      pythonExecutable:
        "C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe",
      integrityValidatorPath: path.join(
        SKILL_DIR,
        "container_tools/inspect_presentation_package_integrity.py"
      ),
      layoutValidatorPath: path.join(
        SKILL_DIR,
        "container_tools/inspect_presentation_layout_geometry.py"
      ),
      layoutArgs: [
        "--expected-slide-size-emu",
        "12192000,6858000",
        "--validate-bullet-geometry",
        "--validate-heading-fit",
        ...tableSlides.flatMap((n) => ["--require-native-table-slide", String(n)]),
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
