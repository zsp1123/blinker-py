import sys
import json
import time as _time
import socket
import threading
from Blinker.BlinkerConfig import *
from Blinker.BlinkerDebug import *
from BlinkerUtility.BlinkerUtility import *
# from BlinkerAdapters.BlinkerBLE import *
# from BlinkerAdapters.BlinkerLinuxWS import *
# from BlinkerAdapters.BlinkerMQTT import *
# from threading import Thread
# from zeroconf import ServiceInfo, Zeroconf
# from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

class Protocol():
    proto1 = None
    proto2 = None
    conn1 = None
    conn2 = None
    conType = BLINKER_WIFI
    state = CONNECTING
    isAvail = False
    isRead = False
    isThreadStart = False
    msgBuf = ""
    msgFrom = None
    Buttons = {}
    Sliders = {}
    Toggles = {}
    Joystick = [BLINKER_JOYSTICK_VALUE_DEFAULT, BLINKER_JOYSTICK_VALUE_DEFAULT]
    Ahrs = [0, 0, 0, False]
    GPS = ["0.000000", "0.000000"]
    RGB = {}
    debug = BLINKER_DEBUG
    thread = None
    isFormat = False
    sendBuf = {}

bProto = Protocol()

def setMode(setType = BLINKER_WIFI):
    bProto.conType = setType
    if bProto.conType == BLINKER_BLE:
        import BlinkerAdapters.BlinkerBLE as bBLE

        bProto.proto1 = bBLE
        bProto.conn1 = bProto.proto1.BlinkerBLEService()
    elif bProto.conType == BLINKER_WIFI:
        import BlinkerAdapters.BlinkerLinuxWS as bWS

        bProto.proto1 = bWS
        bProto.conn1 = bProto.proto1.WebSocketServer()
    elif bProto.conType == BLINKER_MQTT:
        import BlinkerAdapters.BlinkerLinuxWS as bWS
        import BlinkerAdapters.BlinkerMQTT as bMQTT

        bProto.proto1 = bMQTT
        bProto.proto2 = bWS
        bProto.conn1 = bProto.proto1.MQTTClient()
        bProto.conn2 = bProto.proto2.WebSocketServer(BLINKER_DIY_MQTT)

def debugLevel(level = BLINKER_DEBUG):
    bProto.debug = level

def begin(auth = None):
    if bProto.conType == BLINKER_BLE:
        # return
        bProto.proto1.bleProto.debug = bProto.debug
        # bProto.conn1.run()
        bProto.conn1.start()
    elif bProto.conType == BLINKER_WIFI:
        bProto.proto1.wsProto.debug = bProto.debug
        bProto.conn1.start()
    elif bProto.conType == BLINKER_MQTT:
        bProto.proto1.mProto.debug = bProto.debug
        bProto.proto2.wsProto.debug = bProto.debug
        bProto.msgFrom = BLINKER_MQTT
        bProto.conn1.start(auth)
        bProto.conn2.start(bProto.proto1.mProto.deviceName[0: 12])
        bProto.conn1.run()

def thread_run():
    if bProto.conType == BLINKER_BLE:
        bProto.conn1.run()
    while True:
        checkData()

def checkData():
    if bProto.conType == BLINKER_BLE:
        # return
        bProto.state = bProto.proto1.bleProto.state
        if bProto.proto1.bleProto.isRead is True:
            bProto.msgBuf = bProto.proto1.bleProto.msgBuf
            bProto.isRead = True
            bProto.proto1.bleProto.isRead = False
            parse()
    elif bProto.conType == BLINKER_WIFI:
        bProto.state = bProto.proto1.wsProto.state
        if bProto.proto1.wsProto.isRead is True:
            bProto.msgBuf = str(bProto.proto1.wsProto.msgBuf)
            bProto.isRead = True
            bProto.proto1.wsProto.isRead = False
            parse()
    elif bProto.conType == BLINKER_MQTT:
        bProto.state = bProto.proto1.mProto.state
        if bProto.proto2.wsProto.state is CONNECTED:
            bProto.state = bProto.proto2.wsProto.state
        if bProto.proto1.mProto.isRead is True:
            bProto.msgBuf = bProto.proto1.mProto.msgBuf
            bProto.msgFrom = BLINKER_MQTT
            bProto.isRead = True
            bProto.proto1.mProto.isRead = False
            parse()
        if bProto.proto2.wsProto.isRead is True:
            bProto.msgBuf = str(bProto.proto2.wsProto.msgBuf)
            bProto.msgFrom = BLINKER_WIFI
            bProto.isRead = True
            bProto.proto2.wsProto.isRead = False
            parse()

