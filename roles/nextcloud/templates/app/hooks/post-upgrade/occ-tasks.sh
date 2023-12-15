#!/usr/bin/env sh

set -e

# My collection of CLIs that might need execution after an upgrade.
# Some of these are considered expensive and thus are not run automatically.

php occ maintenance:repair --include-expensive
php occ db:add-missing-columns
php occ db:add-missing-primary-keys
php occ db:add-missing-indices
php occ db:convert-filecache-bigint --no-interaction
