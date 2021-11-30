import hassapi as hass
import datetime

#
# Handle home alarm
#
# Scenarios:
#
# Persons | Presence in   | Presence in | Alarm mode #
# at home | isolated room | other rooms |            #
#----------------------------------------------------#
# 0       | *             | *           | away       #
# 1+      | 0             | 1           | home|night #
# 1+      | 1             | 0           | isolated   #
# 1+      | 1             | 1           | home|night #
#
# Args:
#
# presence_in_isolated_rooms_inputs = input_boolean entity list, entities used to detect if someone is in the isolated rooms
# presence_in_other_rooms_inputs = input_boolean entity list, presence in other rooms, if none given, check that number of person at home > isolated room count
# state_away = string, state expected when away
# state_disarmed = string, state expected when disarmed
# state_home = string, state expected when at home
# state_night = string, state expected when at home, night
# state_isolated = string, state expected when someone is in the isolated room
# service_away = string, hass service to call to set alarm on away mode
# service_home = string, hass service to call to set alarm on home mode
# service_night = string, hass service to call to set alarm on night mode
# service_isolated = string, hass service to call to set alarm on isolated mode
# night_mode_start_at = input_datetime entity, time when night mode should be started
# night_mode_end_at = input_datetime entity, time when night mode should be stopped

# TODO: handle manual change (go out of home before start time, someone stays at home, should be disabled to prevent alarm when opening the door)
# TODO: delete duplicate code for presence etc

class HomeAlarm(hass.Hass):
    def initialize(self):
        self.handle_start_at = None
        self.handle_end_at = None

        self.listen_state(self.on_change_time, self.args["night_mode_start_at"])
        self.listen_state(self.on_change_time, self.args["night_mode_end_at"], immediate=True)

        for person in self.get_state("person"):
            self.listen_state(self.on_change, person)

        other_rooms = self.args["presence_in_other_rooms_inputs"]
        if other_rooms != None:
            for room in self.split_device_list(other_rooms):
                self.listen_state(self.on_change, room)

        isolated_rooms = self.split_device_list(self.args["presence_in_isolated_rooms_inputs"])
        for room in isolated_rooms:
            self.listen_state(self.on_change, room, immediate=(room == isolated_rooms[-1]))

    def on_change_time(self, entity, attribute, old, new, kwargs):
        if self.handle_start_at != None:
            self.cancel_timer(self.handle_start_at)
        
        start_at = self.get_state(self.args["night_mode_start_at"])
        self.handle_start_at = self.run_daily(self.on_cron, start_at)

        if self.handle_end_at != None:
            self.cancel_timer(self.handle_end_at)
        
        end_at = self.get_state(self.args["night_mode_end_at"])
        self.handle_end_at = self.run_daily(self.on_cron, end_at)


    def on_cron(self, kwargs):
        self.handle_change()

    def on_change(self, entity, attribute, old, new, kwargs):
        self.handle_change()

    def handle_change(self):
        is_someone_at_home = self.is_someone_at_home()
        
        new_panel_state = None
        service_to_call = None
        if is_someone_at_home == False:
            new_panel_state = self.args["state_away"]
            service_to_call = self.args["service_away"]
        else:
            # Default state at home
            new_panel_state = self.args["state_home"]
            service_to_call = self.args["service_home"]

            # Handle isolated
            is_someone_in_other_rooms = self.is_someone_in_other_rooms()
            is_someone_in_isolated_rooms = self.is_someone_in_isolated_rooms()
            if is_someone_in_isolated_rooms and is_someone_in_other_rooms == False:
                new_panel_state = self.args["state_isolated"]
                service_to_call = self.args["service_isolated"]

            # Handle night
            if new_panel_state == self.args["state_home"] and self.is_night():
                new_panel_state = self.args["state_night"]
                service_to_call = self.args["service_night"]
        
        self.change_panel_state(new_panel_state, service_to_call)

    def change_panel_state(self, new_state, service_to_call):
        if new_state != None and service_to_call != None:
            panels_to_change = []
            for alarm_panel in self.get_state("alarm_control_panel"):
                is_panel_with_right_state = self.get_state(alarm_panel) == new_state
                if is_panel_with_right_state == False:
                    panels_to_change.append(alarm_panel)
                    self.log("{} will be turned in \"{}\" mode".format(alarm_panel, new_state))
            
            if len(panels_to_change) > 0:
                self.call_service(service_to_call, entity_id=panels_to_change)

    def is_someone_at_home(self):
        persons = self.get_state("person")
        for person in persons:
            is_at_home = self.get_state(person) == "home"
            if is_at_home:
                return True

        return False

    def is_someone_in_isolated_rooms(self):
        for room in self.split_device_list(self.args["presence_in_isolated_rooms_inputs"]):
            is_in_room = self.get_state(room) == "on"
            if is_in_room:
                return True
        
        return False

    def is_someone_in_other_rooms(self):
        other_rooms = self.args["presence_in_other_rooms_inputs"]
        if other_rooms != None:
            for room in self.split_device_list(other_rooms):
                is_in_room = self.get_state(room) == "on"
                if is_in_room:
                    return True
        else:
            persons = self.get_state("person")
            person_count = 0
            for person in persons:
                is_at_home = self.get_state(person) == "home"
                if is_at_home:
                    person_count += 1

            isolated_rooms = self.split_device_list(self.args["presence_in_isolated_rooms_inputs"])
            isolated_rooms_presence_count = 0
            for room in isolated_rooms:
                is_in_room = self.get_state(room) == "on"
                if is_in_room:
                    isolated_rooms_presence_count += 1

            return person_count > isolated_rooms_presence_count
        return False

    def is_night(self):
        start_at = self.get_state(self.args["night_mode_start_at"])
        end_at = self.get_state(self.args["night_mode_end_at"])
        return self.now_is_between(start_at, end_at)