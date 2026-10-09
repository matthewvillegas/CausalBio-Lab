import "@testing-library/jest-dom/vitest";

import { vi } from "vitest";
// jsdom has no layout/scroll implementation; browser tests verify actual scrolling.
Element.prototype.scrollIntoView = vi.fn();
window.scrollTo = vi.fn();

// jsdom has no native modal behavior; production browser checks verify Tab and Escape.
HTMLDialogElement.prototype.showModal = function () {
  this.open = true;
};
HTMLDialogElement.prototype.close = function () {
  this.open = false;
};
