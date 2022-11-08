from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from mock import patch

from microservice_websocket.app.services import database as db
from microservice_websocket.app.utils.enums import NodeState


class TestAlertHandle:
    endpoint = "/api/alert/handle"

    # Handle not existing alert
    @pytest.mark.asyncio
    async def test_handle_not_existing(self, app_client: TestClient, auth_header):
        org = db.Organization(organizationName="foo")
        await org.save()
        app = db.Application(applicationName="bar", organization=org.id)
        await app.save()
        node = db.Node(
            nodeID=123,
            nodeName="nodeName",
            application=app.id,
            state=NodeState.ALERT_READY,
            lastSeenAt=datetime.now(),
        )
        await node.save()
        reading = db.Reading(
            node=node.id,
            canID=1,
            sensorNumber=2,
            readingID=32704,
            sessionID=12892,
            publishedAt=datetime.now(),
        )
        await reading.save()
        # Done setup

        response = app_client.post(
            self.endpoint,
            json={
                "alertID": "63186eab0ca2d54a5c258384",
                "isConfirmed": True,
                "handleNote": "foo",
            },
            headers=auth_header,
        )

        assert (
            response.status_code == 404
        ), "Invalid response code when trying to handle non-existing alert"

    @pytest.mark.asyncio
    async def test_handle(self, app_client: TestClient, auth_header):
        org = db.Organization(organizationName="foo")
        await org.save()
        app = db.Application(applicationName="bar", organization=org.id)
        await app.save()
        node = db.Node(
            nodeID=123,
            nodeName="nodeName",
            application=app.id,
            state=NodeState.ALERT_READY,
            lastSeenAt=datetime.now(),
        )
        await node.save()
        reading = db.Reading(
            node=node.id,
            canID=1,
            sensorNumber=2,
            readingID=32704,
            sessionID=12892,
            publishedAt=datetime.now(),
        )
        await reading.save()
        # Done setup

        reading = await db.Reading.find_one()
        assert reading
        node = await db.Node.find_one()
        assert node

        # Manually create Alerts
        alert = db.Alert(
            reading=reading.id,
            node=node.id,
            sessionID=reading.sessionID,
            isHandled=False,
            raisedAt=datetime.now(),
        )
        await alert.save()
        alert2 = db.Alert(
            reading=reading.id,
            node=node.id,
            sessionID=reading.sessionID,
            isHandled=False,
            raisedAt=datetime.now(),
        )
        await alert2.save()

        # Try to handle newly created alert
        with patch("socketio.Client.emit", return_value=None):
            response = app_client.post(
                self.endpoint,
                json={
                    "alertID": str(alert.id),
                    "isConfirmed": True,
                    "handleNote": "foo",
                },
                headers=auth_header,
            )

        alert = await db.Alert.find_one()

        assert (
            response.status_code == 200
            and alert
            and alert.isConfirmed
            and alert.handleNote == "foo"
            and alert.handledBy
            and (user := await db.User.get(alert.handledBy))
            and user.email == "foo@bar.com"
        ), "Invalid response code when trying to handle existing alert"

        node = await db.Node.find_one()

        assert (
            node and node.state == NodeState.ALERT_READY
        ), "Invalid state when handling 1/2 alert"

        # Handle leftover alert
        with patch("socketio.Client.emit", return_value=None):
            response = app_client.post(
                self.endpoint,
                json={
                    "alertID": str(alert2.id),
                    "isConfirmed": True,
                    "handleNote": "foo",
                },
                headers=auth_header,
            )

        assert (
            node := await db.Node.find_one()
        ) and node.state == NodeState.READY, "Invalid state when handling all alert"


class TestAlertInfo:
    endpoint = "/api/alert/info"

    # Test get info alert without query args
    def test_get_info_no_args(self, app_client: TestClient, auth_header):
        response = app_client.get(self.endpoint, headers=auth_header)

        assert (
            response.status_code == 422
        ), "Invalid response code when submitting bad request"

    # Test get info of non-existing alert
    def test_get_info_non_existing_alert(self, app_client: TestClient, auth_header):
        response = app_client.get(
            self.endpoint + "?alertID=63186eab0ca2d54a5c258384",
            headers=auth_header,
        )

        assert (
            response.status_code == 404
        ), "Invalid response code when querying infos of non-existing alert"

    # Test get info
    @pytest.mark.asyncio
    async def test_get_info_alert(self, app_client: TestClient, auth_header):
        org = db.Organization(organizationName="foo")
        await org.save()
        app = db.Application(applicationName="bar", organization=org.id)
        await app.save()
        node = db.Node(
            nodeID=123,
            nodeName="nodeName",
            application=app.id,
            state=NodeState.ALERT_READY,
            lastSeenAt=datetime.now(),
        )
        await node.save()
        reading = db.Reading(
            node=node.id,
            canID=1,
            sensorNumber=2,
            readingID=32704,
            sessionID=12892,
            publishedAt=datetime.now(),
        )
        await reading.save()
        # Done setup

        reading = await db.Reading.find_one()
        assert reading
        node = await db.Node.get(reading.node)
        assert node

        # Manually create Alerts
        alert = db.Alert(
            reading=reading.id,
            node=node.id,
            sessionID=reading.sessionID,
            isHandled=False,
            raisedAt=datetime.now(),
        )
        await alert.save()

        response = app_client.get(
            self.endpoint + f"?alertID={str(alert.id)}", headers=auth_header
        )

        assert (
            response.status_code == 200
        ), "Invalid response code when querying infos of extisting alert"

        for key in [
            "canID",
            "readingID",
            "nodeID",
            "alertID",
            "sessionID",
            "raisedAt",
        ]:
            assert key in response.json(), "Invalid response structure"
