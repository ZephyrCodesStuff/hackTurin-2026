import { get, set } from "idb-keyval";

const CRASH_STORE_PREFIX = "notified_crash_";

/**
 * Checks if a crash event has already triggered a notification.
 */
export async function hasNotifiedCrash(crashId: string | number): Promise<boolean> {
  if (typeof window === "undefined") return true;
  try {
    const val = await get(`${CRASH_STORE_PREFIX}${crashId}`);
    return Boolean(val);
  } catch (err) {
    console.warn("Failed to read from IndexedDB:", err);
    return false;
  }
}

/**
 * Marks a crash event as notified in IndexedDB.
 */
export async function markCrashAsNotified(crashId: string | number): Promise<void> {
  if (typeof window === "undefined") return;
  try {
    await set(`${CRASH_STORE_PREFIX}${crashId}`, Date.now());
  } catch (err) {
    console.warn("Failed to write to IndexedDB:", err);
  }
}
