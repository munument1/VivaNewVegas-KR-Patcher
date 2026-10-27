# VNV tNVSE encoding hardening candidate (2026-10-27)

This is a **source-only regression candidate**, not a validated game build or release.
Apply the existing VNV UI replacement patch, then the strict/lossless encoding patch,
to pinned upstream tNVSE `7355fd3f2e008dc252ac484f9b376c153e584455`.

- Reject overlong UTF-8, truncated sequences, surrogate ranges, and out-of-range Unicode.
- Require non-lossy Windows conversion and Unicode round-trip checks; keep the caller's
  original pointer and bytes when conversion is not representable as CP949.
- Preserve the reviewed Korean display alias `—` to `―`.
- Retain existing VNV key-label, rich-text, icon, GMST and font routing changes.
- Remove old DLL reuse; every build for this change must compile fresh Win32 sources.

Verification required: Windows CI compile and C++ regression; VNV Extended MO2 Output
generation and byte/readback checks; in-game key prompts, skill challenge choices, perk
descriptions, chem expiration notifications, terminal, door/key, HUD and saves.

Do not port Nuclear Sunset TTW-specific scripts, dialogue field conversion, or dynamic
dictionary entries without checking their exact VNV plugin providers and byte contexts.
Do not release until the new DLL, patcher EXE, corresponding source archive and
Nexus/GitHub artifacts have been validated. Existing v1.0.7.6 stays unchanged.
