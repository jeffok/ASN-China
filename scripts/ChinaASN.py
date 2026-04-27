"""
Generate China ASN lists from APNIC delegated file.

Data source: https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest
Output files:
  - ASN.China.list   : Surge/Quantumult X format (IP-ASN,number // description)
  - China_ASN.rsc    : RouterOS /routing/filter/num-list format
"""

import re
import time
from urllib.request import urlopen, Request

APNIC_URL = "https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest"
PATTERN = re.compile(r"^apnic\|CN\|asn\|(\d+)\|")


def fetch_cn_asns() -> list[int]:
    req = Request(APNIC_URL, headers={"User-Agent": "ASN-China-CI/1.0"})
    with urlopen(req, timeout=30) as resp:
        lines = resp.read().decode("utf-8").splitlines()

    asns = []
    for line in lines:
        m = PATTERN.match(line)
        if m:
            asns.append(int(m.group(1)))

    asns.sort()
    return asns


def write_surge_list(asns: list[int], path: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    with open(path, "w") as f:
        f.write(f"// China ASN list (source: APNIC delegated)\n")
        f.write(f"// Last Updated: UTC {ts}\n")
        f.write(f"// https://github.com/jeffok/ASN-China\n\n")
        for asn in asns:
            f.write(f"IP-ASN,{asn}\n")


def write_ros_numlist(asns: list[int], path: str) -> None:
    with open(path, "w") as f:
        f.write("/routing/filter/num-list\n")
        for asn in asns:
            f.write(f"add list=China_ASN range={asn}\n")


def main() -> None:
    asns = fetch_cn_asns()
    print(f"Fetched {len(asns)} China ASNs from APNIC delegated file")

    write_surge_list(asns, "ASN.China.list")
    print(f"Generated ASN.China.list ({len(asns)} entries)")

    write_ros_numlist(asns, "China_ASN.rsc")
    print(f"Generated China_ASN.rsc ({len(asns)} entries)")


if __name__ == "__main__":
    main()
