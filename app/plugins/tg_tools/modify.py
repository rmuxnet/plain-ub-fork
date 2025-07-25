import os
from pathlib import Path

from app import BOT, Message, bot


@bot.add_cmd(cmd="modify")
async def modify_plugin(bot: BOT, message: Message):
    """
    CMD: MODIFY
    INFO: Create, pull, or update plugins directly from chat.
    USAGE: .modify <action> <category/plugin.py> [content]
    """
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not args:
        help_text = (
            "WARNING <b>Plugin Modifier Usage:</b>\n\n"
            "<b>Actions:</b>\n"
            "• <code>.modify create misc/test.py</code> - Create new plugin\n"
            "• <code>.modify pull misc/test.py</code> - Get existing plugin\n"
            "• <code>.modify update misc/test.py</code> - Update plugin (reply to code)\n\n"
            "<i>For create/update: reply to a message with code or send code after command</i>"
        )
        await message.reply(help_text)
        return
    
    action = args[0].lower()
    
    if action == "create":
        await handle_create(message, args[1:])
    elif action == "pull":
        await handle_pull(message, args[1:])
    elif action == "update":
        await handle_update(message, args[1:])
    else:
        await message.reply("ERROR <b>Invalid action!</b>\n<i>Use: create, pull, or update</i>")


async def handle_create(message: Message, args):
    """Handle plugin creation"""
    if not args:
        await message.reply("ERROR <b>Usage:</b> <code>.modify create category/plugin.py</code>")
        return
    
    plugin_path = args[0]
    if '/' not in plugin_path or not plugin_path.endswith('.py'):
        await message.reply("ERROR <b>Invalid format!</b>\n<i>Use: category/plugin.py</i>")
        return
    
    response = await message.reply("WARNING <b>Creating plugin...</b>")
    
    try:
        # Get plugin content from reply or generate template
        plugin_code = await get_plugin_content(message, plugin_path)
        
        # Save plugin
        await save_plugin(plugin_path, plugin_code)
        
        await response.edit(f"SUCCESS <b>Plugin created:</b> <code>{plugin_path}</code>")
        
    except Exception as e:
        await response.edit(f"ERROR <b>Failed to create plugin:</b>\n<code>{str(e)}</code>")


async def handle_pull(message: Message, args):
    """Handle pulling existing plugin"""
    if not args:
        await message.reply("ERROR <b>Usage:</b> <code>.modify pull category/plugin.py</code>")
        return
    
    plugin_path = args[0]
    response = await message.reply("WARNING <b>Pulling plugin...</b>")
    
    try:
        # Get plugins directory
        plugins_dir = Path(__file__).parent.parent
        file_path = plugins_dir / plugin_path
        
        if not file_path.exists():
            await response.edit(f"ERROR <b>Plugin not found:</b> <code>{plugin_path}</code>")
            return
        
        # Read plugin content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Send as file if too long, otherwise as message
        if len(content) > 4000:
            with open(file_path, 'rb') as f:
                await message.reply_document(
                    document=f,
                    caption=f"SUCCESS <b>Plugin:</b> <code>{plugin_path}</code>",
                    file_name=file_path.name
                )
            await response.delete()
        else:
            await response.edit(
                f"SUCCESS <b>Plugin:</b> <code>{plugin_path}</code>\n\n"
                f"<pre><code class='python'>{content}</code></pre>"
            )
        
    except Exception as e:
        await response.edit(f"ERROR <b>Failed to pull plugin:</b>\n<code>{str(e)}</code>")


async def handle_update(message: Message, args):
    """Handle plugin update"""
    if not args:
        await message.reply("ERROR <b>Usage:</b> <code>.modify update category/plugin.py</code> (reply to code)")
        return
    
    plugin_path = args[0]
    response = await message.reply("WARNING <b>Updating plugin...</b>")
    
    try:
        # Get new plugin content
        new_content = await get_plugin_content(message, plugin_path, require_content=True)
        
        if not new_content:
            await response.edit("ERROR <b>No code found!</b>\n<i>Reply to a message with code or send code after command</i>")
            return
        
        # Update plugin
        await save_plugin(plugin_path, new_content)
        
        await response.edit(f"SUCCESS <b>Plugin updated:</b> <code>{plugin_path}</code>")
        
    except Exception as e:
        await response.edit(f"ERROR <b>Failed to update plugin:</b>\n<code>{str(e)}</code>")


async def get_plugin_content(message: Message, plugin_path: str, require_content: bool = False):
    """Get plugin content from reply, document, or generate template"""
    
    # Check for replied message with code
    if message.reply_to_message:
        if message.reply_to_message.text:
            return message.reply_to_message.text
        elif message.reply_to_message.document:
            # Download and read document
            file_path = await message.reply_to_message.download()
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            os.remove(file_path)
            return content
    
    # Check for code in current message (after command)
    text_parts = message.text.split('\n', 1)
    if len(text_parts) > 1:
        return text_parts[1]
    
    # If updating and no content found, return None
    if require_content:
        return None
    
    # Generate template for new plugin
    plugin_name = Path(plugin_path).stem
    cmd_name = plugin_name.replace('_', '')
    
    template = f'''from app import BOT, Message, bot


@bot.add_cmd(cmd="{cmd_name}")
async def {plugin_name}(bot: BOT, message: Message):
    """
    CMD: {cmd_name.upper()}
    INFO: Description of your plugin.
    USAGE: .{cmd_name}
    """
    await message.reply("SUCCESS <b>Hello from {plugin_name}!</b>")
'''
    
    return template


async def save_plugin(plugin_path: str, content: str):
    """Save plugin to file system"""
    # Get plugins directory
    plugins_dir = Path(__file__).parent.parent
    file_path = plugins_dir / plugin_path
    
    # Create directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write content to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
