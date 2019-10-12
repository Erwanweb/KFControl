"""
CASA-IA Security system zone python plugin for Domoticz
Author: Erwanweb,
Version:    0.0.1: alpha
            0.0.2: beta
"""
"""
<plugin key="Keyfob" name="AC Keyfob control" author="Erwanweb" version="0.0.2" externallink="https://github.com/Erwanweb/KFControl.git">
    <description>
        <h2>Keyfob control for CASA-IA</h2><br/>
        Easily control system with fibaro Keyfob<br/>
        <h3>Set-up and Configuration</h3>
    </description>
    <params>
        <param field="Address" label="Domoticz IP Address" width="200px" required="true" default="127.0.0.1"/>
        <param field="Port" label="Port" width="40px" required="true" default="8080"/>
        <param field="Username" label="Username" width="200px" required="false" default=""/>
        <param field="Password" label="Password" width="200px" required="false" default=""/>
        <param field="Mode1" label="Carre (csv list of idx)" width="200px" required="false" default=""/>
        <param field="Mode2" label="Rond (csv list of idx)" width="200px" required="false" default=""/>
        <param field="Mode3" label="croix (csv list of idx)" width="200px" required="false" default=""/>
        <param field="Mode4" label="Alarm Control and Log IDX" width="200px" required="true" default=""/>
        <param field="Mode5" label="Keyfob Owner Name" width="200px" required="true" default=""/>
        <param field="Mode6" label="Logging Level" width="200px">
            <options>
                <option label="Normal" value="Normal"  default="true"/>
                <option label="Verbose" value="Verbose"/>
                <option label="Debug - Python Only" value="2"/>
                <option label="Debug - Basic" value="62"/>
                <option label="Debug - Basic+Messages" value="126"/>
                <option label="Debug - Connections Only" value="16"/>
                <option label="Debug - Connections+Queue" value="144"/>
                <option label="Debug - All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import json
import urllib.parse as parse
import urllib.request as request
from datetime import datetime, timedelta
import time
import base64
import itertools

class deviceparam:

    def __init__(self, unit, nvalue, svalue):
        self.unit = unit
        self.nvalue = nvalue
        self.svalue = svalue


class BasePlugin:

    def __init__(self):

        self.debug = False
        self.KeyfobName = "Unknow"
        self.CarreOn = False
        self.RondOn = False
        self.CroixOn = False
        self.TriangleOn = False
        self.DTPerimetral = []
        self.DTNightAlarm = []
        self.Alarmcontrol = 0
        self.Alarmlog = 0
        self.alarmstate = 0
        self.LastOrder = datetime.now()
        self.loglevel = None
        self.statussupported = True
        return


    def onStart(self):

        # setup the appropriate logging level
        try:
            debuglevel = int(Parameters["Mode6"])
        except ValueError:
            debuglevel = 0
            self.loglevel = Parameters["Mode6"]
        if debuglevel != 0:
            self.debug = True
            Domoticz.Debugging(debuglevel)
            DumpConfigToLog()
            self.loglevel = "Verbose"
        else:
            self.debug = False
            Domoticz.Debugging(0)

        # create the child devices if these do not exist yet
        devicecreated = []
        if 1 not in Devices:
            Domoticz.Device(Name="Carre", Unit=1, TypeName="Switch", Image=9, Used=1).Create()
            devicecreated.append(deviceparam(1, 0, ""))  # default is Off
        if 2 not in Devices:
            Domoticz.Device(Name="Rond", Unit=2, TypeName="Switch", Image=9, Used=1).Create()
            devicecreated.append(deviceparam(2, 0, ""))  # default is Off
        if 3 not in Devices:
            Domoticz.Device(Name="Crois", Unit=3, TypeName="Switch", Image=9, Used=1).Create()
            devicecreated.append(deviceparam(3, 0, ""))  # default is Off
        if 4 not in Devices:
            Domoticz.Device(Name="Triangle", Unit=4, TypeName="Switch", Image=9, Used=1).Create()
            devicecreated.append(deviceparam(4, 0, ""))  # default is Off
        if 5 not in Devices:
            Domoticz.Device(Name="Moins", Unit=5, TypeName="Switch", Image=9, Used=1).Create()
            devicecreated.append(deviceparam(5, 0, ""))  # default is Off
        if 6 not in Devices:
            Domoticz.Device(Name="Plus", Unit=6, TypeName="Switch", Image=9, Used=1).Create()
            devicecreated.append(deviceparam(6, 0, ""))  # default is Off

        # if any device has been created in onStart(), now is time to update its defaults
        for device in devicecreated:
            Devices[device.unit].Update(nValue=device.nvalue, sValue=device.svalue)



        # splits additional parameters for alarm control
        params = parseCSV(Parameters["Mode4"])
        if len(params) == 2:
            self.Alarmcontrol = CheckParam("Alarm Log IDX",params[0],0)
            Domoticz.Debug("Alarm Control device = {}".format(self.Alarmcontrol))
            self.Alarmlog = CheckParam("Alarm Log IDX",params[1],0)
            Domoticz.Debug("Alarm Log device = {}".format(self.Alarmlog))



    def onStop(self):

        Domoticz.Debugging(0)


    def onCommand(self, Unit, Command, Level, Color):

        Domoticz.Debug("onCommand called for Unit {}: Command '{}', Level: {}".format(Unit, Command, Level))

        if (Unit == 4):
            Devices[4].Update(nValue = 1,sValue = Devices[4].sValue)

            if Devices[1].nValue == 1:
                Devices[1].Update(nValue = 0,sValue = Devices[1].sValue)
            if Devices[2].nValue == 1:
                Devices[2].Update(nValue = 0,sValue = Devices[2].sValue)
            if Devices[3].nValue == 1:
                Devices[3].Update(nValue = 0,sValue = Devices[3].sValue)
            if Devices[5].nValue == 1:
                Devices[5].Update(nValue = 0,sValue = Devices[5].sValue)
            if Devices[6].nValue == 1:
                Devices[6].Update(nValue = 0,sValue = Devices[6].sValue)


        if (Unit == 5):
            Devices[5].Update(nValue = 1,sValue = Devices[5].sValue)

            if Devices[4].nValue == 1:
                for idx in self.Alarmlog:
                    DomoticzAPI(
                        "type=command&param=udevice&idx={}&nvalue=0&svalue=Commande alarme depuis keyfob () - Alarme Desarmee".format(
                            idx,self.KeyfobName))
                    Domoticz.Debug("updating alarm log - Alarm turned Off by Keyfob")
                for idx in self.Alarmcontrol:
                    DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=Set Level&level=10".format(idx))
                    Domoticz.Debug("Alarm turned Off by Keyfob")


        if (Unit == 6):
            Devices[6].Update(nValue = 1,sValue = Devices[6].sValue)

            if Devices[4].nValue == 1:
                for idx in self.Alarmlog:
                    DomoticzAPI(
                        "type=command&param=udevice&idx={}&nvalue=0&svalue=Commande alarme depuis keyfob () - Protection totale".format(
                            idx,self.KeyfobName))
                    Domoticz.Debug("updating alarm log - Alarm turned On by Keyfob")
                for idx in self.Alarmcontrol:
                    DomoticzAPI("type=command&param=switchlight&idx={}&switchcmd=Set Level&level=40".format(idx))
                    Domoticz.Debug("Alarm turned On by Keyfob")




    def onHeartbeat(self):

        # fool proof checking....
        if not all(device in Devices for device in (1,2,3,4,5,6)):
            Domoticz.Error("one or more devices required by the plugin is/are missing, please check domoticz device creation settings and restart !")
            return






    def WriteLog(self, message, level="Normal"):

        if self.loglevel == "Verbose" and level == "Verbose":
            Domoticz.Log(message)
        elif level == "Normal":
            Domoticz.Log(message)



global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onCommand(Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Color)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


# Plugin utility functions ---------------------------------------------------

def parseCSV(strCSV):

    listvals = []
    for value in strCSV.split(","):
        try:
            val = int(value)
        except:
            pass
        else:
            listvals.append(val)
    return listvals


def DomoticzAPI(APICall):

    resultJson = None
    url = "http://{}:{}/json.htm?{}".format(Parameters["Address"], Parameters["Port"], parse.quote(APICall, safe="&="))
    Domoticz.Debug("Calling domoticz API: {}".format(url))
    try:
        req = request.Request(url)
        if Parameters["Username"] != "":
            Domoticz.Debug("Add authentification for user {}".format(Parameters["Username"]))
            credentials = ('%s:%s' % (Parameters["Username"], Parameters["Password"]))
            encoded_credentials = base64.b64encode(credentials.encode('ascii'))
            req.add_header('Authorization', 'Basic %s' % encoded_credentials.decode("ascii"))

        response = request.urlopen(req)
        if response.status == 200:
            resultJson = json.loads(response.read().decode('utf-8'))
            if resultJson["status"] != "OK":
                Domoticz.Error("Domoticz API returned an error: status = {}".format(resultJson["status"]))
                resultJson = None
        else:
            Domoticz.Error("Domoticz API: http error = {}".format(response.status))
    except:
        Domoticz.Error("Error calling '{}'".format(url))
    return resultJson


def CheckParam(name, value, default):

    try:
        param = int(value)
    except ValueError:
        param = default
        Domoticz.Error("Parameter '{}' has an invalid value of '{}' ! defaut of '{}' is instead used.".format(name, value, default))
    return param


# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return