from flask_socketio import SocketIO, SocketIOTestClient
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.test import TestResponse
from mock import patch
from microservice_websocket_docker import app as websocket_app
import pytest
import json
from fixtures.data_fixtures import *


class TestFlaskApp:

    @pytest.fixture()
    def app_socketio(self) -> tuple[Flask, SocketIO]: # type: ignore

        with patch('microservice_websocket_docker.app.DISABLE_MQTT', True):
            app, socketio = websocket_app.create_app()

        app.config.update({
            "TESTING": True,
        })
        # set up
        yield app, socketio
        # clean up

    @pytest.fixture()
    def app_client(self, app_socketio: tuple[Flask, SocketIO]) -> FlaskClient:
        app, _ = app_socketio
        return app.test_client()

    @pytest.fixture()
    def socketio_client(
            self,
            app_socketio: tuple[Flask, SocketIO],
            app_client: FlaskClient) -> SocketIOTestClient:
        app, socketio = app_socketio
        return socketio.test_client(app, flask_test_client=app_client)

    @patch('microservice_websocket_docker.app.MOBIUS_URL', "")
    def test_publish_route_post(
            self,
            app_client,
            sensorData_Uplink,
            sensorData_noUplink):

        response: TestResponse = app_client.post("/publish", json=sensorData_Uplink)
        decoded_json: dict = json.loads(response.data)
        payload: dict = websocket_app.to_mobius_payload(sensorData_Uplink)

        print("[DEBUG] Original data: ")
        print(payload)
        print("===========================")
        print("[DEBUG] Data received back from post request: ")
        print(decoded_json)
        assert decoded_json == payload, \
        "Output mismatch when posting valida data. Check stdout log."

        response: TestResponse = app_client.post("/publish", json=sensorData_noUplink)
        decoded_json: dict = json.loads(response.data)
        assert not decoded_json, \
        "Wrong response from post request: should be empty, but it's not"

    @patch('microservice_websocket_docker.app.MOBIUS_URL', "")
    def test_main_route_post(self, app_client: FlaskClient, sensorData_Uplink):
        
        body = {
            "paths": [sensorData_Uplink["tags"]["sensor_path"]],
        }

        response: TestResponse = app_client.post("/", json=body)
        decoded_json: dict = json.loads(response.data)
        assert "data" in decoded_json, "Invalid json from '/' route"
        devices: list = decoded_json["data"]
        assert len(devices) == len(body["paths"]), \
        "Invalid number of devices in json from '/' route"

    @patch('microservice_websocket_docker.app.MOBIUS_URL', "")
    def test_socketio_emits_on_change(
            self,
            app_client: FlaskClient,
            socketio_client: SocketIOTestClient,
            sensorData_Uplink: dict):
        app_client.post("/publish", json=sensorData_Uplink)
        received: list = socketio_client.get_received()
        assert received[0]['name'] == 'change', \
        "Invalid response from socket 'onChange()'"
    
    @patch('microservice_websocket_docker.app.MOBIUS_URL', "")
    def test_get_data(self):
        s: dict = websocket_app.get_data("", "")
        print(f"{s=}")
        assert all(key in s for key in [
                "devEUI",
                "applicationID",
                "state",
                "datiInterni"
            ]) and len(s["datiInterni"]) == 3, \
        "Invalid structure of returned json: doesn't match `to_irma_ui_data()` \
        function, in `data_conversion.py`. Check stdout log."


def test_get_state():
    dato: int = 0
    assert websocket_app.get_state(dato) == websocket_app.State.OFF, \
    "Error in `get_state()` with dato == 0: output mismatch"

    dato = websocket_app.MAX_TRESHOLD-1
    assert websocket_app.get_state(dato) == websocket_app.State.OK, \
    "Error in `get_state()` with dato < MAX_TRESHOLD: output mismatch"

    dato = websocket_app.MAX_TRESHOLD+1
    assert websocket_app.get_state(dato) == websocket_app.State.ALERT, \
    "Error in `get_state()` with dato >= MAX_TRESHOLD: output mismatch"


def test_get_month(isoTimestamp):
    assert websocket_app.get_month(isoTimestamp) == 3, \
    "Error in `get_month()`: output mismatch when providin ISO8601 datetime"

    with pytest.raises(ValueError):
        websocket_app.get_month("1-0")


def test_get_sensorData():
    data: str = '{"sensorData": 123}'
    assert websocket_app.get_sensorData(data) == 123, \
    "Error in `get_sensorData()`: output mismatch when providing right input"

    data: str = '{"sensorData": 1-0}'
    with pytest.raises(ValueError):
        websocket_app.get_sensorData(data)

    data: str = '{"foo": "bar"}'
    with pytest.raises(KeyError):
        websocket_app.get_sensorData(data)




def test_to_mobius_payload(sensorData_Uplink: dict):
    """
    Coherence test for to_mobius_payload() function
    """

    expected_value = {
        "m2m:cin": {
            "con": {
                "metadata": {
                    "sensorId": sensorData_Uplink['tags']['sensorId'],
                    "readingTimestamp": sensorData_Uplink['publishedAt'],
                    "latitude": sensorData_Uplink['rxInfo'][0]['location']['latitude'],
                    "longitude": sensorData_Uplink['rxInfo'][0]['location']['longitude'],
                }
            },
            "sensorData": sensorData_Uplink,
        }
    }

    assert websocket_app.to_mobius_payload(sensorData_Uplink) == expected_value, \
    "Error in `to_mobius_payload`: output mismatch"


def test_to_irma_ui():
    deviceEUI = "2288300834"
    applicationID = "123"
    sensorId = "FOO_bar_01"
    state = "ok"
    titolo1 = "Foo"
    titolo2 = "Bar"
    titolo3 = "Baz"
    dato1 = 0.0
    dato2 = 0.0
    dato3 = 0

    expected_value = {
        "devEUI": deviceEUI,
        "applicationID": applicationID,
        "sensorId": sensorId,
        "state": state,
        "datiInterni": [
            {
                "titolo": titolo1,
                "dato": dato1
            },
            {
                "titolo": titolo2,
                "dato": dato2
            },
            {
                "titolo": titolo3,
                "dato": dato3
            }
        ]
    }

    assert websocket_app.to_irma_ui_data(
        deviceEUI, applicationID, sensorId, state, 
        titolo1, titolo2, titolo3,
        dato1, dato2, dato3
    ) == expected_value, "Error in `to_irma_ui_data`: output mismatch"


def test_decode_devEUI(devEUI):
    assert websocket_app.decode_devEUI(devEUI) == "0202020202020202", \
    "Error in `decode_devEUI()`: output mismatch"

