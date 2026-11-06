from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app import migrate_league_passwords as migration


@pytest.mark.parametrize("saved_hash", [None, "", "existing-hash"])
def test_migration_hashes_only_when_needed_and_clears_plaintext(db, monkeypatch, saved_hash):
    league = SimpleNamespace(access_code="old-password", password_hash=saved_hash, is_private=False)
    db.scalars.return_value.all.return_value = [league]
    hash_password = Mock(return_value="new-hash")
    monkeypatch.setattr(migration, "hash_password", hash_password)

    assert migration.migrate_league_passwords(db) == 1
    assert league.password_hash == (saved_hash or "new-hash")
    assert league.access_code is None
    assert league.is_private is True
    if saved_hash:
        hash_password.assert_not_called()
    else:
        hash_password.assert_called_once_with("old-password")
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_migration_without_legacy_values_does_not_hash_anything(db, monkeypatch):
    db.scalars.return_value.all.return_value = []
    hash_password = Mock()
    monkeypatch.setattr(migration, "hash_password", hash_password)
    assert migration.migrate_league_passwords(db) == 0
    hash_password.assert_not_called()


def test_migration_failure_rolls_back_instead_of_committing(db, monkeypatch):
    db.scalars.return_value.all.return_value = [
        SimpleNamespace(access_code="old-password", password_hash=None),
    ]
    monkeypatch.setattr(migration, "hash_password", Mock(side_effect=RuntimeError("Error simulado")))
    with pytest.raises(RuntimeError, match="Error simulado"):
        migration.migrate_league_passwords(db)
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
