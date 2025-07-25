import asyncio
import socket
from datetime import datetime
from urllib.parse import urlparse

import aiohttp

from app import BOT, Message, bot


@bot.add_cmd(cmd="ping")
async def ping_bot(bot: BOT, message: Message):
    """
    CMD: PING
    INFO: Check bot response time or ping a URL/domain.
    USAGE: .ping [url/domain]
    """
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if args:
        # Ping URL or domain
        target = args[0]
        response = await message.reply(f"WARNING <b>Pinging {target}...</b>")
        
        try:
            # Check if it's a URL or domain
            if not target.startswith(('http://', 'https://')):
                if '.' in target:
                    # Treat as domain
                    await ping_domain(response, target)
                else:
                    await response.edit(f"ERROR <b>Invalid target:</b> <code>{target}</code>\n<i>Use: .ping google.com or .ping https://google.com</i>")
            else:
                # Treat as URL
                await ping_url(response, target)
                
        except Exception as e:
            await response.edit(f"ERROR <b>Ping failed:</b>\n<code>{str(e)}</code>")
    else:
        # Bot ping
        start = datetime.now()
        resp: Message = await message.reply("WARNING <b>Checking bot ping...</b>")
        end = (datetime.now() - start).microseconds / 1000
        
        if end < 100:
            status = "SUCCESS"
        elif end < 500:
            status = "WARNING"
        else:
            status = "ERROR"
        
        await resp.edit(f"{status} <b>Bot Ping:</b> <code>{end:.2f} ms</code>")


async def ping_url(response: Message, url: str):
    """Ping a URL and measure response time"""
    start = datetime.now()
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                end = (datetime.now() - start).total_seconds() * 1000
                status_code = resp.status
                
                if 200 <= status_code < 300:
                    status = "SUCCESS"
                elif 300 <= status_code < 400:
                    status = "WARNING"
                else:
                    status = "ERROR"
                
                domain = urlparse(url).netloc
                await response.edit(
                    f"{status} <b>URL Ping</b>\n\n"
                    f"<b>Target:</b> <code>{domain}</code>\n"
                    f"<b>Status:</b> <code>{status_code}</code>\n"
                    f"<b>Response Time:</b> <code>{end:.2f} ms</code>"
                )
                
    except asyncio.TimeoutError:
        await response.edit(f"ERROR <b>Timeout:</b> <code>{url}</code>\n<i>Request took longer than 10 seconds</i>")
    except Exception as e:
        await response.edit(f"ERROR <b>Failed to ping URL:</b>\n<code>{str(e)}</code>")


async def ping_domain(response: Message, domain: str):
    """Ping a domain using socket connection"""
    start = datetime.now()
    
    try:
        # Try to resolve domain and connect
        loop = asyncio.get_event_loop()
        
        def sync_ping():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            try:
                result = sock.connect_ex((domain, 80))
                sock.close()
                return result == 0
            except:
                sock.close()
                return False
        
        result = await loop.run_in_executor(None, sync_ping)
        end = (datetime.now() - start).total_seconds() * 1000
        
        if result:
            status = "SUCCESS"
            msg = "Domain is reachable"
        else:
            status = "ERROR"
            msg = "Domain is unreachable"
        
        await response.edit(
            f"{status} <b>Domain Ping</b>\n\n"
            f"<b>Target:</b> <code>{domain}</code>\n"
            f"<b>Status:</b> <code>{msg}</code>\n"
            f"<b>Response Time:</b> <code>{end:.2f} ms</code>"
        )
        
    except Exception as e:
        await response.edit(f"ERROR <b>Failed to ping domain:</b>\n<code>{str(e)}</code>")
            f"{status} {emoji} <b>Domain Ping</b>\n\n"
            f"<b>Target:</b> <code>{domain}</code>\n"
            f"<b>Status:</b> <code>{msg}</code>\n"
            f"<b>Response Time:</b> <code>{end:.2f} ms</code>"
        )
        
    except Exception as e:
        await response.edit(f"ERROR 🔴 <b>Failed to ping domain:</b>\n<code>{str(e)}</code>")
