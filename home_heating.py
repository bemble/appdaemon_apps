import hassapi as hass

#
# Handle global home heating
# Generaly, Tado geofincing works great, but I have a particular case: I have an isolated room, with its own heating system,
# and when I'm in this room and alone at home, I want my global home heating to be set on away, to prevent heating the whole home
# for nothing.
#
# Scenarios:
#
# Persons | Presence in        | Presence in | Climate modes #
# at home | isolated rooms     | other rooms |               #
#------------------------------------------------------------#
# 0       | *                  | *           | auto          #
# 1+      | 1                  | 0           | away          #
# 1+      | *                  | 1           | auto          #
#
# Args:
#
# ref_climate = climate entity, reference climate entity used for computation
# presence_in_isolated_rooms_inputs = input_boolean entity list, presence in isolated rooms
# presence_in_other_rooms_inputs = input_boolean entity list, presence in other rooms, if none given, check that number of person at home > isolated room count
#

class HomeHeating(hass.Hass):
    def initialize(self):
        for person in self.get_state("person"):
            self.listen_state(self.on_change, person)

        other_rooms = self.args["presence_in_other_rooms_inputs"]
        if other_rooms != None:
            for room in self.split_device_list(other_rooms):
                self.listen_state(self.on_change, room)

        isolated_rooms = self.split_device_list(self.args["presence_in_isolated_rooms_inputs"])
        for room in isolated_rooms:
            self.listen_state(self.on_change, room, immediate=(room == isolated_rooms[-1]))

    def on_change(self, entity, attribute, old, new, kwargs):
        self.handle_change()

    def handle_change(self):
        is_someone_at_home = self.is_someone_at_home()
        
        new_state = self.get_state(self.args["ref_climate"])
        if is_someone_at_home == False:
            new_state = "auto"
        else:
            is_someone_in_other_rooms = self.is_someone_in_other_rooms()
            is_someone_in_isolated_rooms = self.is_someone_in_isolated_rooms()
            if is_someone_in_other_rooms:
                new_state = "auto"
            elif is_someone_in_isolated_rooms:
                new_state = "away"
        
        self.change_climates_state(new_state)

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

    def change_climates_state(self, new_state):
        for climate in self.get_state("climate"):
            current_state = self.get_state(climate)
            if current_state != new_state:
                self.set_state(climate, state=new_state)