def run():
    if bProto.isThreadStart is False:
        bProto.thread = threading.Thread(target=thread_run)
        bProto.thread.daemon = True
        bProto.thread.start()
        bProto.isThreadStart = True
    checkData()
    

def wInit(name, wType):
    if wType == W_BUTTON:
        if name in bProto.Buttons:
            return
        else:
            bProto.Buttons[name] = BLINKER_CMD_BUTTON_RELEASED
        # BLINKER_LOG(bProto.Buttons)

    elif wType == W_SLIDER:
        if name in bProto.Sliders:
            return
        else:
            bProto.Sliders[name] = 0
        # BLINKER_LOG(bProto.Sliders)

    elif wType == W_TOGGLE:
        if name in bProto.Toggles:
            return
        else:
            bProto.Toggles[name] = False

    elif wType == W_RGB:
        if name in bProto.RGB:
            return
        else:
            rgb = [0, 0, 0]
            bProto.RGB[name] = rgb
        BLINKER_LOG(bProto.Toggles)

def beginFormat():
    bProto.isFormat = True
    bProto.sendBuf.clear()

def endFormat():
    bProto.isFormat = False
    _print(bProto.sendBuf)
    return checkLength(bProto.sendBuf)

def checkLength(data):
    if len(data) > BLINKER_MAX_SEND_SIZE:
        BLINKER_ERR_LOG('SEND DATA BYTES MAX THAN LIMIT!')
        return False
    else:
        return True

def _print(data):
    if checkLength(data) is False:
        return
    
    if bProto.conType == BLINKER_BLE:
        bProto.conn1.response(data)
    elif bProto.conType == BLINKER_WIFI:
        bProto.conn1.broadcast(data)
    elif bProto.conType == BLINKER_MQTT and bProto.msgFrom == BLINKER_MQTT:
        if BLINKER_CMD_NOTICE in data:
            _state = True
        elif BLINKER_CMD_STATE in data:
            _state = True
        else:
            _state = False
        bProto.conn1.pub(data, _state)
    elif bProto.conType == BLINKER_MQTT and bProto.msgFrom == BLINKER_WIFI:
        bProto.conn2.broadcast(data)

    _parse(data)

