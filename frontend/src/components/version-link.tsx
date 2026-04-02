const version = process.env.NEXT_PUBLIC_APP_VERSION;
const RELEASE_URL = `https://github.com/LetAgentPay/letagentpay/releases/tag/v${version}`;

export function VersionLink({ className }: { className?: string }) {
  if (!version || version === "dev") {
    return <span className={className}>v{version ?? "dev"}</span>;
  }

  return (
    <a
      href={RELEASE_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={`hover:opacity-70 ${className ?? ""}`}
    >
      v{version}
    </a>
  );
}
