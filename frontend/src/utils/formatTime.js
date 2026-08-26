export const slotToTime = (slot) => {
  const safe = Math.max(0, Math.min(96, Number(slot) || 0));
  if (safe === 96) return "24:00";
  return `${String(Math.floor(safe / 4)).padStart(2,"0")}:${String((safe % 4) * 15).padStart(2,"0")}`;
};

export const timeToSlot = (time) => {
  const [hours, minutes] = String(time).split(":").map(Number);
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return 0;
  return Math.max(0, Math.min(96, hours * 4 + Math.round(minutes / 15)));
};
