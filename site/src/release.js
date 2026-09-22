export const repository = 'https://github.com/wblekhoa/readease';
export const fallback = `${repository}/releases/latest`;
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
