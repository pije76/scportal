#########################################################
#######################      emonhub.conf     #########################
#######################################################################
###
### SPECIMEN emonHub configuration file
### Note that when installed from apt, a new config file is written
### by the debian/postinst script, so changing this file will do
### nothing in and of itself.
###
### Each Interfacer and each Reporter has
### - a [[name]]: a unique string
### - a type: the name of the class it instantiates
### - a set of init_settings (depends on the type)
### - a set of runtimesettings (depends on the type)
### Both init_settings and runtimesettings sections must be defined,
### even if empty. Init settings are used at initialization,
### and runtime settings are refreshed on a regular basis.
### Many settings below are "commented out" as they are not mandatory and
### have been included as a template or to provide alternative options
### removing the leading # will enable the setting and override the default
### Default settings are shown as comments on the same line as the setting
### eg #(default:xyz) "xyz" is set if the setting is "commented out".
###
### All lines beginning with '###' are comments and can be safely removed.
###
#######################################################################
#######################    emonHub  settings    #######################
#######################################################################

[hub]

### loglevel must be one of DEBUG, INFO, WARNING, ERROR, and CRITICAL
### see here : http://docs.python.org/2/library/logging.html
loglevel = DEBUG #(default:WARNING)

#######################################################################
#######################       Interfacers       #######################
#######################################################################

[interfacers]

### This interfacer manages the RFM2Pi module
[[RFM2Pi]]
    Type = EmonHubJeeInterfacer
    [[[init_settings]]]
        com_port = /dev/ttyAMA0
        com_baud = 38400
    [[[runtimesettings]]]
        pubchannels = ToCloud,
        subchannels = ToRFM12,

        # datacode = B #(default:h)
        # scale = 100 #(default:1)
        group = 210 #(default:210)
        frequency = 433 #(default:433)
        baseid = 5 #(emonPi default:5)
        quiet = false #(default:true)
        calibration = 230V #(UK/EU: 230V, US: 110V)
        # interval = 300 #(default:0)
        # nodeoffset = 32 #(default:0)

### This interfacer manages the RFM2Pi module
[[MQTT]]

    Type = EmonHubMqttInterfacer
    [[[init_settings]]]
        mqtt_host = 127.0.0.1
        mqtt_port = 1883
        mqtt_user = emonpi
        mqtt_passwd = emonpimqtt2016

    [[[runtimesettings]]]
        pubchannels = ToRFM12,
        subchannels = ToEmonCMS,
        basetopic = emonhub/


[[scnordic]]
    Type = EmonHubSCNordicHTTPInterfacer
    [[[init_settings]]]
    [[[runtimesettings]]]
        pubchannels = ToRFM12,
        subchannels = ToCloud,
        url = https://scsmartgrid.dk/api/v3
        apikey = fd9b1def9a1cb1f5e387ab153de0332bfb0f3b48d8359ca5384b07c7c8a763eee9d9de33fde04291b8bceac354d8273ab67c3e5a

#######################################################################
#######################          Nodes          #######################
#######################################################################

[nodes]
[[5]]
    nodename = emonpi
    [[[rx]]]
        names = power1,power2,power1pluspower2********,vrms,t1,t2,t3,t4,t5,t6,pulsecount
        datacodes = h, h, h, h, h, h, h, h, h, h, L
        scales = 1,1,1,0.01,0.1,0.1,0.1,0.1,0.1,0.1,1
        units = W,W,W,V,C,C,C,C,C,C,p
        senddata = 0,0,0,0,0,0,0,0,0,0,0

[[10]]
    nodename = EMONTX10
    firmware =V120
    hardware = SC-EmonTx
    [[[rx]]]
       names = power1, power2, power3, power4, Vrms, pulse, Wh1, Wh2, Wh3, Wh4
       datacodes = h, h, h, h, h, L, l, l, l, l
       scales       = 1, 1, 1, 1, 0.01, 1, 1, 1, 1, 1
       units = W, W, W, W, V, p, Wh, Wh, Wh, Wh
       senddata = 0,0,0,0,0,0,1,1,1,1