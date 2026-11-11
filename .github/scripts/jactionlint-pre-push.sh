#!/usr/bin/env bash
# Copyright 2026 Agentic Data Intelligence SA
# SPDX-License-Identifier: Apache-2.0
#
# jactionlint before a push (the Trunk action jactionlint-pre-push), as CI's jactionlint job runs it: the pinned
# release, this repository's .github/jactionlint.yaml, offline, and --baseline-check while there is a baseline.
#
# The release is downloaded once, checked against its sha256 before anything is unpacked, and kept in
# ${XDG_CACHE_HOME:-~/.cache}/jactionlint/<version>-<asset>/. Findings (1) and config errors (2, 3) block the push.
# When the check can't run (no pinned build for this platform, the download or the sha256 check fails), it says so
# and lets the push through: the CI job still checks.
set -uo pipefail

version=2.5.0
skip() {
	echo "jactionlint: skipped, $1 (CI still checks)" >&2
	exit 0
}

# The release's checksums file, matching GitHub's own digest of each asset.
case "$(uname -s)-$(uname -m)" in
Linux-x86_64) asset=linux_amd64 sha256=5ac307b0499bb0eab45ae99c23e8e0790874fbc667c75224410954e0e3c6e0f5 ;;
Linux-aarch64 | Linux-arm64) asset=linux_arm64 sha256=ad7e33b6264cea16b7e83ad2bb004824d5b1c15aedb35ba0dc84917f791c5525 ;;
Darwin-x86_64) asset=darwin_amd64 sha256=f8f10def21260aa9515974f0aa145f5a6741efd60efe1f880c8c6f53a4ba676c ;;
Darwin-arm64) asset=darwin_arm64 sha256=15b47d53e3b1aafbd674cca0e8fff0d5952f3cf2a7d7501a8f67576ef76397b4 ;;
*) skip "no jactionlint $version build is pinned for $(uname -s)-$(uname -m)" ;;
esac

bin_dir="${XDG_CACHE_HOME:-$HOME/.cache}/jactionlint/$version-$asset"
if ! [ -x "$bin_dir/jactionlint" ] || [ "$(cat "$bin_dir/.sha256" 2>/dev/null)" != "$sha256" ]; then
	tmp="$(mktemp -d)" || skip "no temporary directory"
	trap 'rm -rf "$tmp"' EXIT
	url="https://github.com/jdx/jactionlint/releases/download/v$version/jactionlint_${version}_$asset.tar.gz"
	echo "jactionlint: downloading jactionlint $version ($asset)" >&2
	curl -fsSL --retry 2 --proto '=https' -o "$tmp/release.tar.gz" "$url" || skip "couldn't download $url"
	if command -v sha256sum >/dev/null; then
		got="$(sha256sum "$tmp/release.tar.gz" | cut -d ' ' -f 1)"
	else
		got="$(shasum -a 256 "$tmp/release.tar.gz" | cut -d ' ' -f 1)"
	fi
	[ "$got" = "$sha256" ] || skip "the download has sha256 $got, not the pinned $sha256"
	if ! {
		mkdir -p "$tmp/unpacked" "$bin_dir" &&
			tar -xzf "$tmp/release.tar.gz" -C "$tmp/unpacked" jactionlint &&
			mv -f "$tmp/unpacked/jactionlint" "$bin_dir/jactionlint" &&
			chmod 755 "$bin_dir/jactionlint" &&
			echo "$sha256" >"$bin_dir/.sha256"
	}; then
		skip "couldn't unpack the release into $bin_dir"
	fi
fi

cd "$(git rev-parse --show-toplevel)" || skip "not in a git repository"
args=(--no-online)
if [ -f .github/jactionlint-baseline.json ]; then args+=(--baseline-check); fi
"$bin_dir/jactionlint" "${args[@]}"
