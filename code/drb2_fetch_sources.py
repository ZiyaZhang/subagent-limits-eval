#!/usr/bin/env python3
"""Download the expert source articles behind the Chinese (zh) tasks of
DeepResearch Bench II, for later n-gram overlap checks against agent reports.

Input : data/drb2/repo-src/tasks_and_rubrics.jsonl  (rows with language == "zh")
Output: data/drb2/sources/<idx>/article.html|article.pdf + article.txt
        data/drb2/sources/index.json
        data/drb2/sources/fetch.log

Rules implemented (see the task brief):
  * plain urllib with a normal browser User-Agent, no cookies, no JS, nothing
    that bypasses a login / CAPTCHA / bot challenge; such responses are recorded
    as "blocked" and the next URL is tried;
  * at most 2 concurrent downloads, >= 2 s between requests to the same host,
    at most 3 fetches per URL (route order: direct, proxy, direct);
  * listed URLs are tried in order; a URL is accepted as "full text" when the
    extracted text has > 10,000 chars and the first 60 chars of the article
    title appear in it; the first full-text hit stops the search;
  * only same-publisher renditions of a listed URL are added, never web-searched
    copies: the PDF that a fetched page itself declares (citation_pdf_url),
    the PMC full text that a PubMed abstract page links to, and for mdpi.com
    pages (whose HTML is denied to non-browser clients) the publisher PDF on
    MDPI's own static host mdpi-res.com;
  * if nothing full was obtained, the best partial result (e.g. an abstract) is
    saved with status "partial"; nothing at all -> "missing".

Re-run:  python3 scripts/drb2_fetch_sources.py            (skips tasks already "full")
         python3 scripts/drb2_fetch_sources.py --force    (re-downloads everything)
         python3 scripts/drb2_fetch_sources.py --idx 1 3  (subset)
"""
import argparse
import gzip
import html
import io
import json
import logging
import os
import re
import sys
import threading
import time
import unicodedata
import zlib
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
import urllib.request
import urllib.error

sys.setrecursionlimit(20000)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(ROOT, "data", "drb2", "repo-src", "tasks_and_rubrics.jsonl")
DEFAULT_OUT = os.path.join(ROOT, "data", "drb2", "sources")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 45
MAX_BYTES = 80 * 1024 * 1024
HOST_GAP = 2.0          # seconds between requests to the same host
MAX_ATTEMPTS = 3        # fetches per URL
FULL_MIN_CHARS = 10000
TITLE_PREFIX = 60
SHORT_HTML_CHARS = 25000

# MDPI journal ISSN -> URL slug used on mdpi-res.com (the publisher's PDF host,
# where the article page's "Download PDF" button lands). A wrong slug simply
# 404s; title_matched validates the right ones.
MDPI_SLUG = {
    "1099-4300": "entropy",        # Entropy
    "1420-3049": "molecules",      # Molecules
    "1422-0067": "ijms",           # Int. J. Molecular Sciences
    "1424-8220": "sensors",        # Sensors
    "1660-4601": "ijerph",         # Int. J. Environ. Res. Public Health
    "1911-8074": "jrfm",           # J. Risk and Financial Management
    "1996-1944": "materials",      # Materials
    "2032-6653": "wevj",           # World Electric Vehicle Journal
    "2071-1050": "sustainability", # Sustainability
    "2073-445X": "land",           # Land
    "2076-0752": "arts",           # Arts
    "2076-3417": "applsci",        # Applied Sciences
    "2077-1444": "religions",      # Religions
    "2078-2489": "information",    # Information
    "2079-9292": "electronics",    # Electronics
    "2227-7080": "technologies",   # Technologies
    "2227-7099": "economies",      # Economies
    "2227-7102": "education",      # Education Sciences
    "2227-7390": "mathematics",    # Mathematics
    "2227-9032": "healthcare",     # Healthcare
    "2227-9709": "informatics",    # Informatics
    "2304-6767": "dentistry",      # Dentistry Journal
    "2306-5710": "beverages",      # Beverages
    "2410-3888": "fishes",         # Fishes
    "2413-8851": "urbansci",       # Urban Science
    "2414-4088": "mti",            # Multimodal Technologies and Interaction
}
# DOI journal code -> slug, for doi.org/10.3390/<code><vol><issue><article> URLs
MDPI_DOI_CODE = {"s": "sensors", "rel": "religions", "informatics": "informatics",
                 "technologies": "technologies", "ijerph": "ijerph", "land": "land",
                 "jrfm": "jrfm", "ma": "materials", "app": "applsci", "wevj": "wevj",
                 "su": "sustainability", "arts": "arts", "info": "information",
                 "electronics": "electronics", "economies": "economies",
                 "educsci": "education", "math": "mathematics", "healthcare": "healthcare",
                 "dj": "dentistry", "beverages": "beverages", "fishes": "fishes",
                 "urbansci": "urbansci", "mti": "mti", "e": "entropy",
                 "molecules": "molecules", "ijms": "ijms"}

