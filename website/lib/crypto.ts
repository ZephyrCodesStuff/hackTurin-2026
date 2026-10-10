/**
 * Deterministic client-side PBKDF2 hash using native browser Web Crypto.
 * Matches Python hashlib.pbkdf2_hmac("sha256", password, salt, 100000).hex().
 * Never sends cleartext passwords over the network.
 */
export async function deriveClientPasswordHash(
  username: string,
  password: string
): Promise<string> {
  const cleanUsername = username.trim().toLowerCase();
  const encoder = new TextEncoder();

  // Import raw password as key material
  const keyMaterial = await window.crypto.subtle.importKey(
    "raw",
    encoder.encode(password),
    { name: "PBKDF2" },
    false,
    ["deriveBits"]
  );

  // Deterministic salt tied to username
  const salt = encoder.encode(`traffic-auth:${cleanUsername}`);

  // Derive 256 bits (32 bytes)
  const derivedBits = await window.crypto.subtle.deriveBits(
    {
      name: "PBKDF2",
      salt,
      iterations: 100000,
      hash: "SHA-256",
    },
    keyMaterial,
    256
  );

  // Convert to hex string
  const hashArray = Array.from(new Uint8Array(derivedBits));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}
