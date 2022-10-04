from datetime import datetime

import requests

from ..database import Reading
from .config import config


# Conversione reading per mobius
def to_mobius_payload(reading: Reading, sensorId: str) -> dict:
    return {
        "m2m:cin": {
            "con": {
                "metadata": {
                    "sensorId": sensorId,
                    "readingTimestamp": datetime.fromtimestamp(
                        reading["readingID"]
                    ).isoformat(),
                    # "latitude": <latitudine del sensore>, // opzionale
                    # "longitude": <longitudine del sensore>, // opzionale
                    # "heading": <orientazione del sensore>, // opzionale
                }
            },
            "sensorData": {
                "canID": reading["canID"],
                "sensorNumber": reading["sensorNumber"],
                "dangerLevel": reading["dangerLevel"],
                "window1Count": reading["window1_count"],
                "window2Count": reading["window2_count"],
                "window3Count": reading["window3_count"],
            },
        }
    }


def insert(reading: Reading):
    sensorId = config.nodeID_to_sensorId(reading["nodeID"])
    sensorPath = config.nodeID_to_sensorPath(reading["nodeID"])
    originator = config.originator

    mobius_payload: dict = to_mobius_payload(reading, sensorId)

    requests.post(
        f"{config.host}:{config.port}/{sensorPath}",
        headers={
            "X-M2M-Origin": originator,
            "Content-Type": "application/vnd.onem2m-res+json;ty=4",
            "X-M2M-RI": int(datetime.now().timestamp() * 1000),
        },
        json=mobius_payload,
    )
