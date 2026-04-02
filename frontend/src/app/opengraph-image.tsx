import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "LetAgentPay — Control how your AI agents spend money";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%)",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, sans-serif",
          color: "white",
          padding: "60px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "40px",
          }}
        >
          <div
            style={{
              width: "64px",
              height: "64px",
              borderRadius: "16px",
              background: "white",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "32px",
              color: "#0a0a0a",
              fontWeight: 700,
            }}
          >
            $
          </div>
          <span style={{ fontSize: "48px", fontWeight: 700 }}>LetAgentPay</span>
        </div>
        <div
          style={{
            fontSize: "36px",
            fontWeight: 600,
            textAlign: "center",
            lineHeight: 1.3,
            maxWidth: "800px",
          }}
        >
          Control how your AI agents spend money
        </div>
        <div
          style={{
            fontSize: "20px",
            color: "rgba(255,255,255,0.6)",
            marginTop: "24px",
            textAlign: "center",
          }}
        >
          Budgets · Policies · Real-time approvals
        </div>
      </div>
    ),
    { ...size },
  );
}
