import logging
from tkinter import ttk

from modlunky2.config import Config
from modlunky2.ui.levels.vanilla_levels.variables.dependencies_tree import (
    DependenciesTree,
)
from modlunky2.ui.levels.vanilla_levels.variables.level_dependencies import (
    LevelDependencies,
)

logger = logging.getLogger(__name__)


class VariablesTab(ttk.Frame):
    def __init__(
        self,
        parent,
        modlunky_config: Config,
        lvls_path,
        extracts_path,
        request_save,
        on_conflicts_resolved,
        *args,
        **kwargs
    ):
        super().__init__(parent, *args, **kwargs)
        self.modlunky_config = modlunky_config

        self.lvls_path = lvls_path
        self.extracts_path = extracts_path

        self.current_level_name = None

        self.request_save = request_save
        self.on_conflicts_resolved = on_conflicts_resolved

        self.columnconfigure(0, weight=1)  # Column 1 = Everything Else
        self.rowconfigure(1, weight=1)  # Row 0 = List box / Label
        self.rowconfigure(2, minsize=100)  # Row 0 = List box / Label

        self.depend_order_label = ttk.Label(
            self, text="Conflicts will be shown here", font=("Arial", 15)
        )
        self.depend_order_label.grid(row=0, column=0, sticky="nwse")

        self.no_conflicts_label = ttk.Label(
            self, text="No conflicts detected!", font=("Arial", 15)
        )
        self.no_conflicts_label.grid(row=1, column=0, sticky="nwse")

        self.tree_depend = DependenciesTree(
            self, lvls_path, extracts_path, selectmode="browse"
        )  # This tree shows rules parses from the lvl file
        # self.tree_depend.bind("<Double-1>", lambda e: self.on_double_click(self.tree))
        self.tree_depend.place(x=30, y=95)
        # style = ttk.Style(self)
        self.vsb_depend = ttk.Scrollbar(
            self, orient="vertical", command=self.tree_depend.yview
        )
        self.vsb_depend.place(x=30 + 200 + 2, y=95, height=200 + 20)
        self.tree_depend.configure(yscrollcommand=self.vsb_depend.set)
        self.tree_depend.grid(row=1, column=0, sticky="nwse")
        self.vsb_depend.grid(row=1, column=0, sticky="nse")

        self.button_resolve_variables = ttk.Button(
            self, text="Resolve Conflicts", command=self.resolve_conflicts
        )
        self.button_resolve_variables.grid(row=2, column=0, sticky="nswe")

        self.button_resolve_variables.grid_remove()
        self.no_conflicts_label.grid_remove()

    def resolve_conflicts(self):
        if not self.request_save():
            return

        self.check_dependencies()
        self.tree_depend.resolve_conflicts()
        self.on_conflicts_resolved()
        self.check_dependencies()

    def clear(self):
        self.tree_depend.clear()
        self.depend_order_label.grid_remove()
        self.tree_depend.grid_remove()
        self.button_resolve_variables.grid_remove()
        self.no_conflicts_label.grid()

    def update_current_level_name(self, level_name):
        self.current_level_name = level_name
        self.clear()

    def check_dependencies(self):
        self.clear()

        logger.debug("checking dependencies..")

        levels = LevelDependencies.sister_locations_for_level(
            self.current_level_name, self.lvls_path, self.extracts_path
        )
        current_level = LevelDependencies.get_loaded_level(
            self.current_level_name, self.lvls_path, self.extracts_path
        )
        self.tree_depend.update_dependencies(levels, current_level)

        if len(self.tree_depend.get_children()) == 0:
            self.tree_depend.grid_remove()
            self.button_resolve_variables.grid_remove()
            self.no_conflicts_label.grid()
        else:
            self.tree_depend.grid()
            self.button_resolve_variables.grid()
            self.no_conflicts_label.grid_remove()
        delimiter = ", "
        if len(levels) <= 4:
            delimiter = "\n"
        self.depend_order_label["text"] = delimiter.join(
            [
                " -> ".join([level.level_name for level in level_path])
                for level_path in levels
            ]
        )
        self.depend_order_label.grid()

    def update_lvls_path(self, new_path):
        self.lvls_path = new_path
        self.tree_depend.update_lvls_path(new_path)
