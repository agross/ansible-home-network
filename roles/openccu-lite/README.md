# OpenCCU Lite

1. Define the VM in `host_vars/ccu/proxmox.yml` using the standard `proxmox`
   mapping. Set `proxmox.scsi.scsi0.import: true` alongside its `storage` and
   `size`. The Proxmox role leaves that disk slot empty.
2. Run the site playbook with `--tags vm` to create the VM and configure its
   hardware. Then run it with `--limit ccu --tags openccu-lite`. The role
   delegates to `proxmox.host`. If `scsi0` is empty, it verifies and extracts
   the OVA, attaches the appliance disk, and sets the boot order. The VM must be
   stopped for the import.
3. Start the VM when ready and configure its API credentials. Later runs of
   the same role detect the attached disk and check the running firmware
   through the appliance API. The default HTTPS origin uses the inventory
   hostname and site domain. Override `openccu_lite_api_url` if needed, and
   supply `openccu_lite_api_token` from Vault. The token needs `system:read` and
   `power`. The controller must trust the appliance certificate.

Renovate tracks `openccu_lite_release`. It selects the OVA for the initial
import and the requested firmware version for later API updates. The role reuses
an already staged copy of the requested firmware and verifies the running
version after installation.
