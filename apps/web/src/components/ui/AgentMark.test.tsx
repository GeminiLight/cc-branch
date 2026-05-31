import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import AgentMark from "./AgentMark";
import copilotIconUrl from "../../assets/agent-icons/copilot.svg";
import opencodeIconUrl from "../../assets/agent-icons/opencode.png";

describe("AgentMark", () => {
  it("uses distinctive initials for custom agents", () => {
    render(<AgentMark agent="my-local-agent" />);

    expect(screen.getByLabelText("My-local-agent")).toHaveTextContent("ML");
  });

  it("recognizes GitHub Copilot CLI and OpenCode with logo assets", () => {
    const { container } = render(
      <div>
        <AgentMark agent="copilot" />
        <AgentMark agent="opencode" />
      </div>
    );

    expect(screen.getByLabelText("GitHub Copilot")).toBeInTheDocument();
    expect(screen.getByLabelText("OpenCode")).toBeInTheDocument();
    expect(opencodeIconUrl).toContain("opencode.png");
    expect(copilotIconUrl).toContain("image/svg+xml");
    const images = Array.from(container.querySelectorAll("img"));
    expect(images.map((image) => image.getAttribute("src"))).toEqual([
      copilotIconUrl,
      opencodeIconUrl,
    ]);
  });
});
