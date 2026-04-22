#!/usr/bin/env python3
"""
從串流頁面提取 m3u8 URL
"""

import re
import sys
import urllib.request
import urllib.error

TARGET_URL = "https://anime1.in/2021-jiao-xiang-shi-pian-chao-jin-hua-3-hd-zhong-zi"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": "https://anime1.in/",
}

M3U8_PATTERN = re.compile(r'https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*')
IFRAME_PATTERN = re.compile(r'<iframe[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract_m3u8_urls(html: str) -> list[str]:
    return list(dict.fromkeys(M3U8_PATTERN.findall(html)))


def extract_iframes(html: str) -> list[str]:
    return list(dict.fromkeys(IFRAME_PATTERN.findall(html)))


def main() -> None:
    print(f"正在抓取頁面: {TARGET_URL}")
    try:
        html = fetch(TARGET_URL)
    except urllib.error.HTTPError as e:
        print(f"HTTP 錯誤: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"抓取失敗: {e}", file=sys.stderr)
        sys.exit(1)

    # 直接在頁面 HTML 中搜尋 m3u8
    urls = extract_m3u8_urls(html)
    if urls:
        print("\n找到以下 m3u8 URL:")
        for u in urls:
            print(f"  {u}")
        return

    # 若頁面本身沒有，嘗試跟進 iframe
    iframes = extract_iframes(html)
    if not iframes:
        print("頁面中未找到 m3u8 URL，也沒有 iframe 可追蹤。")
        print("可能需要執行 JavaScript（建議改用 Playwright/Selenium）。")
        return

    print(f"\n找到 {len(iframes)} 個 iframe，逐一追蹤...")
    for src in iframes:
        if not src.startswith("http"):
            src = "https://anime1.in" + src
        print(f"  抓取 iframe: {src}")
        try:
            iframe_html = fetch(src)
        except Exception as e:
            print(f"    失敗: {e}")
            continue
        urls = extract_m3u8_urls(iframe_html)
        if urls:
            print("  找到 m3u8 URL:")
            for u in urls:
                print(f"    {u}")
            return

    print("所有 iframe 中均未找到 m3u8 URL。")
    print("該頁面可能透過 JavaScript 動態載入串流位址，建議使用 Playwright 等工具。")


if __name__ == "__main__":
    main()
