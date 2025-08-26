"""
Validation utilities for AutomagikHive integration.
"""
from typing import Dict, Any
from src.db.models import InstanceConfig


def validate_hive_configuration(config: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate AutomagikHive configuration and return validation errors.
    
    Args:
        config: Dictionary containing AutomagikHive configuration
        
    Returns:
        Dictionary of field_name -> error_message for any validation errors
    """
    errors = {}
    
    # Check if hive is enabled and required fields are present
    if config.get('hive_enabled', False):
        required_fields = ['hive_api_url', 'hive_api_key', 'hive_agent_id']
        for field in required_fields:
            if not config.get(field):
                errors[field] = f"{field} is required when AutomagikHive is enabled"
    
    # Validate API URL format
    if config.get('hive_api_url'):
        url = config['hive_api_url'].strip()
        if not url.startswith(('http://', 'https://')):
            errors['hive_api_url'] = 'API URL must start with http:// or https://'
        elif len(url) < 10:
            errors['hive_api_url'] = 'API URL appears to be too short'
    
    # Validate API key
    if config.get('hive_api_key'):
        key = config['hive_api_key'].strip()
        if len(key) < 8:
            errors['hive_api_key'] = 'API key must be at least 8 characters long'
    
    # Validate timeout
    timeout = config.get('hive_timeout')
    if timeout is not None:
        if not isinstance(timeout, int) or timeout < 5 or timeout > 300:
            errors['hive_timeout'] = 'Timeout must be between 5 and 300 seconds'
    
    # Validate agent ID
    if config.get('hive_agent_id'):
        agent_id = config['hive_agent_id'].strip()
        if len(agent_id) > 255:
            errors['hive_agent_id'] = 'Agent ID cannot exceed 255 characters'
    
    # Validate team ID
    if config.get('hive_team_id'):
        team_id = config['hive_team_id'].strip()
        if len(team_id) > 255:
            errors['hive_team_id'] = 'Team ID cannot exceed 255 characters'
    
    return errors


def can_use_hive_routing(instance: InstanceConfig) -> bool:
    """
    Check if an instance can use AutomagikHive intelligent routing.
    
    Args:
        instance: InstanceConfig object
        
    Returns:
        True if the instance has complete AutomagikHive configuration
    """
    return (
        instance.hive_enabled and
        bool(instance.hive_api_url) and
        bool(instance.hive_api_key) and
        bool(instance.hive_agent_id)
    )


def get_hive_config_summary(instance: InstanceConfig) -> Dict[str, Any]:
    """
    Get a summary of AutomagikHive configuration for an instance.
    
    Args:
        instance: InstanceConfig object
        
    Returns:
        Dictionary with configuration summary
    """
    return {
        'enabled': instance.hive_enabled,
        'configured': can_use_hive_routing(instance),
        'has_api_url': bool(instance.hive_api_url),
        'has_api_key': bool(instance.hive_api_key),
        'has_agent_id': bool(instance.hive_agent_id),
        'has_team_id': bool(instance.hive_team_id),
        'timeout': instance.hive_timeout,
        'stream_mode': instance.hive_stream_mode
    }


def mask_sensitive_hive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive AutomagikHive data for logging.
    
    Args:
        data: Dictionary containing AutomagikHive data
        
    Returns:
        Dictionary with sensitive fields masked
    """
    masked_data = data.copy()
    
    if 'hive_api_key' in masked_data and masked_data['hive_api_key']:
        key = masked_data['hive_api_key']
        if len(key) > 8:
            masked_data['hive_api_key'] = f"{key[:4]}***{key[-4:]}"
        else:
            masked_data['hive_api_key'] = "***"
    
    return masked_data