<?php
$CONFIG = array (
  # Keep trash and files for a maximum of 30 days if free space permits,
  # otherwise delete earlier.
  # https://docs.nextcloud.com/server/latest/admin_manual/configuration_server/config_sample_php_parameters.html#trashbin-retention-obligation
  'trashbin_retention_obligation' => 'auto, 30',
  # https://docs.nextcloud.com/server/latest/admin_manual/configuration_server/config_sample_php_parameters.html#versions-retention-obligation
  'versions_retention_obligation' => 'auto, 30',
);