def print(key, value = None, uint = None):

    if value is None:
        if bProto.isFormat:
            return
        data = str(key)
    else:
        key = str(key)
        if not uint is None:
            value = str(value) + str(uint)
        # data = json_encode(key, value)
        data = {}
        if bProto.isFormat:
            bProto.sendBuf[key] = value
        else:
            data[key] = value

    if bProto.isFormat is False:
        _print(data)

    # if bProto.conType == BLINKER_BLE:
    #     # return
    #     if value is None:
    #         data = str(key)
    #     else:
    #         key = str(key)
    #         if not uint is None:
    #             value = str(value) + str(uint)
    #         # data = json_encode(key, value)
    #         data[key] = value

    #     if len(data) > BLINKER_MAX_SEND_SIZE:
    #         BLINKER_ERR_LOG('SEND DATA BYTES MAX THAN LIMIT!')
    #         return

    #     bProto.conn1.response(data)
    # elif bProto.conType == BLINKER_WIFI:
    #     if value is None:
    #         data = str(key)
    #     else:
    #         key = str(key)
    #         if not uint is None:
    #             value = str(value) + str(uint)
    #         # data = json_encode(key, value)
    #         data[key] = value

    #     if len(data) > BLINKER_MAX_SEND_SIZE:
    #         BLINKER_ERR_LOG('SEND DATA BYTES MAX THAN LIMIT!')
    #         return

    #     bProto.conn1.broadcast(data)
    # elif bProto.conType == BLINKER_MQTT and bProto.msgFrom == BLINKER_MQTT:
    #     notify_state = (key == BLINKER_CMD_NOTICE)
    #     BLINKER_ERR_LOG('key is:', key)
    #     BLINKER_ERR_LOG('notify_state is:', notify_state)
    #     if value is None:
    #         data = str(key)
    #     else:
    #         key = str(key)
    #         if not uint is None:
    #             value = str(value) + str(uint)
    #         data = {}
    #         data[key] = value

    #     if len(data) > BLINKER_MAX_SEND_SIZE:
    #         BLINKER_ERR_LOG('SEND DATA BYTES MAX THAN LIMIT!')
    #         return

    #     bProto.conn1.pub(data, notify_state)
    # elif bProto.conType == BLINKER_MQTT and bProto.msgFrom == BLINKER_WIFI:
    #     if value is None:
    #         data = str(key)
    #     else:
    #         key = str(key)
    #         if not uint is None:
    #             value = str(value) + str(uint)
    #         # data = json_encode(key, value)
    #         data[key] = value

    #     if len(data) > BLINKER_MAX_SEND_SIZE:
    #         BLINKER_ERR_LOG('SEND DATA BYTES MAX THAN LIMIT!')
    #         return

    #     bProto.conn2.broadcast(data)

def notify(msg):
    print(BLINKER_CMD_NOTICE, msg)

def connected():
    if bProto.state is CONNECTED:
        return True
    else:
        return False 

def connect(timeout = BLINKER_STREAM_TIMEOUT):
    bProto.state = CONNECTING
    start_time = millis()
    while (millis() - start_time) < timeout:
        run()
        if bProto.state is CONNECTED:
            return True
    return False

def disconnect():
    bProto.state = DISCONNECTED

def delay(ms):
    start = millis()
    time_run = 0
    while time_run < ms:
        run()
        time_run = millis() - start

def available():
    return bProto.isAvail

def readString():
    bProto.isRead = False
    bProto.isAvail = False
    return bProto.msgBuf

def times():
    return now()

