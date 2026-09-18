import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SmokeBadge } from "../SmokeBadge";

describe("SmokeBadge", () => {
  it("renders the label", () => {
    render(<SmokeBadge label="ReunionAI" />);
    expect(screen.getByTestId("smoke-badge").textContent).toBe("ReunionAI");
  });
});