# Hosts that only ever show an abstract / record page (never the article body):
# an HTML page from them can be saved as "partial" but never counts as "full".
ABSTRACT_HOSTS = {
    "ideas.repec.org", "econpapers.repec.org", "pubmed.ncbi.nlm.nih.gov", "www.semanticscholar.org",
    "ouci.dntb.gov.ua", "doaj.org", "scispace.com", "www.researchgate.net", "ui.adsabs.harvard.edu",
    "inspirehep.net", "www.scilit.com", "colab.ws", "discovery.researcher.life", "www.bohrium.com",
    "www.citedrive.com", "scite.ai", "www.unboundmedicine.com", "www.goodreads.com", "academindex.com",
    "www.ablesci.com", "cn.aminer.org", "www.ivysci.com", "aithor.com", "trid.trb.org", "go.gale.com",
    "text2fa.ir", "www.scribd.com", "encyclopedia.pub", "www.jstor.org", "mycoordinates.org",
    "news.sciencenet.cn", "pureportal.coventry.ac.uk", "pure.ul.ie", "lero.ie", "pure.ups.edu.ec",
    "nchr.elsevierpure.com", "yonsei.elsevierpure.com", "researchportal.hkust.edu.hk",
    "researchportal.u-tokai.ac.jp", "researchportal.ulisboa.pt", "www.scholars.northwestern.edu",
    "profiles.wustl.edu", "portalcientifico.upm.es", "research.ulusofona.pt", "novaresearch.unl.pt",
    "openresearch.surrey.ac.uk", "dro.deakin.edu.au", "pureadmin.qub.ac.uk", "ira.lib.polyu.edu.hk",
    "knowledge.uchicago.edu", "par.nsf.gov", "www.osti.gov", "hdl.handle.net", "scienceon.kisti.re.kr",
    "www.es.mdu.se", "conf.researchr.org", "athena.itec.aau.at", "campus.aau.at",
}

BLOCK_MARKERS = ["just a moment", "access denied", "checking your browser", "recaptcha",
                 "client challenge", "please enable javascript", "verify you are human",
                 "are you a robot", "captcha", "attention required", "request blocked",
                 "bot detection", "security check", "you have been blocked",
                 "javascript is disabled in your browser", "sign in to continue",
                 "incapsula", "radware", "ddos protection"]

log = logging.getLogger("drb2fetch")


# ----------------------------------------------------------------------------- HTTP
class HostThrottle:
    def __init__(self, gap):
        self.gap = gap
        self.lock = threading.Lock()
        self.last = {}

    def wait(self, host):
        while True:
            with self.lock:
                now = time.monotonic()
                due = self.last.get(host, 0) + self.gap
                if now >= due:
                    self.last[host] = now
                    return
                delay = due - now
            time.sleep(delay)


THROTTLE = HostThrottle(HOST_GAP)


def proxy_from_env():
    for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        v = os.environ.get(k)
        if v:
            return v
    return None


def make_opener(route, proxy):
    if route == "proxy" and proxy:
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
    else:
        handler = urllib.request.ProxyHandler({})
    return urllib.request.build_opener(handler)


def decompress(body, encoding):
    enc = (encoding or "").lower()
    try:
        if enc == "gzip":
            return gzip.decompress(body)
        if enc == "deflate":
            try:
                return zlib.decompress(body)
            except zlib.error:
                return zlib.decompress(body, -zlib.MAX_WBITS)
    except Exception:
        return body
    return body


