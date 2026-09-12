#!/usr/bin/env python3
"""
make_trip_revision_figures_v3.py

Publication-grade figures for
  "Risk-Aware Last-Mile Routing under Persistent Disruptions:
   Tail-Risk Planning and Selective Dynamic Recourse"  (TRIP, major revision)

Design principles (V3)
  * One file per figure (multi-panel composites), as requested by Elsevier
    artwork guidelines, instead of one file per panel.
  * Exact physical widths: 180 mm (full width) and 120 mm (1.5 column).
    Figures are saved WITHOUT bbox_inches='tight', so the size on disk is the
    size on the page and fonts stay at their nominal point size.
  * Sans-serif typography (Arial/Helvetica, falling back to Liberation Sans),
    7-7.5 pt text, 9 pt bold panel letters, math set in the same sans font.
  * Colour-blind-safe palette with fixed semantics across figures.
  * Direct labelling instead of legends wherever possible; no gridlines;
    nothing drawn over data.
  * Vector PDF (Type 42 fonts embedded), 600-dpi PNG and 1000-dpi RGB TIFF
    (LZW), i.e. the Elsevier line-art resolution.

Usage
  python make_trip_revision_figures_v3.py                # uses ./figure_data
  python make_trip_revision_figures_v3.py --data DIR --out DIR --zip

All plotted numbers are read from CSV files in figure_data/ (nothing is
hard-coded in the plotting functions).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import math
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch, Rectangle  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

# ----------------------------------------------------------------------------
# User switches
# ----------------------------------------------------------------------------
VERSION = "v3"
PANEL_CASE = "lower"        # "lower" -> a, b, c (Nature/Elsevier)  |  "upper" -> A, B, C
FIG3_WITH_MEAN_PANEL = False  # True adds panel b (mean tardiness) to Fig. 3
PNG_DPI = 600
TIFF_DPI = 1000             # Elsevier: line art >= 1000 dpi

MM = 1 / 25.4
W_FULL = 180 * MM           # full page width
W_MID = 120 * MM            # 1.5 column

# ----------------------------------------------------------------------------
# Palette (Okabe-Ito / Tol derived, colour-blind safe) - fixed semantics
# ----------------------------------------------------------------------------
INK = "#222222"
MUTED = "#6B6B6B"
RULE = "#D0D0D0"
C = {
    "cvar": "#0072B2",      # ALNS-CVaR (proposed tail-risk planning)
    "mean": "#E69F00",      # ALNS-Mean
    "ortools": "#6B6B6B",   # OR-Tools (deterministic)
    "env": "#3B4B8C",       # disruption environment
    "env2": "#B0456E",      # second environment series
    "alns": "#4D4D4D",      # ALNS with adaptive weights (RL comparison)
    "rlff": "#CC6677",      # RL feed-forward
    "rlgru": "#117733",     # RL GRU
    "dddas": "#6A3D9A",     # DDDAS recourse
    "improve": "#1A9E77",
    "tie": "#A0A0A0",
    "worsen": "#D55E00",
    "retained": "#DCDCDC",
}


def pick_font() -> str:
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Arial", "Helvetica", "Helvetica Neue", "Liberation Sans",
                 "TeX Gyre Heros", "DejaVu Sans"):
        if name in available:
            return name
    return "DejaVu Sans"


FONT = pick_font()
FS = 7.0            # base size (tick labels, annotations)
FS_LABEL = 7.5      # axis labels, panel titles
FS_SMALL = 6.4      # secondary annotations
FS_LETTER = 9.0     # panel letters

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [FONT, "DejaVu Sans"],
    "font.size": FS,
    "axes.labelsize": FS_LABEL,
    "axes.titlesize": FS_LABEL,
    "xtick.labelsize": FS,
    "ytick.labelsize": FS,
    "legend.fontsize": FS,
    "axes.linewidth": 0.6,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "axes.labelpad": 3.0,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": INK,
    "ytick.color": INK,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.8,
    "ytick.major.size": 2.8,
    "xtick.major.pad": 2.0,
    "ytick.major.pad": 2.0,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "text.color": INK,
    "lines.linewidth": 1.3,
    "lines.markersize": 4.2,
    "lines.solid_capstyle": "round",
    "legend.frameon": False,
    "legend.handlelength": 1.2,
    "legend.handletextpad": 0.5,
    "legend.columnspacing": 1.2,
    "hatch.linewidth": 0.45,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "mathtext.fontset": "custom",
    "mathtext.rm": FONT,
    "mathtext.sf": FONT,
    "mathtext.it": f"{FONT}:italic",
    "mathtext.bf": f"{FONT}:bold",
    "mathtext.cal": FONT,
    "mathtext.fallback": "stixsans",
    "axes.unicode_minus": True,
    "figure.dpi": 150,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "figure.constrained_layout.h_pad": 2.5 / 72,
    "figure.constrained_layout.w_pad": 2.5 / 72,
})


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def L(letter: str) -> str:
    return letter.lower() if PANEL_CASE == "lower" else letter.upper()


LETTER_OFFSET = 30  # pt, distance of panel letter to the left of the y spine


def panel(ax, letter=None, title=None, note=None, offset=LETTER_OFFSET, pad=7):
    """Panel letter (bold), short title (regular) and optional right-aligned note."""
    if letter is not None:
        ax.annotate(L(letter), xy=(0, 1), xycoords="axes fraction",
                    xytext=(-offset, pad), textcoords="offset points",
                    ha="left", va="baseline", fontsize=FS_LETTER, fontweight="bold")
    if title is not None:
        ax.annotate(title, xy=(0, 1), xycoords="axes fraction",
                    xytext=(-offset + 10 if letter is not None else 0, pad),
                    textcoords="offset points", ha="left", va="baseline",
                    fontsize=FS_LABEL)
    if note is not None:
        ax.annotate(note, xy=(1, 1), xycoords="axes fraction", xytext=(0, pad),
                    textcoords="offset points", ha="right", va="baseline",
                    fontsize=FS_SMALL, color=MUTED)


def eta_axis(ax, etas, nominal=0.35, right_pad=0.04):
    ax.set_xlim(min(etas) - 0.04, max(etas) + right_pad)
    ax.spines["bottom"].set_bounds(min(etas), max(etas))
    labels = []
    for e in etas:
        s = f"{e:.2f}".rstrip("0").rstrip(".") if e != 0 else "0"
        if abs(e - nominal) < 1e-9:
            s += "\n(nominal)"
        labels.append(s)
    ax.set_xticks(etas, labels)
    ax.set_xlabel(r"Hawkes branching ratio, $\eta$")
    x0, x1 = ax.get_xlim()
    # keep automatic vertical placement, centre horizontally on the drawn spine
    ax.xaxis.label.set_x(((min(etas) + max(etas)) / 2 - x0) / (x1 - x0))


def save(fig, stem: str, out: Path):
    fig.savefig(out / "pdf" / f"{stem}.pdf")
    fig.savefig(out / "png" / f"{stem}.png", dpi=PNG_DPI)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=TIFF_DPI)
    buf.seek(0)
    Image.open(buf).convert("RGB").save(out / "tiff" / f"{stem}.tiff",
                                        compression="tiff_lzw",
                                        dpi=(TIFF_DPI, TIFF_DPI))
    plt.close(fig)


def bracket(ax, x0, x1, y, h, text=None, above=True, ha="center", tx=None,
            color=INK, fs=FS_SMALL, lw=0.6, text_color=None, gap=0.06):
    """Square bracket spanning [x0, x1] (data coords) with a label."""
    s = 1 if above else -1
    ax.plot([x0, x0, x1, x1], [y - s * h, y, y, y - s * h], color=color, lw=lw,
            solid_joinstyle="miter", clip_on=False)
    if text:
        if tx is None:
            tx = {"center": (x0 + x1) / 2, "left": x0, "right": x1}[ha]
        ax.text(tx, y + s * gap, text, ha=ha, va="bottom" if above else "top",
                fontsize=fs, color=text_color or color, clip_on=False,
                linespacing=1.25)


# ----------------------------------------------------------------------------
# Figure 1 - conceptual architecture (drawn in millimetre coordinates)
# ----------------------------------------------------------------------------
def fig1(out: Path):
    H = 104
    fig = plt.figure(figsize=(W_FULL, H * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 180)
    ax.set_ylim(0, H)
    ax.axis("off")

    def band(y0, y1, fc, label, sub, where="top"):
        """Shaded layer; its title sits at the layer's outer edge."""
        ax.add_patch(FancyBboxPatch((2, y0), 176, y1 - y0,
                                    boxstyle="round,pad=0,rounding_size=2.2",
                                    fc=fc, ec="none", zorder=0))
        if where == "top":
            t = ax.text(5, y1 - 2.4, label, ha="left", va="top", fontsize=6.3,
                        fontweight="bold", color=MUTED)
            bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
            x_end = 5 + bb.width / fig.bbox.width * 180
            ax.text(x_end + 2.5, y1 - 2.4, "·  " + sub, ha="left", va="top",
                    fontsize=6.3, style="italic", color=MUTED)
        else:
            ax.text(5, y0 + 6.6, label, ha="left", va="bottom", fontsize=6.3,
                    fontweight="bold", color=MUTED)
            ax.text(5, y0 + 2.6, sub, ha="left", va="bottom", fontsize=6.3,
                    style="italic", color=MUTED)

    def node(x, y, w, h, title, body=(), fc="white", ec="#8A8A8A", lw=0.7,
             tcolor=INK):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0,rounding_size=1.6",
                                    fc=fc, ec=ec, lw=lw, zorder=2))
        lines = [title] + list(body)
        lh = 3.25
        top = y + h / 2 + (len(lines) - 1) * lh / 2
        for i, s in enumerate(lines):
            ax.text(x + w / 2, top - i * lh, s, ha="center", va="center",
                    fontsize=7.1 if i == 0 else 6.6,
                    fontweight="bold" if i == 0 else "normal",
                    color=tcolor if i == 0 else INK, zorder=3)

    def arrow(p0, p1, color="#555555", lw=0.8, ls="-", rad=0.0):
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=6.5,
                                     lw=lw, color=color, linestyle=ls,
                                     shrinkA=0, shrinkB=0, zorder=4,
                                     connectionstyle=f"arc3,rad={rad}"))

    env_fc, env_ec = "#E8EDF6", "#8190B8"
    band(52, 102, "#F4F6FA", "EXOGENOUS STOCHASTIC ENVIRONMENT",
         "common to all routing methods")
    band(2, 48, "#F6F6F6", "ROUTING DECISIONS AND EXECUTION",
         "routes differ only in when they sample the environment", where="bottom")

    # Row A: disruption chain + baseline uncertainty
    yA, hA = 79, 15
    node(5, yA, 30, hA, "Disruption events", ["exogenous Hawkes process"],
         env_fc, env_ec, tcolor=C["env"])
    node(43, yA, 20, hA, "Excitation", [r"state $m(t)$"], env_fc, env_ec,
         tcolor=C["env"])
    node(71, yA, 31, hA, r"OMI$(t)$", ["Operational Memory Index"], env_fc,
         env_ec, tcolor=C["env"])
    node(110, yA, 29, hA, "Multiplier", [r"$1+\kappa\,\mathrm{OMI}(t)$"],
         env_fc, env_ec, tcolor=C["env"])
    node(144, yA, 31, hA, "Baseline OD", ["PERT uncertainty",
                                          r"$B_{ij}^{(\omega)}$"],
         "white", "#8A8A8A")
    yc = yA + hA / 2
    for x0, x1 in [(35, 43), (63, 71), (102, 110)]:
        arrow((x0, yc), (x1, yc), color=C["env"])

    # Row B: effective arc travel time
    node(110, 57, 65, 14, "Effective arc travel time",
         [r"$B_{ij}^{(\omega)}\,[\,1+\kappa\,\mathrm{OMI}(t)\,]$"],
         "white", INK, lw=0.9)
    arrow((124.5, yA), (124.5, 71), color=C["env"])
    arrow((159.5, yA), (159.5, 71), color="#555555")

    # Row C: planning -> plan -> execution
    yC, hC = 26, 14
    node(5, yC, 50, hC, "Pre-operational planning",
         ["ALNS-Mean / ALNS-CVaR", "RL operator-selection experiment"],
         "#E6F0F8", C["cvar"], tcolor=C["cvar"])
    node(66, yC, 32, hC, "Route plan", ["customer order +", "vehicle assignment"])
    node(110, yC, 65, hC, "Sequential execution",
         ["route-dependent departures,", "waiting, service, tardiness"],
         "white", INK, lw=0.9)
    arrow((55, yC + hC / 2), (66, yC + hC / 2))
    arrow((98, yC + hC / 2), (110, yC + hC / 2))

    # travel time sampled by execution
    arrow((142.5, 57), (142.5, yC + hC), color=INK, lw=0.9)
    ax.text(145, 44.2, "sampled at route-dependent\ndeparture times",
            ha="left", va="center", fontsize=6.3, style="italic", color=MUTED,
            linespacing=1.2)

    # Row D: DDDAS recourse loop
    node(66, 5, 109, 13, "Causal DDDAS recourse",
         ["observed Hawkes prefix + completed travel times",
          "bounded residual-suffix ALNS-CVaR"],
         "#F1EBF6", C["dddas"], tcolor=C["dddas"])
    arrow((163, yC), (163, 18), color=C["dddas"])
    arrow((122, 18), (122, yC), color=C["dddas"])
    ax.text(161, 22, "observed state", ha="right", va="center", fontsize=6.3,
            style="italic", color=C["dddas"])
    ax.text(120, 22, "revised suffix", ha="right", va="center", fontsize=6.3,
            style="italic", color=C["dddas"])

    # Excluded feedback: route -> Hawkes
    xf = 20
    arrow((xf, yC + hC), (xf, yA), color="#9A9A9A", lw=0.8, ls=(0, (3, 2)))
    yx = 60.5
    ax.add_patch(plt.Circle((xf, yx), 2.3, fc="white", ec=C["worsen"], lw=0.9,
                            zorder=5))
    d = 2.3 / math.sqrt(2)
    ax.plot([xf - d, xf + d], [yx + d, yx - d], color=C["worsen"], lw=0.9,
            zorder=6)
    ax.text(xf + 5, yx + 1.6, "No route-to-Hawkes feedback", ha="left",
            va="center", fontsize=6.8, fontweight="bold", color=INK)
    ax.text(xf + 5, yx - 1.9, "disruptions are exogenous to routing decisions",
            ha="left", va="center", fontsize=6.3, color=MUTED)

    save(fig, f"Fig1_architecture_{VERSION}", out)


