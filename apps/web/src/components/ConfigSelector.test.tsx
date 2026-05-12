import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import ConfigSelector, { ConfigContextNotice } from "./ConfigSelector";

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

    fireEvent.click(screen.getByRole("button", { name: "Workspace profile" }));
    fireEvent.click(screen.getByRole("option", { name: /review/ }));

    expect(onSelect).toHaveBeenCalledWith(configs[1].path);
  });

  it("shows the selected config and available config count before users open the menu", () => {
    render(
      <I18nProvider>
        <ConfigSelector configs={configs} selectedPath={configs[1].path} onSelect={vi.fn()} />
      </I18nProvider>
    );

    expect(screen.getByText("Workspace")).toBeInTheDocument();
    expect(screen.getByText("review")).toBeInTheDocument();
    expect(screen.getByText("2 configs")).toBeInTheDocument();
  });

  it("exposes workspace management actions from the selector", () => {
    const onCreate = vi.fn();
    const onRename = vi.fn();
    const onDelete = vi.fn();

    render(
      <I18nProvider>
        <ConfigSelector
          projectPath="/tmp/demo"
          configs={configs}
          selectedPath={configs[1].path}
          onSelect={vi.fn()}
          onCreate={onCreate}
          onRename={onRename}
          onDelete={onDelete}
        />
      </I18nProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Workspace profile" }));

    expect(screen.getByRole("dialog", { name: "Workspace profiles" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New workspace" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Rename workspace" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Delete workspace" })).toBeEnabled();
  });

  it("creates a workspace profile inline instead of opening a blocking modal", () => {
    const onCreate = vi.fn();

    render(
      <I18nProvider>
        <ConfigSelector
          projectPath="/tmp/demo"
          configs={configs}
          selectedPath={configs[1].path}
          onSelect={vi.fn()}
          onCreate={onCreate}
        />
      </I18nProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Workspace profile" }));
    fireEvent.click(screen.getByRole("button", { name: "New workspace" }));

    expect(screen.getByText("Create a named profile from the default workspace.")).toBeInTheDocument();
    expect(screen.queryByText("Use a short name like review, ui-polish, or release-check.")).not.toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox", { name: "Workspace profile name" }), {
      target: { value: "qa-check" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    expect(onCreate).toHaveBeenCalledWith("qa-check", undefined);
  });

  it("summarizes the active config path and isolated state path in page context", () => {
    render(
      <I18nProvider>
        <ConfigContextNotice configs={configs} selectedPath={configs[1].path} />
      </I18nProvider>
    );

    expect(screen.getByText("Active workspace")).toBeInTheDocument();
    expect(screen.getByText("review")).toBeInTheDocument();
    expect(screen.getByText("/tmp/demo/.cc-branch/configs/review.yaml")).toBeInTheDocument();
    expect(screen.getByText("/tmp/demo/.cc-branch/states/review.yaml")).toBeInTheDocument();
  });
});
