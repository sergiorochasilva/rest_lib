from rest_lib.controller.route_base import RouteBase


class CommandRoute:
    func: callable = None
    rest_lib_route = None

    def __init__(
        self,
        func: callable,
        rest_lib_route: RouteBase,
    ) -> None:
        self.func: callable = func
        self.rest_lib_route = rest_lib_route


class CommandRouter:
    # Padrão singleton
    _instance: "CommandRouter" = None

    def __init__(self) -> None:
        self._functions: dict[str, CommandRoute] = {}

    @staticmethod
    def get_instance():
        if CommandRouter._instance is None:
            CommandRouter._instance = CommandRouter()

        return CommandRouter._instance

    # Métodos de instância
    def register(self, func_name: str, func: callable, rest_lib_route: RouteBase):
        if func_name in self._functions:
            raise Exception(
                f"A função {func_name} já foi registrada anteriormente, e não pode haver registro duplicado."
            )

        self._functions[func_name] = CommandRoute(func, rest_lib_route)

    def get(self, func_name: str) -> CommandRoute:
        if func_name not in self._functions:
            raise Exception(f"Função {func_name} não registrada.")

        return self._functions[func_name]
