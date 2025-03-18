#!/usr/bin/bash

set -euo pipefail

vmid="$1"
phase="$2"

interface=eth0
uid=agross
group=ansible

exec=(pct exec "$vmid" --)

wait-online() {
  printf 'Waiting for %s go online...' "$interface"

  until "${exec[@]}" networkctl status \
                                "$interface" \
                                --json=short \
                                --lines=0 2>/dev/null |
        grep --quiet '"OperationalState":"routable"'; do
    printf .
    sleep 1
  done

  printf 'done!\n'
}

install-sshd-and-ansible-deps() {
  "${exec[@]}" dnf install --assumeyes openssh-server python3-libdnf5 python3-rpm
  "${exec[@]}" systemctl enable --now sshd
}

create-extra-user() {
  password="$("${exec[@]}" getent shadow root)"
  password="${password#*:}"
  password="${password%%:*}"

  "${exec[@]}" groupadd "$group" || true
  "${exec[@]}" sh -c "echo '%$group ALL = (ALL) NOPASSWD: ALL' > '/etc/sudoers.d/$group'"
  "${exec[@]}" chmod 440 "/etc/sudoers.d/$group"

  if ! "${exec[@]}" useradd --create-home \
                            --user-group \
                            --groups "wheel,$group" \
                            --password "$password" \
                            "$uid"; then
    exit 0
  fi

  "${exec[@]}" mkdir --parents -- "/home/$uid/.ssh"
  "${exec[@]}" chmod 700 -- "/home/$uid/.ssh"
  "${exec[@]}" cp --verbose --no-clobber -- /root/.ssh/authorized_keys "/home/$uid/.ssh"
  "${exec[@]}" chown -R "$uid:$uid" -- "/home/$uid/.ssh"
}

case "$phase" in
  post-start)
    wait-online
    install-sshd-and-ansible-deps
    create-extra-user
    ;;
esac
