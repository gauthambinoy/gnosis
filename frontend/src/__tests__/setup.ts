import "@testing-library/jest-dom/vitest";

// Mock methods missing in jsdom
type ElementWithScroll = Element & { scrollIntoView?: () => void };
if (typeof Element !== "undefined" && !(Element.prototype as ElementWithScroll).scrollIntoView) {
  (Element.prototype as ElementWithScroll).scrollIntoView = function () {};
}
