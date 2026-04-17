# Controllers

## [get_route](src/rest_lib/controller/get_route.py)

**Exemplo:**
```
from rest_lib.controller.get_route import GetRoute

@GetRoute(
    url=GET_ROUTE,
    http_method='GET',
    dto_class=ClienteDTO,
    entity_class=ClienteEntity
)
```

## [list_route](src/rest_lib/controller/list_route.py)
***Exemplo:***
```
from rest_lib.controller.list_route import ListRoute

@ListRoute(
    url=LIST_ROUTE,
    http_method='GET',
    dto_class=ClienteDTO,
    entity_class=ClienteEntity
)
```

## [post_route](src/rest_lib/controller/post_route.py)
***Exemplo:***
```
from rest_lib.controller.post_route import PostRoute

@PostRoute(
    url=LIST_POST_ROUTE,
    http_method='POST',
    dto_class=ClienteDTO,
    entity_class=ClienteEntity,
    dto_response_class=ClientePostReturnDTO
)
```

## [put_route](src/rest_lib/controller/put_route.py)
***Exemplo:***
```
from rest_lib.controller.put_route import PutRoute

@PutRoute(
    url=GET_PUT_ROUTE,
    http_method='PUT',
    dto_class=ClienteDTO,
    entity_class=ClienteEntity
)
```

## [delete_route](src/rest_lib/controller/delete_route.py)
***Exemplo:***
```
from rest_lib.controller.delete_route import DeleteRoute

@DeleteRoute(
    url=GET_DELETE_ROUTE,
    http_method="DELETE",
    dto_class=ClienteDTO,
    entity_class=ClienteEntity,
    injector_factory=InjectorFactoryMultibanco,
    service_name="cliente_service",
)
```
