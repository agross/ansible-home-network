<?php
$CONFIG = array (
  # https://docs.nextcloud.com/server/latest/admin_manual/configuration_server/config_sample_php_parameters.html#apps-paths
  "apps_paths" => array (
    0 => array (
      "path"     => OC::$SERVERROOT."/apps",
      "url"      => "/apps",
      "writable" => false,
    ),
    1 => array (
      "path"     => OC::$SERVERROOT."/custom_apps",
      "url"      => "/custom_apps",
      "writable" => true,
    ),
  ),
);
