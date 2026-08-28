# Technitium DNS Server: AdGuard parity audit

Checked 2026-08-28 against Technitium v15.4, commit [d0484b6c1e7439cdc53d67d81e9c876cda2ad756](https://github.com/TechnitiumSoftware/DnsServer/commit/d0484b6c1e7439cdc53d67d81e9c876cda2ad756). Static source verification, not a running-server test.

Scope: current [AdGuard template](../../roles/dns-server/templates/adguard/AdGuardHome.yaml.j2), [role defaults](../../roles/dns-server/defaults/main.yml), and prior extraction of the OGD attachment. The original Downloads attachment was unavailable for this audit; production-only differences remain unverified. No infrastructure changes.

Related alternative: [Pi-hole assessment](pihole-adguard-parity.md), rejected because installer-free native deployment has too many moving parts and Docker is not permitted on the DNS host.

## Configuration management: blocker for this repository

**Technitium is unsuitable for this repository's template-managed deployment model.** The complete desired configuration must be rendered from version-controlled Ansible templates, compared with deployed configuration, and reapplied to detect and correct drift. API access to individual settings does not satisfy that requirement.

Technitium persists core DNS and web-service settings in versioned binary files, not a supported declarative YAML/TOML/JSON configuration that this role can template. Routine configuration uses the UI/API. Some apps expose JSON configuration, but that covers only those apps, not the complete server state. [DNS configuration storage](https://github.com/TechnitiumSoftware/DnsServer/blob/v15.4.0/DnsServerCore/Dns/DnsServer.cs#L1118-L1123), [web configuration storage](https://github.com/TechnitiumSoftware/DnsServer/blob/v15.4.0/DnsServerCore/DnsWebService.cs#L540-L577), [app configuration](https://github.com/TechnitiumSoftware/DnsServer/blob/v15.4.0/Apps/AdvancedBlockingApp/README.md#configuration).

Consequences here:

- No complete server configuration can be managed using the existing template-and-restart workflow.
- Existing Ansible template comparison/check/diff cannot verify that deployed settings have not drifted from the repository's desired state.
- Successful API writes do not prove convergence: obsolete zones, records, rules, or settings can remain unless explicitly reconciled.
- API-based drift detection is theoretically possible, but would require separate read/normalize/compare/reconcile tooling, including deletion handling and authentication. That is a different management model, not a solution within this repository's template requirement.

**Disposition: reject Technitium for this deployment model.** Individual feature matches below do not remove this blocker. Reconsider only if complete declarative configuration support becomes available or the repository's management requirement is explicitly changed.

## Filtering conclusion

Not an exact drop-in replacement. Subscriptions, allowlists, NOERROR address blocking, and update intervals are available. Adblock parsing, selective AAAA composition, and non-address answers need explicit decisions and regression tests.

### Subscriptions

| Existing subscription | State | Technitium mapping |
| --- | --- | --- |
| [AdGuard DNS](https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt) | Enabled | Built-in parser or Advanced Blocking `adblockListUrls`; partial syntax. |
| [AdAway](https://adaway.org/hosts.txt) | Enabled | Built-in parser or app `blockListUrls`; hosts format. |
| [EasyList Germany](https://easylist.to/easylistgermany/easylistgermany.txt) | Enabled | Adblock domain subset only. |
| [EasyList](https://easylist.to/easylist/easylist.txt) | Enabled | Adblock domain subset only. |
| [Smart TV](https://raw.githubusercontent.com/hkamran80/blocklists/refs/heads/main/smart-tv.txt) | Disabled | Omit from app URLs; built-in supports commented URL entries. |
| [Adobe](https://a.dove.isdumb.one/pihole.txt) | Enabled | Built-in parser or app `blockListUrls`; plain domains. |

Both parsers accept anchored domain rules and exceptions, but only narrowly recognize modifiers containing `doc` or `all`. They do not implement AdGuard's full `$important`, `$badfilter`, `$dnstype`, `$dnsrewrite`, or regex semantics. Current AdGuard subscription contains such rules, e.g. `||adsrvmedia.adk2.co^$important`. URL acceptance therefore does not establish filtering parity. EasyList also contains browser-only path/cosmetic rules that neither DNS server reproduces; those are not uniquely a Technitium regression. [Built-in parser](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/ZoneManagers/BlockListZoneManager.cs#L355-L489), [app parser](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/AdvancedBlockingApp/App.cs#L1595-L1673).

Advanced Blocking supports `blockingAnswerTtl: 10` and `blockListUrlUpdateIntervalHours: 12`. Put all subscriptions and exceptions in that app if selected: its configuration is independent of built-in blocking. Built-in also accepts a 12-hour interval. [App configuration](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/AdvancedBlockingApp/README.md), [built-in interval](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/ZoneManagers/BlockListZoneManager.cs#L1095-L1114).

### Allow exceptions

Translate `@@||localhost^$important`, `@@||sdk.split.io^$important`, and `@@||auth.split.io^$important` into explicit allowed domain entries, not verbatim Adblock strings. App allow entries include descendants; allow checks precede blocking. This preserves these exceptions' intent, not arbitrary AdGuard priority semantics. [Allow matching](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/AdvancedBlockingApp/App.cs#L153-L169), [allow-before-block](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L4679-L4700).

### NOERROR/NODATA and TTL

The role pins custom AdGuard `v0.107.79+fix-8024`. Its `noerror` mode returns no answer records plus SOA authority, including non-address queries. [Fork response code](https://github.com/agross/AdGuardHome/blob/v0.107.79%2Bfix-8024/internal/dnsforward/msg.go#L58-L86), [NOERROR constructor](https://github.com/agross/AdGuardHome/blob/v0.107.79%2Bfix-8024/internal/dnsforward/msg.go#L407-L412).

Technitium built-in Custom Address with empty addresses produces NOERROR, empty A/AAAA answers and SOA authority; set blocking TTL to 10. However, NS/SOA queries receive synthesized answer records. Disable TXT blocking reports to avoid TXT answers. Ordinary address blocking matches, universal empty-answer behavior does not. [Built-in answers](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/ZoneManagers/BlockListZoneManager.cs#L826-L979).

Advanced Blocking with `blockAsNxDomain: false`, `blockingAddresses: []`, and `allowTxtBlockingReport: false` yields empty A/AAAA answers **without SOA**; its TTL is not carried in those empty replies. It also synthesizes NS/SOA answers. [App answers](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/AdvancedBlockingApp/App.cs#L613-L707).

### Selective AAAA suppression

All 14 configured domains need apex and descendant coverage:

`google.de`, `google.com`, `youtube.com`, `youtube-nocookie.com`, `googleapis.com`, `googlevideo.com`, `netflix.com`, `netflix.net`, `nflxvideo.net`, `nflximg.net`, `nflximg.com`, `nflxext.com`, `nflxsearch.net`, `nflxso.net`.

NO DATA app accepts `{"blockedTypes":["AAAA"]}` in conditional-forwarder APP records. Use apex and wildcard coverage. It returns empty NOERROR unconditionally for matching AAAA requests, but emits no SOA and ignores APP TTL; negative caching TTL 10 is not equivalent. [NO DATA implementation](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/NoDataApp/App.cs#L55-L73).

**Composition caveat, source-traced but not live-tested:** authoritative/APP processing precedes recursive blocking. NO DATA returns null for A; APP fallback invokes `RecursiveResolveAsync` directly, whereas ordinary FWD processing invokes `ProcessRecursiveQueryAsync`, which checks allow/block rules. APP-covered A queries may therefore bypass subscriptions. Do not assume “NO DATA plus Advanced Blocking” reproduces both policies. [Query ordering](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L2873-L2890), [FWD/APP dispatch](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L3813-L3831), [APP fallback](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L3955-L3980).

Filter AAAA app is **not an exact alternative**: it only removes AAAA when an additional A lookup succeeds with an A answer, preserves CNAMEs, and bypasses signed responses for DNSSEC-aware clients. `filterDomains` covers descendants; an empty list filters globally. [Filter AAAA implementation](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/FilterAaaaApp/App.cs#L115-L226).

### Special blocked questions

Technitium rejects non-IN classes, preventing ordinary CHAOS-class version/identity disclosure. Drop Requests app can additionally match exact `version.bind`, `id.server`, `hostname.bind` for all types. Clear example private/loopback `allowedNetworks` if those clients must also follow rules. [Class refusal](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L2842-L2850), [Drop Requests logic](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/DropRequestsApp/App.cs), [default bypasses](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/DropRequestsApp/dnsApp.config).

AdGuard `refuse_any: true` differs from Technitium's default: Technitium forces UDP ANY onto TCP. Drop Requests can drop ANY on all transports, but silently dropping differs from refusal. [ANY handling](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L2873-L2890), [Drop Requests example](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/DropRequestsApp/dnsApp.config).

## Filtering acceptance tests before migration

- Each apex, child, deep descendant, mixed case, and CNAME target: AAAA empty NOERROR; A unaffected unless independently blocked.
- Names with no A, signed AAAA plus DO bit, and upstream failure: confirm deliberate behavior.
- Temporary blocked descendant inside a NO DATA zone: A must remain blocked, not forwarded around subscriptions.
- Representative domains per subscription; modifier/regex samples; three allow exceptions and descendants.
- Blocked A, AAAA, HTTPS, TXT, NS, SOA, MX: compare RCODE, answers, authority, EDE, and negative TTL against AdGuard.
- ANY over UDP/TCP; special names with IN/CH classes from LAN/loopback.
- Update after 12 hours; failed download keeps prior rules; disabled Smart TV stays inactive.

## Resolver and network settings

Retain dnsmasq, dnscrypt-proxy, and systemd-resolved; this assessment replaces AdGuard only. OGD routing inputs are in [site variables](../../host_vars/dns-ogd/dns-server.yml). Technitium's settings and FWD record API expose the following controls. [Settings implementation](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/WebServiceSettingsApi.cs), [API reference](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/APIDOCS.md#settings-api-calls).

| Current behavior | Mapping and result |
| --- | --- |
| IPv4 listener on port 53 | `dnsServerLocalEndPoints=0.0.0.0:53`. AAAA record queries do not require an IPv6 listener. |
| Default resolver | UDP forwarder `127.0.0.1:54`, retaining the existing downstream chain. |
| OGD domain-specific resolver | Conditional Forwarder zone for each site domain, targeting `172.16.0.4`. Preserve per-FWD DNSSEC=false. |
| 10-second upstream timeout | `forwarderTimeout=10000` and `clientTimeout=10000`; also choose retry count. These do not establish an identical total deadline. |
| DNSSEC/ECS disabled | `dnssecValidation=false`, `eDnsClientSubnet=false`. DNSSEC on FWD records also needs disabling. |
| No DNS rate limit | Clear IPv4/IPv6 QPM prefix limits or set zero limits. |
| No optimistic cache | `serveStale=false`; disable extra prefetch with `cachePrefetchTrigger=0`. Avoid introducing cache persistence if not wanted. |
| 16 MiB cache | No byte-equivalent setting: Technitium limits entries. Measure memory and choose entry budget. [Cache limit](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/ZoneManagers/CacheZoneManager.cs#L1231-L1244). |
| No TTL overrides | Minimum/maximum TTL configurable, but zero maximum does not mean unlimited. Do not copy AdGuard's `0/0` blindly; verify maximum accepted by the deployed build. |
| 300 goroutines | No direct equivalent across Go and .NET. Technitium has per-core concurrent resolution limits; requires performance testing, not numeric translation. |

Private PTR routing requires explicit zones. Configure the applicable IPv4 reverse zones to dnsmasq on port 54 and `ip6.arpa` to `127.0.0.1:56`. Otherwise Technitium's built-in locally served private zones can answer before the global forwarder. Explicit non-root FWD zones override them. Keep systemd-resolved: the routing is supported, but Technitium does not replace its NDP-assisted lookup function. [Special-zone precedence](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L3843-L3875).

IP-literal upstreams need no hostname bootstrap resolvers. Configured forwarders do not automatically fall back to root recursion on failure; leaving forwarders empty selects recursion instead. Different upstream-selection algorithms are immaterial with one resolver per route. Matching in-flight requests share a resolver task, providing the intent of `pending_requests.enabled`. [Forwarding branch](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L5188-L5359), [request sharing](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L4902-L4924).

Default recursion policy permits private networks only. If enabling an IPv6 listener, explicitly allow actual LAN/VPN prefixes, including globally routed TunnelBroker IPv6 ranges; do not expose unrestricted recursion. `resolver.arpa` is locally served, but automatic DDR advertisement parity was not verified. AdGuard TLS is currently disabled, so no working encrypted endpoint must be advertised. [Recursion policy](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/DnsServer.cs#L2689-L2708), [special resolver zone](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/ZoneManagers/SpecialZoneManager.cs#L154-L161).

## Logs, statistics, and client identity

| Current behavior | Result |
| --- | --- |
| Persistent query history, one day | Query Logs SQLite app supports `maxLogDays=1`, `maxLogRecords=0`, `useInMemoryDb=false`. Persistent, searchable history is available, but SQLite is not AdGuard's query-log file format. |
| Statistics, 90 days | `enableInMemoryStats=false`, `maxStatFileDays=90`. |
| Unanonymized clients | Client addresses remain available in query records. |
| Client reverse names | Dashboard consults its own DHCP map, then PTR. Existing dnsmasq names remain available through correct PTR forwarding. |
| ARP/WHOIS discovery | No equivalent verified. Treat as a discovery/UI gap, not loss of DNS resolution. |
| Diagnostic logging | Technitium has general file logging and retention; built-in query logging shares that log. AdGuard's empty diagnostic `log.file` means its file-rotation values are not evidence of an active separate diagnostic file. Configure logging deliberately, not by copying those defaults. |

[SQLite configuration](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/QueryLogsSqliteApp/README.md#configuration), [statistics cleanup](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Dns/StatsManager.cs#L190-L215), [client-name lookup](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/WebServiceDashboardApi.cs#L80-L110). Existing AdGuard history import was not verified.

## DHCP, administration, and disabled features

- **No DHCP:** keep all Technitium scopes disabled/absent. Existing dnsmasq DHCP stays outside this replacement. [Scope controls](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/APIDOCS.md#disable-dhcp-scope).
- **HTTP UI behind Traefik:** bind web console to the required address/port, including port 80 if retaining the current backend URL. Keep web TLS/redirect disabled behind TLS termination; configure only actual trusted proxies and the matching real-IP header. DNS-over-HTTP is a separate service and must remain disabled. [Web settings](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/WebServiceSettingsApi.cs).
- **Users/passwords:** local users supported, but AdGuard bcrypt hashes are not an interchangeable configuration. Recreate credentials from the existing vault through Technitium's account API, which uses PBKDF2. [User API](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/APIDOCS.md#set-user-details).
- **30-day sessions:** `sessionTimeoutSeconds=2592000` can express that duration, but Technitium measures inactivity from last seen; do not assert identical expiry semantics. [Session implementation](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Auth/UserSession.cs#L135-L146).
- **Five login failures / 15-minute lockout:** not exact. Technitium v15.4 hardcodes five attempts and a five-minute network block. Exact 15-minute behavior needs a separate enforcement mechanism or code change. [Authentication constants and logic](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/Auth/AuthManager.cs#L45-L49).
- **Disabled DNS64, Safe Search, parental filtering, Safe Browsing, rewrites:** no active behavior to reproduce; do not enable corresponding apps/policies. DNS64 is an optional app. [DNS64 app](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/Apps/Dns64App/README.md).
- **Disabled inbound encrypted DNS and HTTP/3:** leave DoH/DoT/DoQ/HTTP3 listeners off. Keep existing external DNSCrypt proxy instead of assuming Technitium replaces it. [Listener settings](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerCore/WebServiceSettingsApi.cs).

UI language/theme, profiler settings, unused proxy/IP-set/bogus-NXDOMAIN configuration, and empty persistent-client rules were not treated as active network-policy requirements. No verbatim AdGuard YAML import exists in this assessment; configuration must be translated.

## Deployment constraints

Native custom-systemd deployment without Docker or the installer is supported. Upstream supplies a hardened unit running as an unprivileged user with only the bind-service capability. Adapt its paths, target membership, failure notification, and restart policy. Use Technitium's unit as the starting point; the Pi-hole-specific proposal is not a verified Technitium sandbox. [Upstream unit](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerApp/systemd.service).

**Strict GitHub prebuilt-release download is a gap.** v15.4.0's GitHub release has no uploaded binary assets, only source archives. Choices requiring an explicit implementation decision:

1. Download the versioned official portable archive and checksum from Technitium's own server; this meets no-Docker/no-installer, but not GitHub-only artifact origin.
2. Build pinned GitHub source and its TechnitiumLibrary dependency, then deploy the resulting artifact.

The server targets .NET 10. Neither path is the former single-Go-binary deployment. [GitHub release](https://github.com/TechnitiumSoftware/DnsServer/releases/tag/v15.4.0), [release API](https://api.github.com/repos/TechnitiumSoftware/DnsServer/releases/tags/v15.4.0), [versioned portable archive and checksum](https://download.technitium.com/dns/archive/15.4.0/), [build instructions](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/build.md), [target framework](https://github.com/TechnitiumSoftware/DnsServer/blob/d0484b6c1e7439cdc53d67d81e9c876cda2ad756/DnsServerApp/DnsServerApp.csproj#L5).

## Additional acceptance checks and decision

These checks apply only if the configuration-management blocker is resolved or the management requirement is explicitly changed. Before any cutover, test the actual compiled release and installed app versions:

- Default and every conditional domain reach the intended upstream; failures never leak to a public resolver.
- IPv4 and IPv6 PTR use ports 54 and 56 respectively, including NDP-assisted names.
- Public AAAA remains available outside the 14 selected suffixes; recursion ACL accepts intended clients.
- No DHCP or unintended encrypted-DNS listeners; web console works through Traefik with correct client IPs.
- Query history expires after one day independently of 90-day statistics; credentials and session behavior are acceptable.
- Record actual negative TTL, timeout, and cache-memory behavior rather than assuming similarly named settings are equivalent.

**Decision: do not use Technitium with this repository's current template-based configuration management.** It lacks a complete templateable server configuration, so this workflow cannot verify or correct configuration drift. Custom API reconciliation would be a different management model requiring an explicit change of requirements. Most DNS features being available does not outweigh this blocker; the rule/response parity gaps also remain. Reattach production YAML to check settings that may differ from the repository template. No commands or playbooks were run against production hosts; no deployment changes were made.
