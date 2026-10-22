import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const WORKSPACE = "C:/Users/Administrator/Desktop/MyEdgeSimPy";
const BUILD_DIR = path.join(WORKSPACE, "build/presentation");
const OUTPUT_DIR = path.join(WORKSPACE, "output/presentation");
const SKILL_DIR =
  "C:/Users/Administrator/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations";
const OUTPUT = path.join(OUTPUT_DIR, "迁移资源时间与Base维护_v2.pptx");
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
  amber: "#A56A00",
  amberSoft: "#F6EEDC",
  green: "#547248",
  greenSoft: "#EBF1E7",
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
    fontSize: opts.size ?? 17,
    bold: opts.bold ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "top",
    lineSpacing: opts.lineSpacing ?? 1.28,
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

function addPanel(slide, left, top, width, height, fill = C.paper, line = C.rule, widthPx = 1) {
  return slide.shapes.add({
    geometry: "roundRect",
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: widthPx },
    borderRadius: "rounded-lg",
  });
}

function header(slide, index, title) {
  addText(slide, {
    left: 72,
    top: 36,
    width: 1136,
    height: 20,
    text: `${String(index).padStart(2, "0")}  资源与开销`,
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

function takeaway(slide, text) {
  addRule(slide, 72, 606, 1136, 1, C.rule);
  addText(slide, {
    left: 72,
    top: 620,
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

function notes(slide, text) {
  slide.speakerNotes.text = text;
  slide.speakerNotes.setVisible(true);
}

function newSlide(presentation, background = C.bg) {
  const slide = presentation.slides.add();
  slide.background.fill = background;
  return slide;
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
      const headerRow = r === 0;
      cell.fill = headerRow ? C.teal : r % 2 === 0 ? "#FBFBF8" : C.white;
      const range = table.cells.block({ row: r, column: c, rowCount: 1, columnCount: 1 });
      range.textStyle.typeface = FONT;
      range.textStyle.fontSize = headerRow ? 13 : (opts.fontSize ?? 13.5);
      range.textStyle.bold = headerRow || (opts.boldFirstColumn && c === 0);
      range.textStyle.color = headerRow ? C.white : C.ink;
      range.textStyle.alignment =
        c === 0 || opts.alignLeftColumns?.includes(c) ? "left" : "center";
    }
  }
  return table;
}

async function main() {
  await fs.mkdir(BUILD_DIR, { recursive: true });
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  const renderDir = path.join(BUILD_DIR, "renders_resource");
  await fs.mkdir(renderDir, { recursive: true });

  const presentation = Presentation.create({ slideSize: SIZE });
  presentation.theme.defaultFont = FONT;
  presentation.theme.colorScheme = {
    name: "Migration Resource Teaching",
    themeColors: {
      accent1: C.teal,
      accent2: C.rust,
      accent3: C.amber,
      accent4: C.green,
      accent5: "#4C6B78",
      accent6: "#7A8F8B",
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
      top: 52,
      width: 1000,
      height: 24,
      text: "迁移开销专题  /  2026年10月",
      size: 13,
      bold: true,
      color: "#BFD6D2",
    });
    addText(slide, {
      left: 72,
      top: 188,
      width: 1050,
      height: 140,
      text: "迁移不只搬字节\n还要占多久、并发多少",
      size: 44,
      bold: true,
      color: C.white,
      lineSpacing: 1.14,
    });
    addRule(slide, 72, 368, 96, 3, "#8FB8B2");
    addText(slide, {
      left: 72,
      top: 398,
      width: 1030,
      height: 34,
      text: "资源时间、并发、排队与 base 维护评估",
      size: 22,
      color: "#D6E5E2",
    });
    addText(slide, {
      left: 72,
      top: 452,
      width: 1030,
      height: 56,
      text: "核心问题：一次迁移给链路、控制面和用户连续性带来了多少真实代价。",
      size: 17,
      color: "#BFD6D2",
    });
    notes(
      slide,
      "这份汇报只讨论新补的一组系统开销指标：带宽时间、并发、控制面流、排队和 base 维护。目的不是重新介绍 MEC，而是解释迁移到底占用了哪些资源，以及预热 base 是否值得。"
    );
  }

  // 2. Metric framework
  {
    const slide = newSlide(presentation);
    header(slide, 2, "四个新增指标补齐了字节之外的资源成本");
    const rows = [
      ["带宽-时间积", "迁移数据量 × 占用链路的时间", "链路在多久内被占用了多少容量"],
      ["并发迁移数", "同一时刻正在运行的迁移数量", "是否形成瞬时洪峰"],
      ["控制面流/切换", "每次 handover 对应的状态流与镜像层流数量", "迁移作业本身有多复杂"],
      ["排队时间占比", "迁移总时长中等待资源或调度的比例", "瓶颈在数据量还是调度"],
    ];
    rows.forEach(([name, definition, purpose], i) => {
      const top = 188 + i * 92;
      addText(slide, {
        left: 72,
        top,
        width: 180,
        height: 28,
        text: name,
        size: 18,
        bold: true,
        color: i === 3 ? C.rust : C.teal,
      });
      addText(slide, {
        left: 286,
        top: top + 1,
        width: 456,
        height: 54,
        text: definition,
        size: 15.2,
      });
      addText(slide, {
        left: 780,
        top: top + 1,
        width: 428,
        height: 54,
        text: purpose,
        size: 14.4,
        color: C.muted,
      });
      addRule(slide, 72, top + 66, 1136, 1, C.rule);
    });
    takeaway(slide, "只看迁移 GB，会漏掉链路占用时间和管理复杂度。");
    pageNumber(slide, 2);
    notes(
      slide,
      "四个指标分别回答不同问题。带宽时间衡量链路占用，迁移字节只回答搬了多少。并发数回答同一时刻有多少迁移一起跑。控制面流数量回答一次切换产生多少作业和镜像层下载。排队比例回答时间到底花在等待还是实际传输。"
    );
  }

  // 3. Bandwidth-time
  {
    const slide = newSlide(presentation);
    header(slide, 3, "增量在真实轨迹上大幅降低链路占用");
    addTable(slide, {
      left: 72,
      top: 194,
      width: 520,
      height: 260,
      columnWidths: [150, 185, 185],
      rowHeight: 65,
      fontSize: 14,
      values: [
        ["数据", "全量 MB·s/切换", "增量 MB·s/切换"],
        ["SF", "15,052", "4,392"],
        ["Rome", "16,227", "10,736"],
        ["合成", "102,793", "102,301"],
      ],
    });
    slide.charts.add("bar", {
      position: { left: 654, top: 194, width: 554, height: 260 },
      categories: ["SF", "Rome", "合成"],
      series: [{ name: "增量后占全量比例", values: [29.2, 66.2, 99.5], fill: "accent1" }],
      hasLegend: false,
      dataLabels: { showValue: true, position: "outEnd" },
      yAxis: { majorGridlines: { style: "solid", fill: C.rule, width: 1 } },
    });
    addText(slide, {
      left: 654,
      top: 462,
      width: 554,
      height: 26,
      text: "单位：% ；增量后的带宽-时间积 ÷ 全量",
      size: 12,
      color: C.muted,
    });
    addText(slide, {
      left: 72,
      top: 486,
      width: 1136,
      height: 66,
      text:
        "SF 的增量把链路占用降到约三成。合成数据只降到 99.5%，因为 92.9% 的迁移目标没有 base，实际仍然接近全量传输。",
      size: 15.8,
      lineSpacing: 1.4,
      color: C.muted,
    });
    takeaway(slide, "增量不是固定收益；base 是否命中决定它能否减少链路占用时间。");
    pageNumber(slide, 3);
    notes(
      slide,
      "带宽时间不是只看搬了多少 MB，而是数据量乘以它占用链路的时间。SF 从 15052 降到 4392，Rome 从 16227 降到 10736。合成数据几乎没变，因为绝大多数目标是冷目标，增量仍然要传全量。"
    );
  }

  // 4. Time breakdown
  {
    const slide = newSlide(presentation);
    header(slide, 4, "DATA7 的迁移时间几乎都花在传状态");
    slide.charts.add("bar", {
      position: { left: 72, top: 190, width: 770, height: 350 },
      categories: ["合成", "Rome", "SF", "DATA7"],
      series: [
        {
          name: "拉取镜像",
          values: [74.9, 16.8, 4.3, 2.2],
          fill: "accent3",
          dataLabels: { showValue: false },
        },
        { name: "状态传输", values: [25.1, 83.2, 95.7, 97.8], fill: "accent1" },
      ],
      hasLegend: true,
      barOptions: { direction: "bar", grouping: "stacked", gapWidth: 48, overlap: 100 },
      dataLabels: {
        showValue: true,
        position: "center",
        numberFormatCode: '0.0"%"',
        textStyle: { fill: C.white, fontSize: 12, bold: true },
      },
      xAxis: {
        min: 0,
        max: 100,
        majorUnit: 20,
        numberFormatCode: '0"%"',
      },
      yAxis: { majorGridlines: { style: "solid", fill: C.rule, width: 1 } },
    });
    addText(slide, {
      left: 72,
      top: 552,
      width: 770,
      height: 24,
      text: "拉镜像占比：DATA7 2.2%  |  SF 4.3%  |  Rome 16.8%  |  合成 74.9%",
      size: 12.2,
      color: C.muted,
    });
    addText(slide, {
      left: 872,
      top: 190,
      width: 336,
      height: 26,
      text: "DATA7 新增结果",
      size: 18,
      bold: true,
      color: C.teal,
    });
    addText(slide, {
      left: 872,
      top: 232,
      width: 336,
      height: 92,
      text: "拉镜像 2.2%\n状态传输 97.8%",
      size: 23,
      bold: true,
      lineSpacing: 1.28,
    });
    addText(slide, {
      left: 872,
      top: 346,
      width: 336,
      height: 160,
      text:
        "DATA7 中镜像层大多已有缓存，因此关键路径主要受会话状态传输影响。\n\n合成数据相反，约 75% 的时间在拉镜像。",
      size: 14.5,
      lineSpacing: 1.42,
      color: C.muted,
    });
    addPanel(slide, 872, 516, 336, 44, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 890,
      top: 526,
      width: 300,
      height: 24,
      text: "排队时间占比：0%",
      size: 13.5,
      bold: true,
      color: C.amber,
    });
    takeaway(slide, "DATA7 的优化重点应放在状态传输，而不是继续优化镜像拉取。");
    pageNumber(slide, 4);
    notes(
      slide,
      "补跑的 DATA7 同口径结果已经存在。在 40 公里每小时、500 Mbps、12 辆车、1800 秒的平均结果中，拉镜像只占 2.2%，业务状态传输占 97.8%，排队接近 0。这说明 DATA7 中镜像层大多已有缓存，关键路径是状态传输。作为对照，SF 拉镜像约 4.3%，Rome 约 16.8%，合成数据约 74.9%。来源为 results/data7_report/metrics_summary.csv。"
    );
  }

  // 5. Concurrency and control plane
  {
    const slide = newSlide(presentation);
    header(slide, 5, "并发与镜像层数量决定瞬时管理压力");
    addTable(slide, {
      left: 72,
      top: 188,
      width: 1136,
      height: 294,
      columnWidths: [210, 220, 220, 486],
      rowHeight: 58.8,
      fontSize: 13.5,
      values: [
        ["数据", "平均并发迁移", "并发峰值", "控制面流/切换"],
        ["SF", "1.53", "48", "4.26"],
        ["Rome", "2.94", "48", "5.94"],
        ["合成", "17.81", "48", "12.38"],
      ],
    });
    addText(slide, {
      left: 72,
      top: 512,
      width: 540,
      height: 62,
      text:
        "并发峰值 48 = 12 辆车 × 每车 4 个服务。\n说明切换发生时，所有服务实例可能同时进入迁移。",
      size: 15,
      lineSpacing: 1.38,
    });
    addText(slide, {
      left: 650,
      top: 512,
      width: 558,
      height: 62,
      text:
        "合成数据每次切换约产生 12.38 条控制面流，远高于 SF 的 4.26，主要来自需要拉取的镜像层。",
      size: 15,
      lineSpacing: 1.38,
      color: C.muted,
    });
    takeaway(slide, "迁移数量相同，不代表控制面压力相同；镜像层会把一次切换放大成多条工作流。");
    pageNumber(slide, 5);
    notes(
      slide,
      "SF 和 Rome 平均只同时运行 1.5 到 3 个迁移，合成数据平均约 18 个。三者的峰值都到 48，因为 12 辆车的四类服务可能同时触发。控制面流每切换分别约 4.26、5.94 和 12.38，合成数据明显更高，因为它经常需要拉取很多镜像层。"
    );
  }

  // 6. Waiting ratio
  {
    const slide = newSlide(presentation);
    header(slide, 6, "当前没有明显排队，瓶颈仍是数据量");
    addText(slide, {
      left: 72,
      top: 186,
      width: 250,
      height: 96,
      text: "0%",
      size: 62,
      bold: true,
      color: C.teal,
    });
    addText(slide, {
      left: 330,
      top: 198,
      width: 430,
      height: 58,
      text: "排队时间占比",
      size: 22,
      bold: true,
    });
    addText(slide, {
      left: 330,
      top: 250,
      width: 760,
      height: 72,
      text:
        "当前 500 Mbps、12 辆车的配置下，链路利用率约 3%–11%，迁移基本一开始就能传，没有等待队列。",
      size: 15.5,
      lineSpacing: 1.38,
      color: C.muted,
    });
    addPanel(slide, 72, 352, 540, 164, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 96,
      top: 372,
      width: 492,
      height: 28,
      text: "这个结果说明",
      size: 17,
      bold: true,
      color: C.teal,
    });
    addText(slide, {
      left: 96,
      top: 414,
      width: 492,
      height: 82,
      text:
        "先优化数据量和镜像拉取，比优化调度优先级更直接。\n当前结果不能证明调度算法无效。",
      size: 15.2,
      lineSpacing: 1.4,
    });
    addPanel(slide, 660, 352, 548, 164, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 684,
      top: 372,
      width: 500,
      height: 28,
      text: "要研究调度，需要制造拥塞",
      size: 17,
      bold: true,
      color: C.amber,
    });
    addText(slide, {
      left: 684,
      top: 414,
      width: 500,
      height: 82,
      text:
        "降低带宽、增加车辆数、提高并发，或给迁移设置专用带宽后，再比较调度与排队策略。",
      size: 15.2,
      lineSpacing: 1.4,
    });
    takeaway(slide, "排队时间为 0 是当前负载的诊断，不是迁移系统的普遍结论。");
    pageNumber(slide, 6);
    notes(
      slide,
      "当前排队时间占比是 0，因为链路还没有被打满。这个结果的价值是告诉我们：当前主要瓶颈是数据量，不是调度等待。如果下一步要研究调度，就必须增加压力，例如降低带宽、增加车辆数或增加并发，否则不同调度器不会产生差异。"
    );
  }

  // 7. Base maintenance results
  {
    const slide = newSlide(presentation);
    header(slide, 7, "预热 base 能降低中断，但要支付后台复制流量");
    addTable(slide, {
      left: 72,
      top: 188,
      width: 1136,
      height: 340,
      columnWidths: [130, 150, 145, 180, 175, 176, 180],
      rowHeight: 68,
      fontSize: 12.4,
      values: [
        ["数据", "维护", "中断", "迁移字节", "base 复制", "总流量", "开销比"],
        ["SF", "否", "4.82%", "26.9 GB", "0", "26.9 GB", "3.85×"],
        ["SF", "是", "2.78%", "18.1 GB", "34.0 GB", "52.1 GB", "7.47×"],
        ["Rome", "否", "4.20%", "61.1 GB", "0", "61.1 GB", "8.75×"],
        ["Rome", "是", "2.69%", "47.4 GB", "42.3 GB", "89.7 GB", "12.85×"],
      ],
    });
    addText(slide, {
      left: 72,
      top: 548,
      width: 1136,
      height: 38,
      text:
        "实验：每 600 秒把 base 复制给 4 个相邻节点；比较 reactive_delta 在 40 km/h 下的结果。",
      size: 14,
      color: C.muted,
    });
    takeaway(slide, "base 维护确实买到连续性，但后台复制成本可能超过省下的迁移字节。");
    pageNumber(slide, 7);
    notes(
      slide,
      "这是 base 维护实验。策略是 reactive_delta，40 公里每小时，每 600 秒把 base 复制给四个邻居。SF 的中断从 4.82% 降到 2.78%，Rome 从 4.20% 降到 2.69%。但是总流量分别从 26.9 GB 增到 52.1 GB，以及从 61.1 GB 增到 89.7 GB，开销比明显上升。"
    );
  }

  // 8. Base maintenance interpretation
  {
    const slide = newSlide(presentation);
    header(slide, 8, "base 维护是一项“中断换流量”的交易");
    const comparisons = [
      ["SF", "中断下降 2.04 个百分点", "总流量增加 94%", "+25.2 GB"],
      ["Rome", "中断下降 1.51 个百分点", "总流量增加 47%", "+28.6 GB"],
    ];
    comparisons.forEach(([dataset, benefit, cost, extra], i) => {
      const top = 194 + i * 166;
      addText(slide, {
        left: 72,
        top,
        width: 84,
        height: 34,
        text: dataset,
        size: 22,
        bold: true,
        color: i === 0 ? C.teal : C.rust,
      });
      addPanel(slide, 170, top - 4, 480, 124, C.greenSoft, "#BDD0B4", 1);
      addText(slide, {
        left: 194,
        top: top + 16,
        width: 432,
        height: 28,
        text: benefit,
        size: 17,
        bold: true,
        color: C.green,
      });
      addText(slide, {
        left: 194,
        top: top + 58,
        width: 432,
        height: 40,
        text: "收益：服务不可用时间减少",
        size: 13.2,
        color: C.muted,
      });
      addPanel(slide, 676, top - 4, 532, 124, C.rustSoft, "#DDB1A4", 1);
      addText(slide, {
        left: 700,
        top: top + 16,
        width: 484,
        height: 28,
        text: cost,
        size: 17,
        bold: true,
        color: C.rust,
      });
      addText(slide, {
        left: 700,
        top: top + 58,
        width: 484,
        height: 40,
        text: `代价：额外复制 ${extra}，还要占用邻居存储和链路`,
        size: 13.2,
        color: C.muted,
      });
    });
    addText(slide, {
      left: 72,
      top: 540,
      width: 1136,
      height: 42,
      text:
        "因此问题已经明确：base 需要存到哪些节点、复制给谁、多久复制一次。单纯“有 base”不足以说明方案更优。",
      size: 15.8,
      lineSpacing: 1.38,
      color: C.muted,
    });
    takeaway(slide, "优化目标应从“是否预热”改成“用多少存储和后台流量换取多少连续性”。");
    pageNumber(slide, 8);
    notes(
      slide,
      "这页把 base 维护解释成交易。SF 用总流量增加 94% 换来中断下降约 2 个百分点，Rome 用总流量增加 47% 换来中断下降约 1.5 个百分点。老师关心的存储问题正好在这里：base 副本占用邻居存储，后台复制占用链路，还需要失效和更新机制。"
    );
  }

  // 9. Next experiment
  {
    const slide = newSlide(presentation);
    header(slide, 9, "下一组实验研究 base 的放置范围与刷新间隔");
    const dimensions = [
      ["复制给谁", "四邻居 / 预测下一格 / 高概率下一跳", "识别哪些副本真正被用到"],
      ["多久复制", "60 / 300 / 600 秒", "找连续性收益与后台流量的拐点"],
      ["保留多久", "固定过期 / 访问衰减 / 按存储预算淘汰", "避免无限复制和长期占用存储"],
    ];
    dimensions.forEach(([title, choices, purpose], i) => {
      const left = 72 + i * 384;
      addText(slide, {
        left,
        top: 196,
        width: 330,
        height: 30,
        text: title,
        size: 20,
        bold: true,
        color: i === 0 ? C.teal : i === 1 ? C.amber : C.rust,
      });
      addText(slide, {
        left,
        top: 242,
        width: 330,
        height: 100,
        text: choices,
        size: 15.5,
        lineSpacing: 1.45,
      });
      addRule(slide, left, 360, 330, 1, C.rule);
      addText(slide, {
        left,
        top: 380,
        width: 330,
        height: 74,
        text: purpose,
        size: 14,
        color: C.muted,
      });
    });
    addPanel(slide, 72, 486, 1136, 74, C.amberSoft, "#D7B56A", 1);
    addText(slide, {
      left: 96,
      top: 502,
      width: 1088,
      height: 44,
      text:
        "“只复制预测下一格可降到约 1/4”目前只是流量上界假设。预测错误、命中率和刷新频率都会改变结果，必须实测。",
      size: 15,
      lineSpacing: 1.36,
    });
    takeaway(slide, "最有解释力的实验，是比较 base 命中率、额外流量和后端存储占用。");
    pageNumber(slide, 9);
    notes(
      slide,
      "下一步不应只说复制给一个邻居。要把复制范围、刷新间隔和保存期限一起作为设计变量。只复制预测下一格看似把复制量降到四分之一，但这是一个上界假设，预测错时可能没有命中，仍要回退全量。实验应报告 base 命中率、额外后台流量、邻居存储占用和中断变化。"
    );
  }

  // 10. Conclusion
  {
    const slide = newSlide(presentation);
    header(slide, 10, "结论：迁移开销需要按资源而不是按字节核算");
    const conclusions = [
      ["01", "带宽时间解释了链路代价", "真实轨迹上增量明显降低链路占用；冷目标数据上几乎无效。"],
      ["02", "时间去向决定优化重点", "SF 主要传状态，合成数据约 75% 的时间在拉取镜像。"],
      ["03", "当前没有排队压力", "瓶颈仍是数据量；要验证调度，必须构造更高负载。"],
      ["04", "base 维护需要用流量和存储换连续性", "中断下降有明确收益，但总流量和开销比显著上升。"],
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
        size: 14.2,
        color: C.muted,
        lineSpacing: 1.35,
      });
    });
    addPanel(slide, 72, 548, 1136, 34, C.tealSoft, C.teal, 1);
    addText(slide, {
      left: 92,
      top: 555,
      width: 1096,
      height: 22,
      text: "下一阶段：联合优化 base 放置、复制范围、刷新间隔和迁移触发时机。",
      size: 13.5,
      bold: true,
      color: C.teal,
    });
    takeaway(slide, "后续所有策略比较，都应同时报告中断、带宽时间、总流量和存储占用。");
    pageNumber(slide, 10);
    notes(
      slide,
      "总结四点。第一，带宽时间比字节数更接近链路成本。第二，时间去向说明不同数据的优化重点不同。第三，当前没有排队，所以调度不是第一瓶颈。第四，base 维护确实降低中断，但会显著增加总流量和存储占用。下一阶段应联合研究 base 放置、复制范围和刷新间隔。"
    );
  }

  for (let i = 0; i < presentation.slides.items.length; i += 1) {
    const slide = presentation.slides.items[i];
    const blob = await presentation.export({ slide, format: "png", scale: 1 });
    const stem = `slide-${String(i + 1).padStart(2, "0")}.png`;
    await fs.writeFile(path.join(renderDir, stem), new Uint8Array(await blob.arrayBuffer()));
  }

  const draftPath = path.join(BUILD_DIR, "draft_resource.pptx");
  await (await PresentationFile.exportPptx(presentation)).save(draftPath);
  console.log(`draft: ${draftPath}`);
  console.log(`renders: ${renderDir}`);

  if (process.argv.includes("--finalize")) {
    const { finalizePresentation } = await import(
      pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href
    );
    const stagingDir = path.join(WORKSPACE, ".codex-finalizer");
    await fs.mkdir(stagingDir, { recursive: true });
    const candidatePath = path.join(stagingDir, "candidate_resource.pptx");
    await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
    const tableSlides = [3, 5, 7];
    const result = await finalizePresentation({
      explicitTotalSlideCount: 10,
      requiredNativeTableOwnerSlides: tableSlides,
      requiredNativeChartOwnerSlides: [3, 4],
      materializeLiteralChartWorkbooks: true,
      workspaceDir: WORKSPACE,
      candidatePath,
      finalPath: OUTPUT,
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
      receiptPath: path.join(stagingDir, `${path.basename(OUTPUT)}.validation.json`),
    });
    console.log(JSON.stringify(result, null, 2));
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
