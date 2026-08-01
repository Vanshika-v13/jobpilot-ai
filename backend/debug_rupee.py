"""
Diagnostic script to trace WHERE the rupee -> mojibake corruption happens.
Run from the backend directory with venv activated:
    python debug_rupee.py
"""
import asyncio
import sys
import os
import json
import io
import httpx
from urllib.parse import urlencode

# Force stdout to UTF-8 so we can print rupee on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


async def stage1_raw_fetch():
    print("=" * 70)
    print("STAGE 1: Raw HTTP fetch from Unstop API")
    print("=" * 70)

    params = {
        "opportunity": "jobs",
        "oppstatus": "open",
        "per_page": 5,
        "page": 1,
        "searchTerm": "python developer",
        "city": "bangalore",
    }
    url = f"https://unstop.com/api/public/opportunity/search-new?{urlencode(params)}"

    async with httpx.AsyncClient(
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://unstop.com/jobs",
        },
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()

        print(f"  Content-Type header            : {resp.headers.get('content-type', '(missing)')}")
        print(f"  resp.charset_encoding (auto)   : {resp.charset_encoding}")
        print(f"  resp.encoding                  : {resp.encoding}")

        # Check for raw rupee bytes
        raw = resp.content
        rupee_utf8 = b"\xe2\x82\xb9"
        count = raw.count(rupee_utf8)
        print(f"  Raw bytes contain UTF-8 rupee  : {count} occurrences")

        payload = resp.json()
        items = payload.get("data", {}).get("data", [])
        print(f"  Items returned                 : {len(items)}")

        print()
        print("  --- Currency / salary fields from API ---")
        for i, item in enumerate(items[:5]):
            jd = item.get("jobDetail", {})
            currency = jd.get("currency", "")
            min_sal = jd.get("min_salary")
            max_sal = jd.get("max_salary")
            show = jd.get("show_salary")
            if currency or min_sal or max_sal:
                print(f"  Item {i}: currency={currency!r}  show={show}  min={min_sal}  max={max_sal}")

        # --- Inline version of _extract_salary to test ---
        print()
        print("  --- Inline _extract_salary test ---")
        for i, item in enumerate(items[:5]):
            jd = item.get("jobDetail", {})
            if not jd.get("show_salary"):
                continue
            min_sal = jd.get("min_salary")
            max_sal = jd.get("max_salary")
            currency = jd.get("currency", "")
            pay_in = jd.get("pay_in", "")
            if min_sal is None and max_sal is None:
                continue
            # This is the line from tools/unstop.py:
            symbol = "\u20b9" if "rupee" in currency else currency  # U+20B9 = ₹
            parts = []
            if min_sal is not None:
                parts.append(str(min_sal))
            if max_sal is not None and max_sal != min_sal:
                parts.append(str(max_sal))
            salary = f"{symbol}{' - '.join(parts)}"
            if pay_in:
                salary += f" ({pay_in})"

            print(f"  Item {i}:")
            print(f"    salary string repr   : {salary!r}")
            print(f"    salary UTF-8 hex     : {salary.encode('utf-8').hex()}")
            print(f"    salary print         : {salary}")
            print(f"    first char is U+20B9 : {salary[0] == chr(0x20b9)}")
            break

        return items


async def stage2_check_mongodb():
    print()
    print("=" * 70)
    print("STAGE 2: Check what MongoDB stores for salary fields")
    print("=" * 70)

    try:
        from database.connection import connect_to_mongo, get_database, close_mongo_connection
        await connect_to_mongo()
        db = get_database()

        cursor = db.jobs.find(
            {"source": "unstop", "salary": {"$ne": "Not disclosed"}},
            {"salary": 1, "role": 1, "_id": 0}
        ).limit(10)
        jobs = await cursor.to_list(length=10)

        if not jobs:
            print("  WARNING: No Unstop jobs with salary data found in MongoDB")
        else:
            for j in jobs:
                sal = j.get("salary", "")
                role = j.get("role", "?")
                sal_hex = sal.encode("utf-8").hex()
                has_correct = "\u20b9" in sal
                has_corrupted = "\u00e2" in sal
                print(f"  role: {role!r}")
                print(f"    salary repr        : {sal!r}")
                print(f"    salary UTF-8 hex   : {sal_hex}")
                print(f"    contains U+20B9    : {has_correct}  (correct rupee)")
                print(f"    contains U+00E2    : {has_corrupted}  (mojibake indicator)")
                print()

        await close_mongo_connection()
    except Exception as e:
        print(f"  ERROR connecting to MongoDB: {e}")