# ----------------------------------------------------------------------------
# Figure 2 - environment diagnostics
# ----------------------------------------------------------------------------
def fig2(env: pd.DataFrame, out: Path):
    fig, axs = plt.subplots(1, 3, figsize=(W_FULL, 60 * MM), layout="constrained")
    eta = env["eta"].to_numpy()
    mk = dict(mec="white", mew=0.6, zorder=3)

    ax = axs[0]
    ax.hlines(1, eta.min(), eta.max(), color=MUTED, lw=0.6, ls=(0, (3, 2)),
              zorder=1)
    ax.text(eta.max(), 1.25, "Poisson", ha="right", va="bottom",
            fontsize=FS_SMALL, color=MUTED)
    ax.plot(eta, env["fano"], "-o", color=C["env"], **mk)
    ax.set_ylim(0, 12.5)
    ax.set_yticks([0, 4, 8, 12])
    ax.set_ylabel("Fano factor of event counts")
    eta_axis(ax, eta)
    panel(ax, "a", "Event clustering")

    ax = axs[1]
    ax.plot(eta, 100 * env["p_event_60"], "-^", color=C["env"], ms=4.6, **mk)
    ax.plot(eta, 100 * env["p_no_event"], "-s", color=C["env2"], ms=3.9, **mk)
    ax.text(0.0, 64.5, "Event within first 60 min", ha="left", va="bottom",
            fontsize=FS_SMALL, color=C["env"])
    ax.text(0.0, 4.5, "No event over horizon", ha="left", va="bottom",
            fontsize=FS_SMALL, color=C["env2"])
    ax.set_ylim(0, 70)
    ax.set_yticks([0, 20, 40, 60])
    ax.set_ylabel("Probability (%)")
    eta_axis(ax, eta)
    panel(ax, "b", "Temporal concentration")

    ax = axs[2]
    ax.plot(eta, env["mean_time_omi"], "-D", color=C["env"], ms=3.8, **mk)
    ax.set_ylim(0.03, 0.08)
    ax.set_yticks([0.03, 0.04, 0.05, 0.06, 0.07, 0.08])
    ax.set_ylabel("Time-averaged OMI")
    ax.text(0.0, 0.0315, "Lower mean exposure does not\nimply lower tail risk",
            ha="left", va="bottom", fontsize=FS_SMALL, style="italic",
            color=MUTED, linespacing=1.25)
    eta_axis(ax, eta)
    panel(ax, "c", "Mean environmental exposure")

    fig.get_layout_engine().set(wspace=0.08)
    save(fig, f"Fig2_environment_{VERSION}", out)


