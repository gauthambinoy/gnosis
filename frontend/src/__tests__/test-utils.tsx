import { vi } from "vitest";
import React from "react";

export const mockRouterPush = vi.fn();
export const mockRouterReplace = vi.fn();
export const mockRouterBack = vi.fn();

export const nextNavigationMock = {
  useRouter: () => ({
    push: mockRouterPush,
    replace: mockRouterReplace,
    back: mockRouterBack,
    prefetch: vi.fn(),
    refresh: vi.fn(),
    forward: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
};

export function resetRouterMocks() {
  mockRouterPush.mockReset();
  mockRouterReplace.mockReset();
  mockRouterBack.mockReset();
}

/** Minimal MockWebSocket. Exposes static `instances` for inspection. */
export class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static OPEN = 1;
  static CLOSED = 3;
  url: string;
  readyState = 1;
  onopen: ((e?: unknown) => void) | null = null;
  onclose: ((e?: unknown) => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: ((e?: unknown) => void) | null = null;
  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = 3;
    this.onclose?.();
  });
  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    queueMicrotask(() => this.onopen?.());
  }
  emit(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

export function installMockWebSocket() {
  MockWebSocket.instances = [];
  // @ts-expect-error override global
  globalThis.WebSocket = MockWebSocket;
}

export function MinimalProviders({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
