import os
from pathlib import Path

from app import BOT, Message, bot


@bot.add_cmd(cmd="plugins")
async def list_plugins(bot: BOT, message: Message):
    """
    CMD: PLUGINS
    INFO: List all available plugins organized by category.
    USAGE: .plugins
    """
    response = await message.reply("WARNING <b>Loading plugin list...</b>")
    
    try:
        # Get the plugins directory path - this file is in misc/, so go up to plugins/
        plugins_dir = Path(__file__).parent.parent
        
        if not plugins_dir.exists():
            await response.edit("ERROR <b>Plugins directory not found!</b>")
            return
        
        plugin_categories = {}
        total_plugins = 0
        
        # Scan all subdirectories
        for category_dir in plugins_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith('.'):
                category_name = category_dir.name
                plugins = []
                
                # Get all .py files in the category
                for plugin_file in category_dir.rglob("*.py"):
                    if plugin_file.name != "__init__.py":
                        # Get relative path from category dir
                        rel_path = plugin_file.relative_to(category_dir)
                        if rel_path.parent.name != category_dir.name:
                            # Handle nested directories like gemini/
                            plugin_name = f"{rel_path.parent.name}/{rel_path.stem}"
                        else:
                            plugin_name = rel_path.stem
                        plugins.append(plugin_name)
                        total_plugins += 1
                
                if plugins:
                    plugin_categories[category_name] = sorted(plugins)
        
        # Build the response message
        plugins_text = f"SUCCESS <b>Available Plugins</b>\n\n"
        
        for category, plugins in sorted(plugin_categories.items()):
            plugins_text += f"<b>{category.upper()}:</b>\n"
            for plugin in plugins:
                plugins_text += f"  • <code>{plugin}</code>\n"
            plugins_text += "\n"
        
        plugins_text += f"<b>Total:</b> {len(plugin_categories)} categories, {total_plugins} plugins\n"
        plugins_text += f"<i>Use .help [command] for specific command info</i>"
        
        await response.edit(plugins_text)
        
    except Exception as e:
        await response.edit(f"ERROR <b>Error loading plugins:</b>\n<code>{str(e)}</code>")


@bot.add_cmd(cmd="pluginfo")
async def plugin_info(bot: BOT, message: Message):
    """
    CMD: PLUGINFO
    INFO: Get detailed information about a specific plugin category.
    USAGE: .pluginfo <category>
    """
    if len(message.text.split()) < 2:
        await message.reply("WARNING <b>Usage:</b> <code>.pluginfo &lt;category&gt;</code>\n<i>Example: .pluginfo admin</i>")
        return
    
    category = message.text.split()[1].lower()
    response = await message.reply(f"WARNING <b>Getting info for category: {category}</b>")
    
    try:
        plugins_dir = Path(__file__).parent.parent / category
        
        if not plugins_dir.exists():
            await response.edit(f"ERROR <b>Category '{category}' not found!</b>")
            return
        
        plugins_info = f"SUCCESS <b>Category: {category.upper()}</b>\n\n"
        plugin_count = 0
        
        # Get all .py files with their descriptions
        for plugin_file in plugins_dir.rglob("*.py"):
            if plugin_file.name != "__init__.py":
                rel_path = plugin_file.relative_to(plugins_dir)
                if rel_path.parent.name != plugins_dir.name:
                    plugin_name = f"{rel_path.parent.name}/{rel_path.stem}"
                else:
                    plugin_name = rel_path.stem
                
                # Try to read first few lines for description
                try:
                    with open(plugin_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[:20]  # Read first 20 lines
                    
                    description = "No description available"
                    for line in lines:
                        if 'INFO:' in line and '"""' in line:
                            description = line.split('INFO:')[1].split('"""')[0].strip()
                            break
                        elif '# ' in line and any(word in line.lower() for word in ['plugin', 'module', 'command']):
                            description = line.replace('#', '').strip()
                            break
                    
                    plugins_info += f"<b>{plugin_name}:</b>\n"
                    plugins_info += f"  <i>{description}</i>\n\n"
                    plugin_count += 1
                    
                except Exception:
                    plugins_info += f"<b>{plugin_name}:</b>\n"
                    plugins_info += f"  <i>Unable to read description</i>\n\n"
                    plugin_count += 1
        
        plugins_info += f"<b>Total plugins in {category}:</b> {plugin_count}"
        
        await response.edit(plugins_info)
        
    except Exception as e:
        await response.edit(f"ERROR <b>Error getting plugin info:</b>\n<code>{str(e)}</code>")
