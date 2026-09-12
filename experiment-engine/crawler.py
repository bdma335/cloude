import json
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RULES = json.loads((ROOT / "rules.json").read_text())
STATE_PATH = ROOT / "state.json"
RESULT_PATH = ROOT / "results.json"
SEEDS = [
    "https://github.com/topics/free-online-tools",
    "https://github.com/topics/web-tools",
    "https://github.com/topics/browser-tools"
]

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
    def handle_data(self, data):
        self.text.append(data)

def fetch(url):
    print(f"FETCH {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "cloude-experiment-engine/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", "ignore"), r.geturl()

def score(url, text):
    lower = text.lower()
    signals = ["free", "online", "tool", "browser", "privacy", "no signup", "client-side"]
    return sum(1 for s in signals if s in lower)

def rejected(text):
    lower = text.lower()
    checks = {
        "kyc": ["kyc", "government id", "identity verification", "face verification"],
        "account_required": ["create an account", "sign up required", "login required"],
        "spam": ["bulk email", "mass dm", "spam"],
        "fraud": ["fake reviews", "fake identity", "impersonat"],
        "unauthorized_access": ["bypass captcha", "bypass access", "credential theft", "exploit"],
    }
    return [k for k, words in checks.items() if any(w in lower for w in words)]

def main():
    print("ENGINE START", flush=True)
    state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {"cycle": 0, "seen": []}
    cycle = state["cycle"] + 1
    print(f"CYCLE {cycle}", flush=True)
    findings = []
    for seed in SEEDS:
        try:
            html, final_url = fetch(seed)
            parser = LinkParser()
            parser.feed(html)
            text = " ".join(parser.text)
            flags = rejected(text)
            if flags:
                print(f"REJECT {final_url} {','.join(flags)}", flush=True)
                continue
            item = {"url": final_url, "score": score(final_url, text), "title_terms": re.findall(r"[A-Za-z][A-Za-z -]{2,40}", text)[:20]}
            findings.append(item)
            print(f"ACCEPT {final_url} score={item['score']}", flush=True)
            time.sleep(1)
        except Exception as exc:
            print(f"ERROR {seed} {type(exc).__name__}: {exc}", flush=True)
    findings.sort(key=lambda x: x["score"], reverse=True)
    state["cycle"] = cycle
    state["seen"] = list(dict.fromkeys(state.get("seen", []) + [x["url"] for x in findings]))[-200:]
    RESULT_PATH.write_text(json.dumps({"cycle": state["cycle"], "findings": findings[:10], "rules": RULES}, indent=2))
    STATE_PATH.write_text(json.dumps(state, indent=2))
    print(f"ENGINE COMPLETE findings={len(findings)}", flush=True)

if __name__ == "__main__":
    main()
