# ASN-China

China ASN and IP prefix lists, auto-updated daily via GitHub Actions.

## Generated Files

All files are published to the [`release-files`](https://github.com/jeffok/ASN-China/tree/release-files) branch.

### IP Lists (plain text, one CIDR per line)

| File | Description |
|------|-------------|
| `IPv4.China.list` | China IPv4 prefixes |
| `IPv6.China.list` | China IPv6 prefixes |
| `IP.China.list` | IPv4 + IPv6 combined |

### RouterOS Scripts (.rsc)

| File | Description |
|------|-------------|
| `cn_routes.rsc` | Static routes for CN prefixes (no gateway, universal) |
| `cn_address_list.rsc` | Firewall address-list entries (`list=CN`) |
| `China_ASN.rsc` | BGP filter num-list for China ASNs |

### ASN List

| File | Description |
|------|-------------|
| `ASN.China.list` | China ASN list (Surge/Quantumult X format) |

## RouterOS Usage

### CN Static Routes

`cn_routes.rsc` contains route entries **without gateway**, so every node can use the same file and set its own gateway after import.

**Step 1 — Create the update script on your RouterOS device:**

```routeros
/system script add name="Update_CN_Routes" source={
    :local filename "cn_routes.rsc"
    :local url "https://raw.githubusercontent.com/jeffok/ASN-China/release-files/cn_routes.rsc"
    :local commentTag "CN"
    :local gateway "YOUR_GATEWAY"

    :if ([:len [/file find name=$filename]] > 0) do={
        /file remove $filename
    }

    :log info "Downloading $filename ..."
    /tool fetch url=$url dst-path=$filename
    :delay 5s

    :log info "Removing old $commentTag routes ..."
    /ip route remove [/ip route find comment=$commentTag]

    :if ([:len [/file find name=$filename]] > 0) do={
        :log info "Importing $filename ..."
        /import file-name=$filename
    } else={
        :log error "Download failed: $filename not found"
        :error "abort"
    }

    :log info "Setting gateway=$gateway for $commentTag routes ..."
    /ip route set [/ip route find comment=$commentTag] gateway=$gateway

    :log info "$commentTag routes updated."
}
```

Replace `YOUR_GATEWAY` with the actual gateway for your node, for example:

| Node | Gateway |
|------|---------|
| hkcloud | `45.250.184.1` (ext-cn) |
| szhome | `pppoe-cn` |
| dxbhome | WG peer address to hkcloud |

**Step 2 — Schedule daily updates:**

```routeros
/system scheduler add name="daily_cn_routes" start-time=03:00:00 interval=1d on-event="Update_CN_Routes"
```

### CN Address List

```routeros
/system script add name="Update_CN_AddressList" source={
    :local filename "cn_address_list.rsc"
    :local url "https://raw.githubusercontent.com/jeffok/ASN-China/release-files/cn_address_list.rsc"

    :if ([:len [/file find name=$filename]] > 0) do={
        /file remove $filename
    }

    /tool fetch url=$url dst-path=$filename
    :delay 5s

    /ip firewall address-list remove [/ip firewall address-list find list=CN comment=CN]

    :if ([:len [/file find name=$filename]] > 0) do={
        /import file-name=$filename
        :log info "CN address-list updated."
    }
}
```

### China ASN (BGP filter)

```routeros
/system script add name="Update_China_ASN" source={
    /tool fetch url="https://raw.githubusercontent.com/jeffok/ASN-China/release-files/China_ASN.rsc" dst-path="China_ASN.rsc"
    :delay 10s
    /routing filter num-list remove [find list="China_ASN"]
    /import file-name="China_ASN.rsc"
    :log info "China ASN list updated."
}

/system scheduler add name="daily_china_asn" start-time=04:00:00 interval=1d on-event="Update_China_ASN"
```

## Data Sources

| Data | Source |
|------|--------|
| IP prefixes | [Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip) (aggregated from APNIC, MaxMind, etc.) |
| ASN list | [bgp.he.net/country/CN](https://bgp.he.net/country/CN) |

## Update Schedule

GitHub Actions runs daily at **UTC 18:10 (Beijing 02:10)**. Files are force-pushed to the `release-files` branch.

## License

[MIT](./LICENSE)
