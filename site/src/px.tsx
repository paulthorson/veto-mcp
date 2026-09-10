/* Shared pixel-brand primitives for all site pages. */

export const GITHUB_URL = 'https://github.com/paulthorson/job-apply-mcp';
export const SITE_URL = 'https://job-apply-mcp.vercel.app';

export function PixelX({ size = 30 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      shapeRendering="crispEdges"
      className="brand-mark"
      aria-hidden="true"
    >
      <rect width="16" height="16" fill="#0d0d12" />
      <g fill="#ff4d5e">
        <rect x="3" y="3" width="2" height="2" />
        <rect x="11" y="3" width="2" height="2" />
        <rect x="5" y="5" width="2" height="2" />
        <rect x="9" y="5" width="2" height="2" />
        <rect x="7" y="7" width="2" height="2" />
        <rect x="5" y="9" width="2" height="2" />
        <rect x="9" y="9" width="2" height="2" />
        <rect x="3" y="11" width="2" height="2" />
        <rect x="11" y="11" width="2" height="2" />
      </g>
    </svg>
  );
}

export function PxBtn({
  variant = 'primary',
  href,
  children,
  label,
  target,
}: {
  variant?: 'primary' | 'secondary' | 'ghost';
  href: string;
  children: React.ReactNode;
  label: string;
  target?: string;
}) {
  return (
    <a
      className={`px-btn ${variant}`}
      href={href}
      aria-label={label}
      target={target}
      rel={target === '_blank' ? 'noreferrer' : undefined}
    >
      {children}
    </a>
  );
}

export function PxTag({
  variant = '',
  children,
}: {
  variant?: '' | 'red' | 'amber';
  children: React.ReactNode;
}) {
  return <span className={`px-tag ${variant}`}>{children}</span>;
}
