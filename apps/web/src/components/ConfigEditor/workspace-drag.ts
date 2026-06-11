import { useRef, useState, type DragEvent, type PointerEvent as ReactPointerEvent } from "react";
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

type PointerPaneDrag = {
  source: NonNullable<PaneDragState>;
  pointerId: number;
  startX: number;
  startY: number;
  active: boolean;
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

export function paneDropTargetIndex(
  _drag: PaneDragState,
  _targetSlotIndex: number,
  targetPaneIndex: number,
  after: boolean,
): number {
  return targetPaneIndex + (after ? 1 : 0);
}

export function useWorkspaceDrag({ slots, onMoveTab, onMovePane }: WorkspaceDragOptions) {
  const [paneDrag, setPaneDrag] = useState<PaneDragState>(null);
  const [tabDrag, setTabDrag] = useState<TabDragState>(null);
  const paneDragRef = useRef<PaneDragState>(null);
  const pointerPaneDragRef = useRef<PointerPaneDrag | null>(null);

  function clearPaneDrag() {
    paneDragRef.current = null;
    pointerPaneDragRef.current = null;
    setPaneDrag(null);
  }

  function resolvePointerDropTarget(
    drag: NonNullable<PaneDragState>,
    pointer: { clientX: number; clientY: number },
  ): { slotIndex: number; paneIndex: number } | null {
    if (typeof document === "undefined" || typeof document.elementFromPoint !== "function") return null;
    const element = document.elementFromPoint(pointer.clientX, pointer.clientY);
    if (!element) return null;
    const paneElement = element.closest<HTMLElement>("[data-workspace-pane-index][data-workspace-slot-index]");
    if (paneElement) {
      const slotIndex = Number(paneElement.dataset.workspaceSlotIndex);
      const paneIndex = Number(paneElement.dataset.workspacePaneIndex);
      const target = slots[slotIndex];
      if (!Number.isInteger(slotIndex) || !Number.isInteger(paneIndex) || !target) return null;
      const after = isPointerAfterDropMidpoint(dropAxisForSlot(target), pointer, paneElement.getBoundingClientRect());
      return {
        slotIndex,
        paneIndex: paneDropTargetIndex(drag, slotIndex, paneIndex, after),
      };
    }
    const dropZone = element.closest<HTMLElement>("[data-workspace-pane-drop-zone]");
    if (!dropZone) return null;
    const slotIndex = Number(dropZone.dataset.workspaceSlotIndex);
    const target = slots[slotIndex];
    if (!Number.isInteger(slotIndex) || !target) return null;
    return { slotIndex, paneIndex: paneCount(target) };
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
    onMovePane(currentDrag.slotIndex, currentDrag.paneIndex, slotIndex, paneDropTargetIndex(currentDrag, slotIndex, paneIndex, after));
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

  function handlePanePointerDown(event: ReactPointerEvent<HTMLElement>, slotIndex: number, paneIndex: number) {
    if (event.button !== 0) return;
    const slot = slots[slotIndex];
    if (!slot || !canDragPane(slot)) return;
    event.preventDefault();
    event.stopPropagation();
    pointerPaneDragRef.current = {
      source: { slotIndex, paneIndex },
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      active: false,
    };
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function handlePanePointerMove(event: ReactPointerEvent<HTMLElement>) {
    const drag = pointerPaneDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const moved = Math.abs(event.clientX - drag.startX) + Math.abs(event.clientY - drag.startY);
    if (!drag.active && moved < 6) return;
    if (!drag.active) {
      drag.active = true;
      paneDragRef.current = drag.source;
      setPaneDrag(drag.source);
    }
    event.preventDefault();
    event.stopPropagation();
  }

  function handlePanePointerEnd(event: ReactPointerEvent<HTMLElement>) {
    const drag = pointerPaneDragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    if (drag.active) {
      event.preventDefault();
      event.stopPropagation();
      const target = resolvePointerDropTarget(drag.source, { clientX: event.clientX, clientY: event.clientY });
      if (target) {
        onMovePane(drag.source.slotIndex, drag.source.paneIndex, target.slotIndex, target.paneIndex);
      }
    }
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
    handlePanePointerDown,
    handlePanePointerMove,
    handlePanePointerEnd,
    clearPaneDrag,
  };
}
