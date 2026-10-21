from __future__ import annotations

from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "paper" / "figures"

STYLE = """
  <style>
    text{font-family:Arial,Helvetica,sans-serif;fill:#111827}
    .group{fill:#ffffff;stroke:#374151;stroke-width:1.5}
    .boundary{fill:#f8fafc;stroke:#111827;stroke-width:1.8}
    .node{fill:#ffffff;stroke:#4b5563;stroke-width:1.35}
    .soft{fill:#f3f4f6;stroke:#6b7280;stroke-width:1.25}
    .accent{fill:#eaf0f8;stroke:#2f5597;stroke-width:1.5}
    .safety{fill:#fff7ed;stroke:#9a3412;stroke-width:1.5}
    .gate{fill:#ffffff;stroke:#111827;stroke-width:1.6}
    .arrow{fill:none;stroke:#374151;stroke-width:1.6;marker-end:url(#arrow)}
    .feedback{fill:none;stroke:#4b5563;stroke-width:1.4;stroke-dasharray:7 5;marker-end:url(#arrow)}
    .blocked{fill:none;stroke:#9a3412;stroke-width:1.8;stroke-dasharray:7 5}
    .axis{stroke:#6b7280;stroke-width:1}
    .grid{stroke:#d1d5db;stroke-width:1}
    .section{font-size:18px;font-weight:700;letter-spacing:.3px}
    .label{font-size:17px}
    .small{font-size:16.5px;fill:#374151}
    .tiny{font-size:14px;fill:#4b5563}
    .number{font-size:13px;font-weight:700;fill:#ffffff}
    .metric{font-size:21px;font-weight:700}
    .panel{font-size:20px;font-weight:700}
    .bar1{fill:#2f5597}
    .bar2{fill:#64748b}
    .bar3{fill:#94a3b8}
    .bar4{fill:#cbd5e1}
    .bar5{fill:#e5e7eb;stroke:#9ca3af;stroke-width:.7}
  </style>
"""


def text(
    x: float,
    y: float,
    value: str,
    *,
    css: str = "label",
    anchor: str = "middle",
) -> str:
    return (
        f'<text class="{css}" x="{x}" y="{y}" '
        f'text-anchor="{anchor}">{escape(value)}</text>'
    )


def text_lines(
    x: float,
    y: float,
    values: list[str],
    *,
    css: str = "small",
    anchor: str = "middle",
    leading: float = 20,
) -> str:
    return "\n".join(
        text(x, y + index * leading, value, css=css, anchor=anchor)
        for index, value in enumerate(values)
    )


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    css: str = "node",
    radius: float = 0,
) -> str:
    return (
        f'<rect class="{css}" x="{x}" y="{y}" width="{width}" '
        f'height="{height}" rx="{radius}"/>'
    )


def line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    css: str = "arrow",
) -> str:
    return f'<path class="{css}" d="M{x1} {y1} L{x2} {y2}"/>'


def path(points: list[tuple[float, float]], *, css: str = "arrow") -> str:
    commands = " ".join(
        ("M" if index == 0 else "L") + f"{x} {y}" for index, (x, y) in enumerate(points)
    )
    return f'<path class="{css}" d="{commands}"/>'


def circle_number(x: float, y: float, value: int) -> str:
    return f'<circle cx="{x}" cy="{y}" r="11" fill="#2f5597"/>' + text(
        x, y + 4.5, str(value), css="number"
    )


