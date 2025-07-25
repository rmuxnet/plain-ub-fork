import platform
import psutil
import os
import socket
import subprocess
import re
import shutil
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
    
    # Helper function to run getprop safely
    def getprop(prop):
        try:
            result = subprocess.run(['getprop', prop], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass
        return None
    
    # Helper function to read files safely
    def read_file(filepath):
        try:
            with open(filepath, 'r') as f:
                return f.read().strip()
        except (FileNotFoundError, PermissionError):
            return None
    
    try:
        # Get Android version and device info using getprop
        android_info['version'] = getprop('ro.build.version.release')
        android_info['model'] = getprop('ro.product.model')
        android_info['brand'] = getprop('ro.product.manufacturer')
        android_info['api_level'] = getprop('ro.build.version.sdk')
        android_info['build_id'] = getprop('ro.build.id')
        
        # Fallback to build.prop if getprop fails
        if not any(android_info.values()) and os.path.exists('/system/build.prop'):
            build_prop = read_file('/system/build.prop')
            if build_prop:
                for line in build_prop.split('\n'):
                    if line.startswith('ro.build.version.release='):
                        android_info['version'] = line.split('=')[1].strip()
                    elif line.startswith('ro.product.model='):
                        android_info['model'] = line.split('=')[1].strip()
                    elif line.startswith('ro.product.manufacturer='):
                        android_info['brand'] = line.split('=')[1].strip()
                    elif line.startswith('ro.build.version.sdk='):
                        android_info['api_level'] = line.split('=')[1].strip()
    except:
        pass
    
    # Get Termux version if available
    if 'TERMUX_VERSION' in os.environ:
        android_info['termux_version'] = os.environ['TERMUX_VERSION']
    
    return android_info


def get_cpu_info():
    """Get detailed CPU information, especially for Android."""
    try:
        cpuinfo = None
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        
        if not cpuinfo:
            return platform.processor() or "Unknown CPU", psutil.cpu_count(logical=True)
        
        lines = cpuinfo.split('\n')
        cpu_model = None
        cores = 0
        max_freq = None
        
        for line in lines:
            if line.startswith('model name'):
                cpu_model = line.split(':', 1)[1].strip()
            elif line.startswith('Hardware'):
                if not cpu_model:  # Android devices often use Hardware instead
                    cpu_model = line.split(':', 1)[1].strip()
            elif line.startswith('Processor'):
                if not cpu_model:
                    cpu_model = line.split(':', 1)[1].strip()
            elif line.startswith('processor'):
                cores += 1
        
        # Try to get max frequency
        freq_file = '/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq'
        if os.path.exists(freq_file):
            try:
                with open(freq_file, 'r') as f:
                    freq_data = f.read().strip()
                    if freq_data.isdigit():
                        freq_khz = int(freq_data)
                        max_freq = freq_khz / 1000000  # Convert to GHz
            except:
                pass
        
        cpu_model = cpu_model or "Unknown CPU"
        cores = cores or psutil.cpu_count(logical=True)
        
        return cpu_model, cores, max_freq
        
    except:
        return platform.processor() or "Unknown CPU", psutil.cpu_count(logical=True), None


def get_enhanced_gpu_info():
    """GPU detection for Android devices."""
    if not is_android():
        return None
    
    gpu_options = [
        'ro.hardware.vulkan',
        'ro.hardware.egl',
        'ro.hardware.gralloc',
        'ro.board.platform',
        'ro.chipname'
    ]
    
    for prop in gpu_options:
        try:
            result = subprocess.run(['getprop', prop], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                gpu_value = result.stdout.strip()
                if gpu_value and gpu_value != 'unknown' and len(gpu_value) > 2:
                    return gpu_value
        except:
            continue
    
    # Try to get GPU info from /proc/cpuinfo
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'gpu' in cpuinfo.lower() or 'mali' in cpuinfo.lower() or 'adreno' in cpuinfo.lower():
                for line in cpuinfo.split('\n'):
                    if any(keyword in line.lower() for keyword in ['gpu', 'mali', 'adreno']):
                        return "Integrated GPU"
    except:
        pass
    
    return None


def get_enhanced_memory_info():
    """Get enhanced memory information with percentages."""
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        
        mem_data = {}
        for line in meminfo.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                # Extract number (in kB)
                num_match = re.search(r'(\d+)', value)
                if num_match:
                    mem_data[key.strip()] = int(num_match.group(1))
        
        # Memory calculations
        mem_total = mem_data.get('MemTotal', 0)
        mem_available = mem_data.get('MemAvailable', 0)
        
        if not mem_available:
            mem_free = mem_data.get('MemFree', 0)
            mem_cached = mem_data.get('Cached', 0)
            mem_buffers = mem_data.get('Buffers', 0)
            mem_available = mem_free + mem_cached + mem_buffers
        
        mem_used = mem_total - mem_available
        mem_percent = int((mem_used * 100) / mem_total) if mem_total > 0 else 0
        
        # Swap calculations
        swap_total = mem_data.get('SwapTotal', 0)
        swap_free = mem_data.get('SwapFree', 0)
        swap_used = swap_total - swap_free if swap_total > 0 else 0
        swap_percent = int((swap_used * 100) / swap_total) if swap_total > 0 else 0
        
        return {
            'mem_used': mem_used // 1024,  # Convert to MB
            'mem_total': mem_total // 1024,
            'mem_percent': mem_percent,
            'swap_used': swap_used // 1024 if swap_total > 0 else None,
            'swap_total': swap_total // 1024 if swap_total > 0 else None,
            'swap_percent': swap_percent if swap_total > 0 else None
        }
    except:
        # Fallback to psutil
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'mem_used': memory.used // (1024 * 1024),
            'mem_total': memory.total // (1024 * 1024),
            'mem_percent': int(memory.percent),
            'swap_used': swap.used // (1024 * 1024) if swap.total > 0 else None,
            'swap_total': swap.total // (1024 * 1024) if swap.total > 0 else None,
            'swap_percent': int(swap.percent) if swap.total > 0 else None
        }


def get_shell_info():
    """Get shell information with version."""
    shell_path = os.getenv('SHELL', 'Unknown')
    if shell_path == 'Unknown':
        return shell_path
    
    shell_name = os.path.basename(shell_path)
    
    # Try to get version
    try:
        if shell_name == 'bash':
            result = subprocess.run(['bash', '--version'], 
                                  capture_output=True, text=True, timeout=5)
        elif shell_name == 'zsh':
            result = subprocess.run(['zsh', '--version'], 
                                  capture_output=True, text=True, timeout=5)
        elif shell_name == 'fish':
            result = subprocess.run(['fish', '--version'], 
                                  capture_output=True, text=True, timeout=5)
        else:
            return shell_name
        
        if result.returncode == 0 and result.stdout:
            # Extract version number using regex
            version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', result.stdout)
            if version_match:
                version = version_match.group(1)
                return f"{shell_name} {version}"
    except:
        pass
    
    return shell_name


def get_disk_usage():
    """Get disk usage information for multiple storage locations."""
    disk_info = []
    
    try:
        # Check if we can use df command
        if shutil.which('df'):
            # Root filesystem
            try:
                result = subprocess.run(['df', '-h', '/'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        parts = lines[1].split()
                        if len(parts) >= 6:
                            used, total = parts[2], parts[1]
                            disk_info.append(f"Disk (/): {used} / {total}")
            except:
                pass
            
            # Android external storage
            if is_android():
                storage_paths = [
                    '/storage/emulated/0',
                    '/sdcard',
                    '/storage/self/primary'
                ]
                
                for storage_path in storage_paths:
                    if os.path.exists(storage_path):
                        try:
                            result = subprocess.run(['df', '-h', storage_path], 
                                                  capture_output=True, text=True, timeout=5)
                            if result.returncode == 0:
                                lines = result.stdout.strip().split('\n')
                                if len(lines) > 1:
                                    parts = lines[1].split()
                                    if len(parts) >= 6:
                                        used, total = parts[2], parts[1]
                                        storage_name = storage_path.split('/')[-1] or 'storage'
                                        disk_info.append(f"Disk ({storage_name}): {used} / {total}")
                                        break  # Only add one external storage entry
                        except:
                            continue
        
        # Fallback to psutil if df command failed
        if not disk_info:
            if is_android():
                # Try multiple Android paths
                paths_to_check = ['/data', '/storage/emulated/0', '/']
            else:
                paths_to_check = ['/']
            
            for path in paths_to_check:
                try:
                    if os.path.exists(path) and os.access(path, os.R_OK):
                        disk_usage = psutil.disk_usage(path)
                        used_gb = disk_usage.used // (1024**3)
                        total_gb = disk_usage.total // (1024**3)
                        path_name = path.replace('/storage/emulated/0', 'storage').replace('/', 'root')
                        disk_info.append(f"Disk ({path_name}): {used_gb}GB / {total_gb}GB")
                        if len(disk_info) >= 2:  # Limit to 2 disk entries
                            break
                except:
                    continue
    except:
        pass
    
    return disk_info


def get_network_info():
    """Get network interface information."""
    interfaces = []
    
    if shutil.which('ip'):
        try:
            result = subprocess.run(['ip', 'addr', 'show'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                current_interface = None
                for line in result.stdout.split('\n'):
                    # Parse interface name
                    if line and not line.startswith(' '):
                        parts = line.split()
                        if len(parts) >= 2:
                            current_interface = parts[1].rstrip(':')
                    
                    # Parse IP addresses
                    elif 'inet ' in line and '127.0.0.1' not in line:
                        parts = line.strip().split()
                        for i, part in enumerate(parts):
                            if part == 'inet' and i + 1 < len(parts):
                                ip_addr = parts[i + 1].split('/')[0]
                                if current_interface and ip_addr:
                                    interfaces.append(f"{current_interface}: {ip_addr}")
                                break
        except:
            pass
    
    return interfaces


def get_locale_info():
    """Get system locale information."""
    return os.environ.get('LANG', 'Unknown')


def get_packages_count():
    """Get package count with better detection."""
    try:
        # Try dpkg first
        result = subprocess.run(['dpkg', '-l'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            count = 0
            for line in result.stdout.split('\n'):
                if line.startswith('ii'):
                    count += 1
            if count > 0:
                return count, "dpkg"
    except:
        pass
    
    try:
        # Try pkg for Termux
        result = subprocess.run(['pkg', 'list-installed'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = [line for line in result.stdout.strip().split('\n') if line.strip()]
            if lines:
                return len(lines), "pkg"
    except:
        pass
    
    try:
        # Alternative: count in dpkg status file
        dpkg_status = '/data/data/com.termux/files/usr/var/lib/dpkg/status'
        if os.path.exists(dpkg_status):
            with open(dpkg_status, 'r') as f:
                count = f.read().count('Package:')
                if count > 0:
                    return count, "dpkg"
    except:
        pass
    
    return 0, "unknown"


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
        cpu_model, cpu_count, cpu_freq = get_cpu_info()
        cpu_freq_str = f" @ {cpu_freq:.2f}GHz" if cpu_freq else ""
        
        # GPU Information
        gpu_info = get_enhanced_gpu_info()
        
        # Memory Information
        mem_info = get_enhanced_memory_info()
        
        # Network Information
        network_interfaces = get_network_info()
        
        # Disk Information
        disk_info = get_disk_usage()
        
        # Locale
        locale = get_locale_info()
        
        # Shell Information
        shell_info = get_shell_info()
        
        # Uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        uptime_str = format_uptime(uptime)
        
        # Kernel
        if is_android_system:
            kernel = f"Linux {platform.release()}"
        else:
            kernel = platform.release() if system == "Linux" else f"{system} {release}"
        
        # Terminal detection
        terminal = "Unknown"
        if is_android_system:
            if 'TERMUX_VERSION' in os.environ:
                termux_ver = os.environ.get('TERMUX_VERSION', '')
                terminal = f"Termux {termux_ver}" if termux_ver else "Termux"
            else:
                terminal = "Android Terminal"
        elif os.environ.get('TERM_PROGRAM'):
            terminal = os.environ['TERM_PROGRAM']
        else:
            term = os.environ.get('TERM', '')
            if term and term != 'Unknown':
                terminal = term
        
        # Package count
        packages, package_manager = get_packages_count()
        
        # Format the output similar to neofetch
        ascii_art = get_ascii_art(system)
        
        info_lines = [
            f"{username}@{hostname}",
            "-" * (len(username) + len(hostname) + 1),
        ]
        
        # OS line with device info for Android
        if is_android_system and (android_info.get('brand') or android_info.get('model')):
            device_info = f"{android_info.get('brand', '')} {android_info.get('model', '')}".strip()
            info_lines.append(f"Host: {device_info}")
            info_lines.append(f"OS: {system} {release} {machine}")
        else:
            info_lines.append(f"OS: {system} {release} {machine}")
        
        info_lines.extend([
            f"Kernel: {kernel}",
            f"Uptime: {uptime_str}",
        ])
        
        if packages > 0:
            info_lines.append(f"Packages: {packages} ({package_manager})")
        
        info_lines.append(f"Shell: {shell_info}")
        
        if terminal != "Unknown":
            info_lines.append(f"Terminal: {terminal}")
        
        info_lines.append(f"CPU: {cpu_model} ({cpu_count}){cpu_freq_str}")
        
        if gpu_info:
            info_lines.append(f"GPU: {gpu_info}")
        
        # Memory with percentage
        info_lines.append(f"Memory: {mem_info['mem_used']}MiB / {mem_info['mem_total']}MiB ({mem_info['mem_percent']}%)")
        
        # Swap if available
        if mem_info['swap_total']:
            info_lines.append(f"Swap: {mem_info['swap_used']}MiB / {mem_info['swap_total']}MiB ({mem_info['swap_percent']}%)")
        
        # Disk information
        for disk_entry in disk_info:
            info_lines.append(disk_entry)
        
        # Network interfaces (limit to 2)
        for interface in network_interfaces[:2]:
            info_lines.append(f"Local IP: {interface}")
        
        # Locale
        if locale != "Unknown":
            info_lines.append(f"Locale: {locale}")
        
        # Android-specific info
        if is_android_system:
            if android_info.get('api_level'):
                info_lines.append(f"API Level: {android_info['api_level']}")
            if android_info.get('build_id'):
                info_lines.append(f"Build: {android_info['build_id']}")
        
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
