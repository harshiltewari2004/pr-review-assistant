"""Day 5 — is `Documentation` a type label or a facet label on p5.js?

Confirmatory only. 04 §5 step 4b excludes docs-only PRs on content, so the
answer no longer decides 01 §2. What it checks is whether the content rule
and the label rule would have agreed.

Pre-registered before the run (09 §5 / 01 §14):
    >= 3 of 10 carry substantive source changes -> FACET; a label rule would
       have stripped real code, and step 4b is the correct mechanism.
    <= 2 of 10 -> TYPE; the two rules would have agreed, and step 4b is
       simply the more robust of the two.
"substantive" = >=1 non-test .js/.mjs/.ts file outside translations/.
"""

import os
import time

import requests
from dotenv import load_dotenv

REPO = "processing/p5.js"
LABEL = "Documentation"
SAMPLE = 10
SRC_EXT = (".js", ".mjs", ".ts")


load_dotenv()

HEADERS = {
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def get(url: str, **params):
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    time.sleep(0.5)  # secondary rate limiter (04 §5)
    return resp.json()


def is_source(path: str) -> bool:
    return (
        path.endswith(SRC_EXT)
        and not path.startswith("translations/")
        and not path.startswith("test/")
    )


# PRs appear in the issues endpoint; label filtering is native there.
items = get(
    f"https://api.github.com/repos/{REPO}/issues",
    labels=LABEL,
    state="all",
    per_page=50,
    sort="created",
    direction="desc",
)
prs = [i for i in items if "pull_request" in i][:SAMPLE]
print(f"sampled {len(prs)} PRs labeled {LABEL!r}\n")

facet = 0
for pr in prs:
    n = pr["number"]
    labels = ", ".join(lbl["name"] for lbl in pr["labels"])
    files = get(f"https://api.github.com/repos/{REPO}/pulls/{n}/files", per_page=100)
    src = [f for f in files if is_source(f["filename"])]
    churn = sum(f["additions"] + f["deletions"] for f in src)
    facet += bool(src)
    print(
        f"#{n:<6} {'MIXED' if src else 'DOCS-ONLY':<10} "
        f"{len(files):>3} files, {len(src):>2} source, {churn:>5} src lines"
    )
    print(f"        labels: {labels}")
    for f in src[:3]:
        print(f"        src: {f['filename']}  +{f['additions']}/-{f['deletions']}")
    print()

print(f"VERDICT: {facet}/{len(prs)} carry source changes")
