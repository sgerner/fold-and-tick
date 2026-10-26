#!/usr/bin/env bash
# Official Google WFF syntax/resource/memory checks; downloads are cached locally.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p tools/vendor
fetch() {
  local name="$1" expected="$2"
  if [[ ! -f "tools/vendor/$name.jar" ]]; then
    curl --fail --location --silent --show-error \
      "https://github.com/google/watchface/releases/download/release/$name.jar" \
      --output "tools/vendor/$name.jar"
  fi
  echo "$expected  tools/vendor/$name.jar" | sha256sum --check --status || {
    echo "Validator checksum differs. Review Google's release before updating the pinned checksum." >&2
    exit 1
  }
}
fetch wff-validator fb3262aa146de24c169a1d451901b4df2bfedca28a27c3c168a487e02d393771
fetch memory-footprint 98892722dcb0cf3c872776fa5ec1ba5aea1289621f04d15324e854b1cdaa3460
# This validator can return status 0 even on invalid XML: also inspect its report.
syntax_report=$(java -jar tools/vendor/wff-validator.jar 2 watchface/src/main/res/raw/watchface.xml 2>&1)
echo "$syntax_report"
if [[ "$syntax_report" == *"FAILED"* || "$syntax_report" == *"SEVERE"* ]]; then
  exit 1
fi
python3 -m unittest discover -s tools -p 'test_*.py'
./gradlew :watchface:assembleDebug :watchface:lintDebug
python3 tools/check_apk.py watchface/build/outputs/apk/debug/watchface-debug.apk
python3 tools/build_preview.py --output site
java -jar tools/vendor/memory-footprint.jar \
  --watch-face watchface/build/outputs/apk/debug/watchface-debug.apk \
  --schema-version 2 --ambient-limit-mb 10 --active-limit-mb 100
