import json

import aiohttp

from aiohttp import web
from gidgethub import aiohttp as gh_aiohttp
from gidgethub import routing, sansio

import settings

from . import jwt

router = routing.Router()
routes = web.RouteTableDef()


@router.register("pull_request", action="opened")
async def pr_opened_event(event, gh, *args, **kwargs):
    author = event.data["pull_request"]["user"]["login"]
    await gh.post(
        event.data["pull_request"]["comments_url"],
        data={
            "body": f"Thank you for contributing to IdleRPG, @{author}! Please wait a while until a Developee reviews your contribution.\nA CI build has started. If it fails, please fix your code and it'll automatically retry.\n\nI am a bot. *Beep boop*"
        },
    )
    await gh.post(event.data["pull_request"]["labels_url"], data=["needs review"])


@router.register("issues", action="opened")
async def issue_opened_event(event, gh, *args, **kwargs):
    url = event.data["issue"]["comments_url"]
    author = event.data["issue"]["user"]["login"]
    data = event.data["issue"]["body"]

    if "bug" in data.lower():
        message = f"Thanks for the bug report @{author}! Adrian (@Gelbpunkt) is very busy, he will check back to you soon.\nI am a bot. *Beep boop*"
        labels = ["bug", "needs review"]
    elif "feature request" in data.lower():
        message = f"Hello, @{author}! Many people submit great ideas for the bot and therefore, not all of them can be worked on at once. I will set the priority to low until @Gelbpunkt can review it manually. Cheers!\nI am a bot. *Beep boop*"
        labels = ["enhancement", "Priority: Low"]
    else:
        message = f"Welcome to GitHub, @{author}! I could not detect any template that you used in the issue. This is necessary for easy grouping and labeling. Please go to https://github.com/Gelbpunkt/IdleRPG/issues/new/choose and resubmit it.\nI am a bot. *Beep boop*"
        labels = ["invalid"]
    await gh.post(url, data={"body": message})
    await gh.post(event.data["issue"]["labels_url"], data=labels)


@routes.post("/")
async def main(request):
    body = await request.read()
    loaded = json.loads(body)
    user = loaded["repository"]["owner"]["login"]
    if loaded["repository"]["full_name"] not in settings.listen_to:
        return

    event = sansio.Event.from_http(
        request.headers, body, secret=settings.gh_hook_secret
    )

    async with aiohttp.ClientSession() as session:
        j = jwt.get_jwt(settings.gh_app_id)
        gh = gh_aiohttp.GitHubAPI(session, user)
        installation = await jwt.get_installation(gh, j, user)
        access_token = await jwt.get_installation_access_token(
            gh, jwt=j, installation_id=installation["id"]
        )

        gh = gh_aiohttp.GitHubAPI(
            session, "Gelbpunkt/mystic-warrior", oauth_token=access_token["token"]
        )

        # call the appropriate callback for the event
        await router.dispatch(event, gh)

    # return a "Success"
    return web.Response(status=200)


def run(port):
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=port)
