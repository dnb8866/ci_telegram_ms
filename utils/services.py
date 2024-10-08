import httpx

import config
from utils.models import User, UserRequest, UserRequestSchema


class Requests:

    @staticmethod
    async def _send_get(endpoint: str):
        async with httpx.AsyncClient() as client:
            return await client.get(endpoint)

    @staticmethod
    async def _send_post(endpoint: str, data):
        async with httpx.AsyncClient() as client:
            return await client.post(endpoint, data=data)

    @staticmethod
    async def _send_put(endpoint: str, data):
        async with httpx.AsyncClient() as client:
            return await client.put(endpoint, data=data)

    @staticmethod
    async def _send_delete(endpoint: str):
        async with httpx.AsyncClient() as client:
            return await client.delete(endpoint)

    @staticmethod
    async def get_user(user_id: int) -> User:
        response = await Requests._send_get(f'{config.REPO_HOST}/users/{user_id}')
        if response.status_code not in (200, 307):
            response.raise_for_status()
        return User(**response.json())

    @staticmethod
    async def get_all_users() -> dict[int: User]:
        response = await Requests._send_get(f'{config.REPO_HOST}/users/')
        if response.status_code not in (200, 307):
            response.raise_for_status()
        return {user_id: User(**res) for user_id, res in response.json().items()}

    @staticmethod
    async def add_user(user: User) -> User:
        response = await Requests._send_post(f'{config.REPO_HOST}/users/', user.json())
        if response.status_code != 201:
            response.raise_for_status()
        return User(**response.json())

    @staticmethod
    async def delete_user(user_id: int):
        response = await Requests._send_delete(f'{config.REPO_HOST}/users/{user_id}')
        if response.status_code != 204:
            response.raise_for_status()
        return response

    @staticmethod
    async def update_user(user: User) -> User:
        response = await Requests._send_put(f'{config.REPO_HOST}/users/{user.user_id}', user.json())
        if response.status_code not in (200, 307):
            response.raise_for_status()
        return User(**response.json())

    @staticmethod
    async def get_request(request_id: int) -> UserRequest:
        response = await Requests._send_get(f'{config.REPO_HOST}/requests/{request_id}')
        if response.status_code not in (200, 307):
            response.raise_for_status()
        return UserRequest(**response.json())

    @staticmethod
    async def get_all_requests_for_user(user_id: int) -> list[UserRequest]:
        response = await Requests._send_get(f'{config.REPO_HOST}/requests/users/{user_id}')
        if response.status_code not in (200, 307):
            response.raise_for_status()
        return [UserRequest(**res) for res in response.json()] if response.json() else None

    @staticmethod
    async def get_all_users_for_request(request_id: int):
        response = await Requests._send_get(f"{config.REPO_HOST}/users/requests/{request_id}")
        if response.status_code not in (200, 307):
            response.raise_for_status()
        return [user_id for user_id in response.json()] if response.json() else None

    @staticmethod
    async def add_request(user_id: int, request: UserRequestSchema):
        response = await Requests._send_post(f"{config.REPO_HOST}/requests/?user_id={user_id}", request.json())
        if response.status_code != 201:
            response.raise_for_status()
        return UserRequest(**response.json()[str(user_id)])

    @staticmethod
    async def delete_request(user_id: int, request_id: int):
        response = await Requests._send_delete(f"{config.REPO_HOST}/requests/{user_id}?request_id={request_id}")
        if response.status_code != 204:
            response.raise_for_status()
        return response

    @staticmethod
    async def get_current_price(ticker: str):
        response = await Requests._send_get(f'{config.BINANCE_HOST}/prices/{ticker}')
        return response.json()

    @staticmethod
    async def get_tickers():
        response = await Requests._send_get(f'{config.BINANCE_HOST}/tickers')
        return response.json()