# ----------------------------------------------------------------------------
# Figure 3 - tail risk vs persistence (mean-impact-matched control)
# ----------------------------------------------------------------------------
def fig3(pers: pd.DataFrame, out: Path):
    methods = [("OR-Tools", C["ortools"], "o", 1.2),
               ("ALNS-Mean", C["mean"], "s", 1.2),
               ("ALNS-CVaR", C["cvar"], "D", 1.6)]
    if FIG3_WITH_MEAN_PANEL:
        fig, axs = plt.subplots(1, 2, figsize=(W_FULL, 68 * MM), layout="constrained")
        specs = [(axs[0], "cvar95", r"CVaR$_{0.95}$ of total tardiness", "a",
                  "Upper-tail tardiness", (0, 125)),
                 (axs[1], "mean_tardiness", "Mean total tardiness", "b",
                  "Mean tardiness", (0, 20))]
    else:
        fig, ax = plt.subplots(figsize=(W_MID, 72 * MM), layout="constrained")
        specs = [(ax, "cvar95", r"CVaR$_{0.95}$ of total tardiness", None, None,
                  (0, 125))]

    for ax, col, ylabel, letter, title, ylim in specs:
        etas = np.sort(pers["eta"].unique())
        for name, color, marker, lw in methods:
            d = pers[pers["method"] == name].sort_values("eta")
            ax.plot(d["eta"], d[col], marker=marker, color=color, lw=lw,
                    ms=4.4 if marker != "D" else 4.0, mec="white", mew=0.5,
                    zorder=3)
            ax.text(etas.max() + 0.03, d[col].iloc[-1], name, ha="left",
                    va="center", fontsize=FS, color=color,
                    fontweight="bold" if name == "ALNS-CVaR" else "normal")
        ax.set_ylim(*ylim)
        ax.yaxis.set_major_locator(MaxNLocator(6, integer=True))
        ax.set_ylabel(ylabel)
        eta_axis(ax, etas, right_pad=0.21)
        if letter:
            panel(ax, letter, title)
    name = f"Fig3_tailrisk_persistence_{VERSION}"
    save(fig, name, out)


