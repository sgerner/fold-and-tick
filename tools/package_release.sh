#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${FOLD_TICK_KEYSTORE_PATH:?Set the release keystore path}"
: "${FOLD_TICK_STORE_PASSWORD:?Set the keystore password}"
: "${FOLD_TICK_KEY_ALIAS:?Set the key alias}"
: "${FOLD_TICK_KEY_PASSWORD:?Set the key password}"
[[ -f tools/vendor/memory-footprint.jar ]] || { echo 'Run tools/validate.sh first.' >&2; exit 1; }
# Signing passwords must not be serialized into Gradle's configuration cache.
./gradlew :watchface:assembleRelease --no-configuration-cache
mkdir -p dist
cp watchface/build/outputs/apk/release/watchface-release.apk dist/Fold-and-Tick.apk
python3 tools/check_apk.py dist/Fold-and-Tick.apk
java -jar tools/vendor/memory-footprint.jar --watch-face dist/Fold-and-Tick.apk --schema-version 2 --ambient-limit-mb 10 --active-limit-mb 100
sdk_dir="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [[ -z "$sdk_dir" && -f local.properties ]]; then
  sdk_dir=$(sed -n 's/^sdk.dir=//p' local.properties)
fi
"$sdk_dir/build-tools/36.0.0/apksigner" verify --verbose --print-certs dist/Fold-and-Tick.apk > dist/SIGNING-CERTIFICATE.txt
(cd dist && sha256sum Fold-and-Tick.apk > SHA256SUMS)
echo 'Signed release ready: dist/Fold-and-Tick.apk'
