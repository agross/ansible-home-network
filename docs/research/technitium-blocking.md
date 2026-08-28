# Technitium DNS blocking responses

Checked 2026-08-28 against upstream commit `d0484b6c1e7439cdc53d67d81e9c876cda2ad756`. Static source verification only; no server deployed.

## Answer

Yes. Built-in domain blocking supports genuine NODATA for A and AAAA requests by selecting `CustomAddress` and leaving custom blocking addresses empty. This is not the same as returning `0.0.0.0` or `::`. The response paths explicitly return `NoError`, with no answer records when the requested address-family collection is empty. This applies to both manually blocked domains and subscribed blocklists. [Manual blocking source](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L4575-L4652), [blocklist source](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/ZoneManagers/BlockListZoneManager.cs#L888-L971).

## Configuration

In Settings → Blocking, enable blocking, select **Custom Address**, clear **Custom Blocking Addresses**, then save. The web client serializes the empty field as `customBlockingAddresses=false`. Equivalent settings API fields:

```text
enableBlocking=true
blockingType=CustomAddress
customBlockingAddresses=false
```

Send these fields to `/api/settings/set` using the normal authenticated API request. The API clears both address-family collections, whose setters normalize null to empty collections. [UI fields](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/www/index.html#L2126-L2138), [UI serialization](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/www/js/main.js#L2095-L2114), [API implementation](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/WebServiceSettingsApi.cs#L1516-L1549), [collection setters](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L8119-L8141).

The documented blocking types are `AnyAddress`, `NxDomain`, and `CustomAddress`; there is no separately named NODATA mode. The empty-list behavior above is verified in source, not explicitly promised in the API prose. [API documentation](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/APIDOCS.md#L5222-L5228).

This built-in setting is global for blocked domains, not a per-domain AAAA-only selector. TXT blocking reports can still produce TXT answers when enabled, and blocklist SOA/NS queries have special responses. Do not describe this as empty answers for every query type. [Blocking response source](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/ZoneManagers/BlockListZoneManager.cs#L862-L971).

## OGD AAAA-only requirement

The official **NO DATA** app directly supports selecting record types in Conditional Forwarder zones. An APP record with data below returns `NoError` with no answer for AAAA, while other types return null to continue APP fallback resolution (not necessarily the normal blocklist pipeline):

```json
{"blockedTypes":["AAAA"]}
```

Use records for the domain apex and a wildcard when subdomains must match too. The app checks exact record names or wildcard names before applying the type list. Thus A requests can continue through conditional forwarding rather than receiving fabricated custom addresses. [NO DATA app source](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/NoDataApp/App.cs#L55-L89).

The separate Filter AAAA app is not identical: it filters only when an A answer exists and avoids modifying signed answers for DNSSEC-aware clients. NO DATA supplies unconditional AAAA-only empty answers, but is not an unqualified migration recommendation: APP fallback can bypass normal blocklist checks for A queries on APP-covered names, and the app omits SOA negative-cache TTL metadata. See [full parity review](technitium-adguard-parity.md) for the source trace and required overlap tests. [Filter AAAA source](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/FilterAaaaApp/App.cs).
