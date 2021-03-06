"""Tests for the insecure example auth provider."""
from unittest.mock import Mock
import uuid

import pytest

from homeassistant import auth
from homeassistant.auth_providers import insecure_example

from tests.common import mock_coro


@pytest.fixture
def store(hass):
    """Mock store."""
    return auth.AuthStore(hass)


@pytest.fixture
def provider(hass, store):
    """Mock provider."""
    return insecure_example.ExampleAuthProvider(hass, store, {
        'type': 'insecure_example',
        'users': [
            {
                'username': 'user-test',
                'password': 'password-test',
            },
            {
                'username': '🎉',
                'password': '😎',
            }
        ]
    })


async def test_create_new_credential(provider):
    """Test that we create a new credential."""
    credentials = await provider.async_get_or_create_credentials({
        'username': 'user-test',
        'password': 'password-test',
    })
    assert credentials.is_new is True


async def test_match_existing_credentials(store, provider):
    """See if we match existing users."""
    existing = auth.Credentials(
        id=uuid.uuid4(),
        auth_provider_type='insecure_example',
        auth_provider_id=None,
        data={
            'username': 'user-test'
        },
        is_new=False,
    )
    provider.async_credentials = Mock(return_value=mock_coro([existing]))
    credentials = await provider.async_get_or_create_credentials({
        'username': 'user-test',
        'password': 'password-test',
    })
    assert credentials is existing


async def test_verify_username(provider):
    """Test we raise if incorrect user specified."""
    with pytest.raises(insecure_example.InvalidAuthError):
        await provider.async_validate_login(
            'non-existing-user', 'password-test')


async def test_verify_password(provider):
    """Test we raise if incorrect user specified."""
    with pytest.raises(insecure_example.InvalidAuthError):
        await provider.async_validate_login(
            'user-test', 'incorrect-password')


async def test_utf_8_username_password(provider):
    """Test that we create a new credential."""
    credentials = await provider.async_get_or_create_credentials({
        'username': '🎉',
        'password': '😎',
    })
    assert credentials.is_new is True
