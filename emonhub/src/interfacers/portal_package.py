import datetime

class PortalPackage:
    datasource_name = ''
    timestamp = 0
    value = None
    unit = ''

    WATTHOUR = 'Wh'
    WATT = 'W'
    SECOND = 'sec'
    CELSIUS = 'C'
    PULSE = 'p'


    VALUE_TO_BASEVALUE_MULTIPLIERS = {
        WATTHOUR: 1000,
        WATT: 1000,
        SECOND: 1,
        CELSIUS: 273.15,
        PULSE: 1,
    }

    UNIT_TO_BASEUNIT = {
        WATTHOUR: 'milliwatt*hour',
        WATT: 'milliwatt',
        SECOND: 'impulse',
        CELSIUS: 'millikelvin',
        PULSE: 'impulse',
    }

    def __init__(self, datasource_name, timestamp, value, unit):
        self.datasource_name = datasource_name
        self.timestamp = datetime.datetime.fromtimestamp(timestamp)

        if value > 0 or value < 0:
            if unit == self.CELSIUS:
                self.value = int((value + PortalPackage.VALUE_TO_BASEVALUE_MULTIPLIERS[unit]) * 1000)
            else:
                self.value = int(value * PortalPackage.VALUE_TO_BASEVALUE_MULTIPLIERS[unit])
        else:
            self.value = int(value)

        self.unit = PortalPackage.UNIT_TO_BASEUNIT[unit]