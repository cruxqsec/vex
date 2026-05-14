import httpx

from vex_client.process import INACTIVE_PROCESS


async def check_health_retries(retries: int, host: str, port: int) -> bool:
    """Calls the /health endpoint n times to check if vex-cli is running."""
    while retries > 0:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://{host}:{port}/health")
                if response.status_code == 200:
                    return True
        except httpx.TimeoutException:
            retries -= 1
            continue
        except httpx.RequestError:
            retries -= 1
            continue

    return False


async def check_health_pid(host: str, port: int) -> int:
    """Gets the pid from the /health endpoint. Return INACTIVE_PROCESS constant if it fails."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/health")
            if response.status_code == 200:
                json_response = response.json()
                return json_response["pid"]
    except httpx.TimeoutException:
        pass
    except httpx.RequestError:
        pass

    return INACTIVE_PROCESS
