"""
notification_manager.py
========================
Central dispatcher for in-app notifications.

Notifications are stored in Firestore under the `notifications` collection.
Each document is keyed by a unique notification_id.

Schema:
  notifications/{notification_id}:
    uid            : str   — the recipient user's uid
    title          : str
    message        : str
    deep_link      : str   — hints the frontend which screen to open
    priority       : str   — NORMAL | HIGH | CRITICAL
    is_read        : bool
    created_at     : str   — ISO timestamp

NOTE: FCM Push (real-time popup) is a Phase 4 feature.
      For now, notifications live in Firestore and the frontend polls.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Central notification hub. All reads/writes go to Firestore.
    The `db` client is passed in per-call so this class stays stateless
    (no singleton, no startup dependency).
    """

    COLLECTION = "notifications"

    @classmethod
    async def create_notification(
        cls,
        db,
        uid: str,
        title: str,
        body: str,
        priority: str = "NORMAL",
        deep_link: str = "",
    ) -> str:
        """
        Creates a new notification document in Firestore.
        Returns the notification_id.
        """
        notification_id = f"NOTIF-{uuid.uuid4().hex[:10].upper()}"
        try:
            await db.collection(cls.COLLECTION).document(notification_id).set({
                "notification_id": notification_id,
                "uid":             uid,
                "title":           title,
                "message":         body,
                "deep_link":       deep_link,
                "priority":        priority,
                "is_read":         False,
                "created_at":      datetime.utcnow().isoformat(),
            })
            logger.info(f"[Notification] Created {notification_id} for uid={uid}")
        except Exception as e:
            logger.error(f"[Notification] Failed to create for uid={uid}: {e}")
        return notification_id

    @classmethod
    async def get_unread(cls, db, uid: str) -> list:
        """
        Returns all unread notifications for a user, newest first.
        """
        try:
            query = (
                db.collection(cls.COLLECTION)
                  .where("uid", "==", uid)
                  .where("is_read", "==", False)
            )
            docs = await query.get()
            results = [doc.to_dict() for doc in docs]
            # Sort newest first (Firestore ordering requires an index for multi-field)
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return results
        except Exception as e:
            logger.error(f"[Notification] get_unread failed for uid={uid}: {e}")
            return []

    @classmethod
    async def mark_read(cls, db, notification_id: str) -> bool:
        """
        Marks a single notification as read.
        """
        try:
            await db.collection(cls.COLLECTION).document(notification_id).update({
                "is_read":   True,
                "read_at":   datetime.utcnow().isoformat(),
            })
            return True
        except Exception as e:
            logger.error(f"[Notification] mark_read failed for {notification_id}: {e}")
            return False

    @classmethod
    async def mark_all_read(cls, db, uid: str) -> int:
        """
        Marks ALL unread notifications for a user as read.
        Returns count of notifications updated.
        """
        try:
            query = (
                db.collection(cls.COLLECTION)
                  .where("uid", "==", uid)
                  .where("is_read", "==", False)
            )
            docs  = await query.get()
            count = 0
            for doc in docs:
                await doc.reference.update({
                    "is_read": True,
                    "read_at": datetime.utcnow().isoformat(),
                })
                count += 1
            return count
        except Exception as e:
            logger.error(f"[Notification] mark_all_read failed for uid={uid}: {e}")
            return 0
