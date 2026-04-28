import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict
from models.shared import CitizenRequestStatus
from models.citizen_profile import DisasterRequest
from state_manager import StateManager

class CitizenOrderMonitor:
    """
    WATCHDOG: The Citizen-NGO Handshake Guardian.
    Ensures no citizen is left waiting and both sides confirm help.
    """
    def __init__(self):
        self.logger = logging.getLogger("CitizenMonitor")
        self._phase_timestamps: dict = {}

    async def load_state(self):
        timers = await StateManager.get_all_timers(target_type="CITIZEN_REQ")
        for row in timers:
            try:
                self._phase_timestamps[row["target_id"]] = datetime.fromisoformat(row["started_at"])
            except Exception as e:
                self.logger.error(f"Error parsing timestamp for {row['target_id']}: {e}")
        self.logger.info(f"Loaded {len(timers)} persistent citizen timers from StateManager.")

    async def _phase_start(self, req_id: str, phase: str):
        now = datetime.now()
        self._phase_timestamps[req_id] = now
        await StateManager.save_timer(req_id, "CITIZEN_REQ", phase)

    async def _phase_cleanup(self, req_id: str):
        self._phase_timestamps.pop(req_id, None)
        await StateManager.delete_timer(req_id)
        
    def _phase_elapsed_hours(self, req_id: str) -> float:
        start = self._phase_timestamps.get(req_id, datetime.now())
        return (datetime.now() - start).total_seconds() / 3600

    async def run_handshake_monitor(self, citizen_requests: Dict[str, DisasterRequest]):
        """
        The Loop of Persistence:
        1. Checks for NGO_ACCEPTED but not COMPLETED.
        2. Sends daily reminders if one side is missing.
        3. Flags STALLED if nothing happens for 48 hours.
        """
        while True:
            for req_id, req in citizen_requests.items():
                
                # Check 1: Initialize timer in StateManager
                if req_id not in self._phase_timestamps and req.status != CitizenRequestStatus.COMPLETED:
                    await self._phase_start(req_id, str(req.status))
                    
                elapsed_hours = self._phase_elapsed_hours(req_id)

                if req.status == CitizenRequestStatus.NGO_ACCEPTED:
                    # Logic: If 24 hours passed and not both confirmed
                    if elapsed_hours > 24:
                        if not (req.citizen_confirmed and req.ngo_confirmed):
                            self.logger.warning(
                                f"REMINDER: Request {req_id} is pending. "
                                f"Citizen Confirmed: {req.citizen_confirmed} | "
                                f"NGO Confirmed: {req.ngo_confirmed}"
                            )
                            # In production, this triggers a Push Notification / SMS
                    
                    # Logic: If 48 hours passed with no completion, flag as stalled
                    if elapsed_hours > 48:
                        if not req.ngo_confirmed:
                            req.status = CitizenRequestStatus.STALLED
                            await self._phase_start(req_id, str(req.status)) # Reset state
                            await StateManager.save_citizen_request(req) # Sync to Cloud/DB
                            self.logger.error(f"STALLED: NGO {req.ngo_id} failed to deliver request {req_id}.")

                # Final Closing Logic: When both confirm, it's done.
                if req.citizen_confirmed and req.ngo_confirmed:
                    if req.status != CitizenRequestStatus.COMPLETED:
                        req.status = CitizenRequestStatus.COMPLETED
                        await self._phase_cleanup(req_id)
                        await StateManager.save_citizen_request(req) # Sync to Cloud/DB
                        self.logger.info(f"SUCCESS: Request {req_id} closed. Both sides confirmed.")

            await asyncio.sleep(3600)  # Check every hour (more efficient for daily tasks)