# ----------------------------------------------------------------------------
# Figure 4 - nine-day forest plots
# ----------------------------------------------------------------------------
def fig4(cross: pd.DataFrame, overall: pd.DataFrame, out: Path):
    fig, axs = plt.subplots(1, 2, figsize=(W_FULL, 78 * MM), sharey=True,
                            layout="constrained")
    days = cross["day"].to_numpy()
    y = np.arange(len(days))
    oy = len(days) + 0.55
    specs = [
        (axs[0], "delta_J", "a", "Tail-risk objective",
         r"$\Delta J_{\mathrm{CVaR}}$  (ALNS-Mean $-$ ALNS-CVaR)"),
        (axs[1], "delta_tail", "b", "Tail tardiness",
         r"$\Delta\,\mathrm{CVaR}_{0.95}(Z)$  (ALNS-Mean $-$ ALNS-CVaR)"),
    ]
    col = C["cvar"]
    for ax, metric, letter, title, xlabel in specs:
        v = cross[metric].to_numpy()
        o = overall.set_index("metric").loc[metric]
        ax.axvline(0, color=INK, lw=0.6, zorder=1)
        ax.vlines(o["mean"], -0.6, len(days) - 0.4, color=col, lw=0.6,
                  ls=(0, (2, 2)), alpha=0.7, zorder=1)
        ax.hlines(y, 0, v, color="#C9C9C9", lw=0.9, zorder=2)
        ax.scatter(v, y, s=20, color=col, edgecolor="white", linewidth=0.5,
                   zorder=3)
        ax.axhline(len(days) - 0.25, color=RULE, lw=0.5)
        ax.errorbar(o["mean"], oy, xerr=[[o["mean"] - o["ci_low"]],
                                         [o["ci_high"] - o["mean"]]],
                    fmt="D", ms=5.2, color=col, mec="white", mew=0.5,
                    ecolor=col, elinewidth=1.0, capsize=2.4, capthick=1.0,
                    zorder=4)
        ax.text(o["ci_high"] + 0.5, oy,
                f"{o['mean']:.1f} [{o['ci_low']:.1f}, {o['ci_high']:.1f}]",
                ha="left", va="center", fontsize=FS_SMALL, color=INK)
        n_pos = int((v > 0).sum())
        ax.set_xlim(-1.0, 16.5)
        ax.set_xticks([0, 5, 10, 15])
        ax.spines["bottom"].set_bounds(0, 15)
        ax.set_xlabel(xlabel)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0, pad=3)
        panel(ax, letter, title, note=f"{n_pos}/{len(days)} days favour ALNS-CVaR",
              offset=40 if letter == "a" else 6)
    axs[0].set_yticks(list(y) + [oy],
                      [f"Day {d}" for d in days] + ["Mean (95% CI)"])
    axs[0].set_ylim(oy + 0.8, -0.8)
    fig.get_layout_engine().set(wspace=0.06)
    save(fig, f"Fig4_crossday_{VERSION}", out)


# ----------------------------------------------------------------------------
# Figure 5 - learned operator selection
# ----------------------------------------------------------------------------
def fig5(rl: pd.DataFrame, cost: pd.DataFrame, out: Path):
    fig, axs = plt.subplots(1, 3, figsize=(W_FULL, 62 * MM), layout="constrained",
                            gridspec_kw={"width_ratios": [1, 1, 1.15]})
    style = {"ALNS": (C["alns"], "o"), "RL-FF": (C["rlff"], "s"),
             "RL-GRU": (C["rlgru"], "D")}
    specs = [(axs[0], "Mean", "a", "Mean-oriented search",
              r"Aligned objective, $J_{\mathrm{mean}}$"),
             (axs[1], "CVaR", "b", "CVaR-oriented search",
              r"Aligned objective, $J_{\mathrm{CVaR}}$")]
    for ax, crit, letter, title, ylabel in specs:
        d = rl[rl["criterion"] == crit].reset_index(drop=True)
        ref = d.loc[d["method"] == "ALNS", "objective_mean"].iloc[0]
        ax.axhline(ref, color=RULE, lw=0.6, ls=(0, (2, 2)), zorder=1)
        for i, r in d.iterrows():
            color, marker = style[r["method"]]
            ax.errorbar(i, r["objective_mean"], yerr=r["objective_sd"], fmt=marker,
                        ms=4.6 if marker != "D" else 4.2, color=color, mec="white",
                        mew=0.5, ecolor=color, elinewidth=1.0, capsize=2.4,
                        capthick=1.0, zorder=3)
        ax.set_xticks(range(len(d)), d["method"])
        ax.set_xlim(-0.6, len(d) - 0.4)
        ax.yaxis.set_major_locator(MaxNLocator(5, integer=True, steps=[1, 2, 5, 10]))
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", length=0, pad=4)
        panel(ax, letter, title, note="mean ± s.d.")

    ax = axs[2]
    labels = ["Frozen-policy\nsearch", "Offline policy\ntraining"]
    vals = cost["evaluations_thousands"].to_numpy()
    ypos = [1, 0]
    ax.barh(ypos, vals, height=0.52, color=["#B5B5B5", "#4D4D4D"], zorder=2)
    ratio = vals[1] / vals[0]
    ax.text(vals[0] + 5, 1, f"{vals[0]:.1f}", ha="left", va="center", fontsize=FS)
    ax.text(vals[1] - 6, 0, f"{vals[1]:.0f}", ha="right", va="center",
            fontsize=FS, color="white", fontweight="bold")
    ax.annotate("", xy=(vals[1], 0.5), xytext=(vals[0], 0.5),
                arrowprops=dict(arrowstyle="-|>", lw=0.7, color=MUTED,
                                mutation_scale=6, shrinkA=0, shrinkB=0))
    ax.text((vals[0] + vals[1]) / 2, 0.57, f"≈{ratio:.1f}×", ha="center",
            va="bottom", fontsize=FS, fontweight="bold", color=INK)
    ax.set_yticks(ypos, labels)
    ax.set_ylim(-0.55, 1.55)
    ax.set_xlim(0, 255)
    ax.set_xticks([0, 50, 100, 150, 200, 250])
    ax.set_xlabel(r"Scenario evaluations ($\times 10^{3}$)")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=3)
    panel(ax, "c", "Computational burden", note="per policy", offset=52)
    fig.get_layout_engine().set(wspace=0.10)
    save(fig, f"Fig5_RL_{VERSION}", out)


