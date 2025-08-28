#!/usr/bin/env python3
"""
Fix handler configuration test to properly mock instance attributes.
"""

def fix_handler_config_test():
    handler_file = "/home/cezar/automagik/automagik-omni/tests/test_unified_handlers.py"
    
    with open(handler_file, 'r') as f:
        content = f.read()
    
    # Fix the configuration test to properly mock instance attributes
    old_config_setup = """for config in invalid_configs:
            instance = MagicMock()
            instance.config = config
            
            with pytest.raises(Exception):
                handler._get_unified_evolution_client(instance)"""
    
    new_config_setup = """for config in invalid_configs:
            instance = MagicMock()
            # Mock instance attributes for the validation logic
            instance.evolution_url = config.get("evolution_api_url")  
            instance.evolution_key = config.get("evolution_api_key")
            
            with pytest.raises(Exception):
                handler._get_unified_evolution_client(instance)"""
    
    content = content.replace(old_config_setup, new_config_setup)
    
    with open(handler_file, 'w') as f:
        f.write(content)
        
    print("✓ Fixed TestHandlerConfiguration test mocking")

if __name__ == "__main__":
    fix_handler_config_test()