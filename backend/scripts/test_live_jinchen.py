"""
Live Jinchen MES Integration Test Script.

Validates that:
1. JinchenMESAdapter can connect to http://10.69.12.10:8000.
2. The provided Bearer token is accepted by ASP.NET.
3. LotFinalDataReport returns completed module records.
4. DefectData returns defect counts.
5. get_normalized_data() produces valid MESProductionRecord objects.

Usage:
  python scripts/test_live_jinchen.py
"""

import asyncio
import os
import sys
from datetime import date
from dotenv import load_dotenv

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.adapters.jinchen_adapter import JinchenMESAdapter, JINCHEN_LINE_IDS
from app.core.config import settings


async def main():
    load_dotenv()

    # Priority: explicit env var, settings, or CLI arg
    token = os.getenv("JINCHEN_API_TOKEN") or settings.jinchen_api_token
    base_url = os.getenv("JINCHEN_API_URL") or settings.jinchen_api_url

    print("=" * 65)
    print("      RENEWSYS MES AI CHATBOT — LIVE JINCHEN MES TEST")
    print("=" * 65)
    print(f"Target URL : {base_url}")
    print(f"Token Set  : {'YES (' + token[:15] + '...)' if token else 'NO (Set JINCHEN_API_TOKEN in .env)'}")
    print("-" * 65)

    if not token:
        print("[!] ERROR: Please set JINCHEN_API_TOKEN in your .env file or environment.")
        sys.exit(1)

    adapter = JinchenMESAdapter(base_url=base_url, api_token=token)

    # 1. Test basic connectivity
    print("[1] Testing HTTP reachability to Jinchen host...")
    reachable = await adapter.test_connection()
    if not reachable:
        print(f"    [!] WARNING: Cannot directly reach {base_url} from this machine.")
        print("    If running outside the plant network, ensure VPN or remote tunnel is active.")
        print("    If running inside the UltraViewer session machine, check firewall.")
        return

    print("    [✓] Host is reachable!\n")

    # 2. Test Production Summary (Shift A on 2026-10-03)
    print("[2] Testing LotFinalDataReport (Shift A on 2026-10-03)...")
    try:
        prod_resp = await adapter.fetch_production_summary(
            start_date="2026-10-03 07:00:00",
            end_date="2026-10-03 15:00:00",
            line_id=JINCHEN_LINE_IDS["KM2"],
            page_size=5,
        )
        total_prod = prod_resp.get("TotalCount", 0)
        items = prod_resp.get("Items", [])
        print(f"    [✓] Success! TotalCount = {total_prod} modules for Line 2 (RenK-2).")
        if items:
            sample = items[0]
            print(f"    Sample Lot: {sample.get('LotNumber')} | FinalProcess: {sample.get('FinalProcess')} | Grade: {sample.get('MinGrade')}")
    except Exception as e:
        print(f"    [!] Error calling LotFinalDataReport: {e}")

    print()

    # 3. Test Defect Summary (Shift A on 2026-10-03)
    print("[3] Testing DefectData (Shift A on 2026-10-03 with deduplication Type='0')...")
    try:
        defect_resp = await adapter.fetch_defect_summary(
            start_date="2026-10-03 07:00:00",
            end_date="2026-10-03 15:00:00",
            line_id=JINCHEN_LINE_IDS["KM2"],
            deduplicate=True,
            page_size=5,
        )
        total_defects = defect_resp.get("TotalCount", 0)
        print(f"    [✓] Success! Deduplicated Bad Lot Count = {total_defects} modules.")
    except Exception as e:
        print(f"    [!] Error calling DefectData: {e}")

    print()

    # 4. Test Normalization to MESProductionRecord
    print("[4] Testing End-to-End Data Normalization (get_normalized_data)...")
    try:
        records = await adapter.get_normalized_data(
            line="KM2",
            shift="A",
            date_from=date(2026, 10, 3),
        )
        print(f"    [✓] Generated {len(records)} normalized MESProductionRecord:")
        for r in records:
            print(f"        Date: {r.record_date} | Line: {r.line} | Shift: {r.shift}")
            print(f"        Produced: {r.departure_quantity} | Bad: {r.bad_quantity} | Scrap: {r.scrap_quantity}")
    except Exception as e:
        print(f"    [!] Error normalizing data: {e}")

    print("\n" + "=" * 65)
    print("Verification completed.")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
