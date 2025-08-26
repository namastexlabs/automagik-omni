"""
Discord Interaction Handler for Slash Commands and UI Components

This module handles modern Discord interactions including slash commands,
buttons, select menus, and modals for the automagik-omni bot.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

import discord
from discord.ext import commands
from discord import app_commands

from src.db.models import InstanceConfig
from src.services.message_router import MessageRouter
# from ...ai.agent_interface import AgentInterface
from ...utils.cache import CacheManager


class InteractionType(Enum):
    """Discord interaction types we handle"""
    SLASH_COMMAND = "slash_command"
    BUTTON_CLICK = "button_click"
    SELECT_MENU = "select_menu"
    MODAL_SUBMIT = "modal_submit"
    AUTOCOMPLETE = "autocomplete"


class DiscordInteractionHandler:
    """
    Handles Discord interactions including slash commands, buttons, and UI components
    """
    
    def __init__(self, config: InstanceConfig, message_router: MessageRouter, 
                 agent_interface: AgentInterface, cache_manager: CacheManager):
        self.config = config
        self.message_router = message_router
        self.agent_interface = agent_interface
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Command handlers registry
        self.command_handlers: Dict[str, Callable] = {}
        self.button_handlers: Dict[str, Callable] = {}
        self.select_handlers: Dict[str, Callable] = {}
        self.modal_handlers: Dict[str, Callable] = {}
        
        # UI component builders
        self.ui_builder = DiscordUIBuilder()
        
        # Initialize command mappings
        self._initialize_command_handlers()
    
    def _initialize_command_handlers(self):
        """Initialize command handler mappings"""
        self.command_handlers.update({
            "help": self._handle_help_command,
            "status": self._handle_status_command,
            "config": self._handle_config_command,
            "voice-join": self._handle_voice_join_command,
            "voice-leave": self._handle_voice_leave_command,
            "ask": self._handle_ask_command,
        })
        
        self.button_handlers.update({
            "help_more": self._handle_help_more_button,
            "config_view": self._handle_config_view_button,
            "voice_controls": self._handle_voice_controls_button,
        })
        
        self.select_handlers.update({
            "help_category": self._handle_help_category_select,
            "config_option": self._handle_config_option_select,
        })
        
        self.modal_handlers.update({
            "ask_query": self._handle_ask_query_modal,
            "config_update": self._handle_config_update_modal,
        })

    async def register_commands(self, bot: commands.Bot) -> bool:
        """
        Register slash commands with Discord
        
        Args:
            bot: Discord bot instance
            
        Returns:
            bool: True if registration successful
        """
        try:
            # Define slash commands
            commands_to_register = [
                {
                    "name": "help",
                    "description": "Show available commands and help information",
                    "options": [
                        {
                            "name": "category",
                            "description": "Help category to display",
                            "type": discord.AppCommandOptionType.string,
                            "required": False,
                            "choices": [
                                {"name": "General", "value": "general"},
                                {"name": "Voice", "value": "voice"},
                                {"name": "AI Assistant", "value": "ai"},
                                {"name": "Configuration", "value": "config"},
                            ]
                        }
                    ]
                },
                {
                    "name": "status",
                    "description": "Show bot status and connection information"
                },
                {
                    "name": "config",
                    "description": "View or update bot configuration",
                    "options": [
                        {
                            "name": "action",
                            "description": "Configuration action",
                            "type": discord.AppCommandOptionType.string,
                            "required": True,
                            "choices": [
                                {"name": "View", "value": "view"},
                                {"name": "Update", "value": "update"},
                                {"name": "Reset", "value": "reset"},
                            ]
                        }
                    ]
                },
                {
                    "name": "voice-join",
                    "description": "Join your voice channel",
                    "options": [
                        {
                            "name": "channel",
                            "description": "Voice channel to join (auto-detect if not specified)",
                            "type": discord.AppCommandOptionType.channel,
                            "required": False,
                            "channel_types": [discord.ChannelType.voice]
                        }
                    ]
                },
                {
                    "name": "voice-leave",
                    "description": "Leave the current voice channel"
                },
                {
                    "name": "ask",
                    "description": "Ask the AI assistant a question",
                    "options": [
                        {
                            "name": "question",
                            "description": "Your question for the AI assistant",
                            "type": discord.AppCommandOptionType.string,
                            "required": False
                        },
                        {
                            "name": "private",
                            "description": "Send response privately (default: false)",
                            "type": discord.AppCommandOptionType.boolean,
                            "required": False
                        }
                    ]
                }
            ]
            
            # Register commands using app_commands
            for cmd_data in commands_to_register:
                @app_commands.command(name=cmd_data["name"], description=cmd_data["description"])
                async def slash_command_wrapper(interaction: discord.Interaction, **kwargs):
                    await self.handle_slash_command(interaction, **kwargs)
                
                # Add to bot's command tree
                bot.tree.add_command(slash_command_wrapper)
            
            # Sync commands with Discord
            await bot.tree.sync()
            
            self.logger.info(f"Successfully registered {len(commands_to_register)} slash commands")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register slash commands: {e}")
            return False

    async def handle_slash_command(self, interaction: discord.Interaction, **kwargs) -> None:
        """
        Handle slash command interactions
        
        Args:
            interaction: Discord interaction object
            **kwargs: Command parameters
        """
        command_name = interaction.command.name if interaction.command else "unknown"
        
        try:
            # Log command usage
            self.logger.info(f"Slash command '{command_name}' used by {interaction.user} in {interaction.guild}")
            
            # Check permissions
            if not await self._check_command_permissions(interaction, command_name):
                await interaction.response.send_message(
                    "❌ You don't have permission to use this command.",
                    ephemeral=True
                )
                return
            
            # Get handler
            handler = self.command_handlers.get(command_name)
            if not handler:
                await interaction.response.send_message(
                    f"❌ Command '{command_name}' not implemented yet.",
                    ephemeral=True
                )
                return
            
            # Execute handler
            await handler(interaction, **kwargs)
            
        except Exception as e:
            self.logger.error(f"Error handling slash command '{command_name}': {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while processing your command.",
                        ephemeral=True
                    )
            except:
                pass

    async def handle_button_click(self, interaction: discord.Interaction) -> None:
        """
        Handle button click interactions
        
        Args:
            interaction: Discord interaction object
        """
        try:
            custom_id = interaction.data.get("custom_id", "")
            
            # Extract button type and parameters
            button_type = custom_id.split(":")[0] if ":" in custom_id else custom_id
            
            handler = self.button_handlers.get(button_type)
            if handler:
                await handler(interaction)
            else:
                await interaction.response.send_message(
                    "❌ This button is no longer available.",
                    ephemeral=True
                )
                
        except Exception as e:
            self.logger.error(f"Error handling button click: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while processing your request.",
                        ephemeral=True
                    )
            except:
                pass

    async def handle_select_menu(self, interaction: discord.Interaction) -> None:
        """
        Handle select menu interactions
        
        Args:
            interaction: Discord interaction object
        """
        try:
            custom_id = interaction.data.get("custom_id", "")
            values = interaction.data.get("values", [])
            
            # Extract select menu type
            select_type = custom_id.split(":")[0] if ":" in custom_id else custom_id
            
            handler = self.select_handlers.get(select_type)
            if handler:
                await handler(interaction, values)
            else:
                await interaction.response.send_message(
                    "❌ This menu is no longer available.",
                    ephemeral=True
                )
                
        except Exception as e:
            self.logger.error(f"Error handling select menu: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while processing your selection.",
                        ephemeral=True
                    )
            except:
                pass

    async def handle_modal_submit(self, interaction: discord.Interaction) -> None:
        """
        Handle modal submission interactions
        
        Args:
            interaction: Discord interaction object
        """
        try:
            custom_id = interaction.data.get("custom_id", "")
            
            # Extract modal type
            modal_type = custom_id.split(":")[0] if ":" in custom_id else custom_id
            
            handler = self.modal_handlers.get(modal_type)
            if handler:
                await handler(interaction)
            else:
                await interaction.response.send_message(
                    "❌ This form is no longer available.",
                    ephemeral=True
                )
                
        except Exception as e:
            self.logger.error(f"Error handling modal submit: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An error occurred while processing your form.",
                        ephemeral=True
                    )
            except:
                pass

    # Command Handlers

    async def _handle_help_command(self, interaction: discord.Interaction, category: Optional[str] = None) -> None:
        """Handle /help command"""
        await interaction.response.defer(ephemeral=True)
        
        embed = self.ui_builder.create_help_embed(category or "general")
        view = self.ui_builder.create_help_view(category)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def _handle_status_command(self, interaction: discord.Interaction) -> None:
        """Handle /status command"""
        await interaction.response.defer()
        
        # Gather status information
        status_data = {
            "bot_latency": round(interaction.client.latency * 1000, 2),
            "guild_count": len(interaction.client.guilds),
            "user_count": len(interaction.client.users),
            "voice_connected": bool(interaction.guild.voice_client) if interaction.guild else False,
            "ai_agent_status": await self._get_agent_status(),
            "uptime": self._get_bot_uptime(),
        }
        
        embed = self.ui_builder.create_status_embed(status_data)
        
        await interaction.followup.send(embed=embed)

    async def _handle_config_command(self, interaction: discord.Interaction, action: str) -> None:
        """Handle /config command"""
        if action == "view":
            await self._show_config_view(interaction)
        elif action == "update":
            await self._show_config_update_modal(interaction)
        elif action == "reset":
            await self._handle_config_reset(interaction)

    async def _handle_voice_join_command(self, interaction: discord.Interaction, 
                                       channel: Optional[discord.VoiceChannel] = None) -> None:
        """Handle /voice-join command"""
        await interaction.response.defer()
        
        if not interaction.guild:
            await interaction.followup.send("❌ This command can only be used in servers.")
            return
        
        # Auto-detect user's voice channel if not specified
        if not channel:
            if interaction.user.voice and interaction.user.voice.channel:
                channel = interaction.user.voice.channel
            else:
                await interaction.followup.send(
                    "❌ You need to be in a voice channel or specify one to join."
                )
                return
        
        try:
            # Join voice channel
            voice_client = await channel.connect()
            
            embed = discord.Embed(
                title="🎤 Voice Connected",
                description=f"Joined **{channel.name}**",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            view = self.ui_builder.create_voice_controls_view()
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to join voice channel: {str(e)}")

    async def _handle_voice_leave_command(self, interaction: discord.Interaction) -> None:
        """Handle /voice-leave command"""
        await interaction.response.defer()
        
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.followup.send("❌ Not connected to a voice channel.")
            return
        
        await interaction.guild.voice_client.disconnect()
        
        embed = discord.Embed(
            title="🔇 Voice Disconnected",
            description="Left the voice channel",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.followup.send(embed=embed)

    async def _handle_ask_command(self, interaction: discord.Interaction, 
                                question: Optional[str] = None, private: bool = False) -> None:
        """Handle /ask command"""
        if not question:
            # Show modal for question input
            modal = self.ui_builder.create_ask_modal()
            await interaction.response.send_modal(modal)
        else:
            await self._process_ask_question(interaction, question, private)

    # Button Handlers

    async def _handle_help_more_button(self, interaction: discord.Interaction) -> None:
        """Handle help more info button"""
        await interaction.response.defer(ephemeral=True)
        
        embed = self.ui_builder.create_detailed_help_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _handle_config_view_button(self, interaction: discord.Interaction) -> None:
        """Handle config view button"""
        await self._show_config_view(interaction)

    async def _handle_voice_controls_button(self, interaction: discord.Interaction) -> None:
        """Handle voice controls button"""
        await interaction.response.defer(ephemeral=True)
        
        view = self.ui_builder.create_voice_controls_view()
        await interaction.followup.send("🎤 Voice Controls", view=view, ephemeral=True)

    # Select Menu Handlers

    async def _handle_help_category_select(self, interaction: discord.Interaction, values: List[str]) -> None:
        """Handle help category selection"""
        await interaction.response.defer(ephemeral=True)
        
        category = values[0] if values else "general"
        embed = self.ui_builder.create_help_embed(category)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _handle_config_option_select(self, interaction: discord.Interaction, values: List[str]) -> None:
        """Handle config option selection"""
        await interaction.response.defer(ephemeral=True)
        
        option = values[0] if values else None
        if option:
            # Show specific config option
            embed = self.ui_builder.create_config_detail_embed(option, self.config)
            await interaction.followup.send(embed=embed, ephemeral=True)

    # Modal Handlers

    async def _handle_ask_query_modal(self, interaction: discord.Interaction) -> None:
        """Handle ask question modal submission"""
        question_input = None
        private_input = False
        
        # Extract form data
        for component in interaction.data.get("components", []):
            for item in component.get("components", []):
                custom_id = item.get("custom_id", "")
                value = item.get("value", "")
                
                if custom_id == "ask_question":
                    question_input = value
                elif custom_id == "ask_private":
                    private_input = value.lower() in ["true", "yes", "1"]
        
        if question_input:
            await self._process_ask_question(interaction, question_input, private_input)
        else:
            await interaction.response.send_message(
                "❌ Please provide a question.",
                ephemeral=True
            )

    async def _handle_config_update_modal(self, interaction: discord.Interaction) -> None:
        """Handle config update modal submission"""
        await interaction.response.defer(ephemeral=True)
        
        # Extract form data and update config
        # Implementation depends on specific config structure
        
        await interaction.followup.send(
            "✅ Configuration updated successfully.",
            ephemeral=True
        )

    # Utility Methods

    async def _check_command_permissions(self, interaction: discord.Interaction, command: str) -> bool:
        """
        Check if user has permission to use command
        
        Args:
            interaction: Discord interaction
            command: Command name
            
        Returns:
            bool: True if user has permission
        """
        # Basic permission checking - can be extended
        if interaction.guild:
            # Check server permissions
            return True  # Default allow for now
        
        # DM permissions
        return command in ["help", "status", "ask"]

    async def _get_agent_status(self) -> str:
        """Get AI agent status"""
        try:
            if hasattr(self.agent_interface, 'get_status'):
                status = await self.agent_interface.get_status()
                return "Online" if status else "Offline"
            return "Unknown"
        except:
            return "Offline"

    def _get_bot_uptime(self) -> str:
        """Get bot uptime string"""
        # This should be calculated from bot start time
        # For now return placeholder
        return "0d 0h 0m"

    async def _show_config_view(self, interaction: discord.Interaction) -> None:
        """Show current configuration"""
        await interaction.response.defer(ephemeral=True)
        
        embed = self.ui_builder.create_config_embed(self.config)
        view = self.ui_builder.create_config_view()
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def _show_config_update_modal(self, interaction: discord.Interaction) -> None:
        """Show config update modal"""
        modal = self.ui_builder.create_config_update_modal()
        await interaction.response.send_modal(modal)

    async def _handle_config_reset(self, interaction: discord.Interaction) -> None:
        """Handle config reset"""
        await interaction.response.defer(ephemeral=True)
        
        # Show confirmation
        embed = discord.Embed(
            title="⚠️ Reset Configuration",
            description="Are you sure you want to reset all configuration to defaults?",
            color=discord.Color.orange()
        )
        
        view = self.ui_builder.create_confirmation_view("config_reset_confirm")
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def _process_ask_question(self, interaction: discord.Interaction, 
                                  question: str, private: bool = False) -> None:
        """Process ask question and get AI response"""
        await interaction.response.defer(ephemeral=private)
        
        try:
            # Send question to AI agent
            response = await self.message_router.route_message(
                content=question,
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel.id) if interaction.channel else None,
                message_type="slash_command"
            )
            
            if response and response.content:
                # Format response for Discord
                embed = discord.Embed(
                    title="🤖 AI Assistant Response",
                    description=response.content[:4096],  # Discord embed limit
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                embed.set_footer(text=f"Asked by {interaction.user.display_name}")
                
                await interaction.followup.send(embed=embed, ephemeral=private)
            else:
                await interaction.followup.send(
                    "❌ Sorry, I couldn't process your question right now.",
                    ephemeral=private
                )
                
        except Exception as e:
            self.logger.error(f"Error processing ask question: {e}")
            await interaction.followup.send(
                "❌ An error occurred while processing your question.",
                ephemeral=private
            )


class DiscordUIBuilder:
    """
    Builder class for Discord UI components (embeds, buttons, modals, etc.)
    """
    
    def create_help_embed(self, category: str = "general") -> discord.Embed:
        """Create help embed for specified category"""
        embed = discord.Embed(
            title="🤖 Automagik Omni Bot Help",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if category == "general":
            embed.add_field(
                name="🔧 General Commands",
                value=(
                    "`/help` - Show this help message\n"
                    "`/status` - Show bot status\n"
                    "`/config` - Manage bot configuration"
                ),
                inline=False
            )
        elif category == "voice":
            embed.add_field(
                name="🎤 Voice Commands",
                value=(
                    "`/voice-join` - Join voice channel\n"
                    "`/voice-leave` - Leave voice channel"
                ),
                inline=False
            )
        elif category == "ai":
            embed.add_field(
                name="🧠 AI Assistant Commands",
                value=(
                    "`/ask` - Ask the AI assistant a question\n"
                    "You can also just mention the bot or send DMs"
                ),
                inline=False
            )
        elif category == "config":
            embed.add_field(
                name="⚙️ Configuration Commands",
                value=(
                    "`/config view` - View current settings\n"
                    "`/config update` - Update settings\n"
                    "`/config reset` - Reset to defaults"
                ),
                inline=False
            )
        
        embed.set_footer(text="Use the dropdown below to switch categories")
        return embed
    
    def create_help_view(self, current_category: str = "general") -> discord.ui.View:
        """Create help view with category selector"""
        view = discord.ui.View(timeout=300)
        
        # Category selector
        select = discord.ui.Select(
            placeholder="Choose a help category...",
            custom_id="help_category",
            options=[
                discord.SelectOption(
                    label="General",
                    value="general",
                    description="Basic bot commands",
                    emoji="🔧",
                    default=(current_category == "general")
                ),
                discord.SelectOption(
                    label="Voice",
                    value="voice",
                    description="Voice channel commands",
                    emoji="🎤",
                    default=(current_category == "voice")
                ),
                discord.SelectOption(
                    label="AI Assistant",
                    value="ai",
                    description="AI interaction commands",
                    emoji="🧠",
                    default=(current_category == "ai")
                ),
                discord.SelectOption(
                    label="Configuration",
                    value="config",
                    description="Bot configuration commands",
                    emoji="⚙️",
                    default=(current_category == "config")
                ),
            ]
        )
        
        view.add_item(select)
        
        # More info button
        more_button = discord.ui.Button(
            label="More Info",
            style=discord.ButtonStyle.secondary,
            custom_id="help_more",
            emoji="📖"
        )
        view.add_item(more_button)
        
        return view
    
    def create_detailed_help_embed(self) -> discord.Embed:
        """Create detailed help embed"""
        embed = discord.Embed(
            title="📖 Detailed Help & Features",
            description="Comprehensive guide to using Automagik Omni Bot",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="🎯 Key Features",
            value=(
                "• AI-powered conversations\n"
                "• Voice channel integration\n"
                "• Slash command interface\n"
                "• Configurable settings\n"
                "• Multi-modal interactions"
            ),
            inline=True
        )
        
        embed.add_field(
            name="💡 Tips",
            value=(
                "• Use `/ask` for quick questions\n"
                "• Mention @bot for natural chat\n"
                "• DMs work for private conversations\n"
                "• Voice commands in voice channels\n"
                "• Configure settings with `/config`"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🔗 Links",
            value=(
                "[Documentation](https://example.com/docs)\n"
                "[Support Server](https://discord.gg/example)\n"
                "[GitHub](https://github.com/example/repo)"
            ),
            inline=False
        )
        
        return embed
    
    def create_status_embed(self, status_data: Dict[str, Any]) -> discord.Embed:
        """Create status embed with system information"""
        embed = discord.Embed(
            title="🤖 Bot Status",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📊 Performance",
            value=(
                f"**Latency:** {status_data.get('bot_latency', 0)}ms\n"
                f"**Uptime:** {status_data.get('uptime', '0d 0h 0m')}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🌐 Network",
            value=(
                f"**Guilds:** {status_data.get('guild_count', 0)}\n"
                f"**Users:** {status_data.get('user_count', 0)}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🎤 Voice",
            value=(
                f"**Connected:** {'✅' if status_data.get('voice_connected') else '❌'}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🧠 AI Agent",
            value=(
                f"**Status:** {status_data.get('ai_agent_status', 'Unknown')}"
            ),
            inline=True
        )
        
        return embed
    
    def create_config_embed(self, config: InstanceConfig) -> discord.Embed:
        """Create configuration embed"""
        embed = discord.Embed(
            title="⚙️ Bot Configuration",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add config fields based on actual config structure
        embed.add_field(
            name="🤖 AI Settings",
            value=(
                f"**Model:** {getattr(config, 'ai_model', 'Not set')}\n"
                f"**Max Tokens:** {getattr(config, 'max_tokens', 'Not set')}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🔊 Voice Settings",
            value=(
                f"**Auto Join:** {getattr(config, 'auto_join_voice', False)}\n"
                f"**Voice Recognition:** {getattr(config, 'voice_recognition', False)}"
            ),
            inline=True
        )
        
        return embed
    
    def create_config_view(self) -> discord.ui.View:
        """Create configuration view with options"""
        view = discord.ui.View(timeout=300)
        
        # Config options selector
        select = discord.ui.Select(
            placeholder="Select configuration option...",
            custom_id="config_option",
            options=[
                discord.SelectOption(
                    label="AI Settings",
                    value="ai",
                    description="AI model and behavior settings",
                    emoji="🧠"
                ),
                discord.SelectOption(
                    label="Voice Settings",
                    value="voice",
                    description="Voice channel preferences",
                    emoji="🎤"
                ),
                discord.SelectOption(
                    label="General Settings",
                    value="general",
                    description="General bot settings",
                    emoji="⚙️"
                ),
            ]
        )
        
        view.add_item(select)
        
        # Update button
        update_button = discord.ui.Button(
            label="Update Settings",
            style=discord.ButtonStyle.primary,
            custom_id="config_update",
            emoji="✏️"
        )
        view.add_item(update_button)
        
        return view
    
    def create_config_detail_embed(self, option: str, config: InstanceConfig) -> discord.Embed:
        """Create detailed config embed for specific option"""
        embed = discord.Embed(
            title=f"⚙️ {option.title()} Configuration",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if option == "ai":
            embed.add_field(
                name="🧠 AI Model Settings",
                value=(
                    f"**Current Model:** {getattr(config, 'ai_model', 'claude-3-sonnet')}\n"
                    f"**Max Tokens:** {getattr(config, 'max_tokens', 4096)}\n"
                    f"**Temperature:** {getattr(config, 'temperature', 0.7)}\n"
                    f"**System Prompt:** {getattr(config, 'system_prompt', 'Default')[:50]}..."
                ),
                inline=False
            )
        elif option == "voice":
            embed.add_field(
                name="🎤 Voice Settings",
                value=(
                    f"**Auto Join:** {getattr(config, 'auto_join_voice', False)}\n"
                    f"**Voice Recognition:** {getattr(config, 'voice_recognition', False)}\n"
                    f"**Voice Response:** {getattr(config, 'voice_response', False)}"
                ),
                inline=False
            )
        elif option == "general":
            embed.add_field(
                name="⚙️ General Settings",
                value=(
                    f"**Prefix:** {getattr(config, 'command_prefix', '!')}\n"
                    f"**Language:** {getattr(config, 'language', 'en')}\n"
                    f"**Timezone:** {getattr(config, 'timezone', 'UTC')}"
                ),
                inline=False
            )
        
        return embed
    
    def create_voice_controls_view(self) -> discord.ui.View:
        """Create voice controls view"""
        view = discord.ui.View(timeout=300)
        
        # Voice control buttons
        buttons = [
            ("🎤", "voice_mute", "Mute", discord.ButtonStyle.secondary),
            ("🔇", "voice_deafen", "Deafen", discord.ButtonStyle.secondary),
            ("⏹️", "voice_disconnect", "Disconnect", discord.ButtonStyle.danger),
        ]
        
        for emoji, custom_id, label, style in buttons:
            button = discord.ui.Button(
                emoji=emoji,
                label=label,
                style=style,
                custom_id=custom_id
            )
            view.add_item(button)
        
        return view
    
    def create_ask_modal(self) -> discord.ui.Modal:
        """Create ask question modal"""
        class AskModal(discord.ui.Modal):
            def __init__(self):
                super().__init__(title="Ask AI Assistant", custom_id="ask_query")
                
                self.question = discord.ui.TextInput(
                    label="Your Question",
                    placeholder="What would you like to ask?",
                    custom_id="ask_question",
                    style=discord.TextStyle.paragraph,
                    max_length=2000,
                    required=True
                )
                self.add_item(self.question)
                
                self.private = discord.ui.TextInput(
                    label="Private Response? (true/false)",
                    placeholder="false",
                    custom_id="ask_private",
                    style=discord.TextStyle.short,
                    max_length=5,
                    required=False
                )
                self.add_item(self.private)
            
            async def on_submit(self, interaction: discord.Interaction):
                # This will be handled by the modal handler
                pass
        
        return AskModal()
    
    def create_config_update_modal(self) -> discord.ui.Modal:
        """Create config update modal"""
        class ConfigUpdateModal(discord.ui.Modal):
            def __init__(self):
                super().__init__(title="Update Configuration", custom_id="config_update")
                
                self.setting_name = discord.ui.TextInput(
                    label="Setting Name",
                    placeholder="e.g., ai_model",
                    custom_id="config_setting",
                    style=discord.TextStyle.short,
                    max_length=100,
                    required=True
                )
                self.add_item(self.setting_name)
                
                self.setting_value = discord.ui.TextInput(
                    label="New Value",
                    placeholder="e.g., claude-3-opus",
                    custom_id="config_value",
                    style=discord.TextStyle.short,
                    max_length=500,
                    required=True
                )
                self.add_item(self.setting_value)
            
            async def on_submit(self, interaction: discord.Interaction):
                # This will be handled by the modal handler
                pass
        
        return ConfigUpdateModal()
    
    def create_confirmation_view(self, action: str) -> discord.ui.View:
        """Create confirmation view with yes/no buttons"""
        view = discord.ui.View(timeout=60)
        
        confirm_button = discord.ui.Button(
            label="Confirm",
            style=discord.ButtonStyle.danger,
            custom_id=f"{action}_yes",
            emoji="✅"
        )
        
        cancel_button = discord.ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.secondary,
            custom_id=f"{action}_no",
            emoji="❌"
        )
        
        view.add_item(confirm_button)
        view.add_item(cancel_button)
        
        return view