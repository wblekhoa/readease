export const repository = 'https://github.com/wblekhoa/readease';
// Where a visitor lands when nothing better is known: the repository's
// front page, whose README opens on a big download link (owner, 10/10:
// "rơi về trang repo chính có nút download ở đó vẫn sẽ tiện hơn") - not the
// Releases list, where the file is one asset among six.
export const fallback = repository;
// The newest build's file itself, with no API call to fail: GitHub sends
// /releases/latest/download/<name> to the asset of that name in the latest
// release, and scripts/release.sh uploads every build under these plain
// names too. Used when the API (60 calls an hour per address, 403 after)
// does not answer; when it does, its own link to the build is exact.
export const directDmg = `${repository}/releases/latest/download/ReadEase-arm64.dmg`;
export const directZip = `${repository}/releases/latest/download/ReadEase-arm64.zip`;
export function resolveRelease(release) {
  if (!release || release.draft || release.prerelease || typeof release.tag_name !== 'string') return null;
  const version = release.tag_name.replace(/^v/, '').trim();
  if (!version) return null;
  const assets = Array.isArray(release.assets) ? release.assets : [];
  const trusted = (asset, extension) => {
    if (typeof asset?.name !== 'string' || !asset.name.endsWith(`-arm64.${extension}`)) return false;
    try {
      const url = new URL(asset.browser_download_url);
      return url.protocol === 'https:' && url.hostname === 'github.com' && !url.port &&
        url.pathname.startsWith('/wblekhoa/readease/releases/download/') &&
        !url.username && !url.password && Number.isFinite(asset.size) && asset.size > 0;
    } catch { return false; }
  };
  const dmg = assets.find(a => trusted(a, 'dmg'));
  if (!dmg) return null;
  return { version, dmg, zip: assets.find(a => trusted(a, 'zip')) };
}
export async function fetchRelease(signal, request = fetch) {
  try {
    const response = await request('https://api.github.com/repos/wblekhoa/readease/releases/latest', {
      signal, headers: { Accept: 'application/vnd.github+json' },
    });
    return response.ok ? resolveRelease(await response.json()) : null;
  } catch { return null; }
}
export const mb = bytes => Math.round(bytes / 1e6);