def fetch_once(url, route, proxy):
    """Return dict(status, final_url, ctype, body, error)."""
    THROTTLE.wait(urlparse(url).netloc.lower())
    req = urllib.request.Request(url, headers=HEADERS)
    opener = make_opener(route, proxy)
    out = {"status": None, "final_url": url, "ctype": "", "body": b"", "error": None}
    try:
        resp = opener.open(req, timeout=TIMEOUT)
        try:
            chunks, total = [], 0
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    out["error"] = "too large"
                    break
                chunks.append(chunk)
            body = b"".join(chunks)
            out["status"] = resp.status
            out["final_url"] = resp.geturl()
            out["ctype"] = resp.headers.get("Content-Type", "") or ""
            out["body"] = decompress(body, resp.headers.get("Content-Encoding"))
        finally:
            resp.close()
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        out["final_url"] = getattr(e, "url", url) or url
        out["ctype"] = e.headers.get("Content-Type", "") if e.headers else ""
        try:
            out["body"] = decompress(e.read(), e.headers.get("Content-Encoding") if e.headers else None)
        except Exception:
            out["body"] = b""
        out["error"] = "HTTP %d" % e.code
    except Exception as e:  # URLError, socket.timeout, ssl errors, ...
        out["error"] = "%s: %s" % (type(e).__name__, str(e)[:160])
    return out


# ----------------------------------------------------------------------------- HTML
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}
BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr",
         "table", "section", "article", "header", "footer", "blockquote", "pre", "dd",
         "dt", "dl", "figure", "figcaption", "caption", "hr", "main", "aside", "nav",
         "address", "fieldset", "legend", "details", "summary", "tbody", "thead", "tfoot"}
CELL = {"td", "th"}
SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "math", "iframe", "nav",
             "footer", "form", "button", "select", "option", "input", "textarea",
             "menu", "dialog", "canvas", "object", "video", "audio", "map"}
SKIP_ROLES = {"navigation", "banner", "contentinfo", "search", "menu", "menubar",
              "dialog", "alertdialog", "toolbar", "tablist", "complementary"}
SKIP_CLASS_RE = re.compile(
    r"(?:^|[\s_-])(?:cookie|breadcrumb|breadcrumbs|share|social|popup|modal|dropdown|"
    r"menu|sidebar|sidenav|navbar|nav-|toolbar|skip-link|advert|banner|login|signin|"
    r"footer|newsletter|related-articles|recommended|citation-tools|reading-companion|"
    r"c-article-metrics|c-article-recommendations|c-article-extras|c-pdf-download|"
    r"article-info|article-metrics|altmetric|cited-by|citedby)"
    r"(?:$|[\s_-])", re.I)


class Node(object):
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.parent = parent


