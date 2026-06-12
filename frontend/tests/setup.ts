// Vitest setup: jest-dom matchers + automatic cleanup between tests.
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// jsdom does not implement scrollIntoView; the chat view calls it after each
// message. Stub it so the component code runs unchanged under test.
window.HTMLElement.prototype.scrollIntoView = () => {};

afterEach(() => cleanup());
