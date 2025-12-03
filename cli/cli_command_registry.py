"""
CLI Command Registry
====================

Central registry for CLI command handlers using Command pattern.

Save location: tools/cli/cli_command_registry.py

Responsibilities:
- Register command handlers
- Route commands to appropriate handlers
- Provide command discovery
- Manage command metadata

Design Pattern: Command Pattern + Registry Pattern

Dependencies:
- typing (type hints)
- abc (abstract base classes)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import argparse


class CommandHandler(ABC):
    """
    Abstract base class for command handlers.
    
    All command handlers must implement the execute method.
    """
    
    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute the command with parsed arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        pass
    
    @abstractmethod
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """
        Setup command-specific arguments.
        
        Args:
            parser: ArgumentParser to configure
        """
        pass
    
    @property
    def name(self) -> str:
        """
        Get command name.
        
        Returns:
            Command name string
        """
        return self.__class__.__name__.lower().replace('handler', '')
    
    @property
    def help_text(self) -> str:
        """
        Get command help text.
        
        Returns:
            Help text string
        """
        return f"{self.name} operations"


class CommandRegistry:
    """
    Central registry for CLI commands.
    
    Manages command handlers and routes command execution.
    Uses Command pattern to decouple CLI from command implementations.
    
    Attributes:
        _handlers: Dictionary mapping command names to handlers
    """
    
    def __init__(self):
        """Initialize empty command registry."""
        self._handlers: Dict[str, CommandHandler] = {}
    
    def register(self, command_name: str, handler: CommandHandler) -> None:
        """
        Register a command handler.
        
        Args:
            command_name: Name of the command
            handler: Handler instance for this command
            
        Raises:
            ValueError: If command name already registered
        """
        if command_name in self._handlers:
            raise ValueError(f"Command '{command_name}' already registered")
        
        self._handlers[command_name] = handler
    
    def get_handler(self, command_name: str) -> Optional[CommandHandler]:
        """
        Get handler for a command.
        
        Args:
            command_name: Name of the command
            
        Returns:
            Handler instance or None if not found
        """
        return self._handlers.get(command_name)
    
    def has_command(self, command_name: str) -> bool:
        """
        Check if command is registered.
        
        Args:
            command_name: Name of the command
            
        Returns:
            True if command is registered, False otherwise
        """
        return command_name in self._handlers
    
    def get_all_commands(self) -> Dict[str, CommandHandler]:
        """
        Get all registered commands.
        
        Returns:
            Dictionary of command names to handlers
        """
        return self._handlers.copy()
    
    def execute_command(
        self,
        command_name: str,
        args: argparse.Namespace
    ) -> int:
        """
        Execute a registered command.
        
        Args:
            command_name: Name of the command to execute
            args: Parsed arguments
            
        Returns:
            Exit code from command handler
            
        Raises:
            ValueError: If command not found
        """
        handler = self.get_handler(command_name)
        
        if handler is None:
            raise ValueError(f"Unknown command: {command_name}")
        
        return handler.execute(args)


__all__ = ['CommandHandler', 'CommandRegistry']