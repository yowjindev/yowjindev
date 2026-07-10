#!/usr/bin/env python3
"""
Neofetch-style GitHub profile README generator for @yowjindev.
Regenerates dark_mode.svg / light_mode.svg with live GitHub stats.
Runs on GitHub Actions (uses GITHUB_TOKEN) or locally without a token
(falls back to unauthenticated API / cached values).

stdlib only - no pip installs needed.
"""

import json
import os
import time
import urllib.request
from calendar import monthrange
from datetime import date

USER = "yowjindev"
BIRTHDAY = date(2003, 4, 10)
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

# Used when the API is unreachable (e.g. local run without network)
FALLBACK = {
    "repos": 4, "contributed": 1, "stars": 0,
    "commits": 198, "followers": 0,
    "loc_add": 0, "loc_del": 0,
}

# ---------------------------------------------------------------- api helpers

def _request(url, data=None):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": USER}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode()
        return r.status, json.loads(body) if body.strip() else None


def rest(path):
    return _request(f"https://api.github.com{path}")


def graphql(query):
    payload = json.dumps({"query": query}).encode()
    _, data = _request("https://api.github.com/graphql", data=payload)
    return data


def fetch_stats():
    s = dict(FALLBACK)
    try:
        _, user = rest(f"/users/{USER}")
        s["followers"] = user["followers"]
        s["repos"] = user["public_repos"]

        _, repos = rest(f"/users/{USER}/repos?per_page=100")
        s["stars"] = sum(r["stargazers_count"] for r in repos)

        _, commits = rest(f"/search/commits?q=author:{USER}&per_page=1")
        s["commits"] = commits["total_count"]

        # lines of code: weekly (+/-) across owned repos
        add = rm = 0
        got_loc = False
        for r in repos:
            if r.get("fork"):
                continue
            for attempt in range(5):          # stats are computed async -> 202
                status, weeks = rest(f"/repos/{USER}/{r['name']}/stats/code_frequency")
                if status == 200 and isinstance(weeks, list):
                    for _, a, d in weeks:
                        add += a
                        rm += -d
                    got_loc = True
                    break
                time.sleep(3)
        if got_loc:
            s["loc_add"], s["loc_del"] = add, rm

        if TOKEN:
            q = ('{ user(login: "%s") { repositoriesContributedTo('
                 'first: 1, contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY])'
                 ' { totalCount } } }' % USER)
            data = graphql(q)
            s["contributed"] = (data["data"]["user"]
                                ["repositoriesContributedTo"]["totalCount"])
    except Exception as e:                      # keep the README rendering
        print(f"[warn] stats fetch incomplete: {e}")
    return s


# ------------------------------------------------------------------- content

def uptime():
    t = date.today()
    y = t.year - BIRTHDAY.year
    m = t.month - BIRTHDAY.month
    d = t.day - BIRTHDAY.day
    if d < 0:
        m -= 1
        pm_year, pm_month = (t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12)
        d += monthrange(pm_year, pm_month)[1]
    if m < 0:
        y -= 1
        m += 12
    return f"{y} years, {m} month{'s' if m != 1 else ''}, {d} day{'s' if d != 1 else ''}"


W = 61  # inner text width of the info column, in characters


def kv(label, value_runs):
    """'Label: ..... value'  with dot leaders, right aligned to W chars."""
    if isinstance(value_runs, str):
        value_runs = [(value_runs, "v")]
    vlen = sum(len(t) for t, _ in value_runs)
    dots = max(0, W - len(label) - 1 - 2 - vlen)   # ':' + 2 spaces
    leader = "".join("." if i % 2 == 0 else " " for i in range(dots))
    return ([(label, "k"), (":", "d"), (" " + leader + " ", "dim")]
            + value_runs)


def header(text):
    return [(text, "a"), (" " + "─" * (W - len(text) - 1), "dim")]


def section(text):
    return [(text, "k"), (" " + "─" * 22, "dim")]


