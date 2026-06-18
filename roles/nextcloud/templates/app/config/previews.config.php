<?php
$CONFIG = array (
  # https://docs.nextcloud.com/server/latest/admin_manual/configuration_server/config_sample_php_parameters.html#preview-max-x
  'preview_max_x' => 512,
  'preview_max_y' => 512,
  'preview_max_scale_factor' => 4,
  'preview_imaginary_url' => 'http://imaginary:9000',
  'preview_format' => 'webp',
  'enabledPreviewProviders' => array (
    'OC\Preview\Imaginary',
    'OC\Preview\ImaginaryPDF',
    // Default preview providers.
    'OC\Preview\PNG',
    'OC\Preview\JPEG',
    'OC\Preview\GIF',
    'OC\Preview\BMP',
    'OC\Preview\XBitmap',
    'OC\Preview\Krita',
    'OC\Preview\WebP',
    'OC\Preview\MarkDown',
    'OC\Preview\TXT',
    'OC\Preview\OpenDocument',
    // Extra preview providers.
    'OC\Preview\MSOffice2003',
    'OC\Preview\MSOffice2007',
    'OC\Preview\MSOfficeDoc',
    'OC\Preview\OpenDocument',
    'OC\Preview\PDF',
    'OC\Preview\SVG',
    'OC\Preview\HEIC',
    'OC\Preview\MP3',
  )
);