def parse():
    data = bProto.msgBuf
    if data is '':
        return
    if check_json_format(data):
        data = json.loads(data)
        for key in data.keys():
            # BLINKER_LOG(key)
            if key in bProto.Buttons:
                # bProto.isAvail = False
                bProto.isRead = False
                if data[key] == BLINKER_CMD_BUTTON_TAP:
                    bProto.Buttons[key] = BLINKER_CMD_BUTTON_TAP
                elif data[key] == BLINKER_CMD_BUTTON_PRESSED:
                    bProto.Buttons[key] = BLINKER_CMD_BUTTON_PRESSED
                else:
                    bProto.Buttons[key] = BLINKER_CMD_BUTTON_RELEASED
                # if data[key] 
                # BLINKER_LOG(bProto.Buttons)

            elif key in bProto.Sliders:
                # bProto.isAvail = False
                bProto.isRead = False
                bProto.Sliders[key] = data[key]
                # BLINKER_LOG(bProto.Buttons)

            elif key in bProto.Toggles:
                # bProto.isAvail = False
                bProto.isRead = False
                if data[key] == BLINKER_CMD_ON:
                    bProto.Toggles[key] = True
                else:
                    bProto.Toggles[key] = False
                # BLINKER_LOG(bProto.Toggles)

            elif key in bProto.RGB:
                bProto.isRead = False
                rgb = [0, 0, 0]
                rgb[R] = data[key][R]
                rgb[G] = data[key][G]
                rgb[B] = data[key][B]
                bProto.RGB[key] = rgb
            
            elif key == BLINKER_CMD_JOYSTICK:
                # bProto.isAvail = False
                bProto.isRead = False
                bProto.Joystick[J_Xaxis] = data[key][J_Xaxis]
                bProto.Joystick[J_Yaxis] = data[key][J_Yaxis]
                # BLINKER_LOG(bProto.Joystick)

            elif key == BLINKER_CMD_AHRS:
                # bProto.isAvail = False
                bProto.isRead = False
                bProto.Ahrs[Yaw] = data[key][Yaw]
                bProto.Ahrs[Pitch] = data[key][Pitch]
                bProto.Ahrs[Roll] = data[key][Roll]
                bProto.Ahrs[AHRS_state] = True
                # BLINKER_LOG(bProto.Ahrs)

            elif key == BLINKER_CMD_GPS:
                bProto.isRead = False
                bProto.GPS[LONG] = str(data[key][LONG])
                bProto.GPS[LAT] = str(data[key][LAT])

            elif key == BLINKER_CMD_GET and data[key] == BLINKER_CMD_VERSION:
                bProto.isRead = False
                print(BLINKER_CMD_VERSION, BLINKER_VERSION)

            elif key == BLINKER_CMD_GET and data[key] == BLINKER_CMD_STATE:
                bProto.isRead = False
                heartbeat()

        if bProto.isRead:
            bProto.isAvail = True
        # BLINKER_LOG(data.keys())
    else:
        if bProto.isRead:
            bProto.isAvail = True
        return

def _parse(data):
    if data is '':
        return
    if check_json_format(data):
        data = json.loads(data)
        for key in data.keys():
            # BLINKER_LOG(key)
            if key in bProto.Buttons:
                # bProto.isAvail = False
                bProto.isRead = False
                if data[key] == BLINKER_CMD_BUTTON_TAP:
                    bProto.Buttons[key] = BLINKER_CMD_BUTTON_TAP
                elif data[key] == BLINKER_CMD_BUTTON_PRESSED:
                    bProto.Buttons[key] = BLINKER_CMD_BUTTON_PRESSED
                else:
                    bProto.Buttons[key] = BLINKER_CMD_BUTTON_RELEASED
                # if data[key] 
                # BLINKER_LOG(bProto.Buttons)

            elif key in bProto.Sliders:
                # bProto.isAvail = False
                bProto.isRead = False
                bProto.Sliders[key] = data[key]
                # BLINKER_LOG(bProto.Buttons)

            elif key in bProto.Toggles:
                # bProto.isAvail = False
                bProto.isRead = False
                if data[key] == BLINKER_CMD_ON:
                    bProto.Toggles[key] = True
                else:
                    bProto.Toggles[key] = False
                # BLINKER_LOG(bProto.Toggles)

            elif key in bProto.RGB:
                bProto.isRead = False
                rgb = [0, 0, 0]
                rgb[R] = data[key][R]
                rgb[G] = data[key][G]
                rgb[B] = data[key][B]
                bProto.RGB[key] = rgb

def heartbeat():
    if bProto.conType is BLINKER_MQTT:
        beginFormat()
        print(BLINKER_CMD_STATE, BLINKER_CMD_ONLINE)
        stateData()
        if endFormat() is False:
            print(BLINKER_CMD_STATE, BLINKER_CMD_ONLINE)
    else:
        beginFormat()
        print(BLINKER_CMD_STATE, BLINKER_CMD_CONNECTED)
        stateData()
        if endFormat() is False:
            print(BLINKER_CMD_STATE, BLINKER_CMD_CONNECTED)

def stateData():
    for tKey in bProto.Toggles:
        tValue = ''
        if bProto.Toggles[tKey]:
            tValue = 'on'
        else:
            tValue = 'off'
        print(tKey, tValue)
    for sKey in bProto.Sliders:
        print(sKey, bProto.Sliders[sKey])
    for rgbKey in bProto.RGB:
        print(rgbKey, bProto.RGB[rgbKey])


