<?php
$CONFIG = array (
  # https://docs.nextcloud.com/server/latest/admin_manual/configuration_server/config_sample_php_parameters.html#preview-max-x
  'preview_max_x' => 2048,
  'preview_max_y' => 2048,
  'preview_max_scale_factor' => 4,
  'preview_imaginary_url' => 'http://imaginary:9000',
  'enabledPreviewProviders' => array (
    'OC\Preview\Imaginary',
    // Defaults preview providers.
    'OC\Preview\PNG',
    'OC\Preview\JPEG',
    'OC\Preview\GIF',
    'OC\Preview\HEIC',
    'OC\Preview\BMP',
    'OC\Preview\XBitmap',
    'OC\Preview\MP3',
    'OC\Preview\TXT',
    'OC\Preview\MarkDown',
    // Extra preview providers.
    'OC\Preview\MSOffice2003',
    'OC\Preview\MSOffice2007',
    'OC\Preview\MSOfficeDoc',
    'OC\Preview\OpenDocument',
    'OC\Preview\PDF',
    'OC\Preview\SVG',
  )
);