# ----------------------------------------------------------------------------
# Figure 6 - DDDAS realized effects and operational selectivity
# ----------------------------------------------------------------------------
def fig6(dd: pd.DataFrame, counts: pd.DataFrame, out: Path):
    fig = plt.figure(figsize=(W_FULL, 132 * MM), layout="constrained")
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 0.82])
    top = [fig.add_subplot(gs[0, i]) for i in range(3)]
    axd = fig.add_subplot(gs[1, :])

    specs = [("delta_J", "a", "Composite objective",
              r"$\Delta J_{\mathrm{realized}}$  (static $-$ DDDAS)", None),
             ("delta_T", "b", "Tardiness",
              r"$\Delta Z_{\mathrm{realized}}$  (static $-$ DDDAS)", (-0.5, 1.6)),
             ("delta_D", "c", "Distance",
              r"$\Delta D_{\mathrm{realized}}$  (static $-$ DDDAS)", (-1.3, 0.5))]
    col = C["dddas"]
    for ax, (metric, letter, title, ylabel, ylim) in zip(top, specs):
        d = dd[dd["metric"] == metric].sort_values("day")
        x = np.arange(len(d))
        m, lo, hi = (d[k].to_numpy() for k in ("mean", "low", "high"))
        ax.axhline(0, color=INK, lw=0.6, zorder=1)
        ax.errorbar(x, m, yerr=[m - lo, hi - m], fmt="o", ms=4.6, color=col,
                    mec="white", mew=0.5, ecolor=col, elinewidth=1.0,
                    capsize=2.4, capthick=1.0, zorder=3)
        ax.set_xticks(x, [f"Day {int(v)}" for v in d["day"]])
        ax.set_xlim(-0.5, len(d) - 0.5)
        ax.tick_params(axis="x", length=0, pad=4)
        if ylim:
            ax.set_ylim(*ylim)
        else:
            lo_, hi_ = lo.min(), hi.max()
            span = hi_ - lo_
            ax.set_ylim(lo_ - 0.22 * span, hi_ + 0.14 * span)
        ax.yaxis.set_major_locator(MaxNLocator(5, steps=[1, 2, 4, 5, 10]))
        ax.set_ylabel(ylabel)
        ax.text(0.03, 0.97, "↑ favours DDDAS", transform=ax.transAxes, ha="left",
                va="top", fontsize=FS_SMALL, color=MUTED)
        ax.text(0.03, 0.03, "↓ favours static plan", transform=ax.transAxes,
                ha="left", va="bottom", fontsize=FS_SMALL, color=MUTED)
        panel(ax, letter, title, note="mean, 95% CI" if letter == "a" else None)

    # ---- panel d: proportional bars with separate denominators --------------
    cnt = {(r.level, r.category): int(r.count) for r in counts.itertuples()}
    nA = cnt[("attempt", "total")]
    ch_cap = cnt[("attempt", "changed_capped")]
    ch_unc = cnt[("attempt", "changed")] - ch_cap
    re_cap = cnt[("attempt", "capped")] - ch_cap
    re_unc = nA - ch_unc - ch_cap - re_cap
    n_changed = ch_unc + ch_cap
    n_capped = ch_cap + re_cap
    n_gain = cnt[("attempt", "changed_positive_conditional_gain")]

    nR = cnt[("run", "total")]
    r_imp, r_tie, r_wor = (cnt[("run", k)] for k in ("improve", "tie", "worsen"))
    r_chg = r_imp + r_tie + r_wor
    r_none = nR - r_chg
    assert r_chg == cnt[("run", "with_change")], "run counts inconsistent"

    pA = lambda k: 100 * k / nA  # noqa: E731
    pR = lambda k: 100 * k / nR  # noqa: E731
    yA, yR, bh = 2.05, 0.45, 0.46

    def seg(ax, left, width, yc, fc, hatch=None, text=None, tcolor=INK, bold=False):
        ax.barh(yc, width, left=left, height=bh, color=fc, edgecolor="none",
                zorder=2)
        if hatch:
            ax.barh(yc, width, left=left, height=bh, color="none",
                    edgecolor="#5A5A5A", hatch=hatch, lw=0, zorder=3)
        if text:
            ax.text(left + width / 2, yc, text, ha="center", va="center",
                    fontsize=FS, color=tcolor, zorder=4,
                    fontweight="bold" if bold else "normal",
                    bbox=dict(boxstyle="round,pad=0.15", fc=fc, ec="none")
                    if hatch else None)

    # attempts
    x = 0
    seg(axd, x, pA(ch_unc), yA, col, text=f"{ch_unc}", tcolor="white", bold=True)
    x += pA(ch_unc)
    seg(axd, x, pA(ch_cap), yA, col, hatch="//////")
    x += pA(ch_cap)
    seg(axd, x, pA(re_cap), yA, C["retained"], hatch="//////", text=f"{re_cap}")
    x += pA(re_cap)
    seg(axd, x, pA(re_unc), yA, C["retained"], text=f"{re_unc}")
    for xb in np.cumsum([pA(ch_unc), pA(ch_cap), pA(re_cap)]):
        axd.plot([xb, xb], [yA - bh / 2, yA + bh / 2], color="white", lw=0.6,
                 zorder=5)

    top_y = yA + bh / 2 + 0.12
    bracket(axd, 0, pA(n_changed), top_y, 0.08,
            f"Route changed: {n_changed} ({pA(n_changed):.1f}%)", ha="left",
            color=col)
    axd.text(0, top_y + 0.40,
             f"{n_gain}/{n_changed} with positive conditional search gain",
             ha="left", va="bottom", fontsize=FS_SMALL, color=col,
             fontweight="bold")
    bracket(axd, pA(n_changed), 100, top_y, 0.08,
            f"Route retained: {nA - n_changed} ({pA(nA - n_changed):.1f}%)",
            ha="center", color=MUTED)
    bracket(axd, pA(ch_unc), pA(ch_unc) + pA(n_capped), yA - bh / 2 - 0.12, 0.08,
            f"Cap-terminated searches: {n_capped} ({pA(n_capped):.1f}%), "
            f"of which {ch_cap} changed the route",
            above=False, ha="left", color=MUTED)

    # runs
    x = 0
    seg(axd, x, pR(r_imp), yR, C["improve"], text=f"{r_imp}", tcolor="white",
        bold=True)
    x += pR(r_imp)
    seg(axd, x, pR(r_tie), yR, C["tie"])
    x += pR(r_tie)
    seg(axd, x, pR(r_wor), yR, C["worsen"], text=f"{r_wor}", tcolor="white",
        bold=True)
    x += pR(r_wor)
    seg(axd, x, pR(r_none), yR, C["retained"], text=f"{r_none}")
    for xb in np.cumsum([pR(r_imp), pR(r_tie), pR(r_wor)]):
        axd.plot([xb, xb], [yR - bh / 2, yR + bh / 2], color="white", lw=0.6,
                 zorder=5)
    top_y = yR + bh / 2 + 0.12
    bracket(axd, 0, pR(r_chg), top_y, 0.08,
            f"Runs with ≥1 route change: {r_chg} ({pR(r_chg):.1f}%)", ha="left",
            color=INK)
    bracket(axd, pR(r_chg), 100, top_y, 0.08,
            f"No route change: {r_none} ({pR(r_none):.1f}%)", ha="center",
            color=MUTED)

    handles = [Patch(fc=C["improve"], ec="none", label=f"improves ({r_imp})"),
               Patch(fc=C["tie"], ec="none", label=f"ties ({r_tie})"),
               Patch(fc=C["worsen"], ec="none", label=f"worsens ({r_wor})")]
    leg = axd.legend(handles=handles, ncol=3, loc="upper left",
                     bbox_to_anchor=(0.0, -0.20), title_fontsize=FS_SMALL,
                     fontsize=FS_SMALL, handlelength=0.9, handleheight=0.9,
                     borderaxespad=0, title="Realized $J$ of changed runs vs. static plan:",
                     alignment="left")
    leg._legend_box.align = "left"
    leg.get_title().set_color(MUTED)

    axd.set_xlim(0, 100)
    axd.set_ylim(-0.05, 3.08)
    axd.set_yticks([yA, yR], [f"Recourse attempts\n(n = {nA})",
                              f"Complete paired runs\n(n = {nR})"])
    axd.tick_params(axis="y", length=0, pad=4)
    axd.spines["left"].set_visible(False)
    axd.spines["bottom"].set_bounds(0, 100)
    axd.set_xticks([0, 25, 50, 75, 100])
    axd.set_xlabel("Share of attempts or runs (%)  — separate denominators",
                   labelpad=2)
    axd.xaxis.set_label_coords(0.5, -0.105)
    panel(axd, "d", "Operational selectivity of recourse")
    fig.get_layout_engine().set(hspace=0.06, wspace=0.07)
    save(fig, f"Fig6_DDDAS_{VERSION}", out)