def document(
    width: int,
    height: int,
    title_value: str,
    description: str,
    body: str,
) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title_value)}</title>
  <desc id="desc">{escape(description)}</desc>
  <defs>
{STYLE}
    <marker id="arrow" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">
      <path d="M0 0 L9 3.5 L0 7 Z" fill="#374151"/>
    </marker>
  </defs>
  <rect width="{width}" height="{height}" fill="#ffffff"/>
{body}
</svg>
"""


def figure_1() -> str:
    body = [
        rect(28, 45, 185, 520, css="group"),
        text(120, 76, "INPUT SOURCES", css="section"),
        rect(48, 105, 145, 58),
        text_lines(120, 130, ["Camera", "USB / CSI"], leading=18),
        rect(48, 180, 145, 58),
        text_lines(120, 205, ["Image", "local / HTTP"], leading=18),
        rect(48, 255, 145, 58),
        text_lines(120, 280, ["Video", "file / URL"], leading=18),
        rect(48, 330, 145, 58),
        text_lines(120, 355, ["Stream", "RTSP / HTTP"], leading=18),
        rect(250, 45, 670, 520, css="boundary"),
        text(275, 76, "EDGE RUNTIME (NON-SAFETY-RATED)", css="section", anchor="start"),
        rect(285, 115, 165, 72, css="accent"),
        circle_number(297, 127, 1),
        text_lines(368, 143, ["Capture adapter", "decode · validate"], leading=20),
        rect(500, 115, 165, 72, css="accent"),
        circle_number(512, 127, 2),
        text_lines(583, 143, ["Detector adapter", "public / custom"], leading=20),
        rect(715, 115, 165, 72, css="accent"),
        circle_number(727, 127, 3),
        text_lines(798, 143, ["Detection schema", "class · score · box"], leading=20),
        line(450, 151, 500, 151),
        line(665, 151, 715, 151),
        rect(345, 250, 210, 82),
        circle_number(357, 262, 4),
        text_lines(
            450,
            278,
            ["Tracking and counts", "visible · unique-session"],
            leading=20,
        ),
        rect(620, 250, 210, 82),
        circle_number(632, 262, 5),
        text_lines(
            725,
            278,
            ["Review and policy", "confidence · destination"],
            leading=20,
        ),
        path([(798, 187), (798, 215), (450, 215), (450, 250)]),
        path([(798, 187), (798, 215), (725, 215), (725, 250)]),
        rect(335, 405, 310, 95, css="soft"),
        circle_number(347, 417, 6),
        text_lines(
            490,
            433,
            ["Durable evidence", "SQLite · JSONL · reviews", "confirmed collection"],
            leading=19,
        ),
        rect(700, 405, 145, 95, css="soft"),
        text_lines(772, 440, ["Local API", "dashboard · fleet"], leading=20),
        path([(450, 332), (450, 370), (490, 370), (490, 405)]),
        path([(725, 332), (725, 370), (600, 370), (600, 405)]),
        line(645, 452, 700, 452),
        path([(213, 285), (230, 285), (230, 151), (285, 151)]),
        rect(960, 45, 212, 520, css="group"),
        text(1066, 76, "OPERATIONAL USERS", css="section"),
        rect(985, 120, 162, 68),
        text_lines(1066, 148, ["Human operator", "review / separation"], leading=19),
        rect(985, 245, 162, 68),
        text_lines(1066, 273, ["Fleet system", "route / reporting"], leading=19),
        rect(985, 370, 162, 90, css="safety"),
        text_lines(
            1066,
            398,
            ["Safety controller", "independent authority", "pickup confirmation"],
            leading=19,
        ),
        path([(845, 452), (940, 452), (940, 154), (985, 154)]),
        path([(940, 279), (985, 279)]),
        path([(940, 415), (985, 415)]),
        path(
            [(985, 445), (940, 445), (940, 535), (585, 535), (585, 500)], css="feedback"
        ),
        text(730, 550, "confirmed outcome returned as separate evidence", css="tiny"),
    ]
    return document(
        1200,
        600,
        "Detector-independent operational architecture",
        "A publication-style block diagram of sources, the non-safety-rated edge runtime, operational users, and the separate confirmation path.",
        "\n".join(body),
    )


def figure_2() -> str:
    columns = [
        (
            "D_t",
            "Frame detections",
            ["Objects reported", "in frame t"],
            "What is visible now?",
        ),
        (
            "V_t",
            "Confirmed visible",
            ["Tracks satisfying", "the hit rule"],
            "What is stable now?",
        ),
        (
            "U_r",
            "Unique in run",
            ["Confirmed track IDs", "counted once"],
            "What did run r see?",
        ),
        (
            "P_r",
            "Confirmed collected",
            ["Pickup confirmed by", "human/controller"],
            "What was collected?",
        ),
    ]
    body: list[str] = []
    for index, (symbol, heading, description, question) in enumerate(columns):
        x = 30 + index * 292
        body.extend(
            [
                rect(x, 55, 250, 235, css="node"),
                circle_number(x + 24, 79, index + 1),
                text(x + 125, 92, symbol, css="metric"),
                text(x + 125, 132, heading, css="section"),
                text_lines(x + 125, 170, description, leading=20),
                text(x + 125, 235, question, css="small"),
            ]
        )
        if index < 3:
            body.append(line(x + 250, 172, x + 292, 172))
    body.extend(
        [
            text(306, 45, "track confirmation", css="tiny"),
            text(598, 45, "run-level deduplication", css="tiny"),
            text(890, 45, "independent evidence", css="tiny"),
            rect(130, 335, 940, 62, css="soft"),
            text(
                600,
                363,
                "D_t, V_t, U_r and P_r are stored as distinct quantities with run, device, route and time context.",
                css="small",
            ),
            text(
                600,
                386,
                "Frame detections must not be reported as unique physical objects or confirmed cleanup.",
                css="small",
            ),
        ]
    )
    return document(
        1200,
        430,
        "Litter count semantics",
        "Four distinct count quantities progress from frame detections to independently confirmed collection.",
        "\n".join(body),
    )


def figure_3() -> str:
    body = [
        rect(35, 48, 490, 410, css="boundary"),
        text(60, 80, "(a) PERCEPTION APPLICATION", css="panel", anchor="start"),
        text(60, 105, "advisory; not safety-rated", css="small", anchor="start"),
        rect(85, 145, 145, 68),
        text_lines(157, 174, ["Camera", "and source checks"], leading=19),
        rect(300, 145, 165, 68),
        text_lines(382, 174, ["Detection / tracking", "candidate object"], leading=19),
        line(230, 179, 300, 179),
        rect(175, 280, 210, 72, css="accent"),
        text_lines(
            280,
            310,
            ["Advisory candidate event", "position · class · confidence"],
            leading=20,
        ),
        path([(382, 213), (382, 245), (280, 245), (280, 280)]),
        rect(675, 48, 490, 410, css="group"),
        text(700, 80, "(b) INDEPENDENT SAFETY CONTROL", css="panel", anchor="start"),
        text(
            700, 105, "separate authority and validation", css="small", anchor="start"
        ),
        rect(715, 135, 175, 115, css="soft"),
        text_lines(
            802,
            163,
            [
                "Safety inputs",
                "e-stop · exclusion zone",
                "arm state · load limits",
                "stale-signal checks",
            ],
            leading=19,
        ),
        rect(955, 150, 150, 82, css="safety"),
        text_lines(1030, 182, ["Safety logic", "permit / inhibit"], leading=20),
        line(890, 191, 955, 191),
        rect(955, 305, 150, 72, css="safety"),
        text_lines(1030, 334, ["Actuator", "collection mechanism"], leading=20),
        line(1030, 232, 1030, 305),
        line(525, 316, 675, 316),
        text(600, 287, "bounded advisory interface", css="tiny"),
        path(
            [(385, 340), (600, 340), (600, 410), (955, 410), (955, 355)], css="blocked"
        ),
        text(770, 431, "no direct perception-to-actuation path", css="small"),
        text(600, 415, "×", css="metric"),
        path(
            [(955, 355), (920, 355), (920, 485), (280, 485), (280, 352)], css="feedback"
        ),
        text(
            600,
            505,
            "positive pickup confirmation returns to the evidence store",
            css="small",
        ),
    ]
    return document(
        1200,
        530,
        "Deployment and machinery-safety boundary",
        "The perception application emits an advisory event while an independent safety controller retains actuation authority and returns pickup confirmation.",
        "\n".join(body),
    )


def figure_4() -> str:
    body = [
        rect(35, 80, 175, 78, css="accent"),
        circle_number(47, 92, 1),
        text_lines(122, 111, ["Pinned public", "checkpoint"], leading=20),
        rect(255, 80, 175, 78),
        circle_number(267, 92, 2),
        text_lines(342, 111, ["Bootstrap use", "and data capture"], leading=20),
        rect(475, 80, 175, 78),
        circle_number(487, 92, 3),
        text_lines(562, 111, ["Representative", "labelled data"], leading=20),
        rect(695, 80, 175, 78),
        circle_number(707, 92, 4),
        text_lines(782, 111, ["Train / adapt", "checkpoint"], leading=20),
        rect(915, 80, 220, 78),
        circle_number(927, 92, 5),
        text_lines(
            1025, 111, ["Frozen validation", "detection · count · system"], leading=20
        ),
        line(210, 119, 255, 119),
        line(430, 119, 475, 119),
        line(650, 119, 695, 119),
        line(870, 119, 915, 119),
        rect(490, 250, 220, 82, css="gate"),
        text_lines(
            600, 281, ["Release gate", "predeclared acceptance criteria"], leading=21
        ),
        path([(1025, 158), (1025, 205), (600, 205), (600, 250)]),
        rect(850, 390, 285, 78, css="accent"),
        text_lines(
            992,
            420,
            ["Versioned accepted checkpoint", "same downstream detection contract"],
            leading=21,
        ),
        path([(710, 291), (992, 291), (992, 390)]),
        text(840, 278, "PASS", css="small"),
        path(
            [(490, 291), (430, 291), (430, 210), (782, 210), (782, 158)],
            css="feedback",
        ),
        text(455, 278, "FAIL", css="small", anchor="end"),
        text(455, 326, "revise data / prompt / model", css="tiny", anchor="end"),
        rect(35, 390, 320, 78, css="soft"),
        text_lines(
            195,
            420,
            [
                "Public model remains available",
                "for installation, review and data collection",
            ],
            leading=21,
        ),
        path([(342, 158), (342, 350), (195, 350), (195, 390)], css="feedback"),
    ]
    return document(
        1200,
        510,
        "Public-model bootstrap and target-domain adaptation lifecycle",
        "A public checkpoint enables immediate functional use while a separate evidence-gated lifecycle produces an accepted target-domain checkpoint.",
        "\n".join(body),
    )


def figure_5() -> str:
    body = [
        rect(315, 35, 570, 65, css="accent"),
        text_lines(
            600,
            62,
            [
                "Frozen use-case definition",
                "taxonomy · split · thresholds · hardware condition",
            ],
            leading=21,
        ),
        path([(600, 100), (600, 130), (205, 130), (205, 165)]),
        path([(600, 130), (600, 165)]),
        path([(600, 130), (995, 130), (995, 165)]),
        rect(35, 165, 340, 250, css="group"),
        text(205, 195, "(a) DETECTION / CLASSIFICATION", css="section"),
        text_lines(
            205,
            235,
            [
                "Inputs",
                "held-out labelled images",
                "",
                "Metrics",
                "COCO AP/AR · precision · recall",
                "per-class support · error pairs",
                "",
                "Artifacts",
                "predictions · checksums",
            ],
            leading=20,
        ),
        rect(430, 165, 340, 250, css="group"),
        text(600, 195, "(b) TRACKING / COUNTING", css="section"),
        text_lines(
            600,
            235,
            [
                "Inputs",
                "track-annotated video",
                "",
                "Metrics",
                "visible-count error",
                "unique-count error · ID failures",
                "",
                "Artifacts",
                "track events · count evidence",
            ],
            leading=20,
        ),
        rect(825, 165, 340, 250, css="group"),
        text(995, 195, "(c) EDGE SYSTEM", css="section"),
        text_lines(
            995,
            235,
            [
                "Inputs",
                "fixed device and source condition",
                "",
                "Metrics",
                "latency · throughput · memory",
                "power · thermal · endurance",
                "",
                "Artifacts",
                "profiles · telemetry · logs",
            ],
            leading=20,
        ),
        rect(255, 465, 690, 65, css="soft"),
        text_lines(
            600,
            491,
            [
                "Evidence bundle",
                "environment · model revision · Git revision · configuration · SHA-256",
            ],
            leading=21,
        ),
        line(205, 415, 430, 497),
        line(600, 415, 600, 465),
        line(995, 415, 770, 497),
    ]
    return document(
        1200,
        560,
        "Use-case evaluation and evidence workflow",
        "Detection, counting and edge-system evaluations are separated and joined into one traceable evidence bundle.",
        "\n".join(body),
    )


def figure_6() -> str:
    shares = [
        ("Model forward", 71.10, "bar1"),
        ("Preprocess", 13.69, "bar2"),
        ("Annotate/output", 10.59, "bar3"),
        ("Postprocess", 2.58, "bar4"),
        ("Other", 2.04, "bar5"),
    ]
    x0 = 75
    y0 = 125
    width = 760
    body = [
        text(50, 45, "(a) EXCLUSIVE WALL-TIME SHARE", css="panel", anchor="start"),
        text(
            50,
            73,
            "Mean across three warmed 300-frame full-pipeline runs",
            css="small",
            anchor="start",
        ),
    ]
    cursor = x0
    for label, share, css in shares:
        segment = width * share / 100
        body.append(
            f'<rect class="{css}" x="{cursor}" y="{y0}" width="{segment}" height="62"/>'
        )
        if label == "Model forward":
            fill = "#ffffff" if css in {"bar1", "bar2"} else "#111827"
            body.append(
                f'<text x="{cursor + segment / 2}" y="{y0 + 28}" text-anchor="middle" font-size="14" font-weight="700" fill="{fill}">{escape(label)}</text>'
            )
            body.append(
                f'<text x="{cursor + segment / 2}" y="{y0 + 49}" text-anchor="middle" font-size="13" fill="{fill}">{share:.2f}%</text>'
            )
        cursor += segment
    body.extend(
        [
            '<rect class="bar1" x="75" y="210" width="14" height="14"/>',
            text(96, 222, "Model forward 71.10%", css="tiny", anchor="start"),
            '<rect class="bar2" x="280" y="210" width="14" height="14"/>',
            text(301, 222, "Preprocess 13.69%", css="tiny", anchor="start"),
            '<rect class="bar3" x="470" y="210" width="14" height="14"/>',
            text(491, 222, "Annotation/output 10.59%", css="tiny", anchor="start"),
            '<rect class="bar4" x="690" y="210" width="14" height="14"/>',
            text(711, 222, "Postprocess 2.58%", css="tiny", anchor="start"),
            '<rect class="bar5" x="75" y="238" width="14" height="14"/>',
            text(
                96,
                250,
                "Capture, tracking, SQLite, JSONL and other 2.04%",
                css="tiny",
                anchor="start",
            ),
            text(
                50,
                302,
                "(b) THROUGHPUT AGAINST PROVISIONAL TARGET",
                css="panel",
                anchor="start",
            ),
            text(75, 357, "Measured", css="label", anchor="start"),
            f'<rect class="bar1" x="190" y="337" width="{520 * 5.1877 / 15}" height="28"/>',
            text(
                190 + 520 * 5.1877 / 15 + 12,
                357,
                "5.188 FPS",
                css="small",
                anchor="start",
            ),
            text(75, 407, "Target", css="label", anchor="start"),
            '<rect x="190" y="387" width="520" height="28" fill="#ffffff" stroke="#111827" stroke-width="1.5"/>',
            text(722, 407, "15 FPS", css="small", anchor="start"),
            line(190, 437, 710, 437, css="axis"),
            text(190, 460, "0", css="tiny"),
            text(363, 460, "5", css="tiny"),
            text(537, 460, "10", css="tiny"),
            text(710, 460, "15 FPS", css="tiny"),
            rect(880, 95, 270, 315, css="group"),
            text(905, 130, "Measured condition", css="section", anchor="start"),
            text_lines(
                905,
                165,
                [
                    "Jetson Orin Nano 8 GB",
                    "3 × 300 frames",
                    "10 warm-up calls/run",
                    "mean detector call: 168.62 ms",
                    "population SD: 0.0104 FPS",
                    "whole-board mean: 12.70 W",
                    "peak GPU temperature: 63.94 °C",
                ],
                anchor="start",
                leading=29,
            ),
            text(
                600,
                505,
                "Model forward + preprocessing + annotation/output = 95.38% of measured wall time.",
                css="small",
            ),
        ]
    )
    return document(
        1200,
        540,
        "Jetson Orin Nano full-pipeline latency profile",
        "A scientific stacked bar and throughput comparison summarize three warmed Jetson full-pipeline runs.",
        "\n".join(body),
    )


def figure_7() -> str:
    pairs = [
        ("other_litter → food_wrapper", 31),
        ("other_litter → metal_can", 18),
        ("other_litter → plastic_bag", 17),
        ("other_litter → disposable_cup", 15),
        ("other_litter → plastic_bottle", 10),
        ("disposable_cup → metal_can", 9),
        ("cardboard → food_wrapper", 9),
        ("cardboard → metal_can", 6),
        ("food_wrapper → plastic_bag", 6),
        ("glass_bottle → plastic_bottle", 6),
    ]
    x0 = 430
    chart_width = 650
    body = [
        text(
            35, 38, "Ground-truth class → predicted class", css="small", anchor="start"
        ),
    ]
    for tick in (0, 8, 16, 24, 32):
        x = x0 + chart_width * tick / 32
        body.extend(
            [
                line(x, 55, x, 505, css="grid"),
                text(x, 530, str(tick), css="tiny"),
            ]
        )
    for index, (label, count) in enumerate(pairs):
        y = 65 + index * 43
        bar_width = chart_width * count / 32
        css = "bar1" if index < 5 else "bar2"
        body.extend(
            [
                text(x0 - 18, y + 20, label, css="small", anchor="end"),
                f'<rect class="{css}" x="{x0}" y="{y}" width="{bar_width}" height="25"/>',
                text(
                    x0 + bar_width + 10, y + 19, str(count), css="small", anchor="start"
                ),
            ]
        )
    body.extend(
        [
            text(1145, 530, "count", css="tiny"),
            rect(60, 560, 1080, 50, css="soft"),
            text(
                600,
                591,
                "Diagnostic: 249 localized matches at IoU 0.50; 53 correct-class and 196 wrong-class matches. Not a substitute for COCO AP.",
                css="small",
            ),
        ]
    )
    return document(
        1200,
        630,
        "Top TACO diagnostic class-confusion pairs",
        "The ten most frequent wrong-class pairs after greedy all-class matching at intersection over union 0.50.",
        "\n".join(body),
    )


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    outputs = {
        "figure-1-system-architecture.svg": figure_1(),
        "figure-2-count-semantics.svg": figure_2(),
        "figure-3-deployment-safety-boundary.svg": figure_3(),
        "figure-4-model-adaptation-lifecycle.svg": figure_4(),
        "figure-5-evaluation-evidence-workflow.svg": figure_5(),
        "figure-6-taco-confusions.svg": figure_7(),
        "figure-7-jetson-latency-profile.svg": figure_6(),
    }
    for name, payload in outputs.items():
        destination = FIGURES / name
        destination.write_text(payload, encoding="utf-8")
        print(f"Generated {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
