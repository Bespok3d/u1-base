# SPDX-FileCopyrightText: Copyright (C) 2026 unlucio and the Bespok3d contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Which U1 firmwares Snapmaker has published, and where each one can be downloaded.

Snapmaker's GitHub mirror of the U1 Klipper source is published late and skips releases, so the
list of firmwares a printer can be running is read from the place Snapmaker keeps current: the
release notes on their wiki, which link every release to its own download. The download filename
carries the four part build number, which is the number a printer reports and the number a
manifest's fw_min and fw_max are written in.
"""

import re
import urllib.error
import urllib.request

RELEASE_NOTES_INDEX = "https://wiki.snapmaker.com/en/snapmaker_u1/firmware/release_notes"
WIKI_ORIGIN = "https://wiki.snapmaker.com"
RELEASE_PAGE_LINK = re.compile(r"/en/snapmaker_u1/firmware/release_notes/v\d+")
DOWNLOAD_LINK = re.compile(
    r"https://public\.resource\.snapmaker\.com/firmware/U1/"
    r"U1_(\d+\.\d+\.\d+\.\d+)_\d+_upgrade\.bin"
)
FETCH_TIMEOUT_SECONDS = 30
# What the wiki answers for a release it has listed but not put up yet.
PAGE_NOT_UP_YET = 404
# The wiki turns away a request that does not say who is asking, so this says who is asking.
ASKING_ON_BEHALF_OF = "Bespok3d/u1-base (https://github.com/Bespok3d/u1-base)"


def fetch(url: str) -> str:
    asked = urllib.request.Request(url, headers={"User-Agent": ASKING_ON_BEHALF_OF})
    with urllib.request.urlopen(asked, timeout=FETCH_TIMEOUT_SECONDS) as answer:  # noqa: S310
        return str(answer.read().decode("utf-8", errors="replace"))


def release_pages() -> list[str]:
    """Every per version release notes page, oldest first, as absolute URLs."""
    index_html = fetch(RELEASE_NOTES_INDEX)
    found = dict.fromkeys(RELEASE_PAGE_LINK.findall(index_html))
    return [WIKI_ORIGIN + path for path in sorted(found)]


def download_on(page_url: str) -> tuple[str, str] | None:
    """The build number and download URL a release notes page links to, if it links to one.

    A page the index lists but has not put up yet answers 404, and a page carrying no download link
    links none: both come back as nothing to download, because Snapmaker lists a release before the
    page and the image are up. Every other answer is raised, a refusal and a server error included:
    a published release read as an unpublished one is a firmware the fit proof would go on to cover
    for nobody, without ever saying it had stopped.
    """
    try:
        page_html = fetch(page_url)
    except urllib.error.HTTPError as refused:
        if refused.code != PAGE_NOT_UP_YET:
            raise
        return None
    linked = DOWNLOAD_LINK.search(page_html)
    if linked is None:
        return None
    return linked.group(1), linked.group(0)


def download_per_page() -> dict[str, tuple[str, str] | None]:
    """Each release notes page and the download it links, or nothing where it links none yet."""
    return {page_url: download_on(page_url) for page_url in release_pages()}
