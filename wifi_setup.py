import os
import wifi
import socketpool


def connect():
    ssid = os.getenv("CIRCUITPY_WIFI_SSID")
    password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
    if not ssid:
        raise RuntimeError("CIRCUITPY_WIFI_SSID missing from settings.toml")
    print("Connecting to", ssid)
    wifi.radio.connect(ssid, password)
    print("Connected, IP:", wifi.radio.ipv4_address)
    return socketpool.SocketPool(wifi.radio)
