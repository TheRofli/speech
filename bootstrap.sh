#!/usr/bin/env bash
set -euo pipefail

repository="${SPEECH_REPOSITORY:-TheRofli/speech}"
branch="${SPEECH_BRANCH:-main}"
install_dir="${SPEECH_INSTALL_DIR:-$HOME/.speech}"
download_parakeet="false"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --download-parakeet)
      download_parakeet="true"
      ;;
    --install-dir)
      shift
      install_dir="${1:?Missing value for --install-dir}"
      ;;
    --branch)
      shift
      branch="${1:?Missing value for --branch}"
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
  shift
done

zip_url="https://github.com/$repository/archive/refs/heads/$branch.zip"
temp_root="$(mktemp -d "${TMPDIR:-/tmp}/speech-install.XXXXXX")"
zip_path="$temp_root/speech.zip"

cleanup() {
  case "$temp_root" in
    "${TMPDIR:-/tmp}"/speech-install.*|/tmp/speech-install.*)
      rm -rf "$temp_root"
      ;;
  esac
}
trap cleanup EXIT

echo "Downloading Speech from $zip_url"
curl -fL "$zip_url" -o "$zip_path"

echo "Extracting..."
unzip -q "$zip_path" -d "$temp_root"
source_dir="$(find "$temp_root" -maxdepth 1 -type d \( -name 'speech-*' -o -name 'Speech-*' \) | head -n 1)"
if [ -z "$source_dir" ]; then
  echo "Could not find extracted Speech source folder." >&2
  exit 1
fi

echo "Installing to $install_dir"
mkdir -p "$install_dir"
cp -R "$source_dir"/. "$install_dir"/
chmod +x "$install_dir/install.sh" "$install_dir/speech.sh" "$install_dir/bin/speech" 2>/dev/null || true

"$install_dir/install.sh"

if [ "$download_parakeet" = "true" ]; then
  "$install_dir/bin/speech" parakeet install
fi

echo
echo "Speech is installed at $install_dir."
echo "Start it with: speech"
echo "Download Parakeet later with: speech parakeet install"
