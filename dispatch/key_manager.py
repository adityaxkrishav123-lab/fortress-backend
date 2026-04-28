import os
import logging
import time
from typing import List, Dict

class KeyManager:
    """
    The Zero-Cost Engine.
    Rotates between Gemini API keys to ensure uptime on the free tier.
    - asyncio.Lock is instance-level (Fix #12 — not class-level)
    - report_rate_limit() actually removes blocked keys (Fix #6 from Strike 1)
    - Accepts both GEMINI_KEY_1..5 AND GEMINI_API_KEY (single key setup)
    """

    def __init__(self):
        import asyncio
        self._lock = asyncio.Lock()  # Instance-level — safe inside event loop

        self.keys: List[str] = [
            os.getenv(f"GEMINI_KEY_{i}")
            for i in range(1, 6)
            if os.getenv(f"GEMINI_KEY_{i}")
        ]
        # Accept single-key setup too
        single_key = os.getenv("GEMINI_API_KEY")
        if single_key and single_key not in self.keys:
            self.keys.append(single_key)

        self.usage_history: Dict[str, List[float]] = {key: [] for key in self.keys}
        
        self.current_index = 0
        self.logger = logging.getLogger("KeyManager")

        if not self.keys:
            raise ValueError("CRITICAL: No Gemini API keys found. Set GEMINI_KEY_1..5 or GEMINI_API_KEY in .env")

        self.logger.warning(f"KeyManager initialized with {len(self.keys)} key(s).")

    async def get_active_key(self) -> str:
        """Thread-safe predictive key rotation (Max 14 requests per minute per key)."""
        async with self._lock:
            if not self.keys:
                raise RuntimeError("All API keys exhausted or blocked.")
            
            now = time.time()
            # Try to find a key that is under the 15 RPM limit (14 safe limit)
            for _ in range(len(self.keys)):
                key = self.keys[self.current_index]
                
                # Clean old history > 60s
                self.usage_history[key] = [t for t in self.usage_history[key] if now - t < 60]
                
                if len(self.usage_history[key]) < 14:
                    # Safe to use this key
                    self.usage_history[key].append(now)
                    self.current_index = (self.current_index + 1) % len(self.keys)
                    return key
                
                # If this key is hot, check the next one
                self.current_index = (self.current_index + 1) % len(self.keys)

            # If ALL keys are hot, just return the first one and risk the 429
            # (Circuit breaker will catch it if it fails)
            key = self.keys[0]
            self.usage_history[key].append(now)
            return key

    async def report_rate_limit(self, key: str):
        """
        Removes the blocked key from the active pool immediately.
        Raises RuntimeError if all keys are exhausted.
        """
        async with self._lock:
            if key in self.keys:
                self.keys.remove(key)
                self.logger.error(
                    f"RATE LIMIT: Key {key[:6]}... removed. "
                    f"{len(self.keys)} key(s) remaining."
                )
            if not self.keys:
                raise RuntimeError("ALL API KEYS EXHAUSTED. Cannot call Gemini until keys are restored.")
            # Reset index safely after removal
            self.current_index = self.current_index % len(self.keys)