def button(name):
    if not name in bProto.Buttons:
        wInit(name, W_BUTTON)
        run()

    if bProto.Buttons[name] is BLINKER_CMD_BUTTON_RELEASED:
        return False
    
    if bProto.Buttons[name] is BLINKER_CMD_BUTTON_TAP:
        bProto.Buttons[name] = BLINKER_CMD_BUTTON_RELEASED
    return True

def slider(name):
    if name in bProto.Sliders:
        return bProto.Sliders[name]
    else:
        wInit(name, W_SLIDER)
        run()
        return bProto.Sliders[name]

def toggle(name):
    if name in bProto.Toggles:
        return bProto.Toggles[name]
    else:
        wInit(name, W_TOGGLE)
        run()
        return bProto.Toggles[name]

def rgb(name, color):
    if name in bProto.RGB:
        return bProto.RGB[name][color]
    else:
        wInit(name, W_RGB)
        run()
        return bProto.RGB[name][color]

def joystick(axis):
    if axis >= J_Xaxis and axis <= J_Yaxis:
        return bProto.Joystick[axis]
    else:
        return BLINKER_JOYSTICK_VALUE_DEFAULT

def ahrs(axis):
    if axis >= Yaw and axis <= Roll:
        return bProto.Ahrs[axis]
    else:
        return 0

def attachAhrs():
    state = False
    while connected() is False:
        connect()
    print(BLINKER_CMD_AHRS, BLINKER_CMD_ON)
    delay(100)
    run()
    start_time = millis()
    state = bProto.Ahrs[AHRS_state]
    while state is False:
        if (millis() - start_time) > BLINKER_CONNECT_TIMEOUT_MS:
            BLINKER_LOG("AHRS attach failed...Try again")
            start_time = millis()
            print(BLINKER_CMD_AHRS, BLINKER_CMD_ON)
            delay(100)
            run()
        state = bProto.Ahrs[AHRS_state]
    BLINKER_LOG("AHRS attach sucessed...")

def detachAhrs():
    print(BLINKER_CMD_AHRS, BLINKER_CMD_OFF)
    bProto.Ahrs[Yaw] = 0
    bProto.Ahrs[Roll] = 0
    bProto.Ahrs[Pitch] = 0
    bProto.Ahrs[AHRS_state] = False

def gps(axis):
    print(BLINKER_CMD_GET, BLINKER_CMD_GPS)
    delay(100)
    run()
    if axis >= LONG and axis <= LAT:
        return bProto.GPS[axis]
    else:
        return "0.000000"

def vibrate(time = 200):
    if time > 1000:
        time = 1000
    print(BLINKER_CMD_VIBRATE, time)

def time():
    return _time.time()

def second():
    localtime = _time.localtime(_time.time())
    return localtime.tm_sec

def minute():
    localtime = _time.localtime(_time.time())
    return localtime.tm_min

def hour():
    localtime = _time.localtime(_time.time())
    return localtime.tm_hour

def mday():
    localtime = _time.localtime(_time.time())
    return localtime.tm_mday

def wday():
    localtime = _time.localtime(_time.time())
    return (localtime.tm_wday + 1) % 7

def month():
    localtime = _time.localtime(_time.time())
    return localtime.tm_mon

def year():
    localtime = _time.localtime(_time.time())
    return localtime.tm_year

def yday():
    localtime = _time.localtime(_time.time())
    return localtime.tm_yday

def dtime():
    localtime = _time.localtime(_time.time())
    return localtime.tm_hour * 60 * 60 + localtime.tm_min * 60 + localtime.tm_sec

def sms(sms_msg):
    if bProto.conType == BLINKER_MQTT:
        bProto.conn1.sendSMS(sms_msg)
    else:
        BLINKER_ERR_LOG('This code is intended to run on the MQTT!')