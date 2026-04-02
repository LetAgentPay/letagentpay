import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import DevelopersPage from "@/app/developers/page";

describe("DevelopersPage", () => {
  it("renders the page title", () => {
    render(<DevelopersPage />);
    expect(screen.getByText("Developer Documentation")).toBeInTheDocument();
  });

  it("renders quick start section", () => {
    render(<DevelopersPage />);
    expect(screen.getByText("Quick Start")).toBeInTheDocument();
  });

  it("renders integration tabs", () => {
    render(<DevelopersPage />);
    expect(screen.getByText("Python SDK")).toBeInTheDocument();
    expect(screen.getByText("MCP Server")).toBeInTheDocument();
    expect(screen.getByText("REST API")).toBeInTheDocument();
  });

  it("renders API reference table", () => {
    render(<DevelopersPage />);
    expect(screen.getByText("API Reference")).toBeInTheDocument();
    expect(screen.getByText("Create a purchase request")).toBeInTheDocument();
  });

  it("renders request lifecycle", () => {
    render(<DevelopersPage />);
    expect(screen.getByText("Request Lifecycle")).toBeInTheDocument();
  });

  it("renders llms.txt links", () => {
    render(<DevelopersPage />);
    expect(screen.getByText("/llms.txt")).toBeInTheDocument();
    expect(screen.getByText("/llms-full.txt")).toBeInTheDocument();
  });

  it("renders sign in link", () => {
    render(<DevelopersPage />);
    expect(screen.getByText("Sign In")).toBeInTheDocument();
  });
});
