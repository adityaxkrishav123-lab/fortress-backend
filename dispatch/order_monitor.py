import asyncio
import logging
from datetime import datetime
from typing import List
from models.dispatch_models import DispatchOrder
from state_manager import StateManager

class OrderMonitor:
    """
    AGENT 2: The Full-Lifecycle Tracker.
    Ensures every request is tracked from first Action Card to final Delivery.
    Now backed by SQLite StateManager for 100% Resilience (Amnesia Cure).
    """
    
    def __init__(self, action_card_timeout_mins: int = 15, manual_call_timeout_mins: int = 30):
        self.action_timeout = action_card_timeout_mins
        self.manual_timeout = manual_call_timeout_mins
        self.logger = logging.getLogger("OrderMonitor")
        self._phase_timestamps: dict = {}

    async def load_state(self):
        """Called on startup to load active timers from DB."""
        timers = await StateManager.get_all_timers(target_type="NGO_ORDER")
        for row in timers:
            try:
                self._phase_timestamps[row["target_id"]] = datetime.fromisoformat(row["started_at"])
            except Exception as e:
                self.logger.error(f"Error parsing timestamp for {row['target_id']}: {e}")
        self.logger.info(f"Loaded {len(timers)} persistent timers from StateManager.")

    async def _phase_start(self, order_id: str, phase: str):
        """Mark the moment an order enters a new phase, save to DB."""
        now = datetime.now()
        self._phase_timestamps[order_id] = now
        await StateManager.save_timer(order_id, "NGO_ORDER", phase)

    async def _phase_cleanup(self, order_id: str):
        """Remove from local cache and DB."""
        self._phase_timestamps.pop(order_id, None)
        await StateManager.delete_timer(order_id)

    def _phase_elapsed_mins(self, order_id: str) -> float:
        """Minutes since this order entered its current phase."""
        start = self._phase_timestamps.get(order_id, datetime.now())
        return (datetime.now() - start).total_seconds() / 60

    async def run_lifecycle_monitor(self, active_orders: List[DispatchOrder]):
        """
        The Guardian Loop:
        Phase 1: Awaiting YES/NO on Action Card (15 min timer).
        Phase 2: Awaiting manual phone/email handshake (30 min timer, starts AFTER Phase 1).
        Phase 3: In-transit safety check (24 hour timer, starts from dispatch time).
        """
        while True:
            # Fix 2: Prune terminal orders to prevent memory leak
            TERMINAL_STATES = {
                "DELIVERED", "CANCELLED",
                "REOPEN_FOR_ESCALATION", "REOPEN_LOST_IN_TRANSIT"
            }
            active_orders[:] = [o for o in active_orders if o.status not in TERMINAL_STATES]

            for order in active_orders:
                elapsed = self._phase_elapsed_mins(order.order_id)

                # PHASE 1: Awaiting Digital Confirmation
                if order.status == "AWAITING_CONFIRMATION":
                    if order.order_id not in self._phase_timestamps:
                        await self._phase_start(order.order_id, "AWAITING_CONFIRMATION")
                    elif elapsed > self.action_timeout:
                        self.logger.warning(f"[{order.order_id}] Phase 1 TIMEOUT: NGO ghosted Action Card. Sharing contact details.")
                        order.status = "CONTACT_SHARED_WAITING_MANUAL"
                        order.contact_shared = True
                        await self._phase_start(order.order_id, "CONTACT_SHARED_WAITING_MANUAL")
                        await StateManager.save_active_order(order) # Sync to Cloud/DB

                # PHASE 2: Awaiting Manual Handshake
                elif order.status == "CONTACT_SHARED_WAITING_MANUAL":
                    if elapsed > self.manual_timeout:
                        self.logger.error(f"[{order.order_id}] Phase 2 TIMEOUT: Both digital and manual contact failed. Escalating.")
                        order.status = "REOPEN_FOR_ESCALATION"
                        await self._phase_cleanup(order.order_id)
                        await StateManager.save_active_order(order) # Sync to Cloud/DB

                # PHASE 3: In-Transit Safety (24h timer from dispatch)
                elif order.status == "IN_TRANSIT":
                    if order.order_id not in self._phase_timestamps:
                        await self._phase_start(order.order_id, "IN_TRANSIT")
                    elif elapsed > 24 * 60:
                        self.logger.error(f"[{order.order_id}] DELIVERY FAILURE: Lost in transit. Emergency re-opening.")
                        order.status = "REOPEN_LOST_IN_TRANSIT"
                        await self._phase_cleanup(order.order_id)
                        await StateManager.save_active_order(order) # Sync to Cloud/DB
                
                # Terminal States cleanup
                elif order.status in TERMINAL_STATES:
                    if order.order_id in self._phase_timestamps:
                        await self._phase_cleanup(order.order_id)

            await asyncio.sleep(60)  # Check every 60 seconds
