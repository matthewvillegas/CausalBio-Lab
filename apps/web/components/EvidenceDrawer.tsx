"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";

export function EvidenceDrawer({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    const trigger = document.activeElement;
    // Native dialogs trap focus, but removing one from React bypasses native focus restoration.
    dialog?.showModal();
    return () => {
      dialog?.close();
      if (trigger instanceof HTMLElement && trigger.isConnected) trigger.focus();
    };
  }, []);

  return (
    <dialog
      ref={dialogRef}
      className="evidence-drawer"
      aria-labelledby={titleId}
      onCancel={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="drawer-header">
        <h2 id={titleId}>{title}</h2>
        <button className="button-secondary" onClick={onClose} aria-label="Close evidence">
          Close
        </button>
      </div>
      <div className="drawer-body">{children}</div>
    </dialog>
  );
}
