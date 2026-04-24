import "@testing-library/jest-dom/vitest";

// Mock methods missing in jsdom
if (typeof Element !== "undefined" && !(Element.prototype as any).scrollIntoView) {
  (Element.prototype as any).scrollIntoView = function () {};
}
