import json

import httpx
import pytest

from app.services.sms import (
    SmsConfigurationError,
    SmsProviderError,
    SmslenzClient,
)


@pytest.mark.asyncio
async def test_smslenz_success():
    captured = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        captured["method"] = (
            request.method
        )
        captured["url"] = str(
            request.url
        )
        captured["json"] = json.loads(
            request.content.decode(
                "utf-8"
            )
        )

        return httpx.Response(
            200,
            json={
                "success":
                    True,
                "message":
                    "SMS sent successfully",
                "data": {
                    "status":
                        "success",
                    "campaign_id":
                        42,
                    "message":
                        "Test",
                    "sender_id":
                        "SMSlenzDEMO",
                    "pages":
                        1,
                    "recipient_number":
                        "94771234567",
                    "sms_credit_balance":
                        "2513.95",
                    "charged_from":
                        "main",
                },
            },
        )

    transport = httpx.MockTransport(
        handler
    )

    client = SmslenzClient(
        base_url=(
            "https://www.smslenz.lk"
        ),
        user_id="fake-user",
        api_key="fake-key",
        sender_id="SMSlenzDEMO",
        transport=transport,
    )

    result = await client.send_sms(
        contact="0771234567",
        message="Test message",
    )

    assert (
        captured["method"]
        == "POST"
    )

    assert (
        captured["url"]
        == (
            "https://www.smslenz.lk/"
            "api/send-sms"
        )
    )

    assert captured["json"] == {
        "user_id":
            "fake-user",
        "api_key":
            "fake-key",
        "sender_id":
            "SMSlenzDEMO",
        "contact":
            "+94771234567",
        "message":
            "Test message",
    }

    assert result.success is True
    assert result.status == "success"
    assert result.campaign_id == "42"
    assert result.pages == 1
    assert (
        result.recipient_number
        == "94771234567"
    )
    assert (
        result.sms_credit_balance
        == "2513.95"
    )
    assert (
        result.charged_from
        == "main"
    )


@pytest.mark.asyncio
async def test_smslenz_provider_rejection():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success":
                    False,
                "message":
                    "Invalid API key",
                "data": {
                    "status":
                        "failed",
                },
            },
        )

    client = SmslenzClient(
        base_url=(
            "https://www.smslenz.lk"
        ),
        user_id="fake-user",
        api_key="fake-key",
        sender_id="SMSlenzDEMO",
        transport=(
            httpx.MockTransport(
                handler
            )
        ),
    )

    with pytest.raises(
        SmsProviderError,
        match="Invalid API key",
    ):
        await client.send_sms(
            contact="0771234567",
            message="Test",
        )


@pytest.mark.asyncio
async def test_smslenz_http_error():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            401,
            json={
                "success":
                    False,
                "message":
                    "Unauthorized",
            },
        )

    client = SmslenzClient(
        base_url=(
            "https://www.smslenz.lk"
        ),
        user_id="fake-user",
        api_key="fake-key",
        sender_id="SMSlenzDEMO",
        transport=(
            httpx.MockTransport(
                handler
            )
        ),
    )

    with pytest.raises(
        SmsProviderError,
        match="Unauthorized",
    ):
        await client.send_sms(
            contact="+94771234567",
            message="Test",
        )


@pytest.mark.asyncio
async def test_smslenz_invalid_json():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            text="not-json",
        )

    client = SmslenzClient(
        base_url=(
            "https://www.smslenz.lk"
        ),
        user_id="fake-user",
        api_key="fake-key",
        sender_id="SMSlenzDEMO",
        transport=(
            httpx.MockTransport(
                handler
            )
        ),
    )

    with pytest.raises(
        SmsProviderError,
        match="invalid JSON",
    ):
        await client.send_sms(
            contact="0771234567",
            message="Test",
        )


def test_smslenz_configuration_required():
    with pytest.raises(
        SmsConfigurationError,
    ):
        SmslenzClient(
            base_url=(
                "https://www.smslenz.lk"
            ),
            user_id="",
            api_key="fake-key",
            sender_id="SMSlenzDEMO",
        )


@pytest.mark.asyncio
async def test_smslenz_message_length_limit():
    client = SmslenzClient(
        base_url=(
            "https://www.smslenz.lk"
        ),
        user_id="fake-user",
        api_key="fake-key",
        sender_id="SMSlenzDEMO",
        transport=httpx.MockTransport(
            lambda request:
                httpx.Response(
                    500
                )
        ),
    )

    with pytest.raises(
        ValueError,
        match="1500",
    ):
        await client.send_sms(
            contact="0771234567",
            message="X" * 1501,
        )
