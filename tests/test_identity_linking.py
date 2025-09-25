"""
Identity linking tests for cross-channel user resolution.
"""

from sqlalchemy.orm import Session

from src.db.models import InstanceConfig, UserExternalId
from src.services.user_service import user_service


def test_whatsapp_user_creation_creates_external_link(test_db: Session):
    # Arrange: create instance
    inst = InstanceConfig(
        name="inst_a",
        channel_type="whatsapp",
        whatsapp_instance="inst_a",
        agent_api_url="http://test-agent-api",
        agent_api_key="test-key",
    )
    test_db.add(inst)
    test_db.commit()

    # Act: create user via WhatsApp helper
    user = user_service.get_or_create_user_by_phone(
        phone_number="+15551234567",
        instance_name="inst_a",
        display_name="Alice",
        session_name="inst_a_+15551234567",
        db=test_db,
    )

    # Assert: external link exists for WhatsApp JID
    links = (
        test_db.query(UserExternalId)
        .filter(UserExternalId.user_id == user.id, UserExternalId.provider == "whatsapp")
        .all()
    )
    assert len(links) == 1
    assert links[0].external_id.endswith("@s.whatsapp.net")


def test_cross_channel_resolution_via_external_id(test_db: Session):
    # Arrange: instance and a WhatsApp user
    inst = InstanceConfig(
        name="inst_b",
        channel_type="whatsapp",
        whatsapp_instance="inst_b",
        agent_api_url="http://test-agent-api",
        agent_api_key="test-key",
    )
    test_db.add(inst)
    test_db.commit()

    wa_user = user_service.get_or_create_user_by_phone(
        phone_number="+447911123456",
        instance_name="inst_b",
        display_name="Bob",
        session_name="inst_b_+447911123456",
        db=test_db,
    )

    # Link a Discord external ID to the same local user
    discord_id = "123456789012345678"
    user_service.link_external_id(wa_user.id, "discord", discord_id, "inst_b", test_db)

    # Act: resolve by Discord external ID
    resolved = user_service.resolve_user_by_external("discord", discord_id, test_db)

    # Assert: same local user id is reused
    assert resolved is not None
    assert resolved.id == wa_user.id


def test_link_reassignment_unifies_to_single_user(test_db: Session):
    # Arrange: instance and two WhatsApp users (simulating accidental duplication)
    inst = InstanceConfig(
        name="inst_c",
        channel_type="whatsapp",
        whatsapp_instance="inst_c",
        agent_api_url="http://test-agent-api",
        agent_api_key="test-key",
    )
    test_db.add(inst)
    test_db.commit()

    user1 = user_service.get_or_create_user_by_phone(
        phone_number="+12025550111",
        instance_name="inst_c",
        display_name="Carol",
        session_name="inst_c_+12025550111",
        db=test_db,
    )
    user2 = user_service.get_or_create_user_by_phone(
        phone_number="+12025550112",
        instance_name="inst_c",
        display_name="Carol-2",
        session_name="inst_c_+12025550112",
        db=test_db,
    )

    discord_id = "999888777666555444"

    # Link to user1 then re-link to user2 (should reassign)
    user_service.link_external_id(user1.id, "discord", discord_id, "inst_c", test_db)
    user_service.link_external_id(user2.id, "discord", discord_id, "inst_c", test_db)

    resolved = user_service.resolve_user_by_external("discord", discord_id, test_db)
    assert resolved is not None
    assert resolved.id == user2.id
