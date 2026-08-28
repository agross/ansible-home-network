# Pi-hole: AdGuard replacement assessment

Recorded 2026-08-28 from the earlier dns-server role evaluation. This records the investigation and the operator's deployment decision, not a successful production deployment.

## Decision: reject for this DNS host

**Native Pi-hole installation has too many moving parts for this deployment. Docker is not permitted on the DNS host.** A Docker deployment is therefore not an acceptable alternative to maintaining the native installation.

The constraints were explicit: no Docker, no installer script, GitHub release downloads, and a custom systemd unit. Native installation is technically possible; the rejection is about its maintenance burden under these constraints, not a claim that Pi-hole requires Docker.

Feature support alone does not make Pi-hole a suitable replacement here. Do not proceed with either the installer-free native approach or a Docker workaround unless the operator explicitly changes this decision.

## Earlier feature findings

| Requirement | Finding |
| --- | --- |
| AAAA-only blocking for selected domains | Query-type-specific regex rules with `querytype=AAAA;reply=nodata` can suppress AAAA while leaving A queries outside that rule. |
| Existing upstream routing | Local upstream and conditional forwarding can preserve the dnsmasq/dnscrypt-proxy chain and separate reverse-DNS routing. |
| Blocklist subscriptions | Supported through gravity/adlists. Subscription URLs and enabled state can be represented; this did not establish identical interpretation of every AdGuard filter rule. |
| No Pi-hole DHCP | DHCP can remain disabled. Existing independent dnsmasq DHCP was not being replaced. |

These were configuration/source-level findings, not a complete live parity test. [Regex extensions](https://docs.pi-hole.net/regex/pi-hole/), [FTL configuration](https://docs.pi-hole.net/ftldns/configfile/), [gravity/domain database](https://docs.pi-hole.net/database/domain-database/).

## Why the installer-free native approach was rejected

The earlier implementation exploration required managing:

- Three separately versioned components: FTL, Core scripts/CLI, and the web interface, including release downloads and upgrade compatibility.
- Installation layout, runtime-script links, a service account, directory ownership, and permissions.
- Host package dependencies and upstream pre-start/post-stop lifecycle scripts.
- A custom systemd unit, credentials, restart integration, and hardening adapted from [Pi-hole PR 6518](https://github.com/pi-hole/pi-hole/pull/6518).
- Gravity database initialization, subscription and domain-rule reconciliation, and blocklist refresh scheduling.
- Coordination between environment/configuration files, conditional-forwarding configuration, and database-backed policy.

This is more than downloading one executable and rendering its configuration. Without the installer, this role would own the installation and upgrade logic as well as service configuration. The operator considers that complexity unacceptable on a DNS host.

The earlier exploration used Pi-hole v6's FTL, Core, and Web components; this assessment does not assume a separate legacy PHP/lighttpd stack. A complete template-only policy/drift workflow was not demonstrated: the explored rules and subscriptions also required database reconciliation.

## Verification boundary

Earlier role lint, site playbook syntax checks, and diff checks passed for the implementation draft. Those checks did not establish startup, upgrades, DNS behavior, or operational suitability on a real host. No production playbook execution or successful cutover was established.

This note makes no infrastructure changes and does not authorize installing Docker or running the installer.

## Related alternative

[Technitium assessment](technitium-adguard-parity.md): rejected for a different reason—no complete templateable server configuration, preventing drift verification through this repository's existing template workflow.
