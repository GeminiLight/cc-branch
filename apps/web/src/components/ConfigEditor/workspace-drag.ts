import { useRef, useState, type DragEvent } from "react";
import type { SlotConfig } from "./types";
import { canDragPane, normalizedLayout } from "./workspace-model";
import { paneCount } from "./workspace-display";

export type PaneDragState = { slotIndex: number; paneIndex: number } | null;
export type TabDragState = { slotIndex: number } | null;
export type DropAxis = "horizontal" | "vertical";

type WorkspaceDragOptions = {
  slots: SlotConfig[];
  onMoveTab: (fromSlotIndex: number, toSlotIndex: number) => void;
  onMovePane: (fromSlotIndex: number, fromPaneIndex: number, toSlotIndex: number, toPaneIndex: number) => void;
};

function paneDragFromEvent(event: DragEvent<HTMLElement>): PaneDragState {
  const payload = event.dataTransfer.getData("text/plain");
  const match = payload.match(/^(\d+):(\d+)$/);
  if (!match) return null;
  return { slotIndex: Number(match[1]), paneIndex: Number(match[2]) };
}

export function dropAxisForSlot(slot: SlotConfig | null | undefined): DropAxis {
  if (!slot) return "horizontal";
  const layout = normalizedLayout(slot, paneCount(slot));
  return layout === "vertical" || layout === "main-top" ? "vertical" : "horizontal";
}

export function isPointerAfterDropMidpoint(
  axis: DropAxis,
  pointer: { clientX: number; clientY: number },
  rect: Pick<DOMRect, "left" | "top" | "width" | "height">,
): boolean {
  if (axis === "vertical") return pointer.clientY > rect.top + rect.height / 2;
  return pointer.clientX > rect.left + rect.width / 2;
}

export function useWorkspaceDrag({ slots, onMoveTab, onMovePane }: WorkspaceDragOptions) {
  const [paneDrag, setPaneDrag] = useState<PaneDragState>(null);
  const [tabDrag, setTabDrag] = useState<TabDragState>(null);
  const paneDragRef = useRef<PaneDragState>(null);

  function clearPaneDrag() {
    paneDragRef.current = null;
    setPaneDrag(null);
  }

  function handleTabDragStart(event: DragEvent<HTMLElement>, slotIndex: number) {
    setTabDrag({ slotIndex });
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", `tab:${slotIndex}`);
  }

  function handleTabDragOver(event: DragEvent<HTMLElement>) {
    if (!tabDrag) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }

  function handleTabDrop(event: DragEvent<HTMLElement>, slotIndex: number) {
    event.preventDefault();
    event.stopPropagation();
    if (!tabDrag) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const after = event.clientY > rect.top + rect.height / 2;
    onMoveTab(tabDrag.slotIndex, slotIndex + (after ? 1 : 0));
    setTabDrag(null);
  }

  function handlePaneDragStart(event: DragEvent<HTMLElement>, slotIndex: number, paneIndex: number) {
    const slot = slots[slotIndex];
    if (!slot || !canDragPane(slot)) return;
    event.stopPropagation();
    const nextDrag = { slotIndex, paneIndex };
    paneDragRef.current = nextDrag;
    setPaneDrag(nextDrag);
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", `${slotIndex}:${paneIndex}`);
  }

  function handlePaneDragOver(event: DragEvent<HTMLElement>, slotIndex: number) {
    const target = slots[slotIndex];
    const currentDrag = paneDragRef.current ?? paneDrag ?? paneDragFromEvent(event);
    const source = currentDrag ? slots[currentDrag.slotIndex] : null;
    if (!currentDrag || !target || !source) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }

  function handlePaneDrop(event: DragEvent<HTMLElement>, slotIndex: number, paneIndex: number) {
    event.preventDefault();
    event.stopPropagation();
    const currentDrag = paneDragRef.current ?? paneDrag ?? paneDragFromEvent(event);
    if (!currentDrag) return;
    const target = slots[slotIndex];
    const rect = event.currentTarget.getBoundingClientRect();
    const after = isPointerAfterDropMidpoint(
      dropAxisForSlot(target),
      { clientX: event.clientX, clientY: event.clientY },
      rect,
    );
    onMovePane(currentDrag.slotIndex, currentDrag.paneIndex, slotIndex, paneIndex + (after ? 1 : 0));
    clearPaneDrag();
  }

  function handlePaneAppendDrop(event: DragEvent<HTMLElement>, slotIndex: number) {
    event.preventDefault();
    event.stopPropagation();
    const target = slots[slotIndex];
    const currentDrag = paneDragRef.current ?? paneDrag ?? paneDragFromEvent(event);
    const source = currentDrag ? slots[currentDrag.slotIndex] : null;
    if (!currentDrag || !target || !source) return;
    onMovePane(currentDrag.slotIndex, currentDrag.paneIndex, slotIndex, paneCount(target));
    clearPaneDrag();
  }

  return {
    tabDrag,
    paneDrag,
    handleTabDragStart,
    handleTabDragOver,
    handleTabDrop,
    clearTabDrag: () => setTabDrag(null),
    handlePaneDragStart,
    handlePaneDragOver,
    handlePaneDrop,
    handlePaneAppendDrop,
    clearPaneDrag,
  };
}
