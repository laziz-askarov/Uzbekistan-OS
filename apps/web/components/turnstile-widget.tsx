"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";

type TurnstileApi = {
  remove: (widgetId: string) => void;
  render: (
    container: HTMLElement,
    options: {
      action: string;
      appearance: "always";
      callback: (token: string) => void;
      "error-callback": () => void;
      "expired-callback": () => void;
      language: "auto";
      sitekey: string;
      size: "flexible";
      theme: "light";
    },
  ) => string;
};

declare global {
  interface Window {
    turnstile?: TurnstileApi;
  }
}

type TurnstileWidgetProps = {
  onError: () => void;
  onToken: (token: string | null) => void;
  resetSignal: number;
  siteKey: string;
};

export function TurnstileWidget({
  onError,
  onToken,
  resetSignal,
  siteKey,
}: TurnstileWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scriptReady, setScriptReady] = useState(false);

  useEffect(() => {
    const container = containerRef.current;
    const turnstile = window.turnstile;
    if (!container || !scriptReady || !turnstile) return;

    onToken(null);
    const widgetId = turnstile.render(container, {
      action: "account_auth",
      appearance: "always",
      callback: (token) => onToken(token),
      "error-callback": () => {
        onToken(null);
        onError();
      },
      "expired-callback": () => onToken(null),
      language: "auto",
      sitekey: siteKey,
      size: "flexible",
      theme: "light",
    });

    return () => turnstile.remove(widgetId);
  }, [onError, onToken, resetSignal, scriptReady, siteKey]);

  return (
    <div className="auth-captcha">
      <p className="auth-captcha-label">Security check</p>
      <Script
        id="cloudflare-turnstile"
        onError={onError}
        onReady={() => setScriptReady(true)}
        src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"
        strategy="afterInteractive"
      />
      <div ref={containerRef} />
    </div>
  );
}
