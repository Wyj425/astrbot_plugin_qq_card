"""Obtain a new SDK share card; never modify a signed card's content."""
import json
from urllib.parse import urlsplit

import aiohttp

ENDPOINT = 'https://apii.xianyuw.cn/api/v1/qq-shareArk'


class CardSigningError(RuntimeError):
    pass


def validate_response(response, url):
    if not isinstance(response, dict) or response.get('code') not in (0, 200):
        raise CardSigningError('signing service did not return success')
    value = response.get('data')
    raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    try:
        card = json.loads(raw)
        if card.get('app') not in ('com.tencent.tuwen.lua', 'com.tencent.structmsg'):
            raise ValueError('unexpected card app')
        news = card['meta']['news']
        if news.get('jumpUrl') != url:
            raise ValueError('returned destination does not match requested URL')
        if not news.get('title') or not news.get('preview') or not card.get('config', {}).get('token'):
            raise ValueError('incomplete signed card')
        if urlsplit(news['preview']).scheme not in ('https', 'http'):
            raise ValueError('invalid cover')
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        raise CardSigningError('signing service returned invalid card fields') from e
    # Wrapper fields stay local. Only the exact raw response card is transmitted.
    return {'_signed_json': raw, 'app': card['app']}


async def sign_card(news, token):
    if not token or not token.strip():
        raise CardSigningError('configure the share-card signing token first')
    parameters = {'key': token.strip(), 'title': news['title'], 'desc': news['desc'] or '点击查看原文',
                  'preview': news['preview'], 'url': news['jumpUrl'], 'prompt': news['tag']}
    # aiohttp does not log the request URL by default. Never log parameters or exceptions
    # containing request URLs: this service accepts the account token in the query string.
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as client:
            async with client.get(ENDPOINT, params=parameters, allow_redirects=False) as response:
                if response.status != 200:
                    raise CardSigningError('signing HTTP status ' + str(response.status))
                chunks, size = [], 0
                async for chunk in response.content.iter_chunked(8192):
                    size += len(chunk)
                    if size > 1024 * 1024:
                        raise CardSigningError('signing response too large')
                    chunks.append(chunk)
                body = b''.join(chunks)
        result = json.loads(body)
    except CardSigningError:
        raise
    except Exception:
        raise CardSigningError('signing service request or decoding failed') from None
    return validate_response(result, news['jumpUrl'])
