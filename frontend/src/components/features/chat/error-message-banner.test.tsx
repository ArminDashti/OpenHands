import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { ErrorMessageBanner } from "./error-message-banner";

vi.mock("react-router", () => ({
  Link: ({ children }: { children?: React.ReactNode }) => (
    <a href="https://example.com">{children}</a>
  ),
}));

const removeErrorMessageMock = vi.fn();

vi.mock("#/stores/error-message-store", () => ({
  useErrorMessageStore: () => ({ removeErrorMessage: removeErrorMessageMock }),
}));

describe("ErrorMessageBanner", () => {
  it("calls removeErrorMessage when dismiss is clicked", () => {
    render(<ErrorMessageBanner message="boom" />);

    fireEvent.click(screen.getByLabelText("Dismiss error"));
    expect(removeErrorMessageMock).toHaveBeenCalledTimes(1);
  });

  it("truncates long messages and toggles show more/less", () => {
    const msg = "a".repeat(30);

    render(<ErrorMessageBanner message={msg} truncateAt={10} />);

    expect(screen.getByText(`${"a".repeat(10)}…`)).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Show more/i));
    expect(screen.getByText(msg)).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Show less/i));
    expect(screen.getByText(`${"a".repeat(10)}…`)).toBeInTheDocument();
  });
});