# ----------------------------------------------------------------------------
# LaTeX, notes, contact sheet, manifest
# ----------------------------------------------------------------------------
def latex_block() -> str:
    a, b, c, d = (L(x) for x in "abcd")
    fig3_caption_b = (f" ({b}) Mean total tardiness for the same runs." if FIG3_WITH_MEAN_PANEL
                      else "")
    fig3_width = r"\textwidth" if FIG3_WITH_MEAN_PANEL else r"0.667\textwidth"
    return rf"""% TRIP revision figures {VERSION.upper()}
% One composite file per figure. Figures are drawn at 180 mm (full width) or
% 120 mm (Fig. 3); include them at the widths below so fonts stay at 7-7.5 pt.
% Requires \usepackage{{graphicx}}.

% Figure 1 - end of Related Work
\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig1_architecture_{VERSION}.pdf}}
\caption{{\textbf{{Conceptual architecture of persistent-risk routing.}}
The disruption process is exogenous to routing. Baseline OD uncertainty and the Hawkes-derived OMI jointly determine effective arc travel times, while route choices determine the departure times at which the common environmental state is sampled. Preoperational risk-aware planning is followed by sequential execution. The DDDAS layer uses only the observed disruption prefix and completed travel times to reconsider the unexecuted vehicle suffix; the revised suffix then returns to the execution layer. No route-to-Hawkes feedback is assumed (crossed dashed arrow).}}
\label{{fig:architecture}}
\end{{figure*}}

% Figure 2 - Results: environmental persistence validation
\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig2_environment_{VERSION}.pdf}}
\caption{{\textbf{{Persistence reorganizes disruption activity under matched stationary event intensity.}}
({a}) Event-count overdispersion rises sharply with the Hawkes branching ratio; the dashed line marks the Poisson reference (Fano factor $=1$). ({b}) Higher persistence produces more event-free horizons and fewer early events, consistent with longer quiet intervals separated by clustered disruption episodes. ({c}) Time-averaged OMI decreases as exposure becomes more intermittent; this lower mean should not be interpreted as lower upper-tail routing risk. Environmental diagnostics use 10,000 trajectories per persistence regime.}}
\label{{fig:persistence_environment}}
\end{{figure*}}

% Figure 3 - Results: mean-impact-matched control
\begin{{figure}}[t]
\centering
\includegraphics[width={fig3_width}]{{figures/Fig3_tailrisk_persistence_{VERSION}.pdf}}
\caption{{\textbf{{Routing tail risk under the mean-environmental-impact-matched persistence control.}}
Upper-tail tardiness rises strongly with persistence even though the continuous-time mean environmental travel-time multiplier is matched across regimes. OR-Tools uses the same deterministic route across persistence levels; ALNS-Mean and ALNS-CVaR use the same adaptive search engine but optimize different risk functionals. Values are averages over ten paired repetitions.{fig3_caption_b}}}
\label{{fig:tailrisk_persistence}}
\end{{figure}}

% Figure 4 - Results: headline nine-day result
\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig4_crossday_{VERSION}.pdf}}
\caption{{\textbf{{Cross-instance gains from explicit CVaR-oriented planning.}}
Day-level contrasts compare ALNS-Mean with ALNS-CVaR after averaging the three paired optimization repetitions within each operational day; positive values favour CVaR-oriented search. ({a}) The aligned tail-risk objective improves on all nine days. ({b}) $\mathrm{{CVaR}}_{{0.95}}$ tardiness likewise improves on all nine days. The diamond and the dashed vertical line report the across-day mean; the horizontal bar is the bootstrap 95\% confidence interval (values printed in brackets).}}
\label{{fig:crossday_cvar}}
\end{{figure*}}

% Figure 5 - Results: RL
\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig5_RL_{VERSION}.pdf}}
\caption{{\textbf{{Source-day performance and computational burden of learned operator selection.}}
({a},{b}) Points show the mean aligned objective and error bars one standard deviation over ten paired Day~1 repetitions; the dotted line marks the ALNS mean. These panels summarize descriptive source-day variability; the paired inferential comparisons reported in the text do not establish a robust learned-policy advantage. ({c}) Offline policy fitting requires approximately $2.3\times10^5$ scenario evaluations per policy, about 9.2 times the stochastic evaluation budget of one frozen-policy search.}}
\label{{fig:rl_validation}}
\end{{figure*}}

% Figure 6 - Results: DDDAS
\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig6_DDDAS_{VERSION}.pdf}}
\caption{{\textbf{{Realized effects and operational selectivity of causal DDDAS recourse.}}
Static-minus-DDDAS contrasts are shown for ({a}) realized composite objective, ({b}) realized tardiness and ({c}) realized distance; positive values favour DDDAS. Points are means over 20 realized environmental paths after averaging the three frozen route replicates; error bars are path-bootstrap 95\% confidence intervals. ({d}) Attempt-level and run-level outcomes are shown as proportions of their own denominators to avoid mixing units. Only 87 of 523 recourse attempts modify a route (hatching marks the 194 cap-terminated searches, 3 of which changed the route), and 115 of 180 complete runs contain no route change. Every executed route modification improves the local conditional search objective, but realized full-run cost does not improve systematically (18 of the 65 changed runs improve, 3 tie and 44 worsen relative to the static plan).}}
\label{{fig:dddas}}
\end{{figure*}}
"""


