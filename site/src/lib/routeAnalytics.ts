import { track } from '@vercel/analytics';

/**
 * Records a hash-route view as a Vercel Analytics custom event so we can see
 * which pages and home-page sections visitors actually engage with.
 *
 * The site is hash-routed (#/demo, #features, ...), which Vercel's automatic
 * pageview tracking doesn't follow — hence explicit route_view events.
 * Fire-and-forget: analytics must never break the app.
 */
export function trackRouteView(rawHash: string): void {
  const hash = rawHash || '#/';
  const isPage = hash.startsWith('#/');
  // '#/demo' -> '/demo'; '#features' stays '#features' (home-page anchor)
  const route = (isPage ? hash.slice(1) : hash) || '/';
  try {
    track('route_view', {
      route: route.slice(0, 100),
      kind: isPage ? 'page' : 'anchor',
    });
  } catch {
    /* noop */
  }
}
