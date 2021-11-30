import hassapi as hass

#
# Garage freeze
# Start the pipe heat resistors when temperature is too cold, stop when heat is OK.
#
# Cases:
#
# Temperature | Switch # 
#----------------------#
# <= min      | "on"   #
# > min       | "off"  #
#
# Args:
#
# min_temperature = input_number, temperature threshold to trigger the resistors switch (inclusive)
# temperature_sensor = sensor entity, out temperature sensor
# resistor_switchs = switch entity list, switch to toggle
#

class GarageFreeze(hass.Hass):
    def initialize(self):
        self.min = self.get_state(self.args["min_temperature"], attribute="min")
        self.listen_state(self.min_temperature_changed, self.args["min_temperature"], immediate=True)
        self.listen_state(self.on_change, self.args["temperature_sensor"], immediate=True)

    def min_temperature_changed(self, entity, attribute, old, new, kwargs):
        self.min = float(new)
        self.log("Resistors will be started when temperature <= {} and stopped when above.".format(self.min))
        self.handle_change()

    def on_change(self, entity, attribute, old, new, kwargs):
        self.handle_change()

    def handle_change(self):
        new = self.get_state(self.args["temperature_sensor"])
        if new != None:
            should_enable = float(new) <= self.min
    
            new_state = None
            if should_enable == True:
                new_state = "on"
            elif should_enable == False:
                new_state = "off"
    
            if new_state != None:
                for resistor_switch in self.split_device_list(self.args["resistor_switchs"]):
                    old_state = self.get_state(resistor_switch)
                    if old_state != new_state:
                        self.log("Turn {} {}".format(resistor_switch, new_state))
                        if new_state == "on":
                            self.turn_on(resistor_switch)
                        else:
                            self.turn_off(resistor_switch) 
        