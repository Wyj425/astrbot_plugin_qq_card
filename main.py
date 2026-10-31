import asyncio
from astrbot.api.star import Star,Context,register
from astrbot.api import AstrBotConfig
from .signing import sign_card
from .music import NativeMusic

@register('astrbot_plugin_qq_card','Wyj425','独立QQ图文卡片签名服务；供社区精选和点歌调用','1.0.0')
class QQCard(Star):
    api_version=1
    def __init__(self,context:Context,config:AstrBotConfig):
        super().__init__(context);self.config=config;self.slots=asyncio.Semaphore(2);self.music=NativeMusic()
    async def native_music(self,song):
        if not self.config.get('enabled',True):raise RuntimeError('QQ卡片签名已关闭')
        return await self.music.native(song)
    async def sign(self,news):
        if not self.config.get('enabled',True):raise RuntimeError('QQ卡片签名已关闭')
        # Validate before transmitting fields to the configured signing provider.
        from urllib.parse import urlsplit
        for key in ('jumpUrl','preview'):
            value=urlsplit(news.get(key,''))
            if value.scheme not in ('http','https') or not value.hostname or value.username or value.password:
                raise ValueError('卡片目标或封面URL不正确')
        async with self.slots:
            return await sign_card(news,self.config.get('ark_signing_token',''))
    async def initialize(self):
        self.context.register_web_api('/astrbot_plugin_qq_card/status',self.status,['GET'],'卡片签名配置状态')
    async def status(self):
        return {'status':'ok','data':{'api_version':1,'configured':bool(self.config.get('ark_signing_token')),
            'provider':'咸鱼 API qq-shareArk','note':'签名后不得改写；消息编号不等于手机确认送达'}}
