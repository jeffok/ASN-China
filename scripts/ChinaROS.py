"""
Generate RouterOS .rsc files from IPv4.China.list (CN CIDR prefixes).

Output files (gateway-free, universal for all nodes):
  - cn_routes.rsc        : /ip route add entries (no gateway; each node sets its own after import)
  - cn_address_list.rsc  : /ip firewall address-list entries
"""

INPUT_FILE = "IPv4.China.list"
COMMENT = "CN"
DISTANCE = 50


def read_cidrs(path: str) -> list[str]:
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip()]


def write_routes(cidrs: list[str], path: str) -> None:
    with open(path, "w") as f:
        f.write("/ip route\n")
        for cidr in cidrs:
            f.write(f"add dst-address={cidr} distance={DISTANCE} comment={COMMENT}\n")


def write_address_list(cidrs: list[str], path: str) -> None:
    with open(path, "w") as f:
        f.write("/ip firewall address-list\n")
        for cidr in cidrs:
            f.write(f"add list={COMMENT} address={cidr} comment={COMMENT}\n")


def main() -> None:
    cidrs = read_cidrs(INPUT_FILE)
    print(f"Read {len(cidrs)} IPv4 CIDRs from {INPUT_FILE}")

    write_routes(cidrs, "cn_routes.rsc")
    print(f"Generated cn_routes.rsc ({len(cidrs)} entries)")

    write_address_list(cidrs, "cn_address_list.rsc")
    print(f"Generated cn_address_list.rsc ({len(cidrs)} entries)")


if __name__ == "__main__":
    main()