def build_info(s):
    n = lambda x: f"{x:,}"
    lines = [
        header("yujin@techiron"),
        kv("OS", "macOS Tahoe, Windows 11, Android 14"),
        kv("Uptime", uptime()),
        kv("Host", "Techiron Resources Inc."),
        kv("Kernel", "Software Engineer"),
        kv("IDE", "VSCode, Zed"),
        [],
        kv("Languages.Programming", "C++, PHP, TypeScript, Python, Kotlin"),
        kv("Languages.Computer", "TSX, CPP, PY, PHP, KT"),
        kv("Languages.Real", "English, Tagalog"),
        [],
        kv("Interests.Software", "AI Automation, Backend"),
        kv("Hobbies.Hardware", "Overclocking, Building, Troubleshooting"),
        [],
        section("Contact"),
        kv("Email.Personal", "ecfe0410@gmail.com"),
        kv("Email.Work", "eridao@techiron.ph"),
        kv("LinkedIn", "eugene-clark-eridao"),
        kv("Discord", "YUJINHMNIDA"),
        [],
        section("GitHub Stats"),
        kv("Repos", [(n(s["repos"]), "v"), (" {", "d"), ("Contributed", "k"),
                     (": ", "d"), (n(s["contributed"]), "v"), ("} | ", "d"),
                     ("Stars", "k"), (": ", "d"), (n(s["stars"]), "v")]),
        kv("Commits", [(n(s["commits"]), "v"), (" | ", "d"), ("Followers", "k"),
                       (": ", "d"), (n(s["followers"]), "v")]),
        kv("Lines of Code on GitHub", [
            (n(s["loc_add"] - s["loc_del"]), "v"), (" ( ", "d"),
            (n(s["loc_add"]) + "++", "g"), (", ", "d"),
            (n(s["loc_del"]) + "--", "r"), (" )", "d")]),
    ]
    return lines


# ---------------------------------------------------------------- svg output

THEMES = {
    "dark_mode.svg": {   # Claude Code inspired
        "bg": "#1f1e1d", "border": "#3e3d38", "art": "#c2c0b6",
        "a": "#d97757", "k": "#d97757", "v": "#faf9f5", "d": "#87867f",
        "dim": "#55544e", "g": "#5db97d", "r": "#e0685e",
    },
    "light_mode.svg": {
        "bg": "#ffffff", "border": "#d0d7de", "art": "#24292f",
        "a": "#0969da", "k": "#953800", "v": "#24292f", "d": "#57606a",
        "dim": "#8c959f", "g": "#1a7f37", "r": "#cf222e",
    },
}

FONT = ("'SFMono-Regular','Consolas','Liberation Mono','Menlo',"
        "'DejaVu Sans Mono',monospace")
FS = 15        # info font size
LH = 19        # info line height
CW = 9.03      # monospace char advance at 15px

FS_ART = 10    # art font size (smaller -> higher detail)
LH_ART = 11.5  # art line height
CW_ART = 6.02  # monospace char advance at 10px


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(art_lines, info_lines, theme, out):
    c = THEMES[out] if theme is None else theme
    art_w = max(len(l) for l in art_lines) * CW_ART
    x_art, x_info = 28, 28 + art_w + 40
    width = int(x_info + W * CW + 28)
    art_h = len(art_lines) * LH_ART
    info_h = len(info_lines) * LH
    height = int(max(art_h, info_h) + 60)
    y0_art = 40 + (height - 60 - art_h) / 2
    y0_info = 40 + (height - 60 - info_h) / 2

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
         f'height="{height}" viewBox="0 0 {width} {height}" '
         f'font-family="{FONT}" font-size="{FS}">',
         f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" '
         f'rx="8" fill="{c["bg"]}" stroke="{c["border"]}"/>']

    for i, line in enumerate(art_lines):
        if not line.strip():
            continue
        p.append(f'<text x="{x_art}" y="{y0_art + i * LH_ART:.1f}" '
                 f'xml:space="preserve" font-size="{FS_ART}" '
                 f'fill="{c["art"]}">{esc(line)}</text>')

    for i, runs in enumerate(info_lines):
        if not runs:
            continue
        spans, col = [], 0
        for text, key in runs:
            spans.append(f'<tspan x="{x_info + col * CW:.1f}" '
                         f'fill="{c.get(key, c["v"])}">{esc(text)}</tspan>')
            col += len(text)
        p.append(f'<text y="{y0_info + i * LH:.0f}" '
                 f'xml:space="preserve">{"".join(spans)}</text>')

    p.append("</svg>")
    with open(out, "w") as f:
        f.write("\n".join(p))
    print(f"wrote {out} ({width}x{height})")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    with open("ascii_art.txt") as f:
        art = f.read().rstrip("\n").split("\n")
    stats = fetch_stats()
    info = build_info(stats)
    for name in THEMES:
        render(art, info, None, name)


if __name__ == "__main__":
    main()
