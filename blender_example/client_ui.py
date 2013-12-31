from ui import (Panel, ConsoleRenderer, System, TableRenderer,
                CENTERX, CENTERY, CENTERED, SpriteSequence)

from matchmaker import Matchmaker
from bge_network import (ConnectionErrorSignal, ConnectionSuccessSignal,
                     SignalListener, WorldInfo, ManualTimer, Timer,
                     BroadcastMessage)
from signals import (ConsoleMessage, ConnectToSignal, UIUpdateSignal,
                     UIWeaponChangedSignal)
from datetime import datetime
from functools import partial

import bge
import bgui

import uuid
import copy


def make_gradient(colour, factor, top_down=True):
    by_factor = [v * factor  if i != 3 else v for i, v in enumerate(colour)]
    result = [by_factor, by_factor, colour, colour]
    return result if top_down else list(reversed(result))


class ConnectPanel(Panel):

    def __init__(self, system):
        super().__init__(system, "Connect")

        self.aspect = bge.render.getWindowWidth() / bge.render.getWindowHeight()

        self.center_column = bgui.Frame(parent=self, name="center",
                                        size=[0.8, 0.8], options=CENTERED,
                                        sub_theme="ContentBox")

        self.connect_label = bgui.Label(parent=self.center_column,
                                        name="label", pos=[0.0, 0.025],
                                        text="Connection Wizard",
                                        options=CENTERX, sub_theme="Title")

        # IP input
        self.connection_row = bgui.Frame(parent=self.center_column,
                                         name="connection_frame",
                                         size=[0.8, 0.08], pos=[0.0, 0.85],
                                         sub_theme="ContentRow",
                                         options=CENTERX)

        self.addr_group = bgui.Frame(parent=self.connection_row,
                                     name="addr_group", size=[0.70, 1.0],
                                     pos=[0.0, 0.5], options=CENTERY,
                                     sub_theme="RowGroup")
        self.port_group = bgui.Frame(parent=self.connection_row,
                                     name="port_group", size=[0.3, 1.0],
                                     pos=[0.7, 0.5], options=CENTERY,
                                     sub_theme="RowGroup")

        self.addr_label = bgui.Label(parent=self.addr_group, name="addr_label",
                                     text="IP Address:", options=CENTERY,
                                     pos=[0.05, 0.0])
        self.port_label = bgui.Label(parent=self.port_group, name="port_label",
                                     text="Port:", options=CENTERY,
                                     pos=[0.05, 0.0])

        self.addr_field = bgui.TextInput(parent=self.addr_group,
                                         name="addr_field", size=[0.6, 1.0],
                                         pos=[0.4, 0.0], options=CENTERY,
                                         text="localhost",
                                         allow_empty=False)
        self.port_field = bgui.TextInput(parent=self.port_group,
                                         name="port_field", size=[0.6, 1.0],
                                         pos=[0.4, 0.0], options=CENTERY,
                                         type=bgui.BGUI_INPUT_INTEGER,
                                         text="1200",
                                         allow_empty=False)

        # Allows input fields to accept input when not hovered
        self.connection_row.is_listener = True

        # Data input
        self.data_row = bgui.Frame(parent=self.center_column,
                                   name="data_frame", size=[0.8, 0.08],
                                   pos=[0.0, 0.77], sub_theme="ContentRow",
                                   options=CENTERX)

        self.error_msg_group = bgui.Frame(parent=self.data_row,
                                     name="error_msg_group", size=[0.3, 1.0],
                                     pos=[0.0, 0.5], options=CENTERY,
                                     sub_theme="RowGroup")

        self.error_msg_label = bgui.Label(parent=self.error_msg_group,
                                          name="error_status",
                                          text="Connection Information:",
                                          pos=[0.0, 0.0],
                                          options=CENTERED)

        self.error_group = bgui.Frame(parent=self.data_row,
                                     name="error_group", size=[0.7, 1.0],
                                     pos=[0.3, 0.5], options=CENTERY,
                                     sub_theme="RowGroup")

        self.connect_message = bgui.Label(parent=self.error_group,
                                          name="connect_status",
                                          text="",
                                          pos=[0.0, 0.0],
                                          options=CENTERED)

        self.server_controls = bgui.Frame(parent=self.center_column,
                                   name="server_controls", size=[0.8, 0.08],
                                   pos=[0.0, 0.69], sub_theme="ContentRow",
                                   options=CENTERX)

        self.refresh_group = bgui.Frame(parent=self.server_controls,
                                     name="refresh_group", size=[0.15, 1.0],
                                     pos=[0.0, 0.5], options=CENTERY,
                                     sub_theme="RowGroup")

        self.refresh_button = bgui.FrameButton(parent=self.refresh_group,
                                               name="refresh_button",
                                               text="Update", size=[1.0, 1.0],
                                               options=CENTERED)

        self.connect_group = bgui.Frame(parent=self.server_controls,
                                     name="connect_group", size=[0.15, 1.0],
                                     pos=[0.15, 0.5], options=CENTERY,
                                     sub_theme="RowGroup")

        self.connect_button = bgui.FrameButton(parent=self.connect_group,
                                               name="connect_button",
                                               text="Connect", size=[1.0, 1.0],
                                               options=CENTERED)

        self.match_group = bgui.Frame(parent=self.server_controls,
                                     name="match_group", size=[0.7, 1.0],
                                     pos=[0.3, 0.5], options=CENTERY,
                                     sub_theme="RowGroup")
        self.match_label = bgui.Label(parent=self.match_group, name="match_label",
                                     text="Matchmaker:", options=CENTERY,
                                     pos=[0.025, 0.0])
        self.match_field = bgui.TextInput(parent=self.match_group,
                                         name="match_field", size=[0.8, 1.0],
                                         pos=[0.2, 0.0], options=CENTERY,
                                         text="http://coldcinder.co.uk/networking/matchmaker",
                                         allow_empty=False)

        self.servers_list = bgui.Frame(parent=self.center_column,
                                   name="server_list", size=[0.8, 0.6],
                                   pos=[0.0, 0.09], sub_theme="ContentRow",
                                   options=CENTERX)
        self.servers = []
        self.server_headers = ["name",
                               "map",
                               "players",
                               "max_players",
                               ]

        self.matchmaker = Matchmaker("")

        self.servers_box = bgui.ListBox(parent=self.servers_list,
                                        name="servers",
                                        items=self.servers, padding=0.0,
                                        size=[1.0, 1.0],
                                        pos=[0.0, 0.0])
        self.servers_box.renderer = TableRenderer(self.servers_box,
                                              labels=self.server_headers)

        self.sprite = SpriteSequence(self.error_group, "sprite",
                                     bge.logic.expandPath("//themes/477.tga"),
                                     length=20, loop=True,  size=[0.1, 0.6],
                                     aspect=1, relative_path=False,
                                     options=CENTERY)
        self.sprite_timer = Timer(target_value=1 / 20,
                                        repeat=True,
                                        on_target=self.sprite.next_frame)

        self.connect_button.on_click = self.do_connect
        self.refresh_button.on_click = self.do_refresh
        self.servers_box.on_select = self.on_select
        self.uses_mouse = True
        self.sprite.visible = False

    def on_select(self, list_box, entry):
        data = dict(entry)

        self.addr_field.text = data['address']
        self.port_field.text = data['port']

    def do_refresh(self, button):
        self.matchmaker.url = self.match_field.text
        self.matchmaker.perform_query(self.evaluate_servers,
                                      self.matchmaker.server_query())
        self.sprite.visible = True

    def evaluate_servers(self, response):
        self.servers[:] = [tuple(entry.items()) for entry in response]
        self.connect_message.text = ("Refreshed Server List" if self.servers
                                    else "No Servers Found")
        self.sprite.visible = False

    def do_connect(self, button):
        ConnectToSignal.invoke(self.addr_field.text, int(self.port_field.text))
        self.sprite.visible = True

    @ConnectionSuccessSignal.global_listener
    def on_connect(self, target):
        self.visible = False

    @ConnectionErrorSignal.global_listener
    def on_error(self, error, target, signal):
        self.connect_message.text = str(error)
        self.sprite.visible = False

    def update(self, delta_time):
        self.connect_button.frozen = self.port_field.invalid
        self.matchmaker.update()