def preview_tex(latex: str) -> str:
    body = latex.replace("figures/", "pdf/")
    return (r"""\documentclass[10pt]{article}
% Proof layout: 180 mm text block = Elsevier full-page figure width.
\usepackage[a4paper,textwidth=180mm,top=18mm,bottom=20mm]{geometry}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{helvet}
\usepackage[font=small,labelfont=bf]{caption}
\begin{document}
""" + body + r"""
\end{document}
""")


NOTES = f"""# TRIP revision figures {VERSION.upper()}

## What changed relative to V2

General
- One composite file per figure (Fig1-Fig6) instead of one file per panel. This
  guarantees identical fonts, line weights and panel sizes inside each figure and
  matches Elsevier artwork requirements (one file per figure).
- Exact physical sizes: 180 mm wide (full width) and 120 mm (Fig. 3). Files are
  saved without tight cropping, so the size on disk equals the printed size.
- Typography: Arial/Helvetica (fallback Liberation Sans, metric-compatible with
  Arial), 7-7.5 pt text, 9 pt bold panel letters ({L('a')}, {L('b')}, ...), maths set in
  the same sans-serif font. Fonts are embedded as TrueType (Type 42) in the PDFs.
- Colour-blind-safe palette with fixed meaning across figures: blue = ALNS-CVaR,
  orange = ALNS-Mean, grey = OR-Tools, indigo = disruption environment,
  purple = DDDAS.
- No gridlines, no legends where direct labels suffice, nothing drawn over data.
- Outputs: vector PDF, 600-dpi PNG, 1000-dpi RGB TIFF (LZW; Elsevier line-art spec).

Per figure
- Fig 1: rebuilt on a millimetre grid. Two shaded layers (exogenous environment /
  routing decisions) replace the free-floating subtitle; no overlapping boxes or
  labels; the DDDAS loop now returns the revised suffix to *execution* (as stated
  in the caption) instead of pointing into the route plan; the excluded
  route-to-Hawkes feedback is a short crossed dashed arrow that no longer cuts
  through other boxes.
- Fig 2: three panels in one file; x-ticks at the simulated regimes only, nominal
  regime flagged on the axis; Poisson reference labelled; direct series labels.
- Fig 3: legend replaced by direct end-of-line labels (fixes the collision of
  "nominal" with the legend); ALNS-CVaR slightly emphasised. Optional panel b
  with mean tardiness (set FIG3_WITH_MEAN_PANEL = True; data already in the CSV).
- Fig 4: both forest plots share the day axis; the "9/9 days" note moved to the
  panel header (it previously overprinted the CI); the pooled mean is shown as a
  dashed guide plus diamond with its 95% CI printed numerically.
- Fig 5: three panels in one file; dotted ALNS reference line; the "descriptive"
  qualifier moved to a header note; cost panel as horizontal bars with the 9.2x
  ratio drawn as an arrow.
- Fig 6: panels a-c share styling and carry in-panel direction cues; panel d
  redesigned from boxes-and-arrows (with overprinted text) into two proportional
  bars with separate denominators, encoding every count of V2 (523/87/436/194/3
  and 180/65/115 with 18/3/44). Counts are asserted for internal consistency.

## Things to update in the manuscript
- Panel references: Fig. 4A -> Fig. 4{L('a')}, etc. (set PANEL_CASE = "upper" in the
  script if you prefer capital letters; captions in FIGURES_LATEX_{VERSION.upper()}.tex
  follow the switch).
- \\includegraphics now points to one file per figure (see the .tex file).
- Captions were kept verbatim except for small additions that describe new
  visual elements (Poisson line, dashed mean line, hatching, 18/3/44 split).

Recommended main-text priority (unchanged): Fig 4, Fig 1, Fig 3, Fig 6, Fig 2, Fig 5.
"""