class TreeBuilder(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = Node("document")
        self.cur = self.root
        self.title = ""
        self.metas = {}
        self.pdf_links = []
        self.links = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "meta":
            a = dict(attrs)
            name = (a.get("name") or a.get("property") or "").lower()
            if name and a.get("content"):
                self.metas.setdefault(name, a["content"])
            return
        if tag == "link":
            a = dict(attrs)
            if (a.get("type") or "").lower() == "application/pdf" and a.get("href"):
                self.pdf_links.append(a["href"])
            return
        if tag == "title":
            self._in_title = True
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID and tag.lower() != "meta" and tag.lower() != "link":
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in VOID or tag in ("meta", "link"):
            return
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is None or n is self.root:
            return
        self.cur = n.parent or self.root

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if data:
            self.cur.children.append(data)


def parse_html(text):
    tb = TreeBuilder()
    try:
        tb.feed(text)
        tb.close()
    except Exception:
        pass
    return tb


def node_skipped(node):
    if node.tag in SKIP_TAGS:
        return True
    role = (node.attrs.get("role") or "").lower()
    if role in SKIP_ROLES:
        return True
    if (node.attrs.get("aria-hidden") or "").lower() == "true":
        return True
    if "hidden" in node.attrs and node.attrs["hidden"] in (None, "", "hidden", "true"):
        return True
    cls = " ".join(x for x in (node.attrs.get("class") or "", node.attrs.get("id") or "") if x)
    if cls and SKIP_CLASS_RE.search(cls):
        return True
    return False


def node_text(node, out=None, skip=True):
    """Serialize visible text of a node with block-level line breaks."""
    top = out is None
    if top:
        out = []
    for ch in node.children:
        if isinstance(ch, str):
            out.append(ch)
        else:
            if skip and node_skipped(ch):
                continue
            if ch.tag in BLOCK:
                out.append("\n")
            elif ch.tag in CELL:
                out.append("\t")
            node_text(ch, out, skip)
            if ch.tag in BLOCK:
                out.append("\n")
    if top:
        return clean_text("".join(out))
    return None


def clean_text(s):
    s = s.replace("\r", "")
    s = re.sub(r"[ \t\f\v ]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def walk(node):
    yield node
    for ch in node.children:
        if not isinstance(ch, str):
            for x in walk(ch):
                yield x


def find_nodes(root, pred):
    return [n for n in walk(root) if pred(n)]


def attr_match(node, key, values):
    v = (node.attrs.get(key) or "")
    toks = set(v.split()) if key == "class" else {v}
    return any(x in toks for x in values)


# Containers that hold the article body on known hosts, in order of preference.
HOST_CONTAINERS = [
    (re.compile(r"mdpi\.com$"), [("class", ["html-body"]), ("class", ["article_content"]), ("id", ["abstract"])]),
    (re.compile(r"pmc\.ncbi\.nlm\.nih\.gov$"), [("tag", ["article"]), ("class", ["pmc-layout__content"]), ("id", ["main-content"])]),
    (re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov$"), [("id", ["article-details"]), ("tag", ["main"])]),
    (re.compile(r"journals\.plos\.org$"), [("class", ["article-content"]), ("id", ["artText"]), ("class", ["article-text"])]),
    (re.compile(r"springer\.com$|springeropen\.com$|nature\.com$|biomedcentral\.com$"), [("tag", ["article"]), ("tag", ["main"])]),
    (re.compile(r"frontiersin\.org$"), [("class", ["JournalFullText"]), ("class", ["JournalAbstract"]), ("tag", ["article"])]),
    (re.compile(r"peerj\.com$"), [("tag", ["article"]), ("tag", ["main"])]),
    (re.compile(r"arxiv\.org$"), [("id", ["abs"]), ("class", ["ltx_page_content"]), ("tag", ["main"])]),
    (re.compile(r"ieee\.org$"), [("tag", ["main"])]),
]
GENERIC_CONTAINERS = [("tag", ["article"]), ("tag", ["main"]), ("id", ["content", "main-content", "maincontent", "main"]),
                      ("role", ["main"]), ("tag", ["body"])]


def pick_container(tb, host):
    root = tb.root
    specs = []
    for rx, lst in HOST_CONTAINERS:
        if rx.search(host):
            specs.extend(lst)
    specs.extend(GENERIC_CONTAINERS)
    best = None
    for key, values in specs:
        if key == "tag":
            nodes = find_nodes(root, lambda n, v=values: n.tag in v)
        else:
            nodes = find_nodes(root, lambda n, k=key, v=values: attr_match(n, k, v))
        if not nodes:
            continue
        # several matches (e.g. many <article>): take the longest text
        cand = max(nodes, key=lambda n: len(node_text(n)))
        txt = node_text(cand)
        if len(txt) >= 800:
            return cand, txt
        if best is None or len(txt) > len(best[1]):
            best = (cand, txt)
    if best is None:
        return root, node_text(root)
    return best


def html_to_text(raw, ctype, url):
    enc = None
    m = re.search(r"charset=([\w-]+)", ctype or "", re.I)
    if m:
        enc = m.group(1)
    if not enc:
        m = re.search(br"<meta[^>]+charset=[\"']?([\w-]+)", raw[:5000], re.I)
        if m:
            enc = m.group(1).decode("ascii", "ignore")
    text = None
    for e in [enc, "utf-8", "cp1252"]:
        if not e:
            continue
        try:
            text = raw.decode(e)
            break
        except Exception:
            continue
    if text is None:
        text = raw.decode("utf-8", "replace")
    tb = parse_html(text)
    host = urlparse(url).netloc.lower()
    container, body = pick_container(tb, host)
    # the page's declared title goes on the first line when the chosen container
    # lacks it (e.g. Springer/Nature keep the <h1> in a masthead outside <main>)
    title_line = ""
    for key in ("citation_title", "dc.title", "og:title"):
        v = tb.metas.get(key)
        if v and len(v.strip()) > 8:
            title_line = clean_text(v)
            break
    if not title_line:
        h1s = find_nodes(tb.root, lambda n: n.tag == "h1")
        if h1s:
            title_line = max((node_text(h) for h in h1s), key=len)
    if title_line and norm(title_line[:TITLE_PREFIX]) and norm(title_line[:TITLE_PREFIX]) not in norm(body[:20000]):
        body = title_line + "\n\n" + body
    return body, tb


def norm(s):
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", s.lower()).strip()


def tight(s):
    """NFKC (ligatures, superscripts), casefold, keep only letters/digits/CJK: tolerant
    to PDF line breaks, hyphenation and spacing glitches."""
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", unicodedata.normalize("NFKC", s or "").casefold())


HEAD_WINDOW = 8000      # the article's own title must appear near the top (first page)


def title_in(title, text, declared=None):
    """True when the first TITLE_PREFIX chars of the task title appear in the document's
    declared title (HTML metadata / <title> / <h1>) or within the first HEAD_WINDOW
    chars of its text. Mentions further down (TOC, related articles) do not count."""
    t = tight(title[:TITLE_PREFIX])
    if len(t) < 12:
        return False
    if declared:
        for dname in declared:
            if t in tight(dname):
                return True
    return t in tight(text[:HEAD_WINDOW])


def declared_titles(tb):
    out = [tb.metas.get(k) for k in ("citation_title", "dc.title", "og:title")]
    out.append(tb.title)
    out.extend(node_text(h) for h in find_nodes(tb.root, lambda n: n.tag == "h1"))
    return [x for x in out if x]


# ----------------------------------------------------------------------------- PDF
def pdf_to_text(raw):
    try:
        from pypdf import PdfReader
    except ImportError:
        return "", "pypdf not available"
    try:
        reader = PdfReader(io.BytesIO(raw))
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception as e:
                parts.append("")
        return clean_text("\n\n".join(parts)), None
    except Exception as e:
        return "", "pypdf: %s" % str(e)[:160]


def is_pdf(body, ctype):
    return body[:5] == b"%PDF-" or "application/pdf" in (ctype or "").lower()


# ----------------------------------------------------------------------------- renditions
def mdpi_res_urls(slug, vol, article):
    out = []
    vols = ["%02d" % int(vol)]          # observed: fishes-08-00080, technologies-09-00037
    if str(vol) not in vols:
        vols.append(str(vol))           # unpadded fallback (never observed, kept for safety)
    for v in vols:
        base = "https://mdpi-res.com/d_attachment/%s/%s-%s-%05d/article_deploy/%s-%s-%05d" % (
            slug, slug, v, article, slug, v, article)
        out.extend([base + ".pdf", base + "-v2.pdf", base + "-v3.pdf"])
    return out


def mdpi_renditions(url):
    m = re.match(r"https?://(?:www\.)?mdpi\.com/(\d{4}-\d{3}[\dXx])/(\d+)/(\d+)/(\d+)", url)
    if m:
        slug = MDPI_SLUG.get(m.group(1).upper())
        if slug:
            return mdpi_res_urls(slug, m.group(2), int(m.group(4)))
    m = re.search(r"doi\.org/10\.3390/([A-Za-z]+)(\d+)$", url)
    if m:
        code, digits = m.group(1).lower(), m.group(2)
        slug = MDPI_DOI_CODE.get(code)
        out = []
        if slug:
            # suffix = <vol><issue:2><article:4-5>; the volume length is ambiguous,
            # so emit both readings (the wrong one 404s on mdpi-res.com)
            for vlen in (2, 1):
                vol, rest = digits[:vlen], digits[vlen:]
                if vol and not vol.startswith("0") and len(rest) in (6, 7):
                    out.extend(mdpi_res_urls(slug, vol, int(rest[2:])))
        return out
    return []


def pubmed_renditions(url, proxy, attempts, idx=None):
    """PMC full text of a listed PubMed record, resolved through NCBI's E-utilities
    (the same link the PubMed page shows as 'Free PMC article')."""
    m = re.match(r"https?://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?", url)
    if not m:
        return []
    api = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=" + m.group(1))
    res = fetch_once(api, "direct", proxy)
    pmc = None
    if res["status"] == 200 and res["body"]:
        try:
            doc = json.loads(res["body"].decode("utf-8", "replace"))
            for a in doc["result"][m.group(1)].get("articleids", []):
                if a.get("idtype") == "pmc" and a.get("value", "").startswith("PMC"):
                    pmc = a["value"]
        except Exception:
            pmc = None
    attempts.append({"url": api, "route": "direct", "http": res["status"], "final_url": api, "bytes": len(res["body"]),
                     "kind": "lookup", "text_chars": 0, "title_matched": False,
                     "outcome": "lookup:" + (pmc or "no-pmc"), "error": res["error"], "listed_url": url, "derived": True})
    log.info("idx %s lookup %s -> %s %s", idx, api[:100], res["status"], pmc or "no PMC id")
    return ["https://pmc.ncbi.nlm.nih.gov/articles/%s/" % pmc] if pmc else []


def same_site(a, b):
    def reg(h):
        parts = h.lower().split(".")
        return ".".join(parts[-3:]) if len(parts) >= 3 and parts[-2] in ("ac", "co", "edu", "gov", "org", "com", "net") and len(parts[-1]) == 2 else ".".join(parts[-2:])
    return reg(urlparse(a).netloc) == reg(urlparse(b).netloc)


def declared_renditions(tb, page_url, body_text):
    """Same-publisher full-text URLs that the fetched page itself declares."""
    out = []
    for key in ("citation_pdf_url", "citation_fulltext_html_url"):
        v = tb.metas.get(key)
        if v:
            out.append(urljoin(page_url, v.strip()))
    for href in tb.pdf_links:
        out.append(urljoin(page_url, href.strip()))
    host = urlparse(page_url).netloc.lower()
    if host.endswith("pubmed.ncbi.nlm.nih.gov"):
        # the "Free PMC article" full-text link on the PubMed abstract page
        for href in tb.links:
            m = re.match(r"https://pmc\.ncbi\.nlm\.nih\.gov/articles/PMC\d+/?", urljoin(page_url, href.strip()))
            if m:
                out.append(m.group(0))
                break
    keep, seen = [], set()
    for u in out:
        if u in seen or u == page_url:
            continue
        seen.add(u)
        uh = urlparse(u).netloc.lower()
        if same_site(u, page_url) or uh in ("mdpi-res.com", "pmc.ncbi.nlm.nih.gov", "arxiv.org", "europepmc.org"):
            keep.append(u)
    return keep


# ----------------------------------------------------------------------------- per-URL
def classify(res, text, body_is_pdf):
    st = res["status"]
    if res["error"] and st is None:
        return "transient"
    if st in (401, 403, 203):
        return "blocked"
    if st == 429:
        return "transient"
    if st == 404 and urlparse(res["final_url"]).netloc.lower().endswith("mdpi-res.com"):
        return "transient"
    if st in (404, 410, 451):
        return "notfound"
    if st is not None and st >= 500:
        return "transient"
    if st is None:
        return "transient"
    if body_is_pdf:
        return "ok"
    low = text[:4000].lower()
    if len(text) < 3000 and any(mk in low for mk in BLOCK_MARKERS):
        return "blocked"
    if len(res["body"]) < 200:
        return "transient"
    return "ok"


def try_url(url, title, proxy, listed_url, derived, idx=None):
    """Fetch one URL (<= MAX_ATTEMPTS fetches). Returns (candidate|None, attempts, renditions)."""
    routes = ["direct", "proxy", "direct"] if proxy else ["direct", "direct", "direct"]
    attempts, blocked_routes = [], set()
    for i, route in enumerate(routes[:MAX_ATTEMPTS]):
        if route in blocked_routes:
            if all(r in blocked_routes for r in set(routes)):
                break
            continue
        res = fetch_once(url, route, proxy)
        body, ctype = res["body"], res["ctype"]
        pdf = is_pdf(body, ctype) if body else False
        text, tb, perr = "", None, None
        if body and res["status"] == 200:
            if pdf:
                text, perr = pdf_to_text(body)
            else:
                text, tb = html_to_text(body, ctype, res["final_url"])
        elif body and not pdf:
            text, tb = html_to_text(body, ctype, res["final_url"])
        outcome = classify(res, text, pdf)
        matched = title_in(title, text, declared_titles(tb) if tb is not None else None) if text else False
        att = {"url": url, "route": route, "http": res["status"], "final_url": res["final_url"],
               "bytes": len(body), "kind": "pdf" if pdf else "html", "text_chars": len(text) if outcome == "ok" else 0,
               "title_matched": matched if outcome == "ok" else False, "outcome": outcome,
               "error": res["error"] or perr}
        attempts.append(att)
        log.info("idx %s %s %s -> %s %s %s chars=%d title=%s %s", idx, route, url[:110], res["status"], outcome,
                 att["kind"], att["text_chars"], matched, (res["error"] or perr or ""))
        if outcome == "ok":
            full = len(text) > FULL_MIN_CHARS and matched
            capped = (not pdf) and urlparse(res["final_url"]).netloc.lower() in ABSTRACT_HOSTS
            if capped:
                full = False
                att["capped"] = "abstract-only host"
            cand = {"url_used": url, "final_url": res["final_url"], "kind": att["kind"], "bytes": len(body),
                    "text_chars": len(text), "title_matched": matched, "full": full, "raw": body, "text": text,
                    "listed_url": listed_url, "derived": derived, "capped": capped}
            # a short HTML page that declares its PDF is usually a landing page (abstract +
            # references): the PDF is fetched too and the larger text wins
            want_pdf = tb is not None and (not full or len(text) < SHORT_HTML_CHARS)
            rend = declared_renditions(tb, res["final_url"], text) if want_pdf else []
            return cand, attempts, rend
        if outcome == "notfound":
            break
        if outcome == "blocked":
            blocked_routes.add(route)
            if all(r in blocked_routes for r in set(routes)):
                break
            continue
        time.sleep(3.0 * (i + 1))   # transient: back off before the next attempt
    return None, attempts, []


def rank(c):
    return (c["full"], c["title_matched"], not c.get("capped"), c["text_chars"])


def process_task(task, outdir, proxy):
    idx, blocked = task["idx"], task["content"]["blocked"]
    title, urls = blocked.get("title", ""), list(blocked.get("urls", []))
    attempts, best = [], None
    queue = []  # (url, listed_url, derived_flag)
    for u in urls:
        queue.append((u, u, False))
    tried = set()
    i = 0
    while i < len(queue):
        url, listed_url, derived = queue[i]
        i += 1
        if url in tried:
            continue
        tried.add(url)
        cand, atts, rend = try_url(url, title, proxy, listed_url, derived, idx)
        for a in atts:
            a["listed_url"] = listed_url
            a["derived"] = derived
        attempts.extend(atts)
        if cand is not None and (best is None or rank(cand) > rank(best)):
            best = cand
        # same-publisher renditions of this listed URL go right after it
        extra = []
        if not derived:
            extra.extend(mdpi_renditions(url))
            if best is None or not best["full"]:
                extra.extend(pubmed_renditions(url, proxy, attempts, idx))
        extra.extend(rend)
        inserted = 0
        for e in extra:
            if e not in tried and all(e != q[0] for q in queue):
                queue.insert(i + inserted, (e, listed_url, True))
                inserted += 1
        short_html = (cand is not None and cand["kind"] == "html" and cand["text_chars"] < SHORT_HTML_CHARS
                      and inserted > 0)
        if best is not None and best["full"] and not short_html:
            break
    d = os.path.join(outdir, str(idx))
    os.makedirs(d, exist_ok=True)
    for old in ("article.html", "article.pdf", "article.txt"):
        p = os.path.join(d, old)
        if os.path.exists(p):
            os.remove(p)
    entry = {"idx": idx, "title": title, "status": "missing", "url_used": None, "bytes": 0,
             "text_chars": 0, "title_matched": False, "kind": None, "listed_url": None,
             "derived": False, "capped": False, "attempts": attempts}
    if best is not None:
        fn = "article.pdf" if best["kind"] == "pdf" else "article.html"
        with open(os.path.join(d, fn), "wb") as f:
            f.write(best["raw"])
        with open(os.path.join(d, "article.txt"), "w", encoding="utf-8") as f:
            f.write(best["text"])
        entry.update({"status": "full" if best["full"] else "partial", "url_used": best["url_used"],
                      "final_url": best["final_url"], "bytes": best["bytes"], "text_chars": best["text_chars"],
                      "title_matched": best["title_matched"], "kind": best["kind"],
                      "listed_url": best["listed_url"], "derived": best["derived"], "capped": best.get("capped", False)})
    return entry


def rescore_entry(entry, outdir):
    """Recompute article.txt, title_matched and status from the saved raw file (no network)."""
    d = os.path.join(outdir, str(entry["idx"]))
    raw_path = None
    for fn in ("article.pdf", "article.html"):
        if os.path.exists(os.path.join(d, fn)):
            raw_path = os.path.join(d, fn)
    if raw_path is None or not entry.get("url_used"):
        return entry
    raw = open(raw_path, "rb").read()
    host = urlparse(entry.get("final_url") or entry["url_used"]).netloc.lower()
    if raw_path.endswith(".pdf"):
        text, _ = pdf_to_text(raw)
        matched = title_in(entry["title"], text)
        capped = False
    else:
        text, tb = html_to_text(raw, "", entry.get("final_url") or entry["url_used"])
        matched = title_in(entry["title"], text, declared_titles(tb))
        capped = host in ABSTRACT_HOSTS
    with open(os.path.join(d, "article.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    full = len(text) > FULL_MIN_CHARS and matched and not capped
    entry.update({"text_chars": len(text), "title_matched": matched, "capped": capped,
                  "status": "full" if full else "partial"})
    return entry


# ----------------------------------------------------------------------------- main
def load_tasks(path, only_idx=None):
    tasks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("language") != "zh":
                continue
            if only_idx and row["idx"] not in only_idx:
                continue
            tasks.append(row)
    return tasks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=DEFAULT_INPUT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--idx", type=int, nargs="*", help="only these task idx values")
    ap.add_argument("--force", action="store_true", help="re-download tasks that are already full")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--rescore", action="store_true",
                    help="no network: recompute article.txt / title_matched / status from the saved raw files")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.FileHandler(os.path.join(args.out, "fetch.log"), encoding="utf-8"),
                                  logging.StreamHandler(sys.stdout)])
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    proxy = proxy_from_env()
    log.info("start: input=%s out=%s proxy=%s workers=%d", args.input, args.out, proxy, min(args.workers, 2))

    index_path = os.path.join(args.out, "index.json")
    index = {}
    if os.path.exists(index_path):
        try:
            with open(index_path, encoding="utf-8") as f:
                index = json.load(f)
        except Exception:
            index = {}
    tasks = load_tasks(args.input, set(args.idx) if args.idx else None)
    if args.rescore:
        for t in tasks:
            key = str(t["idx"])
            if key in index:
                index[key] = rescore_entry(index[key], args.out)
                log.info("idx %s rescored: status=%s chars=%d title=%s", key, index[key]["status"],
                         index[key]["text_chars"], index[key]["title_matched"])
        with open(index_path + ".tmp", "w", encoding="utf-8") as f:
            json.dump({k: index[k] for k in sorted(index, key=lambda x: int(x))}, f, ensure_ascii=False, indent=1)
        os.replace(index_path + ".tmp", index_path)
        full = [k for k, v in index.items() if v["status"] == "full"]
        log.info("SUMMARY after rescore: %d entries, full=%d partial=%d missing=%d", len(index), len(full),
                 len([k for k, v in index.items() if v["status"] == "partial"]),
                 len([k for k, v in index.items() if v["status"] == "missing"]))
        return
    todo = []
    for t in tasks:
        key = str(t["idx"])
        prev = index.get(key)
        if (not args.force and prev and prev.get("status") == "full"
                and os.path.exists(os.path.join(args.out, key, "article.txt"))):
            log.info("idx %s already full, skipping (use --force to redo)", key)
            continue
        todo.append(t)
    log.info("%d zh tasks loaded, %d to fetch", len(tasks), len(todo))

    lock = threading.Lock()

    def save_index():
        tmp = index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({k: index[k] for k in sorted(index, key=lambda x: int(x))}, f, ensure_ascii=False, indent=1)
        os.replace(tmp, index_path)

    def run(t):
        try:
            entry = process_task(t, args.out, proxy)
        except Exception as e:
            log.exception("idx %s failed: %s", t["idx"], e)
            entry = {"idx": t["idx"], "title": t["content"]["blocked"].get("title", ""), "status": "missing",
                     "url_used": None, "bytes": 0, "text_chars": 0, "title_matched": False, "kind": None,
                     "error": "%s: %s" % (type(e).__name__, str(e)[:200]), "attempts": []}
        with lock:
            index[str(t["idx"])] = entry
            save_index()
        log.info("idx %s DONE status=%s chars=%d title=%s via %s", t["idx"], entry["status"], entry["text_chars"],
                 entry["title_matched"], entry.get("url_used"))
        return entry

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 2))) as ex:
        list(ex.map(run, todo))

    full = [k for k, v in index.items() if v["status"] == "full"]
    partial = [k for k, v in index.items() if v["status"] == "partial"]
    missing = [k for k, v in index.items() if v["status"] == "missing"]
    log.info("SUMMARY: %d entries, full=%d partial=%d missing=%d", len(index), len(full), len(partial), len(missing))
    log.info("partial idx: %s", sorted(partial, key=int))
    log.info("missing idx: %s", sorted(missing, key=int))


if __name__ == "__main__":
    main()