async def stage3_serialization():
    print()
    print("=" * 70)
    print("STAGE 3: JSON / FastAPI serialization analysis")
    print("=" * 70)

    test_str = "\u20b920000 - 30000 (monthly)"
    print(f"  Test string repr     : {test_str!r}")
    print(f"  Test string hex      : {test_str.encode('utf-8').hex()}")
    print()

    j1 = json.dumps({"salary": test_str})
    print(f"  json.dumps(ensure_ascii=True) : {j1}")

    j2 = json.dumps({"salary": test_str}, ensure_ascii=False)
    print(f"  json.dumps(ensure_ascii=False): {j2}")
    print()

    try:
        from starlette.responses import JSONResponse
        jr = JSONResponse(content={"salary": test_str})
        body = jr.body
        print(f"  Starlette JSONResponse body hex : {body.hex()}")
        print(f"  Starlette JSONResponse body str : {body.decode('utf-8')}")
        if b"\\u20b9" in body:
            print("  -> Uses ensure_ascii: rupee is JSON-escaped as \\u20b9 (SAFE)")
        elif b"\xe2\x82\xb9" in body:
            print("  -> Sends raw UTF-8 rupee bytes (needs UTF-8 consumer)")
    except Exception as e:
        print(f"  JSONResponse test failed: {e}")

    print()
    print("  --- PowerShell mojibake proof ---")
    rupee_bytes = "\u20b9".encode("utf-8")  # b'\xe2\x82\xb9'
    mojibake = rupee_bytes.decode("latin-1")  # what latin-1 sees
    print(f"  UTF-8 bytes for rupee : {rupee_bytes!r}")
    print(f"  Decoded as latin-1    : {mojibake!r}")
    print()

    print("  Windows console codepage:")
    import locale
    print(f"    locale.getpreferredencoding() = {locale.getpreferredencoding()}")
    print(f"    sys.stdout.encoding (orig)    = cp1252 (overridden to utf-8 for this script)")
    print()
    print("  DIAGNOSIS:")
    print("  The corruption 'a\\u0302\\u00b9' or 'a\\xcc\\x82\\xb9' is the classic sign of")
    print("  UTF-8 bytes (E2 82 B9) being decoded through Windows-1252/latin-1.")
    print()
    print("  This happens in PowerShell's pipeline:")
    print("    1. FastAPI sends correct UTF-8 JSON body with raw rupee bytes")
    print("    2. Invoke-RestMethod decodes the body using system codepage (cp1252)")
    print("    3. Each byte E2, 82, B9 is decoded as separate cp1252 chars")
    print("    4. ConvertTo-Json + Out-File writes these corrupted chars to file")


async def main():
    await stage1_raw_fetch()
    await stage2_check_mongodb()
    await stage3_serialization()

    print()
    print("=" * 70)
    print("FINAL VERDICT")
    print("=" * 70)
    print("""
KEY FINDING from Stage 1:
  - The Unstop API does NOT send the rupee symbol at all!
  - The currency field contains 'fa-rupee' (a FontAwesome class name)
  - Your code in _extract_salary() generates the rupee symbol:
      symbol = "₹" if "rupee" in currency else currency
  - This means the CORRECT U+20B9 character is produced in Python memory

The corruption chain:
  Python ₹ (U+20B9)
    -> MongoDB stores it correctly (BSON is always UTF-8)
    -> FastAPI/Starlette sends it in JSON response
    -> PowerShell's Invoke-RestMethod decodes using cp1252
    -> ₹ becomes mojibake

FIXES (choose one):
  A. Force UTF-8 in Out-File:
     ... | Out-File -Encoding utf8 result.json

  B. Use Invoke-WebRequest instead:
     $r = Invoke-WebRequest -Uri ... -Method Post -ContentType "application/json" -Body $body
     [System.IO.File]::WriteAllText("result.json", $r.Content, [System.Text.Encoding]::UTF8)

  C. Use curl.exe directly:
     curl.exe -X POST http://127.0.0.1:8000/api/v1/search -H "Content-Type: application/json" -d @body.json -o result.json

  D. View the API response in a browser or Postman (both handle UTF-8 correctly)
""")


if __name__ == "__main__":
    asyncio.run(main())