class SamanthaPanel(Panel):

    def __init__(self, system):
        super().__init__(system, "Samantha_Overlay")

        aspect = bge.render.getWindowWidth() / bge.render.getWindowHeight()
        scene = system.scene

        camera = scene.objects['Samantha_Camera']

        self.video_source = bge.texture.ImageRender(scene, camera)
        self.video_source.background = 255, 255, 255, 255

        self.video = bgui.ImageRender(parent=self, name="Samantha_Video",
                                    pos=[0, 0], size=[0.2, 0.2],
                                    aspect=aspect, source=self.video_source)


class TimerMixins:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timers = []

    def add_timer(self, timer, name=""):
        def on_stop():
            timer.delete()
            self._timers.remove(timer)

        timer.on_stop = on_stop
        self._timers.append(timer)

    def update(self, delta_time):
        '''Update all active timers'''
        for timer in self._timers[:]:
            timer.update(delta_time)


class Notification(TimerMixins, bgui.Frame):
    default_size = [1.0, 0.06]

    def __init__(self, parent, message, alive_time=5.0,
                 fade_time=0.25, font_size=35, **kwargs):
        super().__init__(parent=parent,
                         name="notification_{}".format(uuid.uuid4()),
                         size=self.default_size[:],
                         **kwargs)

        thin_bar_height = 0.05
        main_bar_width = 0.985

        self.fade_time = fade_time
        self.alive_time = alive_time
        self.message = message
        self.message_length = 34

        if len(message) > self.message_length:
            message = message[:self.message_length]
            status_timer = ManualTimer(target_value=self.alive_time * 0.9)
            status_timer.on_update = partial(self.scroll_message, status_timer)
            self.add_timer(status_timer, "scroll")

        self.upper_bar = bgui.Frame(parent=self, name="upper_bar",
                                    size=[1.0, thin_bar_height],
                                    options=CENTERX,
                                    pos=[0.0, 1 - thin_bar_height])

        self.lower_bar = bgui.Frame(parent=self, name="lower_bar",
                                    size=[1.0, thin_bar_height],
                                    options=CENTERX,
                                    pos=[0.0, 0])

        self.middle_bar = bgui.Frame(parent=self, name="middle_bar",
                                    size=[main_bar_width, 1 - (2 * thin_bar_height)],
                                    options=CENTERED)

        self.message_text = bgui.Label(parent=self,
                                       name="notification_label",
                                       text=message.upper(),
                                       options=CENTERED,
                                       pos=[0.0, 0.0],
                                       font=bge.logic.expandPath("//themes/agency.ttf"),
                                       pt_size=font_size, color=[0.4, 0.4, 0.4, 1])

        self.upper_bar.colors = [[0, 0, 0, 1]] * 4
        self.lower_bar.colors = [[0, 0, 0, 1]] * 4
        self.middle_bar.colors = [[0.93, 0.93, 0.93, 0.75]] * 4

        self.initial_position = self._base_pos[:]
        self.initial_height = self._base_size[:]

        # Record of components
        components = [self.upper_bar, self.middle_bar,
                           self.lower_bar, self.message_text]
        component_colors = [copy.deepcopy(self._get_color(c))
                                 for c in components]
        self.components = dict(zip(components, component_colors))

        # Add alive timer
        status_timer = ManualTimer(target_value=self.alive_time)
        status_timer.on_target = self.alive_expired
        self.add_timer(status_timer, "status")

        self.on_death = None
        self.is_visible = None

    def scroll_message(self, timer):
        message = self.message
        index = min(round(timer.progress * len(message)), len(message) - self.message_length)
        self.message_text.text = message[index: index + self.message_length]

    def _set_color(self, component, color):
        try:
            component.colors[:] = color
        except AttributeError:
            component.color[:] = color[0]

    def _get_color(self, component):
        try:
            return component.colors
        except AttributeError:
            return [component.color]

    def _interpolate(self, target, factor):
        factor = min(max(0.0, factor), 1.0)
        i_x, i_y = self.initial_position

        diff_x = target[0] - i_x
        diff_y = target[1] - i_y

        return [i_x + (diff_x * factor), i_y + (diff_y * factor)]

    def fade_opacity(self, interval=0.5, out=True):
        fade_timer = ManualTimer(target_value=interval)

        def update_fade():
            alpha = (1 - fade_timer.progress) if out else fade_timer.progress
            for (component, colour) in self.components.items():
                new_colour = [[corner[0], corner[1], corner[2], alpha * corner[3]]
                              for corner in colour]
                self._set_color(component, new_colour)

        fade_timer.on_update = update_fade
        self.add_timer(fade_timer, "fade_{}".format("out" if out else "in"))

    def alive_expired(self):
        # Update position
        target = [self.initial_position[0] + 0.2, self.initial_position[1]]

        self.move_to(target, self.fade_time, note_position=False)
        self.fade_opacity(self.fade_time, out=True)

        death_timer = ManualTimer(target_value=self.fade_time,
                                  on_target=self.on_cleanup)
        self.add_timer(death_timer, "death_timer")

    def move_to(self, target, interval=0.5, note_position=True):
        '''Moves notification to a new position'''
        move_timer = ManualTimer(target_value=interval)

        def update_position():
            factor = move_timer.progress
            self.position = self._interpolate(target, factor)

        target_cb = lambda: setattr(self, "initial_position", self._base_pos[:])

        move_timer.on_update = update_position
        if note_position:
            #move_timer.on_target = target_cb
            target_cb()

        self.add_timer(move_timer, "mover")

    def on_cleanup(self):
        '''Remove any circular references'''
        _on_death = self.on_death
        del self.on_death
        del self.is_visible
        if callable(_on_death):
            _on_death()

    def update(self, delta_time):
        '''Update all active timers'''
        if callable(self.is_visible):
            _visible = self.visible
            self.visible = self.is_visible()
            if self.visible and not _visible:
                self.fade_opacity(self.fade_time, out=False)

        super().update(delta_time)


