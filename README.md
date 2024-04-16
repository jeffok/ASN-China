<!--
 * @Author: Vincent Young
 * @Date: 2022-11-17 02:07:33
 * @LastEditors: Vincent Young
 * @LastEditTime: 2022-11-17 03:33:16
 * @FilePath: /ASN-China/README.md
 * @Telegram: https://t.me/missuo
 * 
 * Copyright © 2022 by Vincent, All Rights Reserved. 
-->
# ASN-China
ASN and IP list in China library. UTC 20：00

## Features
- Automatic daily updates
- Reliable and accurate source

## Routeros V7 BGP China_ASN

### add script to Routeros 

```
/system script
add name="Update_China_ASN" source={
/log info "Fetching the script from the github."
/tool fetch url="https://raw.githubusercontent.com/jeffok/ASN-China/main/China_ASN.rsc" mode=https dst-path="China_ASN.rsc" check-certificate=yes
:delay 10s;
/log info "Removing existing entries from num-list 'China_ASN'."
/routing filter num-list/remove [find list="China_ASN"]
/log info "Download complete, preparing to import the script."
/import file-name="my-China_ASN.rsc"
/log info "Script import completed successfully."
}
```

### add scheduler
```
/system scheduler
add name="daily_update_Chain_ASN" start-time="04:00:00" interval=1d on-event="Update_China_ASN"

```

## Use in proxy app
### Surge
```
[Rule]
# > China ASN List
RULE-SET, https://raw.githubusercontent.com/missuo/ASN-China/main/ASN.China.list, Direct
```

### Quantumult X
```
[filter_remote]
# China ASN List
https://raw.githubusercontent.com/missuo/ASN-China/main/ASN.China.list, tag=ChinaASN, force-policy=direct, update-interval=86400, opt-parser=true, enabled=true
```


## Data Source
### ASN Information
- [bgp.he.net](https://bgp.he.net/country/CN)

### IP Information
- [cbuijs/ipasn](https://github.com/cbuijs/ipasn)

## Author's ASN
**[AS206729](https://bgp.he.net/AS206729)**

The ASN name has been officially changed in the Jan 20, 2022 UTC [Commit](https://github.com/missuo/ASN-China/commit/4345acd8e146c99d56792977d88ed1d6417c9e22).

## Author

**ASN-China** © [Vincent Young](https://github.com/missuo), Released under the [MIT](./LICENSE) License.<br>


