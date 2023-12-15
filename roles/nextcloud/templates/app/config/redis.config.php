<?php
$CONFIG = array (
  # https://docs.nextcloud.com/server/latest/admin_manual/configuration_server/config_sample_php_parameters.html#memcache-locking
  'memcache.locking' => '\OC\Memcache\Redis',
  'redis' => array (
    'host' => 'redis',
    'port' => 6379,
    'password' => '',
  ),
);