def contact_sheet(out: Path):
    pngs = sorted((out / "png").glob("*.png"))
    W = 1400                                   # px for a 180-mm-wide figure
    scale = W / (180 / 25.4 * PNG_DPI)        # same scale for all -> true proportions
    try:
        font = ImageFont.truetype(font_manager.findfont(FONT), 26)
    except Exception:  # pragma: no cover
        font = ImageFont.load_default()
    tiles = []
    for p in pngs:
        im = Image.open(p).convert("RGB")
        w, h = int(im.width * scale), int(im.height * scale)
        im = im.resize((w, h), Image.LANCZOS)
        tile = Image.new("RGB", (W + 60, h + 90), "white")
        ImageDraw.Draw(tile).text((30, 22), p.stem, fill=(40, 40, 40), font=font)
        tile.paste(im, (30, 70))
        tiles.append(tile)
    sheet = Image.new("RGB", (W + 60, sum(t.height for t in tiles) + 20 * len(tiles)),
                      (232, 232, 232))
    y = 0
    for t in tiles:
        sheet.paste(t, (0, y))
        y += t.height + 20
    sheet.save(out / f"TRIP_FIGURES_{VERSION.upper()}_CONTACT_SHEET.png", dpi=(150, 150))


def compile_preview(out: Path):
    """Build FIGURES_PREVIEW_*.pdf (all figures + captions at print scale) if
    pdflatex is available; silently skipped otherwise."""
    import subprocess
    import tempfile
    exe = shutil.which("pdflatex")
    if exe is None:
        return
    stem = f"FIGURES_PREVIEW_{VERSION.upper()}"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copy2(out / f"{stem}.tex", tmp)
        shutil.copytree(out / "pdf", tmp / "pdf")
        for _ in range(2):
            subprocess.run([exe, "-interaction=nonstopmode", f"{stem}.tex"],
                           cwd=tmp, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)
        if (tmp / f"{stem}.pdf").exists():
            shutil.copy2(tmp / f"{stem}.pdf", out / f"{stem}.pdf")


def manifest(out: Path):
    lines = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "SHA256_MANIFEST.txt":
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  "
                         f"{p.relative_to(out)}")
    (out / "SHA256_MANIFEST.txt").write_text("\n".join(lines) + "\n")


# ----------------------------------------------------------------------------
def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=here / "figure_data")
    ap.add_argument("--out", type=Path, default=here)
    ap.add_argument("--zip", type=Path, default=None,
                    help="optional path of a zip archive of the output folder")
    args = ap.parse_args()

    out = args.out
    for sub in ("pdf", "png", "tiff", "figure_data"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    data = args.data
    if data.resolve() != (out / "figure_data").resolve():
        for f in data.glob("*.csv"):
            shutil.copy2(f, out / "figure_data" / f.name)

    env = pd.read_csv(data / "Fig2_environment.csv")
    pers = pd.read_csv(data / "Fig3_persistence_routing.csv")
    cross = pd.read_csv(data / "Fig4_crossday.csv")
    overall = pd.read_csv(data / "Fig4_overall.csv")
    rl = pd.read_csv(data / "Fig5_RL.csv")
    cost = pd.read_csv(data / "Fig5C_cost.csv")
    dd = pd.read_csv(data / "Fig6_DDDAS.csv")
    counts = pd.read_csv(data / "Fig6D_counts.csv")

    # sanity check: pooled means in Fig4_overall must equal the day means
    for m in ("delta_J", "delta_tail"):
        pooled = overall.set_index("metric").loc[m, "mean"]
        assert abs(cross[m].mean() - pooled) < 1e-4, f"Fig4 pooled mean mismatch ({m})"

    print(f"Font in use: {FONT}")
    fig1(out)
    fig2(env, out)
    fig3(pers, out)
    fig4(cross, overall, out)
    fig5(rl, cost, out)
    fig6(dd, counts, out)

    latex = latex_block()
    (out / f"FIGURES_LATEX_{VERSION.upper()}.tex").write_text(latex)
    (out / f"FIGURES_PREVIEW_{VERSION.upper()}.tex").write_text(preview_tex(latex))
    (out / "DESIGN_NOTES.md").write_text(NOTES)
    contact_sheet(out)
    compile_preview(out)
    manifest(out)

    if args.zip:
        with zipfile.ZipFile(args.zip, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(out.rglob("*")):
                if p.is_file() and not p.name.startswith("."):
                    z.write(p, arcname=str(Path(out.name) / p.relative_to(out)))
        print("ZIP:", args.zip)
    print("Done:", out)


if __name__ == "__main__":
    main()
