# DNS Server

DNS lookups work like this:

1. The host runs AdGuard (DNS only) with host networking, listening on port
   53/udp.
1. If AdGuard decides the request should not be blocked, it is forwarded to
   dnsmasq.
1. dnsmasq also runs with host networking, listening on 53000/udp.
   dnsmasq also provides DHCPv4 and v6 capabilities to LAN hosts.
1. If dnsmasq cannot satisfy the request from DHCP information, it forwards to
   * ARWEN (Windows Server DC, if *.wghoch4.local was requested), or
   * dnscrypt-proxy otherwise.
1. dnscrypt-proxy is required because I want DNS traffic leaving my network to
   be encrypted and dnsmasq does not handle e.g. DNS over HTTPS (only plain
   UDP-based DNS).
1. dnscrypt-proxy listens on 127.0.0.1:53001 and picks a fast, public and
   encrypted DNS server to resolve the request.

Reverse (PTR) lookups are a bit of a special case because I want AdGuard to
resolve IPv6 addresses to hostnames for its UI. AdGuard does not support NDP,
and dnsmasq only knows about IPv6 from DHCPv6, but is unaware of link-local
addresses. For these cases, systemd-resolved is used which supports upstream DNS
servers as well as NDP. AdGuard uses systemd-resolved's stub resolver only for
PTR queries of IPv6 addresses and resolves PTR IPv4 addresses using dnsmasq.

The host listens on the following ports:

* AdGuard: 0.0.0.0:53 and :::53 (allowed by firewalld)
* dnsmasq: 0.0.0.0:53000 and :::53000 (not allowed by firewalld)
* dnscrypt-proxy: 127.0.0.1:53001
* systemd-resolved stub resolver: 127.0.0.1:53002