class UIPanel(TimerMixins, Panel):

    def __init__(self, system):
        super().__init__(system, "UIPanel")

        self._notifications = []
        self._free_slot = []

        self.start_position = [1 - Notification.default_size[0],
                               1 - Notification.default_size[1]]
        self.entry_padding = 0.02
        self.panel_padding = 0.01

        # Main UI
        self.dark_grey = [0.1, 0.1, 0.1, 1]
        self.light_grey = [0.3, 0.3, 0.3, 1]
        self.faded_white = [1, 1, 1, 0.6]
        self.error_red = [1, 0.05, 0.05, 1]
        self.font_size = 32

        main_size = [0.2, 0.8]
        main_pos = [1 - main_size[0] - self.panel_padding,
              1 - self.panel_padding - main_size[1]]

        self.notifications = bgui.Frame(parent=self, name="NotificationsPanel",
                                        size=main_size[:], pos=main_pos[:])
        lg = [0.3, 0.3, 0.3, 0.3]
        self.notifications.colors = [lg] * 4

        self.weapons_box = bgui.Frame(self, "weapons", size=[main_size[0], 0.25],
                                      pos=[main_pos[0], 0.025])

        self.icon_box = bgui.Frame(self.weapons_box, "icons", size=[1.0, 0.5],
                                   pos=[0.0, 0.5])
        self.stats_box = bgui.Frame(self.weapons_box, "stats", size=[1.0, 0.5],
                                    pos=[0.0, 0.0])

        self.weapon_icon = bgui.Image(self.icon_box, "icon", "",
                                      size=[0.1, 1.0], aspect=314 / 143,
                                      pos=[0.0, 0.0], options=CENTERED)

        bar_size = [1.0, 0.35]
        bar_margin = 0.025
        bar_pos = [max(1 - bar_size[0] - bar_margin, 0),  0.25]

        self.icon_bar = bgui.Frame(self.icon_box, "icon_bar", size=bar_size[:],
                                   pos=bar_pos[:])

        self.icon_shadow = bgui.Image(self.icon_bar, "icon_shadow",
                                      "ui/checkers_border.tga",
                                    size=[1.6, 1.6], aspect=1.0,
                                    pos=[0.8, 0], options=CENTERY)

        self.icon_back = bgui.Frame(self.icon_shadow, "icon_back",
                                    size=[0.8, 0.8], aspect=1.0, options=CENTERED)

        self.icon_middle = bgui.Frame(self.icon_back, "icon_middle",
                                    size=[0.9, 0.9], aspect=1.0,
                                    pos=[0.0, 0], options=CENTERED)
        self.icon_theme = bgui.Frame(self.icon_middle, "icon_theme",
                                    size=[1.0, 1.0], aspect=1.0,
                                    pos=[0.0, 0], options=CENTERED)
        self.icon_checkers = bgui.Image(self.icon_middle, "icon_checkers",
                                        "ui/checkers_overlay.tga",
                                        size=[1.0, 1.0], aspect=1.0,
                                        pos=[0.0, 0.0], options=CENTERED)

        self.weapon_name = bgui.Label(self.icon_bar, "weapon_name", "The Spitter",
                                      font="ui/agency.ttf", pt_size=self.font_size,
                                      shadow=True, shadow_color=self.light_grey,
                                      options=CENTERY, pos=[0.05, 0.0],
                                      color=self.dark_grey)

        self.rounds_info = bgui.Frame(self.stats_box, "clips_info",
                                      pos=[0.0, 0.7], size=[0.6, 0.35])
        self.clips_info = bgui.Frame(self.stats_box, "rounds_info",
                                     pos=[0.0, 0.2], size=[0.6, 0.35])
        self.grenades_info = bgui.Frame(self.stats_box, "grenades_info",
                                        pos=[0.6, 0.2], size=[0.35, 0.85])

        self.frag_img = bgui.Image(self.grenades_info, "frag_img",
                                   "ui/frag.tga", pos=[0.0, 0.0],
                                     size=[1, 0.9], aspect=41 / 92,
                                     options=CENTERY)
        self.flashbang_img = bgui.Image(self.grenades_info, "flashbang_img",
                                        "ui/flashbang.tga", pos=[0.5, 0.0],
                                     size=[1, 0.9], aspect=41 / 92,
                                     options=CENTERY)

        self.frag_info = bgui.Frame(self.frag_img, "frag_info", size=[0.6, 0.35],
                                   aspect=1, pos=[0.0, 0.0], options=CENTERED)
        self.frag_box = bgui.Frame(self.frag_info, "frag_box", size=[1, 1],
                                   pos=[0.0, 0.0], options=CENTERED)

        self.frag_label = bgui.Label(self.frag_box, "frag_label", "4",
                                      font="ui/agency.ttf",
                                      pt_size=self.font_size,
                                      options=CENTERED, pos=[0.05, 0.0],
                                      color=self.dark_grey)

        self.flashbang_info = bgui.Frame(self.flashbang_img, "flashbang_info",
                                        size=[0.6, 0.35], aspect=1,
                                        pos=[0.0, 0.0], options=CENTERED)

        self.flashbang_box = bgui.Frame(self.flashbang_info, "flashbang_box", size=[1, 1],
                                   pos=[0.0, 0.0], options=CENTERED)

        self.flashbang_label = bgui.Label(self.flashbang_box,
                                          "flashbang_label", "4",
                                      font="ui/agency.ttf",
                                      pt_size=self.font_size,
                                      options=CENTERED, pos=[0.05, 0.0],
                                      color=self.dark_grey)

        self.rounds_img = bgui.Image(self.rounds_info, "rounds_img",
                                     "ui/info_box.tga", pos=[0.0, 0.0],
                                     size=[1, 1], aspect=1.0, options=CENTERY)
        self.clips_img = bgui.Image(self.clips_info, "clips_img",
                                    "ui/info_box.tga", pos=[0.0, 0.0],
                                     size=[1, 1], aspect=1.0, options=CENTERY)

        self.rounds_box = bgui.Frame(self.rounds_info, "rounds_box",
                                     size=[0.6, 1.0], pos=[0.3, 0.0],
                                     options=CENTERY)
        self.clips_box = bgui.Frame(self.clips_info, "clips_box",
                                    size=[0.6, 1.0], pos=[0.3, 0.0],
                                    options=CENTERY)

        self.rounds_label = bgui.Label(self.rounds_box, "rounds_label",
                                       "ROUNDS", font="ui/agency.ttf",
                                      pt_size=self.font_size,
                                      options=CENTERY, pos=[0.05, 0.0],
                                      color=self.dark_grey)

        self.clips_label = bgui.Label(self.clips_box, "clips_label", "CLIPS",
                                      font="ui/agency.ttf",
                                      pt_size=self.font_size, options=CENTERY,
                                      pos=[0.05, 0.0], color=self.dark_grey)

        self.rounds_value = bgui.Label(self.rounds_img, "rounds_value", "100",
                                      font="ui/agency.ttf",
                                      pt_size=self.font_size, options=CENTERED,
                                      pos=[0.05, 0.0], color=self.dark_grey)

        self.clips_value = bgui.Label(self.clips_img, "clips_value", "4",
                                      font="ui/agency.ttf",
                                      pt_size=self.font_size, options=CENTERED,
                                      pos=[0.05, 0.0], color=self.dark_grey)

        self.icon_back.colors = [self.dark_grey] * 4
        self.icon_middle.colors = [self.light_grey] * 4
        self.rounds_box.colors = [self.faded_white] * 4
        self.clips_box.colors = [self.faded_white] * 4
        self.flashbang_info.colors = [self.faded_white] * 4
        self.frag_info.colors = [self.faded_white] * 4
        self.frag_box.colors = [self.faded_white] * 4
        self.flashbang_box.colors = [self.faded_white] * 4

        self.icon_bar.colors = [self.faded_white] * 4

        self.visible = False

        self.entries = {"ammo": (self.rounds_info, self.rounds_value),
                         "clips": (self.clips_info, self.clips_value),
                         "frags": (self.frag_box, self.frag_label),
                         "flashbangs": (self.flashbang_box, self.flashbang_label)}
        self.handled_concerns = {}

    @UIUpdateSignal.global_listener
    def update_entry(self, name, value):
        field, value_field = self.entries[name]
        value_field.text = str(value)

    def create_glow_animation(self, entry):
        glow = ManualTimer(1, repeat=True)
        glow.on_update = partial(self.fading_animation, entry, glow)
        self.add_timer(glow, "glow")
        return glow

    @property
    def theme_colour(self):
        return self.icon_theme.colors[0]

    @theme_colour.setter
    def theme_colour(self, value):
        self.icon_theme.colors = make_gradient(value, 1/3)

    @ConnectionSuccessSignal.global_listener
    def on_connect(self, target):
        self.visible = True

    @UIWeaponChangedSignal.global_listener
    def weapon_changed(self, weapon):
        self.weapon_name.text = weapon.__class__.__name__
        self.weapon_icon.update_image(weapon.icon_path)
        self.theme_colour = weapon.theme_colour

    def fading_animation(self, entry, timer):
        err = (self.error_red[0], self.error_red[1],
               self.error_red[2], 1 - timer.progress)
        entry.colors = [err] * 4

    def update(self, delta_time):
        for notification in self._notifications[:]:
            if notification.name in self.notifications._children:
                notification.update(delta_time)

        # Handle sliding up when deleting notifications
        y_shift = Notification.default_size[1] + self.entry_padding
        for index, notification in enumerate(self._notifications):
            intended_y = self.start_position[1] - (index * y_shift)
            position_x, position_y = notification.initial_position

            if (position_y == intended_y):
                continue

            notification.move_to([self.start_position[0], intended_y])

        # Create any alert timers
        for name, (field, label) in self.entries.items():
            if label.text == "0":
                if not name in self.handled_concerns:
                    BroadcastMessage.invoke("Ran out of {}!".format(name), alive_time=10)
                    self.handled_concerns[name] = self.create_glow_animation(
                                                                         field)

        # Check for handled timers
        handled = []
        for name, timer in self.handled_concerns.items():
            field, label = self.entries[name]

            if label.text != "0":
                timer.stop()
                handled.append(name)

        # Remove handled UI timers
        for handled_name in handled:
            self.handled_concerns.pop(handled_name)

        super().update(delta_time)

    @BroadcastMessage.global_listener
    def add_notification(self, message, alive_time=5.0):
        if self._notifications:
            position = self._notifications[-1].initial_position
            position = [position[0], position[1] -
                        self._notifications[-1].initial_height[1]]

        else:
            position = self.start_position[:]

        # Apply padding
        position[1] -= self.entry_padding

        notification = Notification(self.notifications, message, pos=position,
                                    alive_time=alive_time, font_size=self.font_size)
        notification.visible = False

        self._notifications.append(notification)
        notification.on_death = lambda: self.delete_notification(notification)
        notification.is_visible = lambda: bool(notification.position[1] >
                                               self.notifications.position[1])
        return notification

    def delete_notification(self, notification):
        self._notifications.remove(notification)
        self.notifications._remove_widget(notification)


class BGESystem(System):

    def __init__(self):
        super().__init__()

        self.connect_panel = ConnectPanel(self)
        self.ui_panel = UIPanel(self)

    @ConnectionSuccessSignal.global_listener
    def invoke(self, *args, **kwargs):
        ConsoleMessage.invoke("Connected to server", alive_time=4)
