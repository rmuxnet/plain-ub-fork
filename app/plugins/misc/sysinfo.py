import platform
import psutil
import os
import socket
import subprocess
from datetime import datetime, timedelta
from sys import version_info

from pyrogram import __version__ as pyro_version
from pyrogram import filters
from pyrogram.raw.types.messages import BotResults
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ReplyParameters,
)
from ub_core.version import __version__ as core_version

from app import BOT, Config, Message, bot

PY_VERSION = f"{version_info.major}.{version_info.minor}.{version_info.micro}"


def is_android():
    """Check if running on Android/Termux."""
    return (
        os.path.exists('/system/build.prop') or 
        os.path.exists('/data/data/com.termux') or
        'TERMUX_VERSION' in os.environ or
        'ANDROID_ROOT' in os.environ
    )


def get_android_info():
    """Get Android-specific information."""
    android_info = {}
    
    try:
        # Get Android version from build.prop
        if os.path.exists('/system/build.prop'):
            with open('/system/build.prop', 'r') as f:
                for line in f:
                    if line.startswith('ro.build.version.release='):
                        android_info['version'] = line.split('=')[1].strip()
                    elif line.startswith('ro.product.model='):
                        android_info['model'] = line.split('=')[1].strip()
                    elif line.startswith('ro.product.brand='):
                        android_info['brand'] = line.split('=')[1].strip()
                    elif line.startswith('ro.build.version.sdk='):
                        android_info['api_level'] = line.split('=')[1].strip()
    except:
        pass
    
    # Get Termux version if available
    if 'TERMUX_VERSION' in os.environ:
        android_info['termux_version'] = os.environ['TERMUX_VERSION']
    
    # Try to get device info from getprop command
    try:
        result = subprocess.run(['getprop', 'ro.product.model'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            android_info['model'] = result.stdout.strip()
    except:
        pass
    
    try:
        result = subprocess.run(['getprop', 'ro.build.version.release'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            android_info['version'] = result.stdout.strip()
    except:
        pass
    
    return android_info


@bot.add_cmd(cmd="sysinfo")
async def system_info(bot: BOT, message: Message):
    # Inline System Info if Dual Mode
    if bot.is_user and getattr(bot, "has_bot", False):
        inline_result: BotResults = await bot.get_inline_bot_results(
            bot=bot.bot.me.username, query="inline_sysinfo"
        )
        await bot.send_inline_bot_result(
            chat_id=message.chat.id,
            result_id=inline_result.results[0].id,
            query_id=inline_result.query_id,
        )
        return

    system_text = await get_system_info_text()
    
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"<pre>{system_text}</pre>",
        reply_parameters=ReplyParameters(message_id=message.reply_id or message.id),
    )


_bot = getattr(bot, "bot", bot)
if _bot.is_bot:

    @_bot.on_inline_query(filters=filters.regex("^inline_sysinfo$"), group=2)
    async def return_inline_sysinfo_results(client: BOT, inline_query: InlineQuery):
        system_text = await get_system_info_text()
        
        result = InlineQueryResultArticle(
            title="System Information",
            description="Send system information",
            input_message_content=InputTextMessageContent(
                message_text=f"<pre>{system_text}</pre>",
                parse_mode="HTML"
            ),
        )

        await inline_query.answer(results=[result], cache_time=60)


async def get_system_info_text() -> str:
    try:
        # Basic system info
        hostname = socket.gethostname()
        username = os.getenv('USER') or os.getenv('USERNAME') or 'unknown'
        
        # Check if Android
        is_android_system = is_android()
        android_info = get_android_info() if is_android_system else {}
        
        # OS Information
        system = platform.system()
        release = platform.release()
        version = platform.version()
        machine = platform.machine()
        
        # Override for Android
        if is_android_system:
            system = "Android"
            if android_info.get('version'):
                release = android_info['version']
            if android_info.get('api_level'):
                release += f" (API {android_info['api_level']})"
        
        # CPU Information
        cpu_info = platform.processor() or "Unknown CPU"
        if is_android_system:
            # Try to get more detailed CPU info on Android
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('Hardware'):
                            cpu_info = line.split(':')[1].strip()
                            break
                        elif line.startswith('model name'):
                            cpu_info = line.split(':')[1].strip()
                            break
            except:
                pass
        
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_freq_str = f"@ {cpu_freq.current/1000:.1f}GHz" if cpu_freq else ""
        
        # Memory Information
        memory = psutil.virtual_memory()
        memory_used = memory.used // (1024 * 1024)  # MB
        memory_total = memory.total // (1024 * 1024)  # MB
        
        # Uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        uptime_str = format_uptime(uptime)
        
        # Kernel
        if is_android_system:
            kernel = platform.release()
        else:
            kernel = platform.release() if system == "Linux" else f"{system} {release}"
        
        # Shell
        shell = os.getenv('SHELL', 'Unknown')
        if shell != 'Unknown':
            shell = os.path.basename(shell)
        
        # Terminal detection for Android
        terminal = "Unknown"
        if is_android_system:
            if 'TERMUX_VERSION' in os.environ:
                terminal = f"Termux {os.environ.get('TERMUX_VERSION', '')}"
            else:
                terminal = "Android Terminal"
        
        # Disk usage
        try:
            if is_android_system:
                # For Android, check /data partition if accessible, otherwise /
                disk_path = '/data' if os.path.exists('/data') and os.access('/data', os.R_OK) else '/'
            else:
                disk_path = '/'
            disk_usage = psutil.disk_usage(disk_path)
            disk_used = disk_usage.used // (1024**3)  # GB
            disk_total = disk_usage.total // (1024**3)  # GB
        except:
            disk_used = disk_total = 0
        
        # Package count for Android/Termux
        packages = 0
        package_manager = "Unknown"
        if is_android_system:
            try:
                # Count Termux packages
                result = subprocess.run(['pkg', 'list-installed'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    packages = len(result.stdout.strip().split('\n'))
                    package_manager = "pkg"
            except:
                try:
                    # Alternative: count in /data/data/com.termux/files/usr/var/lib/dpkg/status
                    dpkg_status = '/data/data/com.termux/files/usr/var/lib/dpkg/status'
                    if os.path.exists(dpkg_status):
                        with open(dpkg_status, 'r') as f:
                            packages = f.read().count('Package:')
                        package_manager = "dpkg"
                except:
                    pass
        
        # Format the output similar to neofetch
        ascii_art = get_ascii_art(system)
        
        info_lines = [
            f"{username}@{hostname}",
            "-" * (len(username) + len(hostname) + 1),
        ]
        
        # OS line with device info for Android
        if is_android_system and (android_info.get('brand') or android_info.get('model')):
            device_info = f"{android_info.get('brand', '')} {android_info.get('model', '')}".strip()
            info_lines.append(f"OS: {system} {release} on {device_info}")
        else:
            info_lines.append(f"OS: {system} {release} {machine}")
        
        info_lines.extend([
            f"Kernel: {kernel}",
            f"Uptime: {uptime_str}",
        ])
        
        if packages > 0:
            info_lines.append(f"Packages: {packages} ({package_manager})")
        
        info_lines.extend([
            f"Shell: {shell}",
        ])
        
        if is_android_system and terminal != "Unknown":
            info_lines.append(f"Terminal: {terminal}")
        
        info_lines.extend([
            f"CPU: {cpu_info} ({cpu_count}) {cpu_freq_str}",
            f"Memory: {memory_used}MiB / {memory_total}MiB",
        ])
        
        if disk_total > 0:
            info_lines.append(f"Storage: {disk_used}GB / {disk_total}GB")
        
        # Add Android-specific info
        if is_android_system and android_info.get('api_level'):
            info_lines.append(f"API Level: {android_info['api_level']}")
        
        info_lines.extend([
            f"Python: v{PY_VERSION}",
            f"Pyrogram: v{pyro_version}",
            f"Core: v{core_version}",
        ])
        
        # Combine ASCII art with info (simplified for Telegram)
        result = []
        for i, line in enumerate(info_lines):
            if i < len(ascii_art):
                result.append(f"{ascii_art[i]:<30} {line}")
            else:
                result.append(f"{'':<30} {line}")
        
        # Add remaining ASCII art lines if any
        for i in range(len(info_lines), len(ascii_art)):
            result.append(ascii_art[i])
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error gathering system information: {str(e)}"


def format_uptime(uptime: timedelta) -> str:
    """Format uptime in a human-readable way."""
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    if days > 0:
        return f"{days} days, {hours} hours, {minutes} mins"
    elif hours > 0:
        return f"{hours} hours, {minutes} mins"
    else:
        return f"{minutes} mins"


def get_ascii_art(system: str) -> list:
    """Get simple ASCII art based on the operating system."""
    if system.lower() == "android":
        return [
            "         -o          o-",
            "          +hydNNNNNdyh+",
            "       +mMMMMMMMMMMMMMMm+",
            "     /MMM+:+MMMMMMMMMMMy/+MMM/",
            "   +MMM+     +MMMMMMMMMMd     +MMM+",
            "  mMMM:       dMMMMMMMMM       :MMMs",
            " /MMM-         +MMMMMMMy         -MMM/",
            " +MMM-          sMMMMMN          -MMM+",
            "  mMMM/       /dyMMMMMMMMy/       /MMMs",
            "   sMMMMMNmmyMMMMMMMMMMMMMMMMNmmyMMMMM",
            "     +MMMMMMMMMMMMMMMMMMMMMMMMMMMMMM+",
            "       /mMMMMMMMMMMMMMMMMMMMMMMMMm/",
            "          /dMMMMMMMMMMMMMMMMMMd/",
            "             +++DMMMMMMMMMd+++",
            "                  +++DMMMM+++",
        ]
    elif system.lower() == "linux":
        return [
            "        #####",
            "       #######",
            "       ##O#O##",
            "       #######",
            "     ###########",
            "    #############",
            "   ###############",
            "   ################",
            "  #################",
        ]
    elif system.lower() == "windows":
        return [
            "        ################",
            "        ################",
            "        ################",
            "        ################",
            "        ################",
            "        ################",
            "        ################",
            "        ################",
            "        ################",
        ]
    elif system.lower() == "darwin":  # macOS
        return [
            "                    'c.",
            "                 ,xNMM.",
            "               .OMMMMo",
            "               OMMM0,",
            "     .;loddo:' loolloddol;.",
            "   cKMMMMMMMMMMNWMMMMMMMMMM0:",
            " .KMMMMMMMMMMMMMMMMMMMMMMMWd.",
            " XMMMMMMMMMMMMMMMMMMMMMMMX.",
            ";MMMMMMMMMMMMMMMMMMMMMMMM:",
            ":MMMMMMMMMMMMMMMMMMMMMMMM:",
        ]
    else:
        return [
            "   ╔══════════════════════╗",
            "   ║                      ║",
            "   ║      SYSTEM INFO     ║",
            "   ║                      ║",
            "   ╚══════════════════════╝",
            "",
            "",
            "",
            "",
        ]
