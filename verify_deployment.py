"""
verify_deployment.py — FoodBridge GAE Deployment Verifier
Run this AFTER deploying to confirm all endpoints are live.

Usage:
  python verify_deployment.py --url https://YOUR_PROJECT_ID.appspot.com
  python verify_deployment.py --url http://127.0.0.1:5000   (local test)
"""

import sys
import argparse
import urllib.request
import urllib.error
import json
from datetime import datetime


def check(label, url, expected_status=200, check_text=None):
    """Hit a URL and report the result."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FoodBridge-Verifier/1.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            status = res.status
            body   = res.read().decode("utf-8", errors="ignore")
            ok     = (status == expected_status)
            if check_text:
                ok = ok and (check_text.lower() in body.lower())
            icon = "PASS" if ok else "WARN"
            print(f"  [{icon}] {label:<40} HTTP {status}")
            return ok
    except urllib.error.HTTPError as e:
        ok = (e.code == expected_status)
        icon = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {label:<40} HTTP {e.code}")
        return ok
    except Exception as e:
        print(f"  [FAIL] {label:<40} ERROR: {e}")
        return False


def divider(char="-", width=65):
    print(char * width)


def main():
    parser = argparse.ArgumentParser(description="FoodBridge Deployment Verifier")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:5000",
        help="Base URL of deployed app (e.g. https://YOUR_PROJECT.appspot.com)"
    )
    args = parser.parse_args()
    base = args.url.rstrip("/")

    print()
    divider("=")
    print("  FOODBRIDGE -- DEPLOYMENT VERIFICATION")
    print(f"  Target: {base}")
    print(f"  Time  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    divider("=")

    results = []

    # ── Public pages ─────────────────────────────────────────────
    print()
    print("  PUBLIC PAGES")
    divider()
    results.append(check("Home page",          f"{base}/",             200))
    results.append(check("About page",         f"{base}/about",        200))
    results.append(check("Login page",         f"{base}/auth/login",   200))
    results.append(check("Register page",      f"{base}/auth/register",200))

    # ── REST API ──────────────────────────────────────────────────
    print()
    print("  REST API ENDPOINTS")
    divider()
    results.append(check("API donations list", f"{base}/api/donations",         200))
    results.append(check("API nearby donations",f"{base}/api/donations/nearby?lat=13.08&lng=80.27&radius=25", 200))
    results.append(check("API dashboard stats",f"{base}/api/dashboard/stats",   200))

    # ── Protected routes (Flask-Login redirects to login)
    # urllib follows 302 redirects so we see the login page (200)
    print()
    print("  PROTECTED ROUTES (redirect to login page = 200 via urllib)")
    divider()
    results.append(check("Donor dashboard (redirects to login)", f"{base}/donor/dashboard", 200))
    results.append(check("NGO dashboard (redirects to login)",   f"{base}/ngo/dashboard",   200))
    results.append(check("Admin dashboard (redirects to login)", f"{base}/admin/dashboard", 200))

    # ── Error pages ───────────────────────────────────────────────
    print()
    print("  ERROR PAGES")
    divider()
    results.append(check("404 page",           f"{base}/this-page-does-not-exist", 404))

    # ── Summary ───────────────────────────────────────────────────
    passed = sum(results)
    total  = len(results)
    print()
    divider("=")
    print(f"  RESULT : {passed}/{total} checks passed")

    if passed == total:
        print("  STATUS : DEPLOYMENT IS HEALTHY!")
    elif passed >= total * 0.8:
        print("  STATUS : MOSTLY OK — check WARN items above.")
    else:
        print("  STATUS : ISSUES DETECTED — review failures above.")

    divider("=")
    print()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
