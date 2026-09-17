from PySide6.QtCore import QObject, Signal

from aoi_system.core.models.recipe import InspectionRecipe
from aoi_system.ui.components.role_dialog import UserRole


class MainViewModel(QObject):
    """Central view model managing application global state, permissions, and active recipe."""

    role_changed = Signal(object)  # UserRole
    recipe_changed = Signal(object)  # InspectionRecipe
    status_message = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._current_role: UserRole = UserRole.OPERATOR
        self._active_recipe: InspectionRecipe = InspectionRecipe(product_key="DEFAULT_RECIPE")

    @property
    def current_role(self) -> UserRole:
        return self._current_role

    @property
    def active_recipe(self) -> InspectionRecipe:
        return self._active_recipe

    def set_role(self, role: UserRole) -> None:
        if self._current_role != role:
            self._current_role = role
            self.role_changed.emit(role)
            self.status_message.emit(f"權限身分已切換至: {role.value}")

    def set_active_recipe(self, recipe: InspectionRecipe) -> None:
        self._active_recipe = recipe
        self.recipe_changed.emit(recipe)
        self.status_message.emit(f"已切換至配方: {recipe.product_key}")
