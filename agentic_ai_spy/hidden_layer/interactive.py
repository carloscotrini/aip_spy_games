"""Interactive play mode for The Hidden Layer — play the game yourself in a notebook."""

from typing import Callable, Optional

from IPython.display import display, clear_output, HTML
import ipywidgets as widgets

from hidden_layer.game_world import GameWorld, CellType, FACILITY_CATALOG, SAFEHOUSE_CATALOG
from hidden_layer.operative import Operative
from hidden_layer.tools import GameTools
from hidden_layer.oracle import stub_oracle
from hidden_layer.display import (
    _render_html_grid,
    _render_health_bar,
    _render_dossier_bar,
    _render_inventory,
    _render_turn_counter,
    _action_icon,
)


class InteractiveGame:
    """Interactive game UI using ipywidgets.

    Accepts an optional ``game_factory`` callable so that the micro and
    training missions can reuse the same UI with their custom worlds/tools.

    ``game_factory()`` must return ``(operative, world, tools)``.
    If omitted, the full 8x8 game is created.
    """

    def __init__(
        self,
        oracle_fn: Optional[Callable] = None,
        game_factory: Optional[Callable] = None,
        max_turns: int = 100,
        goal_dossiers: int = 10,
        title: str = "THE HIDDEN LAYER",
    ):
        if game_factory is not None:
            self.operative, self.world, self.tools = game_factory()
        else:
            self.operative, self.world, self.tools = self._create_full_game()
        self.tools.set_oracle(oracle_fn or stub_oracle)
        self.max_turns = max_turns
        self.goal_dossiers = goal_dossiers
        self.title = title
        self.turn = 0
        self.last_action = ""
        self.last_result = f"Your mission begins! Collect {goal_dossiers} dossiers to complete the mission."
        self.game_over = False

        # -- Widgets --
        self._game_display = widgets.Output(
            layout=widgets.Layout(flex="0 0 auto"),
        )

        # Direction buttons (cross layout)
        btn_style = widgets.Layout(width="64px", height="40px")
        self._btn_north = widgets.Button(description="\u2b06 N", layout=btn_style,
                                         button_style="primary")
        self._btn_south = widgets.Button(description="\u2b07 S", layout=btn_style,
                                         button_style="primary")
        self._btn_east = widgets.Button(description="\u27a1 E", layout=btn_style,
                                        button_style="primary")
        self._btn_west = widgets.Button(description="\u2b05 W", layout=btn_style,
                                        button_style="primary")
        self._btn_north.on_click(lambda _: self._do_action("move", {"direction": "north"}))
        self._btn_south.on_click(lambda _: self._do_action("move", {"direction": "south"}))
        self._btn_east.on_click(lambda _: self._do_action("move", {"direction": "east"}))
        self._btn_west.on_click(lambda _: self._do_action("move", {"direction": "west"}))

        dpad = widgets.GridBox(
            children=[
                widgets.Label(""),       self._btn_north, widgets.Label(""),
                self._btn_west,          widgets.Label(""),  self._btn_east,
                widgets.Label(""),       self._btn_south, widgets.Label(""),
            ],
            layout=widgets.Layout(
                grid_template_columns="64px 64px 64px",
                grid_template_rows="40px 40px 40px",
                grid_gap="2px",
                justify_items="center",
                align_items="center",
            ),
        )

        # Action buttons
        act_style = widgets.Layout(width="auto", height="36px")
        self._btn_collect = widgets.Button(description="\u270b Collect", layout=act_style,
                                           button_style="success")
        self._btn_collect.on_click(lambda _: self._do_action("collect", {}))

        quick_actions = widgets.HBox(
            [self._btn_collect],
            layout=widgets.Layout(gap="4px"),
        )

        # Talk input
        self._talk_input = widgets.Text(
            placeholder='Say something... (e.g. "Do you have a job for me?")',
            layout=widgets.Layout(flex="1"),
        )
        self._btn_talk = widgets.Button(description="\U0001f4ac Talk", layout=act_style,
                                         button_style="success")
        self._btn_talk.on_click(lambda _: self._do_talk())
        self._talk_input.on_submit(lambda _: self._do_talk())
        talk_row = widgets.HBox(
            [self._talk_input, self._btn_talk],
            layout=widgets.Layout(gap="4px"),
        )

        # Fabricate input
        self._item_input = widgets.Text(
            placeholder='Item name... (e.g. "Flamethrower")',
            layout=widgets.Layout(flex="1"),
        )
        self._btn_fabricate = widgets.Button(description="\U0001f527 Fabricate", layout=act_style,
                                              button_style="warning")
        self._btn_fabricate.on_click(lambda _: self._do_fabricate())
        self._item_input.on_submit(lambda _: self._do_fabricate())
        item_row = widgets.HBox(
            [self._item_input, self._btn_fabricate],
            layout=widgets.Layout(gap="4px"),
        )

        # Assemble controls panel
        controls_title = widgets.HTML(
            '<div style="font-family:Courier New,monospace;color:#00ff41;'
            'font-weight:bold;font-size:13px;letter-spacing:1px;'
            'padding:4px 0;">CONTROLS</div>'
        )
        move_label = widgets.HTML(
            '<div style="font-family:Courier New,monospace;color:#555;'
            'font-size:11px;margin-top:6px;">MOVE</div>'
        )
        action_label = widgets.HTML(
            '<div style="font-family:Courier New,monospace;color:#555;'
            'font-size:11px;margin-top:8px;">QUICK ACTIONS</div>'
        )
        talk_label = widgets.HTML(
            '<div style="font-family:Courier New,monospace;color:#555;'
            'font-size:11px;margin-top:8px;">TALK — SPEAK TO INFORMANT / OPERATOR / ENGINEER</div>'
        )
        item_label = widgets.HTML(
            '<div style="font-family:Courier New,monospace;color:#555;'
            'font-size:11px;margin-top:8px;">FABRICATE ITEM</div>'
        )

        controls = widgets.VBox(
            [controls_title, move_label, dpad, action_label, quick_actions,
             talk_label, talk_row, item_label, item_row],
            layout=widgets.Layout(
                padding="8px",
                min_width="260px",
                border_left="2px solid #1a3a1a",
            ),
        )

        # Main layout — game display and controls side by side
        self._main = widgets.HBox(
            [self._game_display, controls],
            layout=widgets.Layout(align_items="flex-start"),
        )

    def _create_full_game(self):
        world = GameWorld()
        operative = Operative()
        tools = GameTools(operative, world)
        return operative, world, tools

    def _do_action(self, tool_name: str, args: dict):
        if self.game_over:
            return
        result = self.tools.execute(tool_name, args)
        args_str = ", ".join(f'{k}="{v}"' for k, v in args.items())
        self.last_action = f"{tool_name}({args_str})"
        self.last_result = result.message
        self.turn += 1
        self._check_game_state()
        self._render()

    def _do_talk(self):
        message = self._talk_input.value.strip()
        if not message:
            message = "Hello!"
        self._talk_input.value = ""
        self._do_action("talk", {"message": message})

    def _do_fabricate(self):
        item = self._item_input.value.strip()
        if not item:
            return
        self._item_input.value = ""
        self._do_action("fabricate", {"item": item})

    def _check_game_state(self):
        if not self.operative.is_alive:
            self.game_over = True
            self.last_result += " \U0001f480 MISSION FAILED — The operative has been neutralized!"
        elif self.operative.has_won:
            self.game_over = True
            self.last_result += " \U0001f3c6 MISSION COMPLETE — Proceed to extraction!"
        elif self.turn >= self.max_turns:
            self.game_over = True
            self.last_result += " \u23f0 TIME'S UP — Extraction window closed!"

    def _render(self):
        grid_html = _render_html_grid(self.world, self.operative)
        health_html = _render_health_bar(self.operative)
        dossier_html = _render_dossier_bar(self.operative)
        inventory_html = _render_inventory(self.operative)
        turn_html = _render_turn_counter(self.turn, self.max_turns)
        icon = _action_icon(self.last_action)

        if any(w in self.last_result.lower() for w in
               ["dossier", "mission complete", "reward", "collected", "built", "crafted", "victory", "delivered"]):
            result_color = "#00ff41"
            result_border = "#00ff41"
        elif any(w in self.last_result.lower() for w in
                 ["damage", "hurt", "fail", "cannot", "nothing", "retreat", "mission failed"]):
            result_color = "#e94560"
            result_border = "#e94560"
        else:
            result_color = "#888"
            result_border = "#333"

        row, col = self.operative.position
        cell = self.world.get_cell(row, col)
        hints = self._get_cell_hints(cell)

        game_over_banner = ""
        if self.game_over:
            if self.operative.has_won:
                game_over_banner = (
                    '<div style="text-align:center;padding:12px;background:#0a2a0a;'
                    'border:2px solid #00ff41;border-radius:8px;margin-top:8px;">'
                    '<span style="font-size:24px;color:#00ff41;text-shadow:0 0 10px #00ff41;'
                    f'font-weight:bold;">MISSION COMPLETE! {self.operative.dossiers} dossiers in {self.turn} turns</span></div>'
                )
            elif not self.operative.is_alive:
                game_over_banner = (
                    '<div style="text-align:center;padding:12px;background:#2a0a0a;'
                    'border:2px solid #e94560;border-radius:8px;margin-top:8px;">'
                    '<span style="font-size:24px;color:#e94560;text-shadow:0 0 10px #e94560;'
                    f'font-weight:bold;">MISSION FAILED after {self.turn} turns</span></div>'
                )
            else:
                game_over_banner = (
                    '<div style="text-align:center;padding:12px;background:#2a1a0a;'
                    'border:2px solid #e9a045;border-radius:8px;margin-top:8px;">'
                    '<span style="font-size:24px;color:#e9a045;'
                    f'font-weight:bold;">TIME\'S UP! {self.operative.dossiers}/{self.goal_dossiers} dossiers</span></div>'
                )

        html = f"""
<div style="font-family:'Courier New',monospace;background:linear-gradient(180deg,#0a0a0a 0%,#0a1a0a 100%);
  color:#b0b0b0;padding:0;border-radius:12px;width:480px;border:2px solid #1a3a1a;
  box-shadow:0 4px 24px rgba(0,20,0,0.6);overflow:hidden;">

  <!-- Title bar -->
  <div style="background:linear-gradient(90deg,#0a1a0a,#1a2a1a);padding:8px 16px;
    display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #00ff41;">
    <span style="color:#00ff41;font-weight:bold;font-size:16px;letter-spacing:2px;">
      \U0001f575\ufe0f {self.title}</span>
    <span style="color:#00ff41;font-size:13px;font-weight:bold;">INTERACTIVE MODE</span>
    <span style="color:#444;font-size:12px;">({row}, {col})</span>
  </div>

  <!-- Main content -->
  <div style="display:flex;gap:0;">
    <!-- Left: Map -->
    <div style="padding:12px;flex-shrink:0;">
      {grid_html}
    </div>

    <!-- Right: Stats panel -->
    <div style="padding:12px 12px 12px 0;flex:1;min-width:200px;display:flex;flex-direction:column;gap:10px;">
      {turn_html}
      <div style="background:#0a1a0a;border-radius:8px;padding:8px 10px;border:1px solid #1a3a1a;">
        <div style="color:#555;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Health</div>
        {health_html}
      </div>
      <div style="background:#0a1a0a;border-radius:8px;padding:8px 10px;border:1px solid #1a3a1a;">
        <div style="color:#555;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Dossiers</div>
        {dossier_html}
      </div>
      <div style="background:#0a1a0a;border-radius:8px;padding:8px 10px;border:1px solid #1a3a1a;flex:1;">
        <div style="color:#555;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">
          \U0001f392 Inventory</div>
        <div style="font-size:12px;">{inventory_html}</div>
      </div>
    </div>
  </div>

  <!-- Cell info + hints -->
  <div style="padding:6px 16px;background:#050805;border-top:1px solid #1a3a1a;">
    <div style="color:#7b68ee;font-size:12px;">
      <strong>Location:</strong> {cell.description or cell.cell_type.label}
      {hints}
    </div>
  </div>

  <!-- Action log -->
  <div style="border-top:1px solid #1a3a1a;padding:10px 16px;background:#050a05;">
    <div style="color:#00ff41;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Last Action</div>
    <div style="color:#00cc33;font-size:13px;margin-top:2px;">{icon} {self.last_action or '(none yet)'}</div>
    <div style="margin-top:6px;padding:8px 10px;background:#0a1a0a;border-radius:6px;
      border-left:3px solid {result_border};font-size:12px;color:{result_color};
      max-height:180px;overflow:hidden;word-wrap:break-word;overflow-wrap:break-word;">
      {self.last_result}
    </div>
    {game_over_banner}
  </div>
</div>
"""
        with self._game_display:
            clear_output(wait=True)
            display(HTML(html))

    def _get_cell_hints(self, cell) -> str:
        """Generate contextual hints about what actions are available."""
        hints = []
        if cell.items:
            hints.append('\U0001f4a1 <span style="color:#00ff41;">Items here! Use Collect</span>')
        if cell.cell_type == CellType.INFORMANT and cell.npc:
            hints.append(f'\U0001f4a1 <span style="color:#00ff41;">Talk to {cell.npc.name} via Talk</span>')
        if cell.cell_type == CellType.ROBOT:
            alive = True
            if cell.robot_name == "Cryo-Sentinel":
                alive = self.world.cryo_sentinel_alive
            elif cell.robot_name == "Evil AI Robot":
                alive = self.world.evil_ai_robot_alive
            if alive:
                hints.append(f'\U0001f4a1 <span style="color:#e94560;">{cell.robot_name} here! Move in with the correct weapon to destroy it, or you will take damage.</span>')
            else:
                hints.append('<span style="color:#444;">The robot has been destroyed.</span>')
        if cell.cell_type in (CellType.FORGE, CellType.LAB):
            facility = FACILITY_CATALOG.get(cell.facility_pos)
            if facility:
                items = list(facility.sells.keys()) + list(facility.crafts.keys())
                hints.append(f'\U0001f4a1 <span style="color:#e9a045;">Facility: {", ".join(items)}</span>')
        if cell.cell_type == CellType.SAFEHOUSE:
            hints.append('\U0001f4a1 <span style="color:#e9a045;">Safe House: Talk to the operator for delivery errands.</span>')

        if hints:
            return '<br>' + '<br>'.join(hints)
        return ''

    def play(self):
        """Start the interactive game. Call this in a notebook cell."""
        self._render()
        display(self._main)


def play_interactive(oracle_fn=None):
    """Launch an interactive full-mission game session (8x8, 10 dossiers, 100 turns).

    Usage in a notebook cell:
        from hidden_layer.interactive import play_interactive
        play_interactive()

    Or with an LLM oracle:
        play_interactive(oracle_fn=lambda npc, q, o: llm_oracle(npc, q, o, client))
    """
    game = InteractiveGame(oracle_fn=oracle_fn)
    game.play()
    return game
