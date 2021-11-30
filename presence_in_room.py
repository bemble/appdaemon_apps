import hassapi as hass

#
# Set presence in a room
#
# Cases:
#
# Sensor   | Presence in room #
#-----------------------------#
# off+     | 0                #
# on+,off+ | 1                #
#
# Args:
#
# room_presence_input = input_boolean entity, entity to control
# sensors = sensor entities, sensors used to detect presence in a room
#

class PresenceInRoom(hass.Hass):
    def initialize(self):
        sensors = self.split_device_list(self.args["sensors"])
        for sensor in sensors:
            self.listen_state(self.on_change, sensor, immediate=(sensor==sensors[-1]))

    def on_change(self, entity, attribute, old, new, kwargs):
        self.handle_change()

    def handle_change(self):
        sensors = self.split_device_list(self.args["sensors"])
        current_state = self.get_state(self.args["room_presence_input"])

        new_state = "off"
        for sensor in sensors:
            sensor_state = self.get_state(sensor)
            if sensor_state == "on":
                new_state = "on"
                break

        if new_state != current_state:
            self.set_state(self.args["room_presence_input"], state=new_state)