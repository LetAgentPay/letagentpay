"use client";

import { useCallback } from "react";

const _p = ["support", "letagentpay", "com"];

export function openSupportEmail() {
  window.location.href = `mailto:${_p[0]}@${_p[1]}.${_p[2]}`;
}

interface SupportLinkProps {
  className?: string;
  children?: React.ReactNode;
}

export function SupportLink({ className, children }: SupportLinkProps) {
  const handleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    openSupportEmail();
  }, []);

  return (
    <button type="button" onClick={handleClick} className={className}>
      {children ?? "Support"}
    </button>
  );
}