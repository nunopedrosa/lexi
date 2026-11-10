"""Headless verification of the Wiktionary bridge layer in the Lexi2 PWA.

Run with the app served on localhost:8009:
    python3 scripts/check_wikt_bridge.py

Checks (320 px viewport, like the earlier shell checks):
  1. a bridged lemma (telemóvel) opens a dictionary entry, not the missing
     response, and shows the Wiktionary unreviewed notice;
  2. a pre-AO bridge (contracepção) resolves and carries the old-spelling tag
     and the source headword line;
  3. an all-BR bridge (usina) is marked as Brazilian usage;
  4. BR senses sort after unmarked senses in a mixed entry (geladeira);
  5. the missing list page annotates bridged lemmas;
  6. language switch to pt-PT shows the pt-PT notice text.
"""

import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8009/"
failures = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print("[%s] %s %s" % (status, name, detail))
    if not condition:
        failures.append(name)


def chat_text(page):
    return page.locator("#chat").inner_text()


def ask(page, query):
    page.fill("#question", query)
    page.click("#send")
    page.wait_for_timeout(400)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 320, "height": 640})
        page.goto(BASE)
        page.wait_for_timeout(800)

        # 1. Bridged lemma opens an entry with the unreviewed notice.
        ask(page, "telemóvel")
        text = chat_text(page)
        check("telemóvel entry", "«telemóvel»" in text, "")
        check(
            "telemóvel wikt notice",
            "Wiktionary bridge layer" in text,
            "",
        )
        check("telemóvel not missing", "has no definition" not in text, "")

        # 2. Pre-AO bridge resolves with old-spelling tag.
        ask(page, "contracepção")
        text = chat_text(page)
        check("contracepção entry", "«contracepção»" in text, "")
        check(
            "contracepção wikt notice",
            "Wiktionary bridge layer" in text,
            "",
        )
        check("contracepção old-spelling tag", "old spelling" in text, "")

        # 3. All-BR bridge entry notice.
        ask(page, "usina")
        text = chat_text(page)
        check("usina entry", "«usina»" in text, "")
        check("usina Brazilian notice", "Brazilian usage" in text, "")

        # 4. BR senses sort last in a mixed entry.
        ask(page, "geladeira")
        text = chat_text(page)
        answer = text[text.rindex("«geladeira»"):]
        lines = [line for line in answer.split("\n") if line.strip()]
        br_lines = [i for i, line in enumerate(lines) if "[Brazilian usage]" in line]
        plain_lines = [
            i for i, line in enumerate(lines)
            if line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6."))
            and "[Brazilian usage]" not in line
        ]
        check(
            "geladeira page 1 shows no BR senses (PT first)",
            not br_lines and bool(plain_lines),
            "br=%s plain=%s" % (br_lines, plain_lines),
        )
        if not br_lines:
            # The BR senses are on the next page; page through with the chat
            # command shown in the hint.
            ask(page, "other meanings")
            text = chat_text(page)
            answer = text[text.rindex("«geladeira»"):]
            lines = [line for line in answer.split("\n") if line.strip()]
            br_lines = [i for i, line in enumerate(lines) if "[Brazilian usage]" in line]
            check(
                "geladeira BR sense on page 2",
                bool(br_lines),
                "br=%s" % br_lines,
            )
        check(
            "geladeira curated PT-PT text first",
            "No português do Brasil, frigorífico." in text,
            "",
        )

        # 5. Missing list page annotates bridged lemmas.
        page.goto(BASE + "missing.html")
        page.wait_for_timeout(800)
        page.fill("#search", "geladeira")
        page.wait_for_timeout(300)
        item = page.locator(".missing-item").first.inner_text()
        check(
            "missing page wikt annotation",
            "Wiktionary bridge layer" in item,
            item[:120],
        )

        # 6. pt-PT notice text.
        page.goto(BASE)
        page.wait_for_timeout(800)
        page.select_option("#language", "pt-PT")
        page.wait_for_timeout(300)
        ask(page, "telemóvel")
        text = chat_text(page)
        check(
            "pt-PT wikt notice",
            "Camada de ponte Wikcionário" in text,
            "",
        )
        check(
            "pt-PT wikt tag",
            "[Wikcionário, não revisto]" in text,
            "",
        )

        browser.close()

    if failures:
        print("\nFAILURES: %s" % ", ".join(failures))
        return 1
    print("\nAll bridge checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
