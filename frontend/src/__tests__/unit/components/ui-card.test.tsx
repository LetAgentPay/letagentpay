import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardAction,
  CardContent,
  CardFooter,
} from "@/components/ui/card";

describe("Card components", () => {
  it("renders Card with children", () => {
    render(<Card data-testid="card">content</Card>);
    expect(screen.getByTestId("card")).toHaveTextContent("content");
  });

  it("Card accepts size prop", () => {
    render(<Card data-testid="card" size="sm">small</Card>);
    expect(screen.getByTestId("card")).toHaveAttribute("data-size", "sm");
  });

  it("renders CardDescription", () => {
    render(<CardDescription>desc text</CardDescription>);
    expect(screen.getByText("desc text")).toBeInTheDocument();
  });

  it("renders CardAction", () => {
    render(<CardAction data-testid="action">action</CardAction>);
    expect(screen.getByTestId("action")).toBeInTheDocument();
  });

  it("renders CardFooter", () => {
    render(<CardFooter data-testid="footer">footer</CardFooter>);
    expect(screen.getByTestId("footer")).toBeInTheDocument();
  });

  it("renders full card structure", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
          <CardDescription>Description</CardDescription>
          <CardAction>Action</CardAction>
        </CardHeader>
        <CardContent>Body</CardContent>
        <CardFooter>Footer</CardFooter>
      </Card>,
    );
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("Description")).toBeInTheDocument();
    expect(screen.getByText("Action")).toBeInTheDocument();
    expect(screen.getByText("Body")).toBeInTheDocument();
    expect(screen.getByText("Footer")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<CardFooter data-testid="f" className="custom-class">f</CardFooter>);
    expect(screen.getByTestId("f").className).toContain("custom-class");
  });
});
