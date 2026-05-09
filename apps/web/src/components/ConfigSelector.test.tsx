import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import ConfigSelector from "./ConfigSelector";

const configs = [
  {
    id: "default",
    label: "Default",
    path: "/tmp/demo/.cc-branch/config.yaml",
    state_path: "/tmp/demo/.cc-branch/state.yaml",
    exists: true,
    is_default: true,
    selected: true,
  },
  {
    id: "review",
    label: "review",
    path: "/tmp/demo/.cc-branch/configs/review.yaml",
    state_path: "/tmp/demo/.cc-branch/states/review.yaml",
    exists: true,
    is_default: false,
    selected: false,
  },
];

describe("ConfigSelector", () => {
  it("lets users switch the active workspace config", () => {
    const onSelect = vi.fn();

    render(
      <I18nProvider>
        <ConfigSelector configs={configs} selectedPath={configs[0].path} onSelect={onSelect} />
      </I18nProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Workspace config" }));
    fireEvent.click(screen.getByRole("option", { name: "review" }));

    expect(onSelect).toHaveBeenCalledWith(configs[1].path);
  });
});
