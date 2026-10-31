import json,time
from urllib.parse import urlsplit
import aiohttp
def norm(text):
    import re,unicodedata
    return re.sub(r'[^\w\u4e00-\u9fff]','',unicodedata.normalize('NFKC',str(text or '')).lower())
class CardError(RuntimeError):pass
class NativeMusic:
    def __init__(self):self.native_disabled_until={}
    async def native(self, song):
        if song.platform not in ('qq', '163'): raise CardError('native_platform_unverified')
        if self.native_disabled_until.get(song.platform, 0) > time.time(): raise CardError('native_temporarily_unavailable')
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=6)) as client:
                async with client.post('https://ss.xingzhige.com/music_card/card',
                        json={'type': song.platform, 'id': song.id}, allow_redirects=False) as response:
                    body = await response.content.read(262145)
                    if response.status != 200 or len(body) > 262144: raise CardError('native_service_error')
            card = json.loads(body)
            music = card.get('meta', {}).get('music', {})
            if card.get('app') not in ('com.tencent.music.lua', 'com.tencent.structmsg') or card.get('view') != 'music':
                raise CardError('native_invalid_format')
            if norm(music.get('title')) != norm(song.title): raise CardError('native_song_mismatch')
            url = music.get('jumpUrl', '')
            host = urlsplit(url).hostname or ''
            expected = 'y.qq.com' if song.platform == 'qq' else 'music.163.com'
            if host != expected or not any(x and x in url for x in (song.mid, song.id)):
                raise CardError('native_destination_mismatch')
            if not card.get('config', {}).get('token'): raise CardError('native_unsigned')
            return body.decode('utf-8')
        except Exception:
            self.native_disabled_until[song.platform] = time.time() + 3600
            raise CardError('native_unavailable') from None
