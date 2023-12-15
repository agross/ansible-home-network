<?php
$CONFIG = array (
  # Networks used by docker.
  # https://docs.nextcloud.com/server/latest/admin_manual/configuration_server/config_sample_php_parameters.html#trusted-proxies
  'trusted_proxies' => ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'],
  # Always use https to generate URLs.
  # https://docs.nextcloud.com/server/latest/admin_manual/configuration_server/config_sample_php_parameters.html#overwriteprotocol
  'overwriteprotocol' => 'https',
);
