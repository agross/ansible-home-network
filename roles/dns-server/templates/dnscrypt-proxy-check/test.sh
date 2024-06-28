#!/usr/bin/env bash

set -euo pipefail

declare -a server_names untested_servers successful_servers failed_servers
declare default_config
declare port=5353
declare -a dig=(dig @127.0.0.1 -p "$port")

names-of-public-resolvers()
{
  local tmp
  tmp="$(mktemp)"

  curl --fail \
       --output "$tmp" \
       https://raw.githubusercontent.com/DNSCrypt/dnscrypt-resolvers/master/v3/public-resolvers.md

  grep -F '##' -- "$tmp" | cut -d ' ' -f 2 | sort -u

  rm -- "$tmp"
}

download-default-dnscrypt-proxy-config()
{
  local tmp
  tmp="$(mktemp)"

  curl --fail \
       --output "$tmp" \
       https://raw.githubusercontent.com/DNSCrypt/dnscrypt-proxy/master/dnscrypt-proxy/example-dnscrypt-proxy.toml

  printf '%s' "$tmp"
}

start-dnscrypt-proxy-for-server()
{
  local default="${1?-Need default config file}"
  local server_name="${2?-Need server name to use}"

  local config
  config="$(mktemp)"

  sed -e "s/^listen_addresses.*/listen_addresses = ['[::]:$port']/" \
      -e "s/^# server_names.*/server_names = ['$server_name']/" \
      -e "s/^cache_min_ttl.*/cache_min_ttl = 0/" \
      -e "s/^ipv6_servers.*/ipv6_servers = true/" \
      "$default" > "$config"

  pgrep dnscrypt-proxy >/dev/null && killall -q -TERM dnscrypt-proxy
  (dnscrypt-proxy -config "$config"  &) >/dev/null 2>&1

  # Wait until we get a response or time out.
  local attempt=0
  while ((attempt++ < 3)); do
    if host -W 1 -t A -p "$port" example.com 127.0.0.1 >/dev/null; then
      return
    fi

    printf '.'
    sleep 1
  done

  return 1
}

# shellcheck disable=SC2317
test-known-ipv4() {
  local output
  output="$("${dig[@]}" +short A one.one.one.one)"

  printf '%s' "$output"

  [[ "$output" == *1.1.1.1* ]]
}

# shellcheck disable=SC2317
test-known-ipv6() {
  local output
  output="$("${dig[@]}" +short AAAA one.one.one.one)"

  printf '%s' "$output"

  [[ "$output" == *2606:4700:4700::1111* ]]
}

# shellcheck disable=SC2317
test-github-ipv4-only() {
  local output
  output="$("${dig[@]}" +short AAAA github.com)"

  printf '%s' "$output"

  [[ "$output" != *64:ff* ]]
}

# shellcheck disable=SC2317
test-small-ttl-unchanged() {
  local output
  output="$("${dig[@]}" +noall +answer +ttlid A home.therightstuff.de)"

  printf '%s' "$output"

  [[ "$output" =~ [[:blank:]]([[:digit:]]*)[[:blank:]]IN[[:blank:]]A[[:blank:]] ]] &&
  (( BASH_REMATCH[1] <= 60 ))
}

mapfile -t server_names < <(names-of-public-resolvers)
default_config="$(download-default-dnscrypt-proxy-config)"

for (( i=0; i < "${#server_names[@]}"; i++ )); do
  server_name="${server_names[$i]}"
  printf '(%b%s/%s%b) Testing %b%s%b' \
         '\e[1;33m' \
         "$i" \
         "${#server_names[@]}" \
         '\e[0m' \
         '\e[1;34m' \
         "$server_name" \
         '\e[0m'

  if ! start-dnscrypt-proxy-for-server "$default_config" "$server_name"; then
    untested_servers+=("$server_name")

    printf ' Failed to start a working dnscrypt-proxy server, %s is probably unreachable\n' \
           "$server_name"
    continue
  fi

  for test in known-ipv4 \
              known-ipv6 \
              github-ipv4-only \
              small-ttl-unchanged; do
    printf '\n%s ' "$test"

    if output="$(test-$test)"; then
      printf '%bOK%b ' '\e[1;32m' '\e[0m'
    else
      printf '%bfailed%b(%s)\n' '\e[1;31m' '\e[0m' "$output"

      failed_servers+=("$server_name: $test")
      continue 2
    fi
  done

  successful_servers+=("$server_name")

  printf '\n'
done

printf '\n%bServers that passed all tests:%b\n' '\e[1;32m' '\e[0m'
for server_name in "${successful_servers[@]}"; do
  printf '%s\n' "$server_name"
done

printf '\n%bUntested servers:%b\n' '\e[1;33m' '\e[0m'
for server_name in "${untested_servers[@]}"; do
  printf '%s\n' "$server_name"
done

printf '\n%bServers with failed tests:%b\n' '\e[1;31m' '\e[0m'
for server_name in "${failed_servers[@]}"; do
  printf '%s\n' "$server_name"
done
