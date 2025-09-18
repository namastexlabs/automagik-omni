"""Access control service with in-memory caching for phone number rules."""

from __future__ import annotations

import logging
import threading
from typing import Callable, Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import AccessRule, AccessRuleType

logger = logging.getLogger(__name__)

CacheBucket = Dict[AccessRuleType, Dict[str, set]]


class AccessControlService:
    """Service responsible for loading and evaluating access control rules."""

    _GLOBAL_SCOPE = None

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory
        self._lock = threading.RLock()
        self._cache: Dict[Optional[str], CacheBucket] = {}
        self._cache_loaded: bool = False

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def load_rules(self, db: Optional[Session] = None) -> None:
        """Load all rules from the database into the in-memory cache."""
        own_session = False
        if db is None:
            db = self._session_factory()
            own_session = True

        try:
            rules = db.query(AccessRule).all()
            with self._lock:
                self._cache = {}
                for rule in rules:
                    self._store_rule(rule)
                self._cache_loaded = True
            logger.info("Access control cache warmed with %d rules", len(rules))
        finally:
            if own_session:
                db.close()

    def check_access(
        self,
        phone_number: str,
        instance_name: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> bool:
        """Determine whether a phone number is allowed for the given scope.

        Allow rules win ties against block rules when both match with the same
        specificity. If no rules match, access is allowed by default.
        """
        phone_number = phone_number.strip()
        self._ensure_cache_loaded(db)

        with self._lock:
            buckets = []
            global_bucket = self._cache.get(self._GLOBAL_SCOPE)
            if global_bucket:
                buckets.append(global_bucket)

            if instance_name:
                instance_bucket = self._cache.get(instance_name)
                if instance_bucket:
                    buckets.append(instance_bucket)

            allow_score = -1
            block_score = -1
            for bucket in buckets:
                allow_score = max(allow_score, self._match_bucket(bucket, AccessRuleType.ALLOW, phone_number))
                block_score = max(block_score, self._match_bucket(bucket, AccessRuleType.BLOCK, phone_number))

        if allow_score == -1 and block_score == -1:
            return True
        if allow_score >= block_score and allow_score != -1:
            return True
        if block_score != -1:
            return False
        return True

    def add_rule(
        self,
        phone_number: str,
        rule_type: AccessRuleType | str,
        instance_name: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> AccessRule:
        """Persist a new access rule and update the cache."""
        phone_number = phone_number.strip()
        rule_enum = rule_type if isinstance(rule_type, AccessRuleType) else AccessRuleType(rule_type)
        self._ensure_cache_loaded(db)

        own_session = False
        if db is None:
            db = self._session_factory()
            own_session = True

        try:
            rule = AccessRule(
                instance_name=instance_name,
                phone_number=phone_number,
                rule_type=rule_enum.value,
            )
            db.add(rule)
            try:
                db.commit()
            except IntegrityError as exc:  # pragma: no cover - passthrough for caller
                db.rollback()
                logger.warning("Failed to add access rule due to integrity error: %s", exc)
                raise
            db.refresh(rule)
        finally:
            if own_session:
                db.close()

        with self._lock:
            self._store_rule(rule)
        logger.info(
            "Access rule added: scope=%s phone=%s type=%s", instance_name or "global", phone_number, rule_enum.value
        )
        return rule

    def remove_rule(self, rule_id: int, db: Optional[Session] = None) -> bool:
        """Remove an access rule by identifier and update cache."""
        self._ensure_cache_loaded(db)

        own_session = False
        if db is None:
            db = self._session_factory()
            own_session = True

        try:
            rule = db.query(AccessRule).filter(AccessRule.id == rule_id).first()
            if not rule:
                return False

            db.delete(rule)
            db.commit()
        finally:
            if own_session:
                db.close()

        with self._lock:
            self._remove_rule(rule)
        logger.info(
            "Access rule removed: scope=%s phone=%s type=%s", rule.instance_name or "global", rule.phone_number, rule.rule_type
        )
        return True

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _ensure_cache_loaded(self, db: Optional[Session]) -> None:
        with self._lock:
            cache_ready = self._cache_loaded
        if not cache_ready:
            self.load_rules(db=db)

    def _store_rule(self, rule: AccessRule) -> None:
        bucket = self._cache.setdefault(rule.instance_name or self._GLOBAL_SCOPE, self._empty_bucket())
        container = bucket[rule.rule_enum]
        if rule.phone_number.endswith("*"):
            prefix = rule.phone_number[:-1]
            container["prefix"].add(prefix)
        else:
            container["exact"].add(rule.phone_number)

    def _remove_rule(self, rule: AccessRule) -> None:
        key = rule.instance_name or self._GLOBAL_SCOPE
        bucket = self._cache.get(key)
        if not bucket:
            return

        container = bucket.get(rule.rule_enum)
        if not container:
            return

        if rule.phone_number.endswith("*"):
            prefix = rule.phone_number[:-1]
            container["prefix"].discard(prefix)
        else:
            container["exact"].discard(rule.phone_number)

        if self._bucket_empty(bucket):
            self._cache.pop(key, None)

    @staticmethod
    def _empty_bucket() -> CacheBucket:
        return {
            AccessRuleType.ALLOW: {"exact": set(), "prefix": set()},
            AccessRuleType.BLOCK: {"exact": set(), "prefix": set()},
        }

    @staticmethod
    def _bucket_empty(bucket: CacheBucket) -> bool:
        for container in bucket.values():
            if container["exact"] or container["prefix"]:
                return False
        return True

    @staticmethod
    def _match_bucket(bucket: CacheBucket, rule_type: AccessRuleType, phone_number: str) -> int:
        container = bucket[rule_type]
        best = -1
        if phone_number in container["exact"]:
            best = max(best, len(phone_number))
        for prefix in container["prefix"]:
            if phone_number.startswith(prefix):
                best = max(best, len(prefix))
        return best


access_control_service = AccessControlService()

__all__ = ["AccessControlService", "access_control_service"]
