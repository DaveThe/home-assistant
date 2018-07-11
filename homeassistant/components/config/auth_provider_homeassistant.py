"""Offer API to configure the Home Assistant auth provider."""
from homeassistant.auth_providers import homeassistant as auth_ha
from homeassistant.core import callback
from homeassistant.components import websocket_api


WS_TYPE_CREATE = 'config/auth_provider/homeassistant/create'
SCHEMA_WS_CREATE = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    'type': WS_TYPE_CREATE,
    'user_id': str,
    'username': str,
    'password': str,
})

WS_TYPE_DELETE = 'config/auth_provider/homeassistant/delete'
SCHEMA_WS_DELETE = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    'type': WS_TYPE_DELETE,
    'user_id': str,
})


async def async_setup(hass):
    """Enable the Home Assistant views."""
    hass.components.websocket_api.async_register_command(
        WS_TYPE_CREATE, websocket_create,
        SCHEMA_WS_CREATE
    )
    hass.components.websocket_api.async_register_command(
        WS_TYPE_DELETE, websocket_delete,
        SCHEMA_WS_DELETE
    )
    return True


def _get_provider(hass):
    """Get homeassistant auth provider."""
    for prv in hass.auth.auth_providers:
        if prv.type == 'homeassistant':
            return prv

    raise RuntimeError('Provider not found')


@callback
@websocket_api.require_owner
def websocket_create(hass, connection, msg):
    """Create credentials and attach to a user."""
    async def create_creds():
        """Send users."""
        data = auth_ha.Data(hass)
        await data.async_load()

        user = await hass.auth.async_get_user(msg['user_id'])

        if user is None:
            connection.send_message_outside(websocket_api.error_message(
                msg['id'], 'not_found', 'User not found'))
            return

        if user.system_generated:
            connection.send_message_outside(websocket_api.error_message(
                msg['id'], 'system_generated',
                'Cannot add credentials to a system generated user.'))
            return

        try:
            data.add_auth(msg['username'], msg['password'])
        except auth_ha.InvalidUser:
            connection.send_message_outside(websocket_api.error_message(
                msg['id'], 'username_exists', 'Username already exists'))
            return

        provider = _get_provider(hass)
        credentials = await provider.async_get_or_create_credentials({
            'username': msg['username']
        })
        await hass.auth.async_link_user(user, credentials)

        await data.async_save()
        connection.to_write.put_nowait(websocket_api.result_message(msg['id']))

    hass.async_add_job(create_creds())


@callback
@websocket_api.require_owner
def websocket_delete(hass, connection, msg):
    """Delete username and related credential."""

    async def delete_creds():
        """Delete user credentials."""
        data = auth_ha.Data(hass)
        await data.async_load()

        provider = _get_provider(hass)
        credentials = await provider.async_get_or_create_credentials({
            'username': msg['username']
        })

        # If new credential, no user was linked to this username
        if not credentials.is_new:
            await hass.auth.async_remove_credentials(credentials)

        data.remove_auth(msg['username'])
        await data.async_save()
        connection.to_write.put_nowait(
            websocket_api.result_message(msg['id']))

    hass.async_add_job(delete_creds())